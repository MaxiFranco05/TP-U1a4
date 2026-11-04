"""Tests bajo Strict TDD para C-16: Clientes y ventas en UoW con descuento atómico de stock, dueño y sin N+1."""

from collections.abc import AsyncGenerator
from decimal import Decimal
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
from app.core.paginacion import PaginatedResponse
from app.core.repository import BaseRepository
from app.core.unit_of_work import UnitOfWork
from app.modules.autores.models import Autor
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.libros.repository import LibroRepository, MovimientoStockRepository
from app.modules.libros.unit_of_work import LibrosUnitOfWork
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.repository import ClienteRepository, PerfilClienteRepository
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteListItem,
    ClienteRead,
    ClienteUpdate,
    PerfilClienteCreate,
    PerfilClienteRead,
)
from app.modules.clientes.service import (
    actualizar_cliente,
    crear_cliente,
    crear_perfil,
    listar_clientes,
    obtener_cliente,
    obtener_ventas_cliente,
)
from app.modules.clientes.unit_of_work import ClientesUnitOfWork
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.repository import VentaRepository
from app.modules.ventas.schemas import (
    RenglonVentaCreate,
    VentaCreate,
    VentaListItem,
    VentaRead,
)
from app.modules.ventas.service import (
    _notificar_comprobante,
    crear_venta,
)
from app.modules.ventas.unit_of_work import VentasUnitOfWork

EXPECTED_ALL_14_TABLES = {
    "editorial",
    "genero",
    "autor",
    "libro",
    "libro_autor",
    "cliente",
    "perfil_cliente",
    "venta",
    "renglon_venta",
    "usuario",
    "asignacion_rol",
    "intento_acceso",
    "evento_seguridad",
    "movimiento_stock",
}


