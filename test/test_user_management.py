"""Pruebas unitarias e integrales para C-14: administración de usuarios, roles con vigencia, autoprotección y eventos."""

from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from typing import Any
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.exceptions import DomainError
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario
from app.modules.usuarios.repository import AsignacionRolRepository, EventoSeguridadRepository
from app.modules.usuarios.schemas import (
    EventoSeguridadResponse,
    RolAsignacionResponse,
    RolAsignarRequest,
    UsuarioCreateRequest,
    UsuarioReadResponse,
)


@pytest.fixture
async def in_memory_session() -> AsyncGenerator[AsyncSession, None]:
    """Crea una base de datos SQLite en memoria para tests unitarios."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


class TestUserManagementSchemas:
    """Pruebas unitarias de contratos DTO para personal y roles (Tarea 1.1)."""

    def test_usuario_create_request_valid(self) -> None:
        """Scenario: Creación válida de personal con rol inicial."""
        req = UsuarioCreateRequest(
            nombre="Vendedor Juan",
            email="juan@libreria.com",
            password="provisoria123",
            rol="VENDEDOR",
        )
        assert req.nombre == "Vendedor Juan"
        assert req.email == "juan@libreria.com"
        assert req.rol == "VENDEDOR"

    def test_usuario_create_request_rejects_extra_fields(self) -> None:
        """Scenario: Rechazo de campos extra en UsuarioCreateRequest (extra='forbid')."""
        with pytest.raises(ValidationError):
            UsuarioCreateRequest(
                nombre="Juan",
                email="juan@libreria.com",
                password="pass",
                rol="ADMIN",
                extra_field="malicious",  # type: ignore
            )

    def test_usuario_create_request_rejects_password_over_72_bytes(self) -> None:
        """Scenario: Rechazo de contraseña provisoria mayor a 72 bytes UTF-8."""
        with pytest.raises(ValidationError):
            UsuarioCreateRequest(
                nombre="Juan",
                email="juan@libreria.com",
                password="a" * 73,
                rol="ADMIN",
            )

    def test_usuario_create_request_rejects_invalid_rol(self) -> None:
        """Scenario: Rechazo de rol no contemplado por el CHECK enum."""
        with pytest.raises(ValidationError):
            UsuarioCreateRequest(
                nombre="Juan",
                email="juan@libreria.com",
                password="pass",
                rol="SUPERADMIN",
            )

    def test_rol_asignar_request_valid_with_future_tz_vence_en(self) -> None:
        """Scenario: Asignación de rol válida con vence_en futuro con timezone."""
        future = datetime.now(timezone.utc) + timedelta(days=30)
        req = RolAsignarRequest(rol="VENDEDOR", vence_en=future)
        assert req.rol == "VENDEDOR"
        assert req.vence_en == future

    def test_rol_asignar_request_valid_without_vence_en(self) -> None:
        """Scenario: Asignación de rol válida permanente (vence_en=None)."""
        req = RolAsignarRequest(rol="ADMIN")
        assert req.rol == "ADMIN"
        assert req.vence_en is None

    def test_rol_asignar_request_rejects_naive_vence_en(self) -> None:
        """Scenario: Rechazo de vence_en naive (sin zona horaria) con ValidationError (422) (C-07)."""
        naive_future = datetime.now() + timedelta(days=5)
        with pytest.raises(ValidationError) as exc_info:
            RolAsignarRequest(rol="VENDEDOR", vence_en=naive_future)
        assert "zona horaria" in str(exc_info.value)

    def test_rol_asignar_request_rejects_past_vence_en(self) -> None:
        """Scenario: Rechazo de vence_en en el pasado con ValidationError (422) (C-07)."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        with pytest.raises(ValidationError) as exc_info:
            RolAsignarRequest(rol="VENDEDOR", vence_en=past)
        assert "posterior" in str(exc_info.value)

    def test_usuario_read_response_serializes_without_password_hash(self) -> None:
        """Scenario: UsuarioReadResponse no expone password_hash."""
        now = datetime.now(timezone.utc)
        res = UsuarioReadResponse(
            id=1,
            email="admin@libreria.com",
            nombre="Admin",
            activo=True,
            debe_cambiar_password=True,
            creado_en=now,
            roles=["ADMIN"],
        )
        data = res.model_dump()
        assert "password_hash" not in data
        assert data["id"] == 1
        assert data["roles"] == ["ADMIN"]

    def test_rol_asignacion_response(self) -> None:
        """Scenario: RolAsignacionResponse refleja la auditoría y vigencia."""
        now = datetime.now(timezone.utc)
        res = RolAsignacionResponse(
            id=10,
            usuario_id=2,
            rol="VENDEDOR",
            otorgada_por=1,
            desde=now,
            vence_en=None,
            revocada_en=None,
            activa=True,
        )
        assert res.rol == "VENDEDOR"
        assert res.otorgada_por == 1
        assert res.activa is True

    def test_evento_seguridad_response(self) -> None:
        """Scenario: EventoSeguridadResponse estructura la bitácora de auditoría."""
        now = datetime.now(timezone.utc)
        res = EventoSeguridadResponse(
            id=100,
            actor="admin@libreria.com",
            accion="ALTA_PERSONAL",
            cuando=now,
        )
        assert res.actor == "admin@libreria.com"
        assert res.accion == "ALTA_PERSONAL"



