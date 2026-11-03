"""Tests bajo Strict TDD para C-13: Repositorios, UoW, Schemas, Servicio y Router de Autenticación (/auth)."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.modules.clientes.models import Cliente


@pytest.fixture
async def in_memory_session() -> AsyncGenerator[AsyncSession, None]:
    """Crea una base de datos SQLite en memoria para tests unitarios/integrados."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


class TestClienteRepository:
    """Pruebas unitarias para ClienteRepository heredando de BaseRepository (Tarea 1.1)."""

    @pytest.mark.asyncio
    async def test_cliente_repository_add_and_get_by_id(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Agregar y recuperar un cliente por ID vía ClienteRepository."""
        from app.modules.clientes.repository import ClienteRepository

        repo = ClienteRepository(session=in_memory_session)
        cliente = Cliente(nombre="Juan Pérez", email="juan@example.com")
        saved = await repo.add(cliente)
        assert saved.id is not None

        retrieved = await repo.get_by_id(saved.id)
        assert retrieved is not None
        assert retrieved.email == "juan@example.com"
        assert retrieved.nombre == "Juan Pérez"

    @pytest.mark.asyncio
    async def test_cliente_repository_get_by_email(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Buscar un cliente por email existente e inexistente."""
        from app.modules.clientes.repository import ClienteRepository

        repo = ClienteRepository(session=in_memory_session)
        cliente = Cliente(nombre="Ana Gómez", email="ana@example.com")
        await repo.add(cliente)

        found = await repo.get_by_email("ana@example.com")
        assert found is not None
        assert found.nombre == "Ana Gómez"

        not_found = await repo.get_by_email("noexiste@example.com")
        assert not_found is None

    @pytest.mark.asyncio
    async def test_cliente_repository_count_and_update(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Contar clientes y actualizar datos respetando flush sin commit."""
        from app.modules.clientes.repository import ClienteRepository

        repo = ClienteRepository(session=in_memory_session)
        assert await repo.count() == 0

        c = await repo.add(Cliente(nombre="Carlos Ruiz", email="carlos@example.com"))
        assert await repo.count() == 1

        c.nombre = "Carlos Alberto Ruiz"
        updated = await repo.update(c)
        assert updated.nombre == "Carlos Alberto Ruiz"


class TestUsuariosRepositories:
    """Pruebas unitarias para repositorios de persistencia del módulo usuarios (Tarea 1.2)."""

    @pytest.mark.asyncio
    async def test_usuario_repository_add_and_get_by_email(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Persistir y buscar Usuario por email."""
        from app.modules.usuarios.models import Usuario
        from app.modules.usuarios.repository import UsuarioRepository

        repo = UsuarioRepository(session=in_memory_session)
        u = Usuario(
            email="admin@libreria.com",
            nombre="Admin General",
            password_hash="$2b$04$dummyhash",
            activo=True,
            debe_cambiar_password=False,
        )
        saved = await repo.add(u)
        assert saved.id is not None

        found = await repo.get_by_email("admin@libreria.com")
        assert found is not None
        assert found.nombre == "Admin General"
        assert await repo.get_by_email("otro@libreria.com") is None

    @pytest.mark.asyncio
    async def test_asignacion_rol_repository_roles_vigentes(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Consultar roles vigentes ignorando revocados y vencidos."""
        from datetime import datetime, timedelta, timezone
        from app.modules.usuarios.models import AsignacionRol, Usuario
        from app.modules.usuarios.repository import AsignacionRolRepository, UsuarioRepository

        u_repo = UsuarioRepository(session=in_memory_session)
        u = await u_repo.add(
            Usuario(
                email="vendedor@libreria.com",
                nombre="Vendedor Uno",
                password_hash="hash",
                activo=True,
            )
        )

        rol_repo = AsignacionRolRepository(session=in_memory_session)
        # Rol 1: CLIENTE activo sin vencimiento
        await rol_repo.add(AsignacionRol(usuario_id=u.id, rol="CLIENTE"))
        # Rol 2: VENDEDOR activo con vencimiento futuro
        await rol_repo.add(
            AsignacionRol(
                usuario_id=u.id,
                rol="VENDEDOR",
                vence_en=datetime.now(timezone.utc) + timedelta(days=1),
            )
        )
        # Rol 3: ADMIN revocado
        await rol_repo.add(
            AsignacionRol(
                usuario_id=u.id,
                rol="ADMIN",
                revocada_en=datetime.now(timezone.utc),
            )
        )

        roles = await rol_repo.get_roles_vigentes_usuario(u.id)
        assert set(roles) == {"CLIENTE", "VENDEDOR"}
        asignaciones = await rol_repo.get_asignaciones_vigentes(u.id)
        assert len(asignaciones) == 2

        # Usuario 2: con rol vencido en el pasado
        u2 = await u_repo.add(
            Usuario(
                email="vencido@libreria.com",
                nombre="Usuario Vencido",
                password_hash="hash",
                activo=True,
            )
        )
        await rol_repo.add(
            AsignacionRol(
                usuario_id=u2.id,
                rol="VENDEDOR",
                vence_en=datetime.now(timezone.utc) - timedelta(hours=1),
            )
        )
        roles_u2 = await rol_repo.get_roles_vigentes_usuario(u2.id)
        assert roles_u2 == []

    @pytest.mark.asyncio
    async def test_intento_acceso_contar_fallos_recientes_y_reinicio_por_exito(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Conteo de fallos en ventana de 60s y reinicio tras login exitoso (RN-07)."""
        from datetime import datetime, timedelta, timezone
        from app.modules.usuarios.models import IntentoAcceso
        from app.modules.usuarios.repository import IntentoAccesoRepository

        repo = IntentoAccesoRepository(session=in_memory_session)
        now = datetime.now(timezone.utc)
        email = "test@user.com"
        ip = "192.168.1.50"

        # 3 fallos hace 30 segundos
        for _ in range(3):
            await repo.add(IntentoAcceso(email=email, ip=ip, exito=False, cuando=now - timedelta(seconds=30)))

        count = await repo.contar_fallos_recientes(email=email, ip=ip, ventana_segundos=60)
        assert count == 3

        # Login exitoso hace 20 segundos
        await repo.add(IntentoAcceso(email=email, ip=ip, exito=True, cuando=now - timedelta(seconds=20)))

        # Conteo debe reiniciarse a 0 porque no hubo fallos posteriores al éxito
        count_after_success = await repo.contar_fallos_recientes(email=email, ip=ip, ventana_segundos=60)
        assert count_after_success == 0

        # Nuevo fallo posterior al éxito
        await repo.add(IntentoAcceso(email=email, ip=ip, exito=False, cuando=now - timedelta(seconds=5)))
        assert await repo.contar_fallos_recientes(email=email, ip=ip, ventana_segundos=60) == 1

    @pytest.mark.asyncio
    async def test_evento_seguridad_repository_registrar_evento(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Registrar eventos de seguridad en bitácora (RN-16)."""
        from app.modules.usuarios.repository import EventoSeguridadRepository

        repo = EventoSeguridadRepository(session=in_memory_session)
        ev = await repo.registrar_evento(actor="admin@libreria.com", accion="ALTA_USUARIO")
        assert ev.id is not None
        assert ev.actor == "admin@libreria.com"
        assert ev.accion == "ALTA_USUARIO"


class TestUsuariosUnitOfWork:
    """Pruebas unitarias para UsuariosUnitOfWork (Tarea 1.3)."""

    @pytest.mark.asyncio
    async def test_usuarios_uow_atomic_commit(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: UsuariosUnitOfWork persiste atómicamente Usuario, AsignacionRol y Cliente."""
        from app.modules.clientes.models import Cliente
        from app.modules.usuarios.models import AsignacionRol, Usuario
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        uow = UsuariosUnitOfWork(session=in_memory_session)
        async with uow:
            u = await uow.usuarios.add(
                Usuario(
                    email="uow_user@test.com",
                    nombre="UoW User",
                    password_hash="hashed",
                    activo=True,
                )
            )
            await uow.asignaciones_rol.add(
                AsignacionRol(usuario_id=u.id, rol="CLIENTE")
            )
            await uow.clientes.add(
                Cliente(nombre="UoW User", email="uow_user@test.com", usuario_id=u.id)
            )

        # Verificar que las tres entidades se persistieron
        saved_u = await uow.usuarios.get_by_email("uow_user@test.com")
        assert saved_u is not None
        roles = await uow.asignaciones_rol.get_roles_vigentes_usuario(saved_u.id)
        assert roles == ["CLIENTE"]
        cliente = await uow.clientes.get_by_email("uow_user@test.com")
        assert cliente is not None
        assert cliente.usuario_id == saved_u.id

    @pytest.mark.asyncio
    async def test_usuarios_uow_rollback_on_exception(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: UsuariosUnitOfWork revierte todo en caso de excepción."""
        from app.modules.usuarios.models import Usuario
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        uow = UsuariosUnitOfWork(session=in_memory_session)
        with pytest.raises(RuntimeError, match="Fallo simulado"):
            async with uow:
                await uow.usuarios.add(
                    Usuario(
                        email="rollback@test.com",
                        nombre="Rollback User",
                        password_hash="hashed",
                        activo=True,
                    )
                )
                raise RuntimeError("Fallo simulado")

        saved = await uow.usuarios.get_by_email("rollback@test.com")
        assert saved is None


class TestAuthSchemas:
    """Pruebas unitarias para esquemas DTO de autenticación (Tarea 2.1)."""

    def test_registro_request_valid_and_extra_forbid(self) -> None:
        """Scenario: Schema acepta datos válidos y rechaza campos extras con extra='forbid'."""
        from pydantic import ValidationError
        from app.modules.usuarios.schemas import UsuarioRegistroRequest

        valid = UsuarioRegistroRequest(
            nombre="Lucas",
            email="lucas@test.com",
            password="securePassword123",
        )
        assert valid.nombre == "Lucas"
        assert valid.email == "lucas@test.com"

        # Rechazo por extra field
        with pytest.raises(ValidationError):
            UsuarioRegistroRequest(
                nombre="Lucas",
                email="lucas@test.com",
                password="securePassword123",
                campo_extra="no_permitido",
            )

    def test_schemas_validate_72_bytes_password_limit(self) -> None:
        """Scenario: Schemas rechazan contraseñas > 72 bytes UTF-8."""
        from pydantic import ValidationError
        from app.modules.usuarios.schemas import (
            CambiarPasswordRequest,
            LoginRequest,
            UsuarioRegistroRequest,
        )

        long_pwd = "a" * 73
        with pytest.raises(ValidationError):
            UsuarioRegistroRequest(nombre="Test", email="t@test.com", password=long_pwd)

        with pytest.raises(ValidationError):
            LoginRequest(email="t@test.com", password=long_pwd)

        with pytest.raises(ValidationError):
            CambiarPasswordRequest(password_actual="valid123", password_nueva=long_pwd)

        with pytest.raises(ValidationError):
            CambiarPasswordRequest(password_actual=long_pwd, password_nueva="valid123")

    def test_schemas_do_not_expose_password_hash(self) -> None:
        """Scenario: Schemas de respuesta no exponen password_hash."""
        from app.modules.usuarios.schemas import (
            LoginResponse,
            MensajeResponse,
            UsuarioYoResponse,
        )

        for schema_cls in (LoginResponse, UsuarioYoResponse, MensajeResponse):
            assert "password_hash" not in schema_cls.model_fields


class TestAuthServiceRegistro:
    """Pruebas unitarias para el servicio de registro de usuarios (Tarea 3.1)."""

    @pytest.mark.asyncio
    async def test_registro_exitoso_crea_tres_entidades(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Auto-registro crea Usuario, AsignacionRol(CLIENTE) y Cliente en un solo UoW (RN-02)."""
        from app.modules.usuarios.schemas import UsuarioRegistroRequest
        from app.modules.usuarios.service import AuthService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = AuthService()

        req = UsuarioRegistroRequest(
            nombre="Laura Paz",
            email="laura@libreria.com",
            password="Password123!",
        )

        res = await service.registro(datos=req, uow=uow)
        assert res.email == "laura@libreria.com"
        assert res.nombre == "Laura Paz"

        # Verificar persistencia atómica
        saved_u = await uow.usuarios.get_by_email("laura@libreria.com")
        assert saved_u is not None
        assert saved_u.debe_cambiar_password is False
        assert saved_u.activo is True

        roles = await uow.asignaciones_rol.get_roles_vigentes_usuario(saved_u.id)
        assert roles == ["CLIENTE"]

        saved_c = await uow.clientes.get_by_email("laura@libreria.com")
        assert saved_c is not None
        assert saved_c.usuario_id == saved_u.id

    @pytest.mark.asyncio
    async def test_registro_conflicto_email_existente_responde_409(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Correo duplicado en usuario o cliente produce 409 Conflict sin tocar datos previos (RN-02, C-02)."""
        from fastapi import HTTPException
        from app.modules.clientes.models import Cliente
        from app.modules.usuarios.schemas import UsuarioRegistroRequest
        from app.modules.usuarios.service import AuthService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = AuthService()

        # Insertamos un cliente de mostrador previo con email 'mostrador@test.com'
        async with uow:
            await uow.clientes.add(Cliente(nombre="Cliente Previo", email="mostrador@test.com"))

        req = UsuarioRegistroRequest(
            nombre="Intento Registro",
            email="mostrador@test.com",
            password="Password123!",
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.registro(datos=req, uow=uow)

        assert exc_info.value.status_code == 409
        assert "ya registrado" in exc_info.value.detail.lower() or "conflicto" in exc_info.value.detail.lower()

        # Verificar que no quedó el usuario registrado
        assert await uow.usuarios.get_by_email("mostrador@test.com") is None


class TestAuthServiceLogin:
    """Pruebas unitarias para el servicio de login (Tarea 3.2)."""

    @pytest.mark.asyncio
    async def test_login_exitoso_genera_token_y_audita_exito(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Login correcto retorna token, LoginResponse y persiste intento exitoso (C-03)."""
        from app.core.security import hash_password
        from app.modules.usuarios.models import AsignacionRol, Usuario
        from app.modules.usuarios.schemas import LoginRequest
        from app.modules.usuarios.service import AuthService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = AuthService()

        # Mock o fábrica para session_factory
        session_factory = async_sessionmaker(
            in_memory_session.bind,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        pwd_hash = await hash_password("ValidPassword123!")
        async with uow:
            u = await uow.usuarios.add(
                Usuario(
                    email="login_user@test.com",
                    nombre="Login User",
                    password_hash=pwd_hash,
                    activo=True,
                    debe_cambiar_password=False,
                )
            )
            await uow.asignaciones_rol.add(AsignacionRol(usuario_id=u.id, rol="VENDEDOR"))

        req = LoginRequest(email="login_user@test.com", password="ValidPassword123!")
        token, resp = await service.login(
            datos=req,
            client_ip="127.0.0.1",
            uow=uow,
            session_factory=session_factory,
            dummy_password_hash="$2b$04$dummy",
        )

        assert token is not None
        assert resp.debe_cambiar_password is False
        assert resp.expira_en_segundos > 0

        # Verificar auditoría
        intentos = await uow.intentos_acceso.get_all()
        assert len(intentos) == 1
        assert intentos[0].exito is True
        assert intentos[0].email == "login_user@test.com"

    @pytest.mark.asyncio
    async def test_login_password_incorrecta_responde_401_y_audita_fallo(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Login con contraseña incorrecta da 401 y audita intento fallido (RN-08, C-04)."""
        from fastapi import HTTPException
        from app.core.security import hash_password
        from app.modules.usuarios.models import Usuario
        from app.modules.usuarios.schemas import LoginRequest
        from app.modules.usuarios.service import AuthService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = AuthService()
        session_factory = async_sessionmaker(
            in_memory_session.bind,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        pwd_hash = await hash_password("CorrectPassword123!")
        async with uow:
            await uow.usuarios.add(
                Usuario(
                    email="bad_pass@test.com",
                    nombre="Bad Pass User",
                    password_hash=pwd_hash,
                    activo=True,
                )
            )

        req = LoginRequest(email="bad_pass@test.com", password="WrongPassword!")
        with pytest.raises(HTTPException) as exc_info:
            await service.login(
                datos=req,
                client_ip="127.0.0.1",
                uow=uow,
                session_factory=session_factory,
                dummy_password_hash="$2b$04$dummy",
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Credenciales inválidas"

        # Verificar auditoría con exito=False
        intentos = await uow.intentos_acceso.get_all()
        assert len(intentos) == 1
        assert intentos[0].exito is False

    @pytest.mark.asyncio
    async def test_login_usuario_inexistente_tiempo_constante_dummy_y_401(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Usuario inexistente ejecuta dummy y responde 401 idéntico (RN-08, C-04)."""
        from fastapi import HTTPException
        from app.core.security import hash_password
        from app.modules.usuarios.schemas import LoginRequest
        from app.modules.usuarios.service import AuthService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = AuthService()
        session_factory = async_sessionmaker(
            in_memory_session.bind,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        dummy_hash = await hash_password("dummy")

        req = LoginRequest(email="non_existent@test.com", password="SomePassword123!")
        with pytest.raises(HTTPException) as exc_info:
            await service.login(
                datos=req,
                client_ip="127.0.0.1",
                uow=uow,
                session_factory=session_factory,
                dummy_password_hash=dummy_hash,
            )

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Credenciales inválidas"

        intentos = await uow.intentos_acceso.get_all()
        assert len(intentos) == 1
        assert intentos[0].exito is False
        assert intentos[0].email == "non_existent@test.com"

    @pytest.mark.asyncio
    async def test_login_rate_limiting_5_fallos_bloquea_429(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: 5 intentos fallidos previos disparan 429 Retry-After sin calcular bcrypt (RN-07, C-05)."""
        from datetime import datetime, timedelta, timezone
        from fastapi import HTTPException
        from app.modules.usuarios.models import IntentoAcceso
        from app.modules.usuarios.schemas import LoginRequest
        from app.modules.usuarios.service import AuthService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = AuthService()
        session_factory = async_sessionmaker(
            in_memory_session.bind,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        email = "brute_force@test.com"
        ip = "200.50.10.1"
        now = datetime.now(timezone.utc)

        # Insertar 5 fallos previos dentro de los 60s
        async with uow:
            for i in range(5):
                await uow.intentos_acceso.add(
                    IntentoAcceso(
                        email=email,
                        ip=ip,
                        exito=False,
                        cuando=now - timedelta(seconds=10 + i),
                    )
                )

        req = LoginRequest(email=email, password="AnyPassword123!")
        with pytest.raises(HTTPException) as exc_info:
            await service.login(
                datos=req,
                client_ip=ip,
                uow=uow,
                session_factory=session_factory,
                dummy_password_hash="dummy",
            )

        assert exc_info.value.status_code == 429
        assert exc_info.value.headers.get("Retry-After") == "60"

        # Verificar que el 6to intento fallido (que dio 429) también quedó registrado
        intentos = await uow.intentos_acceso.get_all()
        assert len(intentos) == 6


class TestAuthServiceYoAndCambiarPassword:
    """Pruebas unitarias para introspección y cambio de password (Tarea 3.3)."""

    @pytest.mark.asyncio
    async def test_obtener_yo_roles_vigentes_vs_token(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: GET /auth/yo contrasta roles vigentes en BD contra los del token (C-07)."""
        from app.modules.usuarios.models import AsignacionRol, Usuario
        from app.modules.usuarios.service import AuthService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = AuthService()

        async with uow:
            u = await uow.usuarios.add(
                Usuario(
                    email="yo_user@test.com",
                    nombre="Yo User",
                    password_hash="hash",
                    activo=True,
                    debe_cambiar_password=False,
                )
            )
            await uow.asignaciones_rol.add(AsignacionRol(usuario_id=u.id, rol="CLIENTE"))

        # Supongamos que el token decía ["ADMIN", "CLIENTE"], pero en la base sólo tiene "CLIENTE"
        resp = await service.obtener_yo(
            usuario=u,
            token_roles=["ADMIN", "CLIENTE"],
            uow=uow,
        )

        assert resp.id == u.id
        assert resp.email == "yo_user@test.com"
        assert resp.roles_vigentes == ["CLIENTE"]
        assert resp.roles_token == ["ADMIN", "CLIENTE"]

    @pytest.mark.asyncio
    async def test_cambiar_password_exitoso_actualiza_hash_y_registra_evento(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Cambio de password exitoso actualiza hash, quita flag y crea evento_seguridad (RN-16, C-09)."""
        from app.core.security import hash_password, verify_password
        from app.modules.usuarios.models import Usuario
        from app.modules.usuarios.schemas import CambiarPasswordRequest
        from app.modules.usuarios.service import AuthService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = AuthService()

        old_hash = await hash_password("OldPassword123!")
        async with uow:
            u = await uow.usuarios.add(
                Usuario(
                    email="cambio@test.com",
                    nombre="Cambio User",
                    password_hash=old_hash,
                    activo=True,
                    debe_cambiar_password=True,
                )
            )

        req = CambiarPasswordRequest(
            password_actual="OldPassword123!",
            password_nueva="NewPassword456!",
        )

        await service.cambiar_password(usuario=u, datos=req, uow=uow)

        # Verificar usuario actualizado
        updated_u = await uow.usuarios.get_by_id(u.id)
        assert updated_u.debe_cambiar_password is False
        assert await verify_password("NewPassword456!", updated_u.password_hash) is True

        # Verificar evento de seguridad
        eventos = await uow.eventos_seguridad.get_all()
        assert len(eventos) == 1
        assert eventos[0].actor == "cambio@test.com"
        assert eventos[0].accion == "CAMBIO_PASSWORD"

    @pytest.mark.asyncio
    async def test_cambiar_password_actual_incorrecta_responde_401(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Contraseña actual incorrecta produce 401 Unauthorized sin tocar la base."""
        from fastapi import HTTPException
        from app.core.security import hash_password
        from app.modules.usuarios.models import Usuario
        from app.modules.usuarios.schemas import CambiarPasswordRequest
        from app.modules.usuarios.service import AuthService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = AuthService()

        old_hash = await hash_password("RealOldPassword123!")
        async with uow:
            u = await uow.usuarios.add(
                Usuario(
                    email="bad_change@test.com",
                    nombre="Bad Change User",
                    password_hash=old_hash,
                    activo=True,
                    debe_cambiar_password=True,
                )
            )

        req = CambiarPasswordRequest(
            password_actual="WrongOldPassword!",
            password_nueva="NewPassword456!",
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.cambiar_password(usuario=u, datos=req, uow=uow)

        assert exc_info.value.status_code == 401
        assert "incorrecta" in exc_info.value.detail.lower()

        # Flag debe permanecer en True
        fresh_u = await uow.usuarios.get_by_id(u.id)
        assert fresh_u.debe_cambiar_password is True
        assert len(await uow.eventos_seguridad.get_all()) == 0


class TestAuthRouterIntegration:
    """Pruebas de integración sobre los endpoints /auth (Tarea 4.1)."""

    @pytest.mark.asyncio
    async def test_endpoint_registro_201_y_409(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: POST /auth/registro responde 201 y segundo intento con mismo email responde 409 (C-02)."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        from app.core.database import get_session
        from app.modules.usuarios.router import router as auth_router

        app = FastAPI()
        app.include_router(auth_router)

        async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
            yield in_memory_session

        app.dependency_overrides[get_session] = override_get_session

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "nombre": "Esteban Quito",
                "email": "esteban@libreria.com",
                "password": "Password123!",
            }
            # 1. Primer intento exitoso -> 201
            r1 = await ac.post("/auth/registro", json=payload)
            assert r1.status_code == 201
            assert "exitosamente" in r1.json()["mensaje"].lower()

            # 2. Segundo intento repetido -> 409
            r2 = await ac.post("/auth/registro", json=payload)
            assert r2.status_code == 409
            assert "ya registrado" in r2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_endpoint_login_cookie_httponly_y_logout(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: POST /auth/login setea cookie HttpOnly sin token en body y logout la borra (C-03)."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        from app.core.database import get_session
        from app.core.security import hash_password
        from app.modules.usuarios.models import AsignacionRol, Usuario
        from app.modules.usuarios.router import router as auth_router

        app = FastAPI()
        app.state.session_factory = async_sessionmaker(
            in_memory_session.bind,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        app.state.dummy_password_hash = await hash_password("dummy")
        app.include_router(auth_router)

        async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
            yield in_memory_session

        app.dependency_overrides[get_session] = override_get_session

        # Crear usuario previo
        pwd = await hash_password("MiClaveSegura123!")
        u = Usuario(
            email="cliente_test@libreria.com",
            nombre="Cliente Test",
            password_hash=pwd,
            activo=True,
            debe_cambiar_password=False,
        )
        in_memory_session.add(u)
        await in_memory_session.flush()
        in_memory_session.add(AsignacionRol(usuario_id=u.id, rol="CLIENTE"))
        await in_memory_session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Login exitoso
            r_login = await ac.post(
                "/auth/login",
                json={"email": "cliente_test@libreria.com", "password": "MiClaveSegura123!"},
            )
            assert r_login.status_code == 200
            body = r_login.json()
            assert "access_token" not in body
            assert body["debe_cambiar_password"] is False

            # Cookie en headers
            set_cookie = r_login.headers.get("set-cookie", "")
            assert "access_token=" in set_cookie
            assert "HttpOnly" in set_cookie or "httponly" in set_cookie

            # GET /auth/yo usando la cookie recibida
            r_yo = await ac.get("/auth/yo")
            assert r_yo.status_code == 200
            yo_body = r_yo.json()
            assert yo_body["email"] == "cliente_test@libreria.com"
            assert "CLIENTE" in yo_body["roles_vigentes"]

            # Logout
            r_logout = await ac.post("/auth/logout")
            assert r_logout.status_code == 200
            logout_cookie = r_logout.headers.get("set-cookie", "")
            assert "access_token=" in logout_cookie
            assert "max-age=0" in logout_cookie.lower()

    def test_app_main_includes_auth_routes(self) -> None:
        """Scenario: app/main.py incluye las rutas de /auth en el grupo abierto."""
        from app.main import app

        paths = app.openapi()["paths"]
        assert "/auth/registro" in paths
        assert "/auth/login" in paths
        assert "/auth/logout" in paths
        assert "/auth/yo" in paths
        assert "/auth/cambiar-password" in paths

    @pytest.mark.asyncio
    async def test_endpoint_login_rate_limiting_429_y_dummy_401(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Integración API para rate limit 429 (C-05) y credenciales inexistentes 401 (C-04)."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        from app.core.database import get_session
        from app.core.security import hash_password
        from app.modules.usuarios.router import router as auth_router

        app = FastAPI()
        app.state.session_factory = async_sessionmaker(
            in_memory_session.bind,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        app.state.dummy_password_hash = await hash_password("dummy")
        app.include_router(auth_router)

        async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
            yield in_memory_session

        app.dependency_overrides[get_session] = override_get_session

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Email inexistente -> 401 con mensaje genérico
            r_fake = await ac.post("/auth/login", json={"email": "nobody@test.com", "password": "Password123!"})
            assert r_fake.status_code == 401
            assert r_fake.json()["detail"] == "Credenciales inválidas"

            # 2. 4 intentos fallidos más con el mismo email -> acumula 5
            for _ in range(4):
                await ac.post("/auth/login", json={"email": "nobody@test.com", "password": "WrongPassword!"})

            # 3. 6to intento -> 429 Too Many Requests con Retry-After
            r_blocked = await ac.post("/auth/login", json={"email": "nobody@test.com", "password": "AnyPassword!"})
            assert r_blocked.status_code == 429
            assert r_blocked.headers.get("retry-after") == "60"

    @pytest.mark.asyncio
    async def test_endpoint_cambiar_password_integracion_y_evento_seguridad(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: POST /auth/cambiar-password cambia clave, desactiva flag y crea evento_seguridad (C-09)."""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient
        from app.core.database import get_session
        from app.core.security import hash_password, verify_password
        from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario
        from app.modules.usuarios.router import router as auth_router

        app = FastAPI()
        app.state.session_factory = async_sessionmaker(
            in_memory_session.bind,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        app.state.dummy_password_hash = await hash_password("dummy")
        app.include_router(auth_router)

        async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
            yield in_memory_session

        app.dependency_overrides[get_session] = override_get_session

        # Crear usuario con debe_cambiar_password=True
        old_hash = await hash_password("ClaveProvisoria123!")
        u = Usuario(
            email="empleado@libreria.com",
            nombre="Empleado Nuevo",
            password_hash=old_hash,
            activo=True,
            debe_cambiar_password=True,
        )
        in_memory_session.add(u)
        await in_memory_session.flush()
        in_memory_session.add(AsignacionRol(usuario_id=u.id, rol="CLIENTE"))
        await in_memory_session.commit()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Login inicial para obtener cookie
            r_login = await ac.post(
                "/auth/login",
                json={"email": "empleado@libreria.com", "password": "ClaveProvisoria123!"},
            )
            assert r_login.status_code == 200
            assert r_login.json()["debe_cambiar_password"] is True

            # 2. Intento de cambio con password actual incorrecta -> 401
            r_bad = await ac.post(
                "/auth/cambiar-password",
                json={"password_actual": "Incorrecta!", "password_nueva": "NuevaClave456!"},
            )
            assert r_bad.status_code == 401

            # 3. Cambio con password correcta -> 200
            r_good = await ac.post(
                "/auth/cambiar-password",
                json={"password_actual": "ClaveProvisoria123!", "password_nueva": "NuevaClave456!"},
            )
            assert r_good.status_code == 200

            # 4. Verificar usuario en base de datos
            await in_memory_session.refresh(u)
            assert u.debe_cambiar_password is False
            assert await verify_password("NuevaClave456!", u.password_hash) is True

            # 5. Verificar evento_seguridad
            stmt = select(EventoSeguridad).where(EventoSeguridad.actor == "empleado@libreria.com")
            res = await in_memory_session.execute(stmt)
            eventos = res.scalars().all()
            assert len(eventos) == 1
            assert eventos[0].accion == "CAMBIO_PASSWORD"