@pytest.fixture
async def session_factory() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    """Provee la fábrica de sesiones contra PostgreSQL y limpia las tablas al finalizar."""
    settings = get_settings()
    engine = build_engine(settings.database_url, sql_echo=False)
    factory = build_session_factory(engine)
    yield factory
    async with factory() as cleanup_session:
        res = await cleanup_session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
            )
        )
        existing_tables = {row[0] for row in res.fetchall()}
        if EXPECTED_ALL_14_TABLES.issubset(existing_tables):
            await cleanup_session.execute(
                text(
                    "TRUNCATE TABLE movimiento_stock, renglon_venta, venta, asignacion_rol, "
                    "intento_acceso, evento_seguridad, perfil_cliente, cliente, libro_autor, "
                    "libro, genero, autor, editorial, usuario RESTART IDENTITY CASCADE"
                )
            )
            await cleanup_session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_task_1_1_cliente_repository_and_uow(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica ClienteRepository, PerfilClienteRepository y ClientesUnitOfWork sin commit en repositorios."""
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        commit_spy = AsyncMock(wraps=session.commit)
        flush_spy = AsyncMock(wraps=session.flush)
        monkeypatch.setattr(session, "commit", commit_spy)
        monkeypatch.setattr(session, "flush", flush_spy)

        uow = ClientesUnitOfWork(session=session)
        assert isinstance(uow, UnitOfWork)
        assert isinstance(uow.clientes, ClienteRepository)
        assert isinstance(uow.perfiles, PerfilClienteRepository)

        async with uow:
            cliente = await uow.clientes.add(
                Cliente(nombre=f"Cliente {suffix}", email=f"cli_{suffix}@example.com")
            )
            assert cliente.id is not None
            perfil = await uow.perfiles.add(
                PerfilCliente(
                    cliente_id=cliente.id,
                    telefono="+54 11 1234-5678",
                    direccion="Av. Siempre Viva 742",
                )
            )
            assert perfil.id is not None
            # flush llamado, commit AÚN NO
            assert flush_spy.call_count >= 2
            assert commit_spy.call_count == 0

        # Al salir del bloque async with, commit fue ejecutado por el UoW
        assert commit_spy.call_count == 1

        # get_con_perfil precarga perfil
        cliente_cargado = await uow.clientes.get_con_perfil(cliente.id)
        assert cliente_cargado is not None
        assert cliente_cargado.perfil is not None
        assert cliente_cargado.perfil.telefono == "+54 11 1234-5678"

        # PerfilClienteRepository.get_por_cliente
        perfil_cargado = await uow.perfiles.get_por_cliente(cliente.id)
        assert perfil_cargado is not None
        assert perfil_cargado.id == perfil.id


@pytest.mark.asyncio
async def test_task_1_1_cliente_uow_triangulation_uniqueness(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Triangulación: Verifica unicidad de email y un perfil por cliente en UoW sin commit en repos."""
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        uow = ClientesUnitOfWork(session=session)
        async with uow:
            c1 = await uow.clientes.add(
                Cliente(nombre=f"Cliente A {suffix}", email=f"unico_{suffix}@example.com")
            )
            await uow.perfiles.add(
                PerfilCliente(
                    cliente_id=c1.id,
                    telefono="11111",
                    direccion="Dir 1",
                )
            )

        # 1. Email duplicado lanza IntegrityError en flush
        async with session_factory() as session_dup:
            uow_dup = ClientesUnitOfWork(session=session_dup)
            with pytest.raises(IntegrityError):
                async with uow_dup:
                    await uow_dup.clientes.add(
                        Cliente(nombre="Otro", email=f"unico_{suffix}@example.com")
                    )

        # 2. Segundo perfil para mismo cliente lanza IntegrityError
        async with session_factory() as session_dup_perf:
            uow_perf = ClientesUnitOfWork(session=session_dup_perf)
            with pytest.raises(IntegrityError):
                async with uow_perf:
                    await uow_perf.perfiles.add(
                        PerfilCliente(
                            cliente_id=c1.id,
                            telefono="22222",
                            direccion="Dir 2",
                        )
                    )

        # 3. Cliente sin perfil
        async with session_factory() as session_solo:
            uow_solo = ClientesUnitOfWork(session=session_solo)
            async with uow_solo:
                c2 = await uow_solo.clientes.add(
                    Cliente(nombre=f"Cliente B {suffix}", email=f"sinperfil_{suffix}@example.com")
                )
            c2_cargado = await uow_solo.clientes.get_con_perfil(c2.id)
            assert c2_cargado is not None
            assert c2_cargado.perfil is None


@pytest.mark.asyncio
async def test_task_1_2_clientes_service_crud_and_forbid(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica servicio de clientes con UoW, extra='forbid', PaginatedResponse y errores 404/409/422."""
    from fastapi import HTTPException
    from pydantic import ValidationError

    suffix = uuid.uuid4().hex[:8]

    # 1. extra="forbid" en ClienteCreate, ClienteUpdate y PerfilClienteCreate
    with pytest.raises(ValidationError):
        ClienteCreate.model_validate(
            {"nombre": "Juan", "email": "juan@test.com", "desconocido": "invalido"}
        )

    with pytest.raises(ValidationError):
        ClienteUpdate.model_validate({"nombre": "Nuevo", "extra_invalido": 123})

    with pytest.raises(ValidationError):
        PerfilClienteCreate.model_validate(
            {"telefono": "123", "direccion": "dir", "campo_extra": True}
        )

    async with session_factory() as session:
        uow = ClientesUnitOfWork(session=session)

        # 2. Alta de cliente 201
        payload = ClienteCreate(nombre=f"Ana {suffix}", email=f"ana_{suffix}@example.com")
        creado = await crear_cliente(uow, payload)
        assert isinstance(creado, ClienteRead)
        assert creado.id is not None
        assert creado.nombre == f"Ana {suffix}"
        assert creado.perfil is None

        # 3. Email duplicado -> 409 sin texto interno de BD
        with pytest.raises(HTTPException) as exc_info:
            await crear_cliente(uow, payload)
        assert exc_info.value.status_code == 409
        assert "duplicate key" not in str(exc_info.value.detail).lower()

        # 4. Obtener cliente existente
        obtenido = await obtener_cliente(uow, creado.id)
        assert obtenido.id == creado.id

        # 5. Obtener cliente inexistente -> 404
        with pytest.raises(HTTPException) as exc_info:
            await obtener_cliente(uow, 999999)
        assert exc_info.value.status_code == 404

        # 6. Actualizar cliente existente
        actualizado = await actualizar_cliente(
            uow, creado.id, ClienteUpdate(nombre=f"Ana Modificada {suffix}")
        )
        assert actualizado.nombre == f"Ana Modificada {suffix}"

        # 7. Actualizar cliente inexistente -> 404
        with pytest.raises(HTTPException) as exc_info:
            await actualizar_cliente(uow, 999999, ClienteUpdate(nombre="Fantasma"))
        assert exc_info.value.status_code == 404

        # 8. Crear perfil para cliente existente -> 201
        perf = await crear_perfil(
            uow,
            creado.id,
            PerfilClienteCreate(telefono="11-2233-4455", direccion="Calle Falsa 123"),
        )
        assert isinstance(perf, PerfilClienteRead)
        assert perf.cliente_id == creado.id

        # 9. Segundo perfil para mismo cliente -> 409
        with pytest.raises(HTTPException) as exc_info:
            await crear_perfil(
                uow,
                creado.id,
                PerfilClienteCreate(telefono="99-8877", direccion="Otra Calle"),
            )
        assert exc_info.value.status_code == 409

        # 10. Crear perfil para cliente inexistente -> 404
        with pytest.raises(HTTPException) as exc_info:
            await crear_perfil(
                uow,
                999999,
                PerfilClienteCreate(telefono="123", direccion="dir"),
            )
        assert exc_info.value.status_code in (404, 409)

        # 11. Listar ventas de cliente inexistente -> 404
        with pytest.raises(HTTPException) as exc_info:
            await obtener_ventas_cliente(uow, 999999)
        assert exc_info.value.status_code == 404

        # 12. Listar ventas de cliente sin ventas -> PaginatedResponse vacía
        ventas_resp = await obtener_ventas_cliente(uow, creado.id)
        assert isinstance(ventas_resp, PaginatedResponse)
        assert ventas_resp.total == 0
        assert ventas_resp.items == []


@pytest.mark.asyncio
async def test_task_1_2_clientes_service_triangulation_pagination(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Triangulación: Paginación de clientes con envoltorio PaginatedResponse y validación de páginas."""
    from fastapi import HTTPException

    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        uow = ClientesUnitOfWork(session=session)
        # Crear 3 clientes
        for i in range(3):
            await crear_cliente(
                uow,
                ClienteCreate(
                    nombre=f"Paginado {i} {suffix}",
                    email=f"pag_{i}_{suffix}@example.com",
                ),
            )

        # Listar con size=2, page=1
        resp_p1 = await listar_clientes(uow, page=1, size=2)
        assert isinstance(resp_p1, PaginatedResponse)
        assert resp_p1.page == 1
        assert resp_p1.size == 2
        assert resp_p1.total >= 3
        assert len(resp_p1.items) == 2

        # Listar con page excedido -> 422
        with pytest.raises(HTTPException) as exc_info:
            await listar_clientes(uow, page=resp_p1.pages + 1, size=2)
        assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_task_1_3_clientes_endpoints_auth_and_roles(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica autenticación y RBAC (VENDEDOR/ADMIN) en rutas de /clientes."""
    from httpx import ASGITransport, AsyncClient
    from app.main import create_app
    from app.modules.usuarios.models import AsignacionRol, Usuario
    from app.core.security import create_access_token

    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        vendedor = Usuario(
            email=f"vendedor_{suffix}@test.com",
            nombre="Vendedor Test",
            password_hash="hash_dummy",
            activo=True,
            password_cambiada=True,
        )
        cliente_user = Usuario(
            email=f"cliente_user_{suffix}@test.com",
            nombre="Cliente User Test",
            password_hash="hash_dummy",
            activo=True,
            password_cambiada=True,
        )
        session.add(vendedor)
        session.add(cliente_user)
        await session.flush()
        session.add(AsignacionRol(usuario_id=vendedor.id, rol="VENDEDOR"))
        session.add(AsignacionRol(usuario_id=cliente_user.id, rol="CLIENTE"))
        await session.commit()

    token_vendedor = create_access_token({"sub": str(vendedor.id), "roles": ["VENDEDOR"]})
    token_cliente = create_access_token({"sub": str(cliente_user.id), "roles": ["CLIENTE"]})

    app_instance = create_app()
    async with app_instance.router.lifespan_context(app_instance):
        transport = ASGITransport(app=app_instance)

        # 1. Sin sesión -> 401
        async with AsyncClient(transport=transport, base_url="http://test") as anon_client:
            r1 = await anon_client.get("/clientes")
            assert r1.status_code == 401
            r2 = await anon_client.post("/clientes", json={"nombre": "A", "email": "a@a.com"})
            assert r2.status_code == 401
            r3 = await anon_client.get("/clientes/1")
            assert r3.status_code == 401
            r4 = await anon_client.patch("/clientes/1", json={"nombre": "B"})
            assert r4.status_code == 401
            r5 = await anon_client.post("/clientes/1/perfil", json={"telefono": "1", "direccion": "2"})
            assert r5.status_code == 401
            r6 = await anon_client.get("/clientes/1/ventas")
            assert r6.status_code == 401

        # 2. Con rol CLIENTE -> 403
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies={"access_token": token_cliente},
        ) as cli_client:
            r1 = await cli_client.get("/clientes")
            assert r1.status_code == 403
            r2 = await cli_client.post("/clientes", json={"nombre": "A", "email": "a@a.com"})
            assert r2.status_code == 403
            r3 = await cli_client.get("/clientes/1")
            assert r3.status_code == 403
            r4 = await cli_client.patch("/clientes/1", json={"nombre": "B"})
            assert r4.status_code == 403
            r5 = await cli_client.post("/clientes/1/perfil", json={"telefono": "1", "direccion": "2"})
            assert r5.status_code == 403
            r6 = await cli_client.get("/clientes/1/ventas")
            assert r6.status_code == 403

        # 3. Con rol VENDEDOR -> permitido
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies={"access_token": token_vendedor},
        ) as vend_client:
            # POST /clientes
            r_post = await vend_client.post(
                "/clientes",
                json={"nombre": f"Cli Vend {suffix}", "email": f"clivend_{suffix}@test.com"},
            )
            assert r_post.status_code == 201
            cli_id = r_post.json()["id"]

            # GET /clientes (paginado con items, total, page, size, pages)
            r_list = await vend_client.get("/clientes")
            assert r_list.status_code == 200
            data_list = r_list.json()
            assert "items" in data_list
            assert "total" in data_list
            assert "page" in data_list

            # GET /clientes/{id}
            r_get = await vend_client.get(f"/clientes/{cli_id}")
            assert r_get.status_code == 200
            assert r_get.json()["id"] == cli_id

            # PATCH /clientes/{id}
            r_patch = await vend_client.patch(
                f"/clientes/{cli_id}",
                json={"nombre": f"Cli Vend Editado {suffix}"},
            )
            assert r_patch.status_code == 200
            assert r_patch.json()["nombre"] == f"Cli Vend Editado {suffix}"

            # POST /clientes/{id}/perfil
            r_perf = await vend_client.post(
                f"/clientes/{cli_id}/perfil",
                json={"telefono": "123456", "direccion": "Calle Venta 100"},
            )
            assert r_perf.status_code == 201
            assert r_perf.json()["cliente_id"] == cli_id

            # GET /clientes/{id}/ventas
            r_v = await vend_client.get(f"/clientes/{cli_id}/ventas")
            assert r_v.status_code == 200
            assert "items" in r_v.json()


@pytest.mark.asyncio
async def test_task_1_3_clientes_admin_role_and_revocation(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Triangulación: ADMIN tiene acceso, y revocación de rol en BD bloquea con 403."""
    from datetime import datetime, timezone
    from httpx import ASGITransport, AsyncClient
    from app.main import create_app
    from app.modules.usuarios.models import AsignacionRol, Usuario
    from app.core.security import create_access_token

    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        admin = Usuario(
            email=f"admin_{suffix}@test.com",
            nombre="Admin Test",
            password_hash="hash_dummy",
            activo=True,
            password_cambiada=True,
        )
        revocado = Usuario(
            email=f"revocado_{suffix}@test.com",
            nombre="Revocado Test",
            password_hash="hash_dummy",
            activo=True,
            password_cambiada=True,
        )
        session.add(admin)
        session.add(revocado)
        await session.flush()
        session.add(AsignacionRol(usuario_id=admin.id, rol="ADMIN"))
        session.add(
            AsignacionRol(
                usuario_id=revocado.id,
                rol="VENDEDOR",
                revocada_en=datetime.now(timezone.utc),
            )
        )
        await session.commit()

    token_admin = create_access_token({"sub": str(admin.id), "roles": ["ADMIN"]})
    token_revocado = create_access_token({"sub": str(revocado.id), "roles": ["VENDEDOR"]})

    app_instance = create_app()
    async with app_instance.router.lifespan_context(app_instance):
        transport = ASGITransport(app=app_instance)

        # ADMIN accede
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies={"access_token": token_admin},
        ) as admin_client:
            r = await admin_client.get("/clientes")
            assert r.status_code == 200

        # Rol revocado en BD -> 403 aunque el token diga VENDEDOR
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies={"access_token": token_revocado},
        ) as rev_client:
            r = await rev_client.get("/clientes")
            assert r.status_code == 403


@pytest.mark.asyncio
async def test_task_2_1_reutilizacion_punto_unico_stock(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica que VentasUnitOfWork reutiliza el punto único de stock sin violar la regla AST."""
    import ast
    from pathlib import Path
    from app.modules.usuarios.models import Usuario

    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        user = Usuario(
            email=f"stock_user_{suffix}@test.com",
            nombre="Stock User",
            password_hash="hash",
            activo=True,
            password_cambiada=True,
        )
        session.add(user)
        ed = Editorial(nombre=f"Ed Stock {suffix}", pais="Argentina")
        gen = Genero(nombre=f"Gen Stock {suffix}")
        session.add(ed)
        session.add(gen)
        await session.flush()

        libro = Libro(
            isbn=f"978-STK-{suffix}",
            titulo=f"Libro Stock {suffix}",
            precio=Decimal("500.00"),
            stock=10,
            editorial_id=ed.id,
            genero_id=gen.id,
        )
        session.add(libro)
        await session.commit()
        libro_id = libro.id
        user_id = user.id

    # 1. VentasUnitOfWork delega en registrar_movimiento_stock
    async with session_factory() as session:
        uow = VentasUnitOfWork(session=session)
        async with uow:
            mov = await uow.registrar_movimiento_stock(
                libro=libro_id,
                cantidad=-3,
                motivo="Venta #1",
                usuario_id=user_id,
            )
            assert mov is not None
            assert mov.cantidad == -3
            assert mov.motivo == "Venta #1"

        # Verificar stock actualizado a 7
        libro_db = await uow.libros.get_by_id(libro_id)
        assert libro_db is not None
        assert libro_db.stock == 7

        # 2. Stock insuficiente lanza ValueError
        async with uow:
            with pytest.raises(ValueError, match="Stock insuficiente"):
                await uow.registrar_movimiento_stock(
                    libro=libro_id,
                    cantidad=-15,
                    motivo="Exceso",
                    usuario_id=user_id,
                )

        # 3. Soft delete del libro y verificar que registrar_movimiento_stock lo rechaza
        async with uow:
            await uow.libros.soft_delete(libro_db)

        async with uow:
            with pytest.raises(ValueError, match="dado de baja"):
                await uow.registrar_movimiento_stock(
                    libro=libro_id,
                    cantidad=-1,
                    motivo="Venta en baja",
                    usuario_id=user_id,
                )

    # 4. Verificación AST: Sólo app/modules/libros/unit_of_work.py puede asignar a .stock
    app_dir = Path("app")
    allowed_file = Path("app/modules/libros/unit_of_work.py").resolve()
    violating_occurrences: list[str] = []
    for py_file in app_dir.rglob("*.py"):
        resolved = py_file.resolve()
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr == "stock":
                        if resolved != allowed_file:
                            violating_occurrences.append(f"{py_file}:{node.lineno}")
            elif isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Attribute) and node.target.attr == "stock":
                    if resolved != allowed_file:
                        violating_occurrences.append(f"{py_file}:{node.lineno}")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "setattr":
                    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and node.args[1].value == "stock":
                        if resolved != allowed_file:
                            violating_occurrences.append(f"{py_file}:{node.lineno}")
    assert not violating_occurrences, f"Violación AST: asignación a .stock fuera de {allowed_file}: {violating_occurrences}"


@pytest.mark.asyncio
async def test_task_2_2_venta_repository_and_query_count(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica VentaRepository (get_detalle, listar, listar_por_usuario) y conteo fijo de queries (sin N+1)."""
    from sqlalchemy import event
    from app.modules.usuarios.models import Usuario

    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        user = Usuario(
            email=f"usr_repo_{suffix}@test.com",
            nombre="User Repo",
            password_hash="hash",
            activo=True,
            password_cambiada=True,
        )
        session.add(user)
        ed = Editorial(nombre=f"Ed Repo {suffix}", pais="Argentina")
        gen = Genero(nombre=f"Gen Repo {suffix}")
        session.add(ed)
        session.add(gen)
        await session.flush()

        cli = Cliente(nombre=f"Cli Repo {suffix}", email=f"cli_repo_{suffix}@test.com", usuario_id=user.id)
        session.add(cli)
        await session.flush()

        libros = []
        for i in range(4):
            lib = Libro(
                isbn=f"978-R-{i}-{suffix}",
                titulo=f"Libro R{i} {suffix}",
                precio=Decimal(f"{(i+1)*100}.00"),
                stock=50,
                editorial_id=ed.id,
                genero_id=gen.id,
            )
            session.add(lib)
            libros.append(lib)
        await session.flush()

        # Venta 1 con 2 renglones
        v1 = Venta(cliente_id=cli.id, total=Decimal("300.00"))
        session.add(v1)
        await session.flush()
        session.add(RenglonVenta(venta_id=v1.id, libro_id=libros[0].id, cantidad=1, precio_unitario=libros[0].precio))
        session.add(RenglonVenta(venta_id=v1.id, libro_id=libros[1].id, cantidad=1, precio_unitario=libros[1].precio))

        # Venta 2 con 4 renglones
        v2 = Venta(cliente_id=cli.id, total=Decimal("1000.00"))
        session.add(v2)
        await session.flush()
        for lib in libros:
            session.add(RenglonVenta(venta_id=v2.id, libro_id=lib.id, cantidad=1, precio_unitario=lib.precio))

        await session.commit()
        v1_id = v1.id
        v2_id = v2.id
        cli_id = cli.id
        user_id = user.id
        lib0_id = libros[0].id

    # Dar de baja libros[0] posteriormente a la venta
    async with session_factory() as session:
        uow_lib = LibrosUnitOfWork(session=session)
        async with uow_lib:
            l0 = await uow_lib.libros.get_by_id(lib0_id)
            assert l0 is not None
            await uow_lib.libros.soft_delete(l0)

    # Medir cantidad de queries ejecutadas para v1 (2 renglones) y v2 (4 renglones)
    queries_v1 = []
    queries_v2 = []

    async with session_factory() as session:
        uow = VentasUnitOfWork(session=session)

        def count_queries(conn, cursor, statement, parameters, context, executemany):
            queries_v1.append(statement)

        event.listen(session.sync_session.bind, "before_cursor_execute", count_queries)
        try:
            detalle1 = await uow.ventas.get_detalle(v1_id)
        finally:
            event.remove(session.sync_session.bind, "before_cursor_execute", count_queries)

        assert detalle1 is not None
        assert len(detalle1.renglones) == 2
        # El libro dado de baja debe seguir mostrando su título
        titulos_v1 = [r.libro.titulo for r in detalle1.renglones if r.libro]
        assert f"Libro R0 {suffix}" in titulos_v1
        assert f"Libro R1 {suffix}" in titulos_v1

    async with session_factory() as session:
        uow = VentasUnitOfWork(session=session)

        def count_queries_2(conn, cursor, statement, parameters, context, executemany):
            queries_v2.append(statement)

        event.listen(session.sync_session.bind, "before_cursor_execute", count_queries_2)
        try:
            detalle2 = await uow.ventas.get_detalle(v2_id)
        finally:
            event.remove(session.sync_session.bind, "before_cursor_execute", count_queries_2)

        assert detalle2 is not None
        assert len(detalle2.renglones) == 4

    # Ambas lecturas de detalle deben ejecutar exactamente la misma cantidad de queries SQL (conteo fijo, sin N+1)
    assert len(queries_v1) == len(queries_v2), (
        f"Conteo distinto de queries: v1 (2 renglones) ejecutó {len(queries_v1)}, v2 (4 renglones) ejecutó {len(queries_v2)}"
    )

    # Verificar listados de ventas y listado por usuario
    async with session_factory() as session:
        uow = VentasUnitOfWork(session=session)
        lista = await uow.ventas.listar(offset=0, limit=10)
        assert len(lista) >= 2

        por_usuario = await uow.ventas.listar_por_usuario(usuario_id=user_id, offset=0, limit=10)
        assert len(por_usuario) == 2
        count_usuario = await uow.ventas.count_por_usuario(usuario_id=user_id)
        assert count_usuario == 2


@pytest.mark.asyncio
async def test_task_2_3_crear_venta_atomica_y_stock(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica alta de venta atómica, descuento por punto único y rollback total ante error (409)."""
    from fastapi import HTTPException
    from sqlalchemy import select, func
    from app.modules.usuarios.models import Usuario

    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        vendedor = Usuario(
            email=f"vend_v_{suffix}@test.com",
            nombre="Vendedor Venta",
            password_hash="hash",
            activo=True,
            password_cambiada=True,
        )
        session.add(vendedor)
        cli = Cliente(nombre=f"Cliente V {suffix}", email=f"cli_v_{suffix}@test.com")
        session.add(cli)
        ed = Editorial(nombre=f"Ed V {suffix}", pais="Argentina")
        gen = Genero(nombre=f"Gen V {suffix}")
        session.add(ed)
        session.add(gen)
        await session.flush()

        l1 = Libro(
            isbn=f"978-V1-{suffix}",
            titulo=f"Libro V1 {suffix}",
            precio=Decimal("100.00"),
            stock=8,
            editorial_id=ed.id,
            genero_id=gen.id,
        )
        l2 = Libro(
            isbn=f"978-V2-{suffix}",
            titulo=f"Libro V2 {suffix}",
            precio=Decimal("250.00"),
            stock=5,
            editorial_id=ed.id,
            genero_id=gen.id,
        )
        session.add(l1)
        session.add(l2)
        await session.commit()
        vendedor_id = vendedor.id
        cli_id = cli.id
        l1_id = l1.id
        l2_id = l2.id

    # 1. Venta exitosa: 2 unidades de l1 y 1 unidad de l2 -> total = 2*100 + 1*250 = 450.00
    async with session_factory() as session:
        uow = VentasUnitOfWork(session=session)
        data = VentaCreate(
            cliente_id=cli_id,
            renglones=[
                RenglonVentaCreate(libro_id=l1_id, cantidad=2),
                RenglonVentaCreate(libro_id=l2_id, cantidad=1),
            ],
        )
        venta_creada = await crear_venta(uow, data, usuario_actual_id=vendedor_id)
        assert venta_creada.id is not None
        assert venta_creada.total == Decimal("450.00")
        assert len(venta_creada.renglones) == 2

    # Verificar stocks y movimientos en BD
    async with session_factory() as session:
        uow = VentasUnitOfWork(session=session)
        libro1 = await uow.libros.get_by_id(l1_id)
        libro2 = await uow.libros.get_by_id(l2_id)
        assert libro1.stock == 6
        assert libro2.stock == 4

        # Movimientos
        movs = (
            await session.execute(
                select(MovimientoStock).where(MovimientoStock.venta_id == venta_creada.id)
            )
        ).scalars().all()
        assert len(movs) == 2
        cantidades = {m.libro_id: m.cantidad for m in movs}
        assert cantidades[l1_id] == -2
        assert cantidades[l2_id] == -1

    # 2. Rollback total ante stock insuficiente en 2do renglón:
    # l1 pide 2 (alcanza, hay 6), l2 pide 10 (no alcanza, hay 4)
    async with session_factory() as session:
        uow = VentasUnitOfWork(session=session)
        data_insuf = VentaCreate(
            cliente_id=cli_id,
            renglones=[
                RenglonVentaCreate(libro_id=l1_id, cantidad=2),
                RenglonVentaCreate(libro_id=l2_id, cantidad=10),
            ],
        )
        with pytest.raises(HTTPException) as exc_info:
            await crear_venta(uow, data_insuf, usuario_actual_id=vendedor_id)
        assert exc_info.value.status_code == 409

    # Verificar que el stock de l1 NO cambió (sigue en 6) y l2 sigue en 4
    async with session_factory() as session:
        uow = VentasUnitOfWork(session=session)
        libro1 = await uow.libros.get_by_id(l1_id)
        libro2 = await uow.libros.get_by_id(l2_id)
        assert libro1.stock == 6
        assert libro2.stock == 4

        # Invariante: stock == stock_inicial + SUM(movimientos)
        total_movs_l1 = (
            await session.execute(
                select(func.coalesce(func.sum(MovimientoStock.cantidad), 0)).where(
                    MovimientoStock.libro_id == l1_id
                )
            )
        ).scalar_one()
        # l1 arrancó con 8, se movió -2 -> suma de movs = -2, stock = 6 (8 + -2 = 6)
        assert total_movs_l1 == -2

    # 3. Rollback si libro dado de baja
    async with session_factory() as session:
        uow = VentasUnitOfWork(session=session)
        async with uow:
            l2_obj = await uow.libros.get_by_id(l2_id)
            await uow.libros.soft_delete(l2_obj)

        data_baja = VentaCreate(
            cliente_id=cli_id,
            renglones=[RenglonVentaCreate(libro_id=l2_id, cantidad=1)],
        )
        with pytest.raises(HTTPException) as exc_info:
            await crear_venta(uow, data_baja, usuario_actual_id=vendedor_id)
        assert exc_info.value.status_code == 409

    # 4. Rollback si cliente inexistente
    async with session_factory() as session:
        uow = VentasUnitOfWork(session=session)
        data_cli_inex = VentaCreate(
            cliente_id=999999,
            renglones=[RenglonVentaCreate(libro_id=l1_id, cantidad=1)],
        )
        with pytest.raises(HTTPException) as exc_info:
            await crear_venta(uow, data_cli_inex, usuario_actual_id=vendedor_id)
        assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_task_2_4_background_task_notification(
    session_factory: async_sessionmaker[AsyncSession],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verifica que el comprobante se agenda en BackgroundTasks solo tras commit exitoso."""
    import logging
    from httpx import ASGITransport, AsyncClient
    from app.main import create_app
    from app.modules.usuarios.models import AsignacionRol, Usuario
    from app.core.security import create_access_token

    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        vendedor = Usuario(
            email=f"vend_bg_{suffix}@test.com",
            nombre="Vendedor BG",
            password_hash="hash",
            activo=True,
            password_cambiada=True,
        )
        session.add(vendedor)
        cli = Cliente(nombre=f"Cliente BG {suffix}", email=f"cli_bg_{suffix}@test.com")
        session.add(cli)
        ed = Editorial(nombre=f"Ed BG {suffix}", pais="Argentina")
        gen = Genero(nombre=f"Gen BG {suffix}")
        session.add(ed)
        session.add(gen)
        await session.flush()
        session.add(AsignacionRol(usuario_id=vendedor.id, rol="VENDEDOR"))

        libro = Libro(
            isbn=f"978-BG-{suffix}",
            titulo=f"Libro BG {suffix}",
            precio=Decimal("300.00"),
            stock=10,
            editorial_id=ed.id,
            genero_id=gen.id,
        )
        session.add(libro)
        await session.commit()
        token_vendedor = create_access_token({"sub": str(vendedor.id), "roles": ["VENDEDOR"]})
        cli_id = cli.id
        libro_id = libro.id

    app_instance = create_app()
    async with app_instance.router.lifespan_context(app_instance):
        transport = ASGITransport(app=app_instance)

        # 1. Venta exitosa registra log de comprobante
        with caplog.at_level(logging.INFO):
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
                cookies={"access_token": token_vendedor},
            ) as client:
                r = await client.post(
                    "/ventas",
                    json={
                        "cliente_id": cli_id,
                        "renglones": [{"libro_id": libro_id, "cantidad": 2}],
                    },
                )
                assert r.status_code == 201
                venta_id = r.json()["id"]

        assert any(
            f"Comprobante generado para venta {venta_id}" in record.message
            for record in caplog.records
        )

        caplog.clear()

        # 2. Venta fallida (409) NO registra log de comprobante
        with caplog.at_level(logging.INFO):
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
                cookies={"access_token": token_vendedor},
            ) as client:
                r = await client.post(
                    "/ventas",
                    json={
                        "cliente_id": cli_id,
                        "renglones": [{"libro_id": libro_id, "cantidad": 999}],
                    },
                )
                assert r.status_code == 409

        assert not any("Comprobante generado para venta" in record.message for record in caplog.records)


@pytest.mark.asyncio
async def test_task_2_5_ventas_dto_and_auth(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica DTO estricto con extra='forbid', renglones vacíos/duplicados (422) y roles 401/403."""
    from pydantic import ValidationError
    from httpx import ASGITransport, AsyncClient
    from app.main import create_app
    from app.modules.usuarios.models import AsignacionRol, Usuario
    from app.core.security import create_access_token

    suffix = uuid.uuid4().hex[:8]

    # 1. Validaciones DTO (extra="forbid", repetidos, vacíos, cantidad <= 0)
    with pytest.raises(ValidationError):
        VentaCreate.model_validate(
            {
                "cliente_id": 1,
                "renglones": [{"libro_id": 1, "cantidad": 1}],
                "desconocido": "invalido",
            }
        )

    with pytest.raises(ValidationError):
        RenglonVentaCreate.model_validate({"libro_id": 1, "cantidad": 1, "extra": "no"})

    with pytest.raises(ValidationError):
        # Repetidos
        VentaCreate.model_validate(
            {
                "cliente_id": 1,
                "renglones": [
                    {"libro_id": 1, "cantidad": 1},
                    {"libro_id": 1, "cantidad": 2},
                ],
            }
        )

    with pytest.raises(ValidationError):
        # Vacíos
        VentaCreate.model_validate({"cliente_id": 1, "renglones": []})

    with pytest.raises(ValidationError):
        # Cantidad <= 0
        RenglonVentaCreate.model_validate({"libro_id": 1, "cantidad": 0})

    # 2. Endpoints: Sin sesión (401), Rol CLIENTE (403)
    async with session_factory() as session:
        cliente_user = Usuario(
            email=f"usr_c_{suffix}@test.com",
            nombre="User C",
            password_hash="hash",
            activo=True,
            password_cambiada=True,
        )
        session.add(cliente_user)
        await session.flush()
        session.add(AsignacionRol(usuario_id=cliente_user.id, rol="CLIENTE"))
        await session.commit()
        token_cliente = create_access_token({"sub": str(cliente_user.id), "roles": ["CLIENTE"]})

    app_instance = create_app()
    async with app_instance.router.lifespan_context(app_instance):
        transport = ASGITransport(app=app_instance)

        async with AsyncClient(transport=transport, base_url="http://test") as anon_client:
            r = await anon_client.post(
                "/ventas",
                json={"cliente_id": 1, "renglones": [{"libro_id": 1, "cantidad": 1}]},
            )
            assert r.status_code == 401

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies={"access_token": token_cliente},
        ) as cli_client:
            r = await cli_client.post(
                "/ventas",
                json={"cliente_id": 1, "renglones": [{"libro_id": 1, "cantidad": 1}]},
            )
            assert r.status_code == 403


@pytest.mark.asyncio
async def test_task_3_1_lecturas_autorizacion_duenio_y_personal(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica GET /ventas (personal) y GET /ventas/{id} (dueño o personal en BD, 403 ajeno, 404 inexistente)."""
    from httpx import ASGITransport, AsyncClient
    from app.main import create_app
    from app.modules.usuarios.models import AsignacionRol, Usuario
    from app.core.security import create_access_token

    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        u_ana = Usuario(
            email=f"ana_{suffix}@test.com",
            nombre="Ana Dueña",
            password_hash="hash",
            activo=True,
            password_cambiada=True,
        )
        u_pedro = Usuario(
            email=f"pedro_{suffix}@test.com",
            nombre="Pedro Ajeno",
            password_hash="hash",
            activo=True,
            password_cambiada=True,
        )
        u_vend = Usuario(
            email=f"vendedor_3_{suffix}@test.com",
            nombre="Vendedor Staff",
            password_hash="hash",
            activo=True,
            password_cambiada=True,
        )
        session.add(u_ana)
        session.add(u_pedro)
        session.add(u_vend)
        await session.flush()
        session.add(AsignacionRol(usuario_id=u_ana.id, rol="CLIENTE"))
        session.add(AsignacionRol(usuario_id=u_pedro.id, rol="CLIENTE"))
        session.add(AsignacionRol(usuario_id=u_vend.id, rol="VENDEDOR"))

        cli_ana = Cliente(nombre=f"Cliente Ana {suffix}", email=f"cliana_{suffix}@test.com", usuario_id=u_ana.id)
        cli_pedro = Cliente(nombre=f"Cliente Pedro {suffix}", email=f"clipedro_{suffix}@test.com", usuario_id=u_pedro.id)
        session.add(cli_ana)
        session.add(cli_pedro)
        ed = Editorial(nombre=f"Ed 3 {suffix}", pais="Argentina")
        gen = Genero(nombre=f"Gen 3 {suffix}")
        session.add(ed)
        session.add(gen)
        await session.flush()

        libro = Libro(
            isbn=f"978-3-{suffix}",
            titulo=f"Libro Tres {suffix}",
            precio=Decimal("200.00"),
            stock=100,
            editorial_id=ed.id,
            genero_id=gen.id,
        )
        session.add(libro)
        await session.flush()

        # Venta de Ana
        v_ana = Venta(cliente_id=cli_ana.id, total=Decimal("200.00"))
        session.add(v_ana)
        await session.flush()
        session.add(RenglonVenta(venta_id=v_ana.id, libro_id=libro.id, cantidad=1, precio_unitario=Decimal("200.00")))

        # Venta de Pedro
        v_pedro = Venta(cliente_id=cli_pedro.id, total=Decimal("400.00"))
        session.add(v_pedro)
        await session.flush()
        session.add(RenglonVenta(venta_id=v_pedro.id, libro_id=libro.id, cantidad=2, precio_unitario=Decimal("200.00")))

        await session.commit()
        v_ana_id = v_ana.id
        v_pedro_id = v_pedro.id
        ana_id = u_ana.id
        pedro_id = u_pedro.id
        vend_id = u_vend.id

    token_ana = create_access_token({"sub": str(ana_id), "roles": ["CLIENTE"]})
    token_pedro = create_access_token({"sub": str(pedro_id), "roles": ["CLIENTE"]})
    token_vend = create_access_token({"sub": str(vend_id), "roles": ["VENDEDOR"]})
    # Token falsificado: sub es Pedro (CLIENTE en BD), pero el token afirma "ADMIN"
    token_falsificado = create_access_token({"sub": str(pedro_id), "roles": ["ADMIN"]})

    app_instance = create_app()
    async with app_instance.router.lifespan_context(app_instance):
        transport = ASGITransport(app=app_instance)

        # 1. Ana (dueña) ve su venta -> 200
        async with AsyncClient(transport=transport, base_url="http://test", cookies={"access_token": token_ana}) as c_ana:
            r = await c_ana.get(f"/ventas/{v_ana_id}")
            assert r.status_code == 200
            assert r.json()["id"] == v_ana_id

            # Ana intenta ver venta ajena (de Pedro) -> 403
            r_ajena = await c_ana.get(f"/ventas/{v_pedro_id}")
            assert r_ajena.status_code == 403

            # Ana intenta consultar venta inexistente -> 404 (el 404 se evalúa antes de 403)
            r_inex = await c_ana.get("/ventas/999999")
            assert r_inex.status_code == 404

            # Ana intenta listar todas las ventas -> 403 (requiere VENDEDOR/ADMIN)
            r_list = await c_ana.get("/ventas")
            assert r_list.status_code == 403

        # 2. Vendedor (personal) ve cualquier venta y el listado -> 200
        async with AsyncClient(transport=transport, base_url="http://test", cookies={"access_token": token_vend}) as c_vend:
            r1 = await c_vend.get(f"/ventas/{v_ana_id}")
            assert r1.status_code == 200
            r2 = await c_vend.get(f"/ventas/{v_pedro_id}")
            assert r2.status_code == 200

            # Listado paginado con envoltorio
            r_list = await c_vend.get("/ventas?page=1&size=10")
            assert r_list.status_code == 200
            data_list = r_list.json()
            assert "items" in data_list
            assert "total" in data_list
            assert "pages" in data_list
            assert data_list["total"] >= 2

        # 3. Verificación de roles en BD (RN-04): token falsificado con ADMIN pero CLIENTE en BD -> 403
        async with AsyncClient(transport=transport, base_url="http://test", cookies={"access_token": token_falsificado}) as c_fake:
            r_fake_list = await c_fake.get("/ventas")
            assert r_fake_list.status_code == 403
            # Y no puede ver la venta de Ana
            r_fake_ana = await c_fake.get(f"/ventas/{v_ana_id}")
            assert r_fake_ana.status_code == 403


@pytest.mark.asyncio
async def test_task_3_2_mis_ventas_paginado(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica GET /mis-ventas paginado: ventas propias, vacío sin cliente y 422 ante paginación inválida."""
    from httpx import ASGITransport, AsyncClient
    from app.main import create_app
    from app.modules.usuarios.models import AsignacionRol, Usuario
    from app.core.security import create_access_token

    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        u_ana = Usuario(
            email=f"ana_mv_{suffix}@test.com",
            nombre="Ana MisVentas",
            password_hash="hash",
            activo=True,
            password_cambiada=True,
        )
        u_huerfano = Usuario(
            email=f"huerfano_{suffix}@test.com",
            nombre="User Sin Cliente",
            password_hash="hash",
            activo=True,
            password_cambiada=True,
        )
        session.add(u_ana)
        session.add(u_huerfano)
        await session.flush()
        session.add(AsignacionRol(usuario_id=u_ana.id, rol="CLIENTE"))
        session.add(AsignacionRol(usuario_id=u_huerfano.id, rol="CLIENTE"))

        cli_ana = Cliente(nombre=f"Cli Ana MV {suffix}", email=f"ana_mv_cli_{suffix}@test.com", usuario_id=u_ana.id)
        session.add(cli_ana)
        await session.flush()

        v = Venta(cliente_id=cli_ana.id, total=Decimal("500.00"))
        session.add(v)
        await session.commit()
        ana_id = u_ana.id
        huerfano_id = u_huerfano.id
        v_id = v.id

    token_ana = create_access_token({"sub": str(ana_id), "roles": ["CLIENTE"]})
    token_huerfano = create_access_token({"sub": str(huerfano_id), "roles": ["CLIENTE"]})

    app_instance = create_app()
    async with app_instance.router.lifespan_context(app_instance):
        transport = ASGITransport(app=app_instance)

        # 1. Ana consulta /mis-ventas -> 200 con su venta
        async with AsyncClient(transport=transport, base_url="http://test", cookies={"access_token": token_ana}) as c_ana:
            r = await c_ana.get("/mis-ventas")
            assert r.status_code == 200
            data = r.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["id"] == v_id

            # Paginación excedida -> 422
            r_excedida = await c_ana.get("/mis-ventas?page=10&size=10")
            assert r_excedida.status_code == 422

        # 2. Usuario sin cliente asociado -> 200 con listado vacío y total: 0
        async with AsyncClient(transport=transport, base_url="http://test", cookies={"access_token": token_huerfano}) as c_huerf:
            r_h = await c_huerf.get("/mis-ventas")
            assert r_h.status_code == 200
            data_h = r_h.json()
            assert data_h["total"] == 0
            assert data_h["items"] == []


@pytest.mark.asyncio
async def test_task_3_3_detalle_sin_n_mas_1_http(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica detalle de venta vía HTTP con título visible para libro dado de baja posterior a la venta."""
    from httpx import ASGITransport, AsyncClient
    from app.main import create_app
    from app.modules.usuarios.models import AsignacionRol, Usuario
    from app.core.security import create_access_token

    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        vendedor = Usuario(
            email=f"v_n1_{suffix}@test.com",
            nombre="Vend N1",
            password_hash="hash",
            activo=True,
            password_cambiada=True,
        )
        session.add(vendedor)
        await session.flush()
        session.add(AsignacionRol(usuario_id=vendedor.id, rol="VENDEDOR"))

        cli = Cliente(nombre=f"Cli N1 {suffix}", email=f"cli_n1_{suffix}@test.com")
        session.add(cli)
        ed = Editorial(nombre=f"Ed N1 {suffix}", pais="Argentina")
        gen = Genero(nombre=f"Gen N1 {suffix}")
        session.add(ed)
        session.add(gen)
        await session.flush()

        libro = Libro(
            isbn=f"978-N1-{suffix}",
            titulo=f"Rayuela Histórica {suffix}",
            precio=Decimal("1200.00"),
            stock=10,
            editorial_id=ed.id,
            genero_id=gen.id,
        )
        session.add(libro)
        await session.flush()

        venta = Venta(cliente_id=cli.id, total=Decimal("1200.00"))
        session.add(venta)
        await session.flush()
        session.add(RenglonVenta(venta_id=venta.id, libro_id=libro.id, cantidad=1, precio_unitario=Decimal("1200.00")))
        await session.commit()
        vendedor_id = vendedor.id
        libro_id = libro.id
        venta_id = venta.id

    # Dar de baja el libro
    async with session_factory() as session:
        uow_lib = LibrosUnitOfWork(session=session)
        async with uow_lib:
            l_obj = await uow_lib.libros.get_by_id(libro_id)
            assert l_obj is not None
            await uow_lib.libros.soft_delete(l_obj)

    token_vend = create_access_token({"sub": str(vendedor_id), "roles": ["VENDEDOR"]})

    app_instance = create_app()
    async with app_instance.router.lifespan_context(app_instance):
        transport = ASGITransport(app=app_instance)
        async with AsyncClient(transport=transport, base_url="http://test", cookies={"access_token": token_vend}) as client:
            r = await client.get(f"/ventas/{venta_id}")
            assert r.status_code == 200
            detalle = r.json()
            assert detalle["id"] == venta_id
            assert len(detalle["renglones"]) == 1
            # El libro dado de baja debe mostrar su título original
            assert detalle["renglones"][0]["titulo"] == f"Rayuela Histórica {suffix}"