class TestUserManagementRepositories:
    """Pruebas unitarias para consultas en AsignacionRolRepository y EventoSeguridadRepository (Tarea 2.1)."""

    @pytest.mark.asyncio
    async def test_asignacion_rol_repository_queries(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Consultas de asignación activa, historial y conteo de admins vigentes."""
        now = datetime.now(timezone.utc)
        # Crear 3 usuarios: admin1 (activo), admin2 (inactivo), vendedor (activo)
        admin1 = Usuario(email="adm1@libreria.com", nombre="Admin 1", password_hash="hash", activo=True)
        admin2 = Usuario(email="adm2@libreria.com", nombre="Admin 2", password_hash="hash", activo=False)
        vendedor = Usuario(email="vend@libreria.com", nombre="Vendedor", password_hash="hash", activo=True)
        in_memory_session.add_all([admin1, admin2, vendedor])
        await in_memory_session.flush()

        roles_repo = AsignacionRolRepository(session=in_memory_session)

        # Asignar ADMIN a admin1 (vigente)
        asig_adm1 = AsignacionRol(usuario_id=admin1.id, rol="ADMIN", otorgada_por=admin1.id, desde=now)
        # Asignar ADMIN a admin2 (pero admin2 está inactivo)
        asig_adm2 = AsignacionRol(usuario_id=admin2.id, rol="ADMIN", otorgada_por=admin1.id, desde=now)
        # Asignar VENDEDOR a vendedor (vigente)
        asig_vend = AsignacionRol(usuario_id=vendedor.id, rol="VENDEDOR", otorgada_por=admin1.id, desde=now)
        await roles_repo.add(asig_adm1)
        await roles_repo.add(asig_adm2)
        await roles_repo.add(asig_vend)

        # 1. get_asignacion_activa_por_rol
        activa = await roles_repo.get_asignacion_activa_por_rol(vendedor.id, "VENDEDOR")
        assert activa is not None
        assert activa.rol == "VENDEDOR"

        inactiva = await roles_repo.get_asignacion_activa_por_rol(vendedor.id, "ADMIN")
        assert inactiva is None

        # 2. get_asignaciones_usuario
        asigs_vend = await roles_repo.get_asignaciones_usuario(vendedor.id)
        assert len(asigs_vend) == 1
        assert asigs_vend[0].rol == "VENDEDOR"

        # 3. contar_admins_vigentes: solo admin1 cuenta (admin2 inactivo no cuenta)
        admins_count = await roles_repo.contar_admins_vigentes()
        assert admins_count == 1

        # Si revocamos a admin1, el conteo baja a 0
        asig_adm1.revocada_en = now
        await roles_repo.update(asig_adm1)
        admins_count_after = await roles_repo.contar_admins_vigentes()
        assert admins_count_after == 0

    @pytest.mark.asyncio
    async def test_evento_seguridad_repository_pagination(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Listado paginado de eventos de seguridad con orden determinista."""
        eventos_repo = EventoSeguridadRepository(session=in_memory_session)

        # Registrar 5 eventos
        for i in range(1, 6):
            await eventos_repo.registrar_evento(
                actor=f"user{i}@libreria.com",
                accion="LOGIN_FALLIDO",
            )


        items_page1, total = await eventos_repo.listar_eventos_paginado(offset=0, limit=2)
        assert total == 5
        assert len(items_page1) == 2
        # Evento 5 debe ser el primero por orden descendente
        assert items_page1[0].actor == "user5@libreria.com"
        assert items_page1[1].actor == "user4@libreria.com"

        items_page2, total2 = await eventos_repo.listar_eventos_paginado(offset=2, limit=2)
        assert total2 == 5
        assert len(items_page2) == 2
        assert items_page2[0].actor == "user3@libreria.com"
        assert items_page2[1].actor == "user2@libreria.com"


class TestUsuarioServicePersonal:
    """Pruebas unitarias para UsuarioService.crear_personal (Tarea 3.1)."""

    @pytest.mark.asyncio
    async def test_crear_personal_exitoso(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Alta de personal con contraseña provisoria, rol y auditoría en un UoW."""
        from app.modules.usuarios.service import UsuarioService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        # Crear admin actor en BD
        admin_actor = Usuario(
            email="admin@libreria.com",
            nombre="Admin Principal",
            password_hash="adminhash",
            activo=True,
        )
        in_memory_session.add(admin_actor)
        await in_memory_session.commit()

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = UsuarioService()

        req = UsuarioCreateRequest(
            nombre="Carlos Vendedor",
            email="carlos@libreria.com",
            password="provisoria123",
            rol="VENDEDOR",
        )

        nuevo_usuario = await service.crear_personal(
            admin_actor=admin_actor,
            datos=req,
            uow=uow,
        )

        assert nuevo_usuario.id is not None
        assert nuevo_usuario.nombre == "Carlos Vendedor"
        assert nuevo_usuario.email == "carlos@libreria.com"
        assert nuevo_usuario.debe_cambiar_password is True
        assert nuevo_usuario.activo is True

        # Verificar rol asignado
        roles = await in_memory_session.execute(
            select(AsignacionRol).where(AsignacionRol.usuario_id == nuevo_usuario.id)
        )
        roles_list = list(roles.scalars().all())
        assert len(roles_list) == 1
        assert roles_list[0].rol == "VENDEDOR"
        assert roles_list[0].otorgada_por == admin_actor.id
        assert roles_list[0].revocada_en is None

        # Verificar evento de seguridad
        eventos = await in_memory_session.execute(
            select(EventoSeguridad).where(EventoSeguridad.actor == admin_actor.email)
        )
        eventos_list = list(eventos.scalars().all())
        assert len(eventos_list) == 1
        assert eventos_list[0].accion == "ALTA_PERSONAL"

    @pytest.mark.asyncio

    async def test_crear_personal_duplicado_email_409(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Conflicto 409 al intentar dar de alta personal con email ya existente."""
        from fastapi import HTTPException
        from app.modules.usuarios.service import UsuarioService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        admin_actor = Usuario(
            email="admin2@libreria.com",
            nombre="Admin Dos",
            password_hash="adminhash",
            activo=True,
        )
        in_memory_session.add(admin_actor)
        await in_memory_session.commit()

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = UsuarioService()

        req = UsuarioCreateRequest(
            nombre="Admin Duplicado",
            email="admin2@libreria.com",
            password="provisoria123",
            rol="VENDEDOR",
        )

        with pytest.raises((HTTPException, DomainError)) as exc_info:
            await service.crear_personal(
                admin_actor=admin_actor,
                datos=req,
                uow=uow,
            )

        assert exc_info.value.status_code == 409
        assert "ya está registrado" in exc_info.value.detail


class TestUsuarioServiceRoles:
    """Pruebas unitarias para UsuarioService.listar_roles y asignar_rol (Tarea 3.2)."""

    @pytest.mark.asyncio
    async def test_listar_roles_usuario_no_encontrado_404(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: listar_roles responde 404 si el usuario no existe."""
        from fastapi import HTTPException
        from app.modules.usuarios.service import UsuarioService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = UsuarioService()

        with pytest.raises((HTTPException, DomainError)) as exc_info:
            await service.listar_roles(usuario_id=999, uow=uow)
        assert exc_info.value.status_code == 404
        assert "Usuario no encontrado" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_asignar_rol_exitoso_y_duplicado_409(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Asignar rol exitoso y rechazo 409 si ya está activo y vigente (RN-03)."""
        from fastapi import HTTPException
        from app.modules.usuarios.service import UsuarioService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        now = datetime.now(timezone.utc)
        admin = Usuario(email="adm@libreria.com", nombre="Admin", password_hash="h", activo=True)
        user = Usuario(email="cli@libreria.com", nombre="Cliente", password_hash="h", activo=True)
        in_memory_session.add_all([admin, user])
        await in_memory_session.commit()

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = UsuarioService()

        # Asignar VENDEDOR con vencimiento futuro
        req = RolAsignarRequest(
            rol="VENDEDOR",
            vence_en=now + timedelta(days=10),
        )
        asig = await service.asignar_rol(admin_actor=admin, usuario_id=user.id, datos=req, uow=uow)
        assert asig.id is not None
        assert asig.rol == "VENDEDOR"
        assert asig.otorgada_por == admin.id
        assert asig.revocada_en is None

        # Reintentar asignar VENDEDOR mientras está vigente -> 409
        with pytest.raises((HTTPException, DomainError)) as exc_info:
            await service.asignar_rol(admin_actor=admin, usuario_id=user.id, datos=req, uow=uow)
        assert exc_info.value.status_code == 409
        assert "ya tiene ese rol asignado" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_asignar_rol_reemplazo_automatico_de_rol_vencido(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Si existe asignación previa vencida en el tiempo, se cierra y se crea la nueva."""
        from app.modules.usuarios.service import UsuarioService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        now = datetime.now(timezone.utc)
        admin = Usuario(email="adm_rep@libreria.com", nombre="Admin Rep", password_hash="h", activo=True)
        user = Usuario(email="usr_rep@libreria.com", nombre="User Rep", password_hash="h", activo=True)
        in_memory_session.add_all([admin, user])
        await in_memory_session.flush()

        # Insertar asignación VENDEDOR ya vencida en el pasado
        asig_vieja = AsignacionRol(
            usuario_id=user.id,
            rol="VENDEDOR",
            otorgada_por=admin.id,
            desde=now - timedelta(days=20),
            vence_en=now - timedelta(days=5),
            revocada_en=None,
        )
        in_memory_session.add(asig_vieja)
        await in_memory_session.commit()

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = UsuarioService()

        # Asignar VENDEDOR nuevamente
        req = RolAsignarRequest(rol="VENDEDOR", vence_en=now + timedelta(days=15))
        nueva_asig = await service.asignar_rol(admin_actor=admin, usuario_id=user.id, datos=req, uow=uow)

        assert nueva_asig.id != asig_vieja.id
        assert nueva_asig.revocada_en is None

        # Verificar que la vieja quedó cerrada con revocada_en informado
        await in_memory_session.refresh(asig_vieja)
        assert asig_vieja.revocada_en is not None


class TestUsuarioServiceRevocacionYEventos:
    """Pruebas unitarias para UsuarioService.revocar_rol y listar_eventos (Tarea 3.3)."""

    @pytest.mark.asyncio
    async def test_revocar_rol_exitoso(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Revocación lógica exitosa y registro de auditoría."""
        from app.modules.usuarios.service import UsuarioService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        now = datetime.now(timezone.utc)
        admin = Usuario(email="admin_rev@libreria.com", nombre="Admin", password_hash="h", activo=True)
        vendedor = Usuario(email="vend_rev@libreria.com", nombre="Vendedor", password_hash="h", activo=True)
        in_memory_session.add_all([admin, vendedor])
        await in_memory_session.flush()

        asig_vend = AsignacionRol(usuario_id=vendedor.id, rol="VENDEDOR", otorgada_por=admin.id, desde=now)
        in_memory_session.add(asig_vend)
        await in_memory_session.commit()

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = UsuarioService()

        revocada = await service.revocar_rol(admin_actor=admin, usuario_id=vendedor.id, rol="VENDEDOR", uow=uow)
        assert revocada.revocada_en is not None

        # Verificar que la fila sigue existiendo en BD (no DELETE)
        asigs_db = await in_memory_session.execute(
            select(AsignacionRol).where(AsignacionRol.id == asig_vend.id)
        )
        asig_persisted = asigs_db.scalar_one()
        assert asig_persisted.revocada_en is not None

        # Verificar evento de seguridad
        eventos = await in_memory_session.execute(
            select(EventoSeguridad).where(EventoSeguridad.accion == "REVOCACION_ROL")
        )
        assert len(list(eventos.scalars().all())) == 1

    @pytest.mark.asyncio
    async def test_revocar_rol_usuario_o_rol_no_encontrado_404(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: 404 si el usuario no existe o no tiene ese rol activo (incluso con 1 solo admin)."""
        from fastapi import HTTPException
        from app.modules.usuarios.service import UsuarioService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        admin = Usuario(email="only_admin@libreria.com", nombre="Admin", password_hash="h", activo=True)
        otro = Usuario(email="otro@libreria.com", nombre="Otro", password_hash="h", activo=True)
        in_memory_session.add_all([admin, otro])
        await in_memory_session.flush()

        asig_admin = AsignacionRol(usuario_id=admin.id, rol="ADMIN", otorgada_por=admin.id, desde=datetime.now(timezone.utc))
        in_memory_session.add(asig_admin)
        await in_memory_session.commit()

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = UsuarioService()

        # 1. Usuario inexistente -> 404
        with pytest.raises((HTTPException, DomainError)) as exc1:
            await service.revocar_rol(admin_actor=admin, usuario_id=9999, rol="ADMIN", uow=uow)
        assert exc1.value.status_code == 404

        # 2. Usuario existente pero sin el rol -> 404 (directiva auditor: no dar 409 de último admin si ni siquiera tiene el rol)
        with pytest.raises((HTTPException, DomainError)) as exc2:
            await service.revocar_rol(admin_actor=admin, usuario_id=otro.id, rol="ADMIN", uow=uow)
        assert exc2.value.status_code == 404

    @pytest.mark.asyncio
    async def test_revocar_rol_autoproteccion_auto_revocacion_409(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Rechazo 409 si un admin intenta auto-revocarse ADMIN (RN-05, C-08)."""
        from fastapi import HTTPException
        from app.modules.usuarios.service import UsuarioService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        now = datetime.now(timezone.utc)
        # 2 administradores para descartar la restricción de último admin
        admin1 = Usuario(email="adm1_auto@libreria.com", nombre="Admin 1", password_hash="h", activo=True)
        admin2 = Usuario(email="adm2_auto@libreria.com", nombre="Admin 2", password_hash="h", activo=True)
        in_memory_session.add_all([admin1, admin2])
        await in_memory_session.flush()

        asig1 = AsignacionRol(usuario_id=admin1.id, rol="ADMIN", otorgada_por=admin1.id, desde=now)
        asig2 = AsignacionRol(usuario_id=admin2.id, rol="ADMIN", otorgada_por=admin1.id, desde=now)
        in_memory_session.add_all([asig1, asig2])
        await in_memory_session.commit()

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = UsuarioService()

        with pytest.raises((HTTPException, DomainError)) as exc_info:
            await service.revocar_rol(admin_actor=admin1, usuario_id=admin1.id, rol="ADMIN", uow=uow)
        assert exc_info.value.status_code == 409
        assert "auto-revocarse" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_revocar_rol_autoproteccion_ultimo_admin_409(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Rechazo 409 si se intenta revocar al único administrador vigente (RN-05, C-08)."""
        from fastapi import HTTPException
        from app.modules.usuarios.service import UsuarioService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        now = datetime.now(timezone.utc)
        admin_actor = Usuario(email="actor@libreria.com", nombre="Actor", password_hash="h", activo=True)
        target_admin = Usuario(email="target@libreria.com", nombre="Target", password_hash="h", activo=True)
        in_memory_session.add_all([admin_actor, target_admin])
        await in_memory_session.flush()

        # Solo target_admin tiene rol ADMIN (el actor no tiene ADMIN en BD en este setup de prueba)
        asig_target = AsignacionRol(usuario_id=target_admin.id, rol="ADMIN", otorgada_por=target_admin.id, desde=now)
        in_memory_session.add(asig_target)
        await in_memory_session.commit()

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = UsuarioService()

        with pytest.raises((HTTPException, DomainError)) as exc_info:
            await service.revocar_rol(admin_actor=admin_actor, usuario_id=target_admin.id, rol="ADMIN", uow=uow)
        assert exc_info.value.status_code == 409
        assert "único administrador" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_listar_eventos_paginado_y_error_422(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Listado paginado de eventos con envoltorio y error 422 si page > pages (C-16)."""
        from fastapi import HTTPException
        from app.core.paginacion import PaginationParams
        from app.modules.usuarios.service import UsuarioService
        from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork

        eventos_repo = EventoSeguridadRepository(session=in_memory_session)
        for i in range(1, 4):
            await eventos_repo.registrar_evento(actor=f"user{i}@test.com", accion="TEST_ACTION")
        await in_memory_session.commit()

        uow = UsuariosUnitOfWork(session=in_memory_session)
        service = UsuarioService()

        # 1. Página válida (page=1, size=2) -> total=3, pages=2
        params = PaginationParams(page=1, size=2)
        resultado = await service.listar_eventos(params=params, uow=uow)
        assert resultado.total == 3
        assert resultado.page == 1
        assert resultado.size == 2
        assert resultado.pages == 2
        assert len(resultado.items) == 2

        # 2. Página inválida (page=3 > pages=2) -> 422 con formato exacto C-16
        invalid_params = PaginationParams(page=3, size=2)
        with pytest.raises(HTTPException) as exc_info:
            await service.listar_eventos(params=invalid_params, uow=uow)
        assert exc_info.value.status_code == 422
        assert "La página 3 no existe: hay 2" in exc_info.value.detail


class TestUserManagementAPIEndpoints:
    """Pruebas de integración API para routers /usuarios y /eventos (Tareas 4.1 y 4.2)."""

    @pytest.mark.asyncio
    async def test_usuarios_and_eventos_routes_mounted_in_openapi(self) -> None:
        """Scenario: Verificar que las rutas de personal y eventos estén registradas en OpenAPI."""
        from app.main import create_app

        app = create_app()
        paths = app.openapi()["paths"]
        assert "/usuarios" in paths or "/usuarios/" in paths
        assert "/usuarios/{id}/roles" in paths
        assert "/usuarios/{id}/roles/{rol}" in paths
        assert "/eventos" in paths or "/eventos/" in paths

    @pytest.mark.asyncio
    async def test_usuarios_endpoints_unauthenticated_returns_401(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Petición anónima a /usuarios o /eventos retorna 401 Unauthorized."""
        from httpx import ASGITransport, AsyncClient
        from app.core.database import get_session
        from app.main import create_app

        app = create_app()
        app.dependency_overrides[get_session] = lambda: in_memory_session

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp_post = await client.post("/usuarios", json={"nombre": "A", "email": "a@a.com", "password": "p", "rol": "VENDEDOR"})
            assert resp_post.status_code == 401

            resp_eventos = await client.get("/eventos")
            assert resp_eventos.status_code == 401

    @pytest.mark.asyncio
    async def test_usuarios_endpoints_client_role_returns_403(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Usuario con rol CLIENTE recibe 403 Forbidden al intentar acceder a rutas de ADMIN."""
        from httpx import ASGITransport, AsyncClient
        from app.core.database import get_session
        from app.core.security import create_access_token
        from app.main import create_app

        cliente_user = Usuario(email="cliente_test@libreria.com", nombre="Cliente Test", password_hash="h", activo=True)
        in_memory_session.add(cliente_user)
        await in_memory_session.flush()

        asig_cli = AsignacionRol(usuario_id=cliente_user.id, rol="CLIENTE", desde=datetime.now(timezone.utc))
        in_memory_session.add(asig_cli)
        await in_memory_session.commit()

        token = create_access_token(data={"sub": str(cliente_user.id), "roles": ["CLIENTE"]})

        app = create_app()
        app.dependency_overrides[get_session] = lambda: in_memory_session

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", cookies={"access_token": token}) as client:
            resp = await client.post("/usuarios", json={"nombre": "Vend", "email": "v@lib.com", "password": "p", "rol": "VENDEDOR"})
            assert resp.status_code == 403
            assert "permisos requeridos" in resp.json()["detail"].lower()


    @pytest.mark.asyncio
    async def test_admin_crud_usuarios_roles_and_eventos_flow(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario: Flujo integral de administrador con alta de personal, asignación de rol, autoprotección y eventos."""
        from httpx import ASGITransport, AsyncClient
        from app.core.database import get_session
        from app.core.security import create_access_token
        from app.main import create_app

        now = datetime.now(timezone.utc)
        # Crear Admin 1
        admin1 = Usuario(email="super_admin@libreria.com", nombre="Super Admin", password_hash="h", activo=True)
        in_memory_session.add(admin1)
        await in_memory_session.flush()

        asig_adm1 = AsignacionRol(usuario_id=admin1.id, rol="ADMIN", desde=now)
        in_memory_session.add(asig_adm1)
        await in_memory_session.commit()

        token_admin = create_access_token(data={"sub": str(admin1.id), "roles": ["ADMIN"]})

        app = create_app()
        app.dependency_overrides[get_session] = lambda: in_memory_session

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", cookies={"access_token": token_admin}) as client:
            # 1. POST /usuarios: Crear Vendedor
            resp_create = await client.post(
                "/usuarios",
                json={
                    "nombre": "Pedro Vendedor",
                    "email": "pedro_vendedor@libreria.com",
                    "password": "provisoria123",
                    "rol": "VENDEDOR",
                },
            )
            assert resp_create.status_code == 201
            vendedor_data = resp_create.json()
            assert vendedor_data["email"] == "pedro_vendedor@libreria.com"
            assert vendedor_data["debe_cambiar_password"] is True
            assert "password_hash" not in vendedor_data
            vendedor_id = vendedor_data["id"]

            # 2. GET /usuarios/{id}/roles: Consultar asignaciones
            resp_roles = await client.get(f"/usuarios/{vendedor_id}/roles")
            assert resp_roles.status_code == 200
            roles_data = resp_roles.json()
            assert len(roles_data) == 1
            assert roles_data[0]["rol"] == "VENDEDOR"

            # 3. POST /usuarios/{id}/roles: Validación 422 de vence_en naive (C-07)
            naive_dt = (now + timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S")
            resp_naive = await client.post(
                f"/usuarios/{vendedor_id}/roles",
                json={"rol": "ADMIN", "vence_en": naive_dt},
            )
            assert resp_naive.status_code == 422

            # 4. POST /usuarios/{id}/roles: Asignar segundo ADMIN con vigencia futura
            future_dt = (now + timedelta(days=30)).isoformat()
            resp_asig = await client.post(
                f"/usuarios/{vendedor_id}/roles",
                json={"rol": "ADMIN", "vence_en": future_dt},
            )
            assert resp_asig.status_code == 200
            asig_data = resp_asig.json()
            assert asig_data["rol"] == "ADMIN"
            assert asig_data["otorgada_por"] == admin1.id

            # 5. DELETE /usuarios/{id}/roles/ADMIN: Intento de auto-revocación da 409 (C-08)
            resp_auto = await client.delete(f"/usuarios/{admin1.id}/roles/ADMIN")
            assert resp_auto.status_code == 409
            assert "auto-revocarse" in resp_auto.json()["detail"]

            # 6. DELETE /usuarios/{id}/roles/VENDEDOR: Revocar rol vendedor exitosamente
            resp_rev = await client.delete(f"/usuarios/{vendedor_id}/roles/VENDEDOR")
            assert resp_rev.status_code == 200
            rev_data = resp_rev.json()
            assert rev_data["revocada_en"] is not None

            # 7. GET /eventos: Listado paginado con total y páginas
            resp_ev = await client.get("/eventos?page=1&size=10")
            assert resp_ev.status_code == 200
            ev_data = resp_ev.json()
            assert "items" in ev_data
            assert ev_data["total"] >= 2
            assert ev_data["page"] == 1
            assert ev_data["pages"] >= 1

            # 8. GET /eventos?page=999&size=10: Error 422 si page > pages (C-16)
            resp_ev_invalid = await client.get("/eventos?page=999&size=10")
            assert resp_ev_invalid.status_code == 422
            assert "La página 999 no existe: hay" in resp_ev_invalid.json()["detail"]

    @pytest.mark.asyncio
    async def test_c07_revocacion_rol_quita_permisos_de_inmediato(
        self,
        in_memory_session: AsyncSession,
    ) -> None:
        """Scenario C-07: Revocación de rol quita permisos de inmediato en petición subsecuente y /auth/yo refleja el cambio."""
        from httpx import ASGITransport, AsyncClient
        from app.core.database import get_session
        from app.core.security import create_access_token
        from app.main import create_app

        now = datetime.now(timezone.utc)
        user = Usuario(email="revoked_admin@libreria.com", nombre="Revoked Admin", password_hash="h", activo=True)
        in_memory_session.add(user)
        await in_memory_session.flush()

        asig = AsignacionRol(usuario_id=user.id, rol="ADMIN", desde=now)
        in_memory_session.add(asig)
        await in_memory_session.commit()

        # Token JWT firmado con claims de roles: ["ADMIN"]
        token = create_access_token(data={"sub": str(user.id), "roles": ["ADMIN"]})

        app = create_app()
        app.dependency_overrides[get_session] = lambda: in_memory_session

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", cookies={"access_token": token}) as client:
            # 1. Petición inicial con rol vigente en BD -> 200 OK
            yo_antes = await client.get("/auth/yo")
            assert yo_antes.status_code == 200
            assert "ADMIN" in yo_antes.json()["roles_vigentes"]
            assert "ADMIN" in yo_antes.json()["roles_token"]

            # 2. Revocación lógica en la BD
            asig.revocada_en = datetime.now(timezone.utc)
            await in_memory_session.commit()

            # 3. Petición subsecuente a /auth/yo con la MISMA cookie/token -> roles_vigentes ya NO tiene ADMIN
            yo_despues = await client.get("/auth/yo")
            assert yo_despues.status_code == 200
            assert "ADMIN" not in yo_despues.json()["roles_vigentes"]
            assert "ADMIN" in yo_despues.json()["roles_token"]  # En el token sigue estando

            # 4. Petición subsecuente a endpoint protegido (/usuarios) con la MISMA cookie -> 403 Forbidden
            resp_bloqueada = await client.post(
                "/usuarios",
                json={
                    "nombre": "Test",
                    "email": "test_bloq@lib.com",
                    "password": "pass",
                    "rol": "VENDEDOR",
                },
            )
            assert resp_bloqueada.status_code == 403
            assert "permisos requeridos" in resp_bloqueada.json()["detail"].lower()






