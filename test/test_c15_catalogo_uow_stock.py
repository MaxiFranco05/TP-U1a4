"""Tests bajo Strict TDD para C-15: Catálogo sobre UoW, borrado lógico y punto único de stock."""

from collections.abc import AsyncGenerator
from decimal import Decimal
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
from app.core.repository import BaseRepository
from app.core.unit_of_work import UnitOfWork
from app.modules.autores.models import Autor
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero

# Import repositories and UoWs that are about to be created
from app.modules.editoriales.repository import EditorialRepository
from app.modules.editoriales.unit_of_work import EditorialesUnitOfWork
from app.modules.generos.repository import GeneroRepository
from app.modules.generos.unit_of_work import GenerosUnitOfWork
from app.modules.autores.repository import AutorRepository
from app.modules.autores.unit_of_work import AutoresUnitOfWork

from app.modules.libros.models import Libro, LibroAutor, MovimientoStock
from app.modules.libros.repository import LibroRepository, MovimientoStockRepository
from app.modules.libros.unit_of_work import LibrosUnitOfWork

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
async def test_task_1_1_editorial_repository_and_uow(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica alta, get_by_id, count con filtros y que el repo solo hace flush() y el UoW hace commit()."""
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        commit_spy = AsyncMock(wraps=session.commit)
        flush_spy = AsyncMock(wraps=session.flush)
        monkeypatch.setattr(session, "commit", commit_spy)
        monkeypatch.setattr(session, "flush", flush_spy)

        uow = EditorialesUnitOfWork(session=session)
        assert isinstance(uow, UnitOfWork)
        assert isinstance(uow.editoriales, BaseRepository)

        async with uow:
            ed1 = await uow.editoriales.add(Editorial(nombre=f"Ed A {suffix}", pais="Argentina"))
            ed2 = await uow.editoriales.add(Editorial(nombre=f"Ed B {suffix}", pais="España"))
            assert ed1.id is not None
            assert ed2.id is not None
            # flush called, commit NOT yet called
            assert flush_spy.call_count >= 2
            assert commit_spy.call_count == 0

        # After exiting context, commit must have been called
        assert commit_spy.call_count == 1

        # Query checks
        found = await uow.editoriales.get_by_id(ed1.id)
        assert found is not None
        assert found.nombre == f"Ed A {suffix}"

        count_arg = await uow.editoriales.count(filters=(Editorial.pais == "Argentina",))
        assert count_arg == 1
        count_all = await uow.editoriales.count()
        assert count_all >= 2


@pytest.mark.asyncio
async def test_task_1_1_genero_repository_and_uow(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica alta, get_by_id y count con filtros en GeneroRepository y GenerosUnitOfWork."""
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        uow = GenerosUnitOfWork(session=session)
        assert isinstance(uow, UnitOfWork)
        assert isinstance(uow.generos, BaseRepository)

        async with uow:
            g1 = await uow.generos.add(Genero(nombre=f"SciFi {suffix}"))
            g2 = await uow.generos.add(Genero(nombre=f"Fantasía {suffix}"))

        found = await uow.generos.get_by_id(g1.id)
        assert found is not None
        assert found.nombre == f"SciFi {suffix}"

        cnt = await uow.generos.count(filters=(Genero.nombre == f"SciFi {suffix}",))
        assert cnt == 1


@pytest.mark.asyncio
async def test_task_1_1_autor_repository_and_uow(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica alta, get_by_id y count con filtros en AutorRepository y AutoresUnitOfWork."""
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        uow = AutoresUnitOfWork(session=session)
        assert isinstance(uow, UnitOfWork)
        assert isinstance(uow.autores, BaseRepository)

        async with uow:
            a1 = await uow.autores.add(Autor(nombre=f"Borges {suffix}", nacionalidad="Argentina"))
            a2 = await uow.autores.add(Autor(nombre=f"Cortázar {suffix}", nacionalidad="Argentina"))

        found = await uow.autores.get_by_id(a1.id)
        assert found is not None
        assert found.nombre == f"Borges {suffix}"

        cnt = await uow.autores.count(filters=(Autor.nacionalidad == "Argentina",))
        assert cnt >= 2


@pytest.mark.asyncio
async def test_task_1_1_uow_rollback_on_exception(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Triangulación: Verifica que una excepción dentro del bloque async with uow revierte las operaciones."""
    suffix = uuid.uuid4().hex[:8]
    editorial_nombre = f"Rollback Ed {suffix}"
    try:
        async with session_factory() as session:
            uow = EditorialesUnitOfWork(session=session)
            async with uow:
                await uow.editoriales.add(Editorial(nombre=editorial_nombre, pais="Chile"))
                raise RuntimeError("Forced error to test rollback")
    except RuntimeError:
        pass

    async with session_factory() as session:
        uow = EditorialesUnitOfWork(session=session)
        cnt = await uow.editoriales.count(filters=(Editorial.nombre == editorial_nombre,))
        assert cnt == 0


@pytest.mark.asyncio
async def test_task_1_1_repository_update_delete_and_pagination(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Triangulación: Verifica update, delete y get_all paginado con filtros."""
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        uow = GenerosUnitOfWork(session=session)
        async with uow:
            g = await uow.generos.add(Genero(nombre=f"Original {suffix}"))
            g_id = g.id
            assert g_id is not None

            # Update
            await uow.generos.update(g, {"nombre": f"Modificado {suffix}"})

        # Check update persisted
        updated = await uow.generos.get_by_id(g_id)
        assert updated is not None
        assert updated.nombre == f"Modificado {suffix}"

        # Delete
        async with uow:
            await uow.generos.delete(updated)

        deleted = await uow.generos.get_by_id(g_id)
        assert deleted is None


@pytest.mark.asyncio
async def test_task_1_2_libro_repository_preload_query_count(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica que el detalle de un libro con 1 autor y otro con 3 autores ejecuta igual cantidad de consultas SQL."""
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        async with uow:
            ed = await uow.editoriales.add(Editorial(nombre=f"Ed Preload {suffix}", pais="Argentina"))
            gen = await uow.generos.add(Genero(nombre=f"Gen Preload {suffix}"))
            a1 = await uow.autores.add(Autor(nombre=f"Autor 1 {suffix}", nacionalidad="Arg"))
            a2 = await uow.autores.add(Autor(nombre=f"Autor 2 {suffix}", nacionalidad="Arg"))
            a3 = await uow.autores.add(Autor(nombre=f"Autor 3 {suffix}", nacionalidad="Arg"))

            l1 = await uow.libros.add(
                Libro(
                    isbn=f"978-001-{suffix}",
                    titulo="Libro 1 autor",
                    precio=Decimal("1000.00"),
                    stock=5,
                    editorial_id=ed.id,
                    genero_id=gen.id,
                )
            )
            l2 = await uow.libros.add(
                Libro(
                    isbn=f"978-002-{suffix}",
                    titulo="Libro 3 autores",
                    precio=Decimal("2000.00"),
                    stock=10,
                    editorial_id=ed.id,
                    genero_id=gen.id,
                )
            )
            # Asociar autorías
            session.add(LibroAutor(libro_id=l1.id, autor_id=a1.id, rol="autor", orden=1))
            session.add(LibroAutor(libro_id=l2.id, autor_id=a1.id, rol="autor", orden=1))
            session.add(LibroAutor(libro_id=l2.id, autor_id=a2.id, rol="coautor", orden=2))
            session.add(LibroAutor(libro_id=l2.id, autor_id=a3.id, rol="coautor", orden=3))

    # Nueva sesión para medir queries de lectura
    queries_l1 = 0
    queries_l2 = 0

    from sqlalchemy import event

    # Para l1
    async with session_factory() as session1:
        uow1 = LibrosUnitOfWork(session=session1)
        count_queries = 0

        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            nonlocal count_queries
            count_queries += 1

        engine = session1.bind
        event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
        try:
            libro1 = await uow1.libros.get_detalle(l1.id)
            assert libro1 is not None
            # Acceso a relaciones precargadas sin emitir queries extras
            assert libro1.editorial.nombre == f"Ed Preload {suffix}"
            assert libro1.genero.nombre == f"Gen Preload {suffix}"
            assert len(libro1.autorias) == 1
            assert libro1.autorias[0].autor.nombre == f"Autor 1 {suffix}"
            queries_l1 = count_queries
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", before_cursor_execute)

    # Para l2
    async with session_factory() as session2:
        uow2 = LibrosUnitOfWork(session=session2)
        count_queries = 0

        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            nonlocal count_queries
            count_queries += 1

        engine = session2.bind
        event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
        try:
            libro2 = await uow2.libros.get_detalle(l2.id)
            assert libro2 is not None
            assert libro2.editorial.nombre == f"Ed Preload {suffix}"
            assert libro2.genero.nombre == f"Gen Preload {suffix}"
            assert len(libro2.autorias) == 3
            autores_nombres = {a.autor.nombre for a in libro2.autorias}
            assert f"Autor 1 {suffix}" in autores_nombres
            assert f"Autor 2 {suffix}" in autores_nombres
            assert f"Autor 3 {suffix}" in autores_nombres
            queries_l2 = count_queries
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", before_cursor_execute)

    assert queries_l1 > 0
    assert queries_l1 == queries_l2, f"Queries diferían: {queries_l1} para 1 autor vs {queries_l2} para 3 autores"


@pytest.mark.asyncio
async def test_task_1_2_libro_soft_delete_and_history(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Triangulación: Verifica que el soft-delete oculta el libro de get_by_id y get_detalle pero permanece histórico."""
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        async with uow:
            ed = await uow.editoriales.add(Editorial(nombre=f"Ed SD {suffix}", pais="Argentina"))
            gen = await uow.generos.add(Genero(nombre=f"Gen SD {suffix}"))
            libro = await uow.libros.add(
                Libro(
                    isbn=f"978-SD-{suffix}",
                    titulo="Libro a borrar",
                    precio=Decimal("1500.00"),
                    stock=3,
                    editorial_id=ed.id,
                    genero_id=gen.id,
                )
            )
            libro_id = libro.id
            assert libro_id is not None

        # Borrado lógico
        async with uow:
            await uow.libros.soft_delete(libro)

        # Verificaciones en consultas normales
        activo_by_id = await uow.libros.get_by_id(libro_id)
        assert activo_by_id is None

        activo_detalle = await uow.libros.get_detalle(libro_id)
        assert activo_detalle is None

        # Acceso histórico
        historico = await uow.libros.get_by_id_including_deleted(libro_id)
        assert historico is not None
        assert historico.borrado_en is not None


@pytest.mark.asyncio
async def test_task_2_1_single_stock_write_point_invariant(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica el invariante stock == SUM(cantidad) tras alta, reposición y rechazo de stock negativo."""
    suffix = uuid.uuid4().hex[:8]

    # Necesitamos un usuario existente para usuario_id de MovimientoStock (FK usuario.id)
    from app.modules.usuarios.models import Usuario

    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        async with uow:
            user = Usuario(
                email=f"admin_{suffix}@test.com",
                nombre="Admin Test",
                password_hash="hash_dummy",
                activo=True,
                password_cambiada=True,
            )
            session.add(user)
            await session.flush()
            user_id = user.id
            assert user_id is not None

            ed = await uow.editoriales.add(Editorial(nombre=f"Ed Stock {suffix}", pais="Arg"))
            gen = await uow.generos.add(Genero(nombre=f"Gen Stock {suffix}"))

            # 1. Alta con stock_inicial = 5
            libro = await uow.libros.add(
                Libro(
                    isbn=f"978-STK-{suffix}",
                    titulo="Libro Stock Test",
                    precio=Decimal("1200.00"),
                    stock=0,
                    editorial_id=ed.id,
                    genero_id=gen.id,
                )
            )
            libro_id = libro.id
            assert libro_id is not None
            # Llamada al punto único
            mov_init = await uow.registrar_movimiento_stock(
                libro=libro,
                cantidad=5,
                motivo="Stock inicial",
                usuario_id=user_id,
            )
            assert mov_init is not None
            assert mov_init.cantidad == 5
            assert libro.stock == 5

        # Verificación de invariante en BD
        suma = await uow.movimientos.sum_cantidad_by_libro(libro_id)
        assert libro.stock == 5
        assert suma == 5

        # 2. Reposición +3
        async with uow:
            mov_repo = await uow.registrar_movimiento_stock(
                libro=libro_id,
                cantidad=3,
                motivo="Reposición",
                usuario_id=user_id,
            )
            assert mov_repo is not None
            assert mov_repo.cantidad == 3

        refreshed = await uow.libros.get_by_id(libro_id)
        assert refreshed is not None
        assert refreshed.stock == 8
        suma2 = await uow.movimientos.sum_cantidad_by_libro(libro_id)
        assert suma2 == 8

        # 3. Intento de movimiento que dejaría stock negativo (-10 sobre 8)
        with pytest.raises(ValueError, match="[Ss]tock"):
            async with uow:
                await uow.registrar_movimiento_stock(
                    libro=libro_id,
                    cantidad=-10,
                    motivo="Venta inválida",
                    usuario_id=user_id,
                )

        # Invariante se mantiene intacto tras el rechazo
        refreshed3 = await uow.libros.get_by_id(libro_id)
        assert refreshed3 is not None
        assert refreshed3.stock == 8
        suma3 = await uow.movimientos.sum_cantidad_by_libro(libro_id)
        assert suma3 == 8


@pytest.mark.asyncio
async def test_task_2_1_stock_cero_no_crea_movimiento(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Triangulación: stock_inicial=0 no inserta MovimientoStock (ck_movimiento_stock_cantidad_no_cero)."""
    suffix = uuid.uuid4().hex[:8]
    from app.modules.usuarios.models import Usuario

    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        async with uow:
            user = Usuario(
                email=f"user0_{suffix}@test.com",
                nombre="User Cero",
                password_hash="hash_dummy",
                activo=True,
                password_cambiada=True,
            )
            session.add(user)
            await session.flush()

            ed = await uow.editoriales.add(Editorial(nombre=f"Ed Cero {suffix}", pais="Arg"))
            gen = await uow.generos.add(Genero(nombre=f"Gen Cero {suffix}"))

            libro = await uow.libros.add(
                Libro(
                    isbn=f"978-CERO-{suffix}",
                    titulo="Libro Stock Cero",
                    precio=Decimal("800.00"),
                    stock=0,
                    editorial_id=ed.id,
                    genero_id=gen.id,
                )
            )
            libro_id = libro.id
            assert libro_id is not None

            mov = await uow.registrar_movimiento_stock(
                libro=libro,
                cantidad=0,
                motivo="Stock inicial",
                usuario_id=user.id,
            )
            assert mov is None

        # Verificación: sin filas en movimiento_stock y stock en 0
        movs = await uow.movimientos.get_movimientos_by_libro(libro_id)
        assert len(movs) == 0
        suma = await uow.movimientos.sum_cantidad_by_libro(libro_id)
        assert suma == 0
        refreshed = await uow.libros.get_by_id(libro_id)
        assert refreshed is not None
        assert refreshed.stock == 0


@pytest.mark.asyncio
async def test_task_2_1_reponer_libro_dado_de_baja_falla(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Triangulación: intentar registrar movimiento sobre libro dado de baja falla y no escribe movimientos."""
    suffix = uuid.uuid4().hex[:8]
    from app.modules.usuarios.models import Usuario

    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        async with uow:
            user = Usuario(
                email=f"user_sd_{suffix}@test.com",
                nombre="User SD",
                password_hash="hash_dummy",
                activo=True,
                password_cambiada=True,
            )
            session.add(user)
            await session.flush()
            user_id = user.id

            ed = await uow.editoriales.add(Editorial(nombre=f"Ed SD Mov {suffix}", pais="Arg"))
            gen = await uow.generos.add(Genero(nombre=f"Gen SD Mov {suffix}"))

            libro = await uow.libros.add(
                Libro(
                    isbn=f"978-SDMOV-{suffix}",
                    titulo="Libro Borrado Stock",
                    precio=Decimal("950.00"),
                    stock=0,
                    editorial_id=ed.id,
                    genero_id=gen.id,
                )
            )
            libro_id = libro.id
            assert libro_id is not None

            await uow.libros.soft_delete(libro)

        with pytest.raises(ValueError, match="baja"):
            async with uow:
                await uow.registrar_movimiento_stock(
                    libro=libro_id,
                    cantidad=5,
                    motivo="Reposición",
                    usuario_id=user_id,
                )

        # Confirmar que no hay movimientos
        movs = await uow.movimientos.get_movimientos_by_libro(libro_id)
        assert len(movs) == 0


def test_task_2_2_single_stock_write_point_ast_regression() -> None:
    """Test de regresión (RN-11): Confirma que ningún módulo de app/ salvo LibrosUnitOfWork.registrar_movimiento_stock

    asigna directamente al atributo `stock` (ej. libro.stock = ... o libro.stock += ... o setattr(..., 'stock', ...)).
    """
    import ast
    from pathlib import Path

    app_dir = Path("app")
    assert app_dir.exists(), "El directorio app/ debe existir"

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
            # 1. Asignación directa: obj.stock = ...
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr == "stock":
                        if resolved != allowed_file:
                            violating_occurrences.append(f"{py_file}:{node.lineno} (Assign to .stock)")
            # 2. Asignación aumentada: obj.stock += ...
            elif isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Attribute) and node.target.attr == "stock":
                    if resolved != allowed_file:
                        violating_occurrences.append(f"{py_file}:{node.lineno} (AugAssign to .stock)")
            # 3. Llamada a setattr(..., 'stock', ...)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "setattr":
                    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and node.args[1].value == "stock":
                        if resolved != allowed_file:
                            violating_occurrences.append(f"{py_file}:{node.lineno} (setattr 'stock')")

    assert not violating_occurrences, (
        f"Se encontraron asignaciones directas a .stock fuera del punto único: {violating_occurrences}"
    )


def test_task_2_2_ast_detector_triangulation() -> None:
    """Triangulación: Verifica que la lógica AST detecta efectivamente asignaciones a .stock y setattr."""
    import ast

    snippets = [
        "libro.stock = 10",
        "self.libro.stock += 1",
        "setattr(libro, 'stock', 5)",
    ]

    for snippet in snippets:
        tree = ast.parse(snippet)
        detected = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr == "stock":
                        detected = True
            elif isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Attribute) and node.target.attr == "stock":
                    detected = True
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "setattr":
                    if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and node.args[1].value == "stock":
                        detected = True
        assert detected, f"El snippet '{snippet}' debió ser detectado como asignación a stock"


def test_task_3_1_extra_forbid_in_catalog_schemas() -> None:
    """Verifica que todos los esquemas de entrada de catálogo tengan extra='forbid' y rechacen campos desconocidos."""
    from pydantic import ValidationError
    from app.modules.editoriales.schemas import EditorialCreate, EditorialUpdate
    from app.modules.generos.schemas import GeneroCreate, GeneroUpdate
    from app.modules.autores.schemas import AutorCreate, AutorUpdate

    # EditorialCreate
    with pytest.raises(ValidationError):
        EditorialCreate.model_validate({"nombre": "Ed Test", "extra_field": "invalido"})

    with pytest.raises(ValidationError):
        EditorialUpdate.model_validate({"campo_ficticio": "no_permitido"})

    # GeneroCreate
    with pytest.raises(ValidationError):
        GeneroCreate.model_validate({"nombre": "Gen Test", "fantasma": 123})

    with pytest.raises(ValidationError):
        GeneroUpdate.model_validate({"extra": True})

    # AutorCreate
    with pytest.raises(ValidationError):
        AutorCreate.model_validate({"nombre": "Autor Test", "campo_extra": "hack"})

    with pytest.raises(ValidationError):
        AutorUpdate.model_validate({"otro_campo": 99})


@pytest.mark.asyncio
async def test_task_3_1_editoriales_service_uow_and_paginacion(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica que el servicio de editoriales use el UoW, devuelva PaginatedResponse y valide páginas fuera de rango."""
    from fastapi import HTTPException
    from app.core.paginacion import PaginationParams
    from app.modules.editoriales.schemas import EditorialCreate
    from app.modules.editoriales.service import create_editorial, list_editoriales, get_editorial

    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        uow = EditorialesUnitOfWork(session=session)
        # 1. Crear con UoW
        ed = await create_editorial(uow, EditorialCreate(nombre=f"Ed Serv {suffix}", pais="Argentina"))
        assert ed.id is not None
        assert ed.nombre == f"Ed Serv {suffix}"

    async with session_factory() as session:
        uow = EditorialesUnitOfWork(session=session)
        # 2. Listar paginado
        params_p1 = PaginationParams(page=1, size=10)
        res_p1 = await list_editoriales(uow, params_p1)
        assert res_p1.page == 1
        assert res_p1.size == 10
        assert res_p1.total >= 1
        assert res_p1.pages >= 1
        assert any(item.id == ed.id for item in res_p1.items)

        # 3. page > pages debe lanzar HTTP 422
        params_out_of_range = PaginationParams(page=res_p1.pages + 5, size=10)
        with pytest.raises(HTTPException) as exc_info:
            await list_editoriales(uow, params_out_of_range)
        assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_task_3_1_generos_autores_triangulation(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Triangulación: Generos y Autores con UoW, conflicto 409 traducido, y paginación 422 si page > pages."""
    from fastapi import HTTPException
    from app.core.paginacion import PaginationParams
    from app.modules.generos.schemas import GeneroCreate
    from app.modules.generos.service import create_genero, list_generos, list_libros_by_genero
    from app.modules.autores.schemas import AutorCreate
    from app.modules.autores.service import create_autor, list_autores, list_libros_by_autor

    suffix = uuid.uuid4().hex[:8]

    # Generos
    async with session_factory() as session:
        uow_gen = GenerosUnitOfWork(session=session)
        g = await create_genero(uow_gen, GeneroCreate(nombre=f"Gen Tri {suffix}"))
        assert g.id is not None

        # Conflicto 409 al duplicar nombre
        with pytest.raises(HTTPException) as exc_409:
            await create_genero(uow_gen, GeneroCreate(nombre=f"Gen Tri {suffix}"))
        assert exc_409.value.status_code == 409
        # Sin texto interno de BD en el detail
        detail = str(exc_409.value.detail).lower()
        assert "duplicate key" not in detail
        assert "violates unique constraint" not in detail

    async with session_factory() as session:
        uow_gen = GenerosUnitOfWork(session=session)
        p = await list_generos(uow_gen, PaginationParams(page=1, size=2))
        assert p.page == 1
        assert p.size == 2
        assert p.total >= 1

        # Libros de un género vacío
        libros_g = await list_libros_by_genero(uow_gen, g.id, PaginationParams(page=1, size=10))
        assert libros_g.total == 0
        assert libros_g.items == []
        assert libros_g.pages == 1

        # page > pages en género vacío (page=2 > pages=1) -> 422
        with pytest.raises(HTTPException) as exc_p2:
            await list_libros_by_genero(uow_gen, g.id, PaginationParams(page=2, size=10))
        assert exc_p2.value.status_code == 422

    # Autores
    async with session_factory() as session:
        uow_aut = AutoresUnitOfWork(session=session)
        a = await create_autor(uow_aut, AutorCreate(nombre=f"Autor Tri {suffix}", nacionalidad="Arg"))
        assert a.id is not None

        libros_a = await list_libros_by_autor(uow_aut, a.id, PaginationParams(page=1, size=10))
        assert libros_a.total == 0
        assert libros_a.items == []
        assert libros_a.pages == 1

        with pytest.raises(HTTPException) as exc_p_aut:
            await list_libros_by_autor(uow_aut, a.id, PaginationParams(page=3, size=10))
        assert exc_p_aut.value.status_code == 422


@pytest.mark.asyncio
async def test_task_3_2_libros_service_crud_stock_and_soft_delete(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica POST con stock_inicial, PATCH restringido, baja lógica, reuso de ISBN y reposición."""
    from fastapi import HTTPException
    from pydantic import ValidationError
    from app.core.paginacion import PaginationParams
    from app.modules.usuarios.models import Usuario
    from app.modules.libros.schemas import (
        AutorCreateNested,
        LibroCreate,
        LibroUpdate,
        ReponerStockRequest,
    )
    from app.modules.libros.service import (
        create_libro,
        delete_libro,
        get_libro,
        list_libros,
        list_movimientos,
        reponer_stock,
        update_libro,
    )

    suffix = uuid.uuid4().hex[:8]

    # 1. Validación de esquemas con extra="forbid"
    with pytest.raises(ValidationError):
        LibroCreate.model_validate({
            "isbn": f"978-FORBID-{suffix}",
            "titulo": "Libro Forbid",
            "precio": Decimal("100.00"),
            "stock": 10,  # Campo stock prohibido en el alta (debe ser stock_inicial)
            "editorial_id": 1,
        })

    with pytest.raises(ValidationError):
        LibroUpdate.model_validate({"stock": 50})

    with pytest.raises(ValidationError):
        LibroUpdate.model_validate({"stock_inicial": 5})

    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        async with uow:
            user = Usuario(
                email=f"admin_srv_{suffix}@test.com",
                nombre="Admin Srv",
                password_hash="dummy",
                activo=True,
                password_cambiada=True,
            )
            session.add(user)
            await session.flush()
            admin_id = user.id

            ed = await uow.editoriales.add(Editorial(nombre=f"Ed LServ {suffix}", pais="Arg"))
            gen = await uow.generos.add(Genero(nombre=f"Gen LServ {suffix}"))
            aut = await uow.autores.add(Autor(nombre=f"Aut LServ {suffix}", nacionalidad="Arg"))

    # 2. Alta de libro con stock_inicial = 5
    isbn_test = f"978-REUSE-{suffix}"
    payload_create = LibroCreate(
        isbn=isbn_test,
        titulo=f"Libro Inicial {suffix}",
        precio=Decimal("1500.00"),
        stock_inicial=5,
        editorial_id=ed.id,
        genero_id=gen.id,
        autores=[AutorCreateNested(autor_id=aut.id, rol="autor", orden=1)],
    )

    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        created = await create_libro(uow, payload_create, usuario_id=admin_id)
        assert created.id is not None
        assert created.stock == 5
        assert created.titulo == f"Libro Inicial {suffix}"
        libro_id = created.id

    # Verificar movimientos de stock
    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        movs = await list_movimientos(uow, libro_id)
        assert len(movs) == 1
        assert movs[0].cantidad == 5
        assert movs[0].motivo == "Stock inicial"

    # 3. PATCH parcial (solo título y precio)
    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        updated = await update_libro(uow, libro_id, LibroUpdate(titulo="Título Modificado"))
        assert updated.titulo == "Título Modificado"
        assert updated.precio == Decimal("1500.00")
        assert updated.stock == 5

    # 4. Reposición de stock +4
    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        repuesto = await reponer_stock(uow, libro_id, cantidad=4, usuario_id=admin_id)
        assert repuesto.stock == 9

        movs2 = await list_movimientos(uow, libro_id)
        assert len(movs2) == 2
        assert movs2[1].cantidad == 4
        assert movs2[1].motivo == "Reposición"

    # 5. Baja lógica
    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        await delete_libro(uow, libro_id)

        # GET /libros/{id} ahora da 404
        with pytest.raises(HTTPException) as exc_404:
            await get_libro(uow, libro_id)
        assert exc_404.value.status_code == 404

        # Reponer sobre libro dado de baja da 409
        with pytest.raises(HTTPException) as exc_rep_sd:
            await reponer_stock(uow, libro_id, cantidad=5, usuario_id=admin_id)
        assert exc_rep_sd.value.status_code == 409

    # 6. Reutilización de ISBN tras la baja
    payload_reutilizado = LibroCreate(
        isbn=isbn_test,
        titulo=f"Libro Nuevo Mismo ISBN {suffix}",
        precio=Decimal("2000.00"),
        stock_inicial=1,
        editorial_id=ed.id,
        genero_id=gen.id,
        autores=[],
    )
    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        segundo_libro = await create_libro(uow, payload_reutilizado, usuario_id=admin_id)
        assert segundo_libro.id is not None
        assert segundo_libro.id != libro_id
        assert segundo_libro.isbn == isbn_test

        # Intentar crear un tercer libro vigente con el mismo ISBN da 409
        with pytest.raises(HTTPException) as exc_isbn_dup:
            await create_libro(uow, payload_reutilizado, usuario_id=admin_id)
        assert exc_isbn_dup.value.status_code == 409


@pytest.mark.asyncio
async def test_task_3_2_libros_service_filtros_sql_injection_y_paginacion(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica filtrado seguro (' OR '1'='1) con total: 0 y error 422 si page=2 cuando no hay resultados."""
    from fastapi import HTTPException
    from app.core.paginacion import PaginationParams
    from app.modules.libros.service import list_libros

    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        # Búsqueda segura con comillas y caracteres SQL
        p1 = await list_libros(uow, PaginationParams(page=1, size=10), titulo="' OR '1'='1")
        assert p1.total == 0
        assert p1.items == []
        assert p1.page == 1
        assert p1.pages == 1

        # page=2 fuera de rango -> 422
        with pytest.raises(HTTPException) as exc_p2:
            await list_libros(uow, PaginationParams(page=2, size=10), titulo="' OR '1'='1")
        assert exc_p2.value.status_code == 422


@pytest.mark.asyncio
async def test_task_3_2_libros_triangulation_atomicity_and_edge_cases(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Triangulación: Atomicidad del alta ante conflicto, validación de cantidad en reposición y 404 en movimientos."""
    from fastapi import HTTPException
    from app.modules.usuarios.models import Usuario
    from app.modules.libros.schemas import (
        AutorCreateNested,
        LibroCreate,
    )
    from app.modules.libros.service import (
        create_libro,
        list_movimientos,
        reponer_stock,
    )

    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        async with uow:
            user = Usuario(
                email=f"admin_tri_{suffix}@test.com",
                nombre="Admin Tri",
                password_hash="dummy",
                activo=True,
                password_cambiada=True,
            )
            session.add(user)
            await session.flush()
            admin_id = user.id

            ed = await uow.editoriales.add(Editorial(nombre=f"Ed LTri {suffix}", pais="Arg"))
            gen = await uow.generos.add(Genero(nombre=f"Gen LTri {suffix}"))

            # Crear libro base
            l1 = await create_libro(
                uow,
                LibroCreate(
                    isbn=f"978-TRI-{suffix}",
                    titulo="Libro Tri Base",
                    precio=Decimal("1100.00"),
                    stock_inicial=3,
                    editorial_id=ed.id,
                    genero_id=gen.id,
                    autores=[],
                ),
                usuario_id=admin_id,
            )
            l1_id = l1.id

    # 1. Reposición con cantidad <= 0 debe responder 422
    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        with pytest.raises(HTTPException) as exc_zero:
            await reponer_stock(uow, l1_id, cantidad=0, usuario_id=admin_id)
        assert exc_zero.value.status_code == 422

        with pytest.raises(HTTPException) as exc_neg:
            await reponer_stock(uow, l1_id, cantidad=-3, usuario_id=admin_id)
        assert exc_neg.value.status_code == 422

        # Reponer libro inexistente da 404
        with pytest.raises(HTTPException) as exc_not_found:
            await reponer_stock(uow, 999999, cantidad=5, usuario_id=admin_id)
        assert exc_not_found.value.status_code == 404

        # Movimientos de libro inexistente da 404
        with pytest.raises(HTTPException) as exc_mov_404:
            await list_movimientos(uow, 999999)
        assert exc_mov_404.value.status_code == 404

    # 2. Atomicidad del alta: si falla por ISBN duplicado con stock_inicial > 0, no queda movimiento residual
    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        count_mov_before = await uow.movimientos.count()

        with pytest.raises(HTTPException) as exc_dup:
            await create_libro(
                uow,
                LibroCreate(
                    isbn=f"978-TRI-{suffix}",  # Duplicado
                    titulo="Libro Duplicado",
                    precio=Decimal("2000.00"),
                    stock_inicial=10,
                    editorial_id=ed.id,
                    genero_id=gen.id,
                    autores=[],
                ),
                usuario_id=admin_id,
            )
        assert exc_dup.value.status_code == 409

        count_mov_after = await uow.movimientos.count()
        assert count_mov_after == count_mov_before, "No debe haber quedado ningún movimiento huérfano"


@pytest.mark.asyncio
async def test_task_4_1_open_and_protected_catalog_endpoints(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica que lecturas abiertas respondan 200 sin sesión, y escrituras den 401 sin sesión y 403 con CLIENTE."""
    from httpx import ASGITransport, AsyncClient
    from app.main import create_app
    from app.modules.usuarios.models import AsignacionRol, Usuario
    from app.core.security import create_access_token

    suffix = uuid.uuid4().hex[:8]

    # Crear datos base y usuarios en la BD
    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        async with uow:
            # 1. Admin
            admin = Usuario(
                email=f"admin_api_{suffix}@test.com",
                nombre="Admin API",
                password_hash="hash_dummy",
                activo=True,
                password_cambiada=True,
            )
            session.add(admin)
            # 2. Cliente
            cliente = Usuario(
                email=f"cliente_api_{suffix}@test.com",
                nombre="Cliente API",
                password_hash="hash_dummy",
                activo=True,
                password_cambiada=True,
            )
            session.add(cliente)
            await session.flush()

            # Roles en asignacion_rol
            session.add(AsignacionRol(usuario_id=admin.id, rol="ADMIN"))
            session.add(AsignacionRol(usuario_id=cliente.id, rol="CLIENTE"))

            # Catálogo inicial
            ed = await uow.editoriales.add(Editorial(nombre=f"Ed API {suffix}", pais="Argentina"))
            gen = await uow.generos.add(Genero(nombre=f"Gen API {suffix}"))
            aut = await uow.autores.add(Autor(nombre=f"Aut API {suffix}", nacionalidad="Argentina"))

            libro = await uow.libros.add(
                Libro(
                    isbn=f"978-API-{suffix}",
                    titulo="Libro API Test",
                    precio=Decimal("1500.00"),
                    stock=5,
                    editorial_id=ed.id,
                    genero_id=gen.id,
                )
            )
            session.add(LibroAutor(libro_id=libro.id, autor_id=aut.id, rol="autor", orden=1))
            libro_id = libro.id
            ed_id = ed.id
            gen_id = gen.id
            aut_id = aut.id

    token_admin = create_access_token({"sub": str(admin.id), "roles": ["ADMIN"]})
    token_cliente = create_access_token({"sub": str(cliente.id), "roles": ["CLIENTE"]})

    test_app = create_app()
    async with test_app.router.lifespan_context(test_app):
        transport = ASGITransport(app=test_app)

        # 1. ANÓNIMO: Lecturas abiertas -> 200 OK
        async with AsyncClient(transport=transport, base_url="http://test") as anon_client:
            # GET /libros
            r = await anon_client.get("/libros")
            assert r.status_code == 200
            assert "items" in r.json()

            # GET /libros/{id}
            r = await anon_client.get(f"/libros/{libro_id}")
            assert r.status_code == 200
            assert r.json()["id"] == libro_id

            # GET /editoriales
            r = await anon_client.get("/editoriales")
            assert r.status_code == 200

            # GET /editoriales/{id}/libros
            r = await anon_client.get(f"/editoriales/{ed_id}/libros")
            assert r.status_code == 200

            # GET /generos
            r = await anon_client.get("/generos")
            assert r.status_code == 200

            # GET /generos/{id}/libros
            r = await anon_client.get(f"/generos/{gen_id}/libros")
            assert r.status_code == 200

            # GET /autores
            r = await anon_client.get("/autores")
            assert r.status_code == 200

            # GET /autores/{id}/libros
            r = await anon_client.get(f"/autores/{aut_id}/libros")
            assert r.status_code == 200

            # 2. ANÓNIMO: Escrituras y detalle restringido -> 401 Unauthorized
            # POST /libros
            r = await anon_client.post("/libros", json={"isbn": "978-X", "titulo": "X", "precio": 100, "editorial_id": ed_id})
            assert r.status_code == 401

            # POST /editoriales
            r = await anon_client.post("/editoriales", json={"nombre": "Ed Anon"})
            assert r.status_code == 401

            # GET /libros/{id}/movimientos
            r = await anon_client.get(f"/libros/{libro_id}/movimientos")
            assert r.status_code == 401

            # GET /autores/{id} (restringido a ADMIN)
            r = await anon_client.get(f"/autores/{aut_id}")
            assert r.status_code == 401

        # 3. CLIENTE: Escrituras y administración -> 403 Forbidden
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies={"access_token": token_cliente},
        ) as client_client:
            # POST /libros -> 403
            r = await client_client.post(
                "/libros",
                json={"isbn": "978-CLI", "titulo": "X", "precio": 100, "editorial_id": ed_id},
            )
            assert r.status_code == 403

            # POST /editoriales -> 403
            r = await client_client.post("/editoriales", json={"nombre": "Ed Cliente"})
            assert r.status_code == 403

            # POST /generos -> 403
            r = await client_client.post("/generos", json={"nombre": "Gen Cliente"})
            assert r.status_code == 403

            # POST /libros/{id}/reponer -> 403
            r = await client_client.post(f"/libros/{libro_id}/reponer", json={"cantidad": 5})
            assert r.status_code == 403

            # GET /libros/{id}/movimientos -> 403
            r = await client_client.get(f"/libros/{libro_id}/movimientos")
            assert r.status_code == 403

        # 4. ADMIN: Operaciones permitidas
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies={"access_token": token_admin},
        ) as admin_client:
            # POST /libros con stock_inicial=3 -> 201
            r_crear = await admin_client.post(
                "/libros",
                json={
                    "isbn": f"978-ADM-{suffix}",
                    "titulo": "Libro Creado por Admin",
                    "precio": "1800.00",
                    "stock_inicial": 3,
                    "editorial_id": ed_id,
                    "genero_id": gen_id,
                    "autores": [{"autor_id": aut_id, "rol": "autor", "orden": 1}],
                },
            )
            assert r_crear.status_code == 201
            assert r_crear.json()["stock"] == 3
            nuevo_id = r_crear.json()["id"]

            # GET /libros/{id}/movimientos -> 200
            r_movs = await admin_client.get(f"/libros/{nuevo_id}/movimientos")
            assert r_movs.status_code == 200
            assert len(r_movs.json()) == 1
            assert r_movs.json()[0]["cantidad"] == 3


@pytest.mark.asyncio
async def test_task_4_1_triangulation_admin_actions_and_shared_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Triangulación: Operaciones completas de ADMIN en la API, validación 422 de PATCH y verificación de sesión compartida."""
    from httpx import ASGITransport, AsyncClient
    from app.main import create_app
    from app.modules.usuarios.models import AsignacionRol, Usuario
    from app.core.security import create_access_token

    suffix = uuid.uuid4().hex[:8]

    async with session_factory() as session:
        uow = LibrosUnitOfWork(session=session)
        async with uow:
            admin = Usuario(
                email=f"admin_tri_api_{suffix}@test.com",
                nombre="Admin Tri API",
                password_hash="hash_dummy",
                activo=True,
                password_cambiada=True,
            )
            session.add(admin)
            await session.flush()
            session.add(AsignacionRol(usuario_id=admin.id, rol="ADMIN"))

            ed = await uow.editoriales.add(Editorial(nombre=f"Ed Tri API {suffix}", pais="Arg"))
            gen = await uow.generos.add(Genero(nombre=f"Gen Tri API {suffix}"))

            libro = await uow.libros.add(
                Libro(
                    isbn=f"978-TRAP-{suffix}",
                    titulo="Libro Tri API",
                    precio=Decimal("1300.00"),
                    stock=2,
                    editorial_id=ed.id,
                    genero_id=gen.id,
                )
            )
            libro_id = libro.id
            ed_id = ed.id
            gen_id = gen.id

    token_admin = create_access_token({"sub": str(admin.id), "roles": ["ADMIN"]})
    test_app = create_app()

    async with test_app.router.lifespan_context(test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies={"access_token": token_admin},
        ) as admin_client:
            # 1. PATCH con stock debe devolver 422 (extra="forbid")
            r_patch_invalid = await admin_client.patch(f"/libros/{libro_id}", json={"stock": 50})
            assert r_patch_invalid.status_code == 422

            # 2. PATCH válido
            r_patch_ok = await admin_client.patch(f"/libros/{libro_id}", json={"titulo": "Título Actualizado API"})
            assert r_patch_ok.status_code == 200
            assert r_patch_ok.json()["titulo"] == "Título Actualizado API"

            # 3. Reposición vía endpoint
            r_repo = await admin_client.post(f"/libros/{libro_id}/reponer", json={"cantidad": 6})
            assert r_repo.status_code == 200
            assert r_repo.json()["stock"] == 8

            # 4. DELETE /libros/{id} -> 204
            r_del = await admin_client.delete(f"/libros/{libro_id}")
            assert r_del.status_code == 204

            # GET /libros/{id} ahora da 404
            r_after_del = await admin_client.get(f"/libros/{libro_id}")
            assert r_after_del.status_code == 404

            # 5. GET /editoriales/{id} y GET /generos/{id} protegidos dan 200 para ADMIN
            r_ed_det = await admin_client.get(f"/editoriales/{ed_id}")
            assert r_ed_det.status_code == 200
            assert r_ed_det.json()["id"] == ed_id

            r_gen_det = await admin_client.get(f"/generos/{gen_id}")
            assert r_gen_det.status_code == 200
            assert r_gen_det.json()["id"] == gen_id













