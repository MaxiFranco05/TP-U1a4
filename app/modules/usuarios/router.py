"""Rutas de la API para autenticación, gestión de personal y auditoría (/auth, /usuarios, /eventos)."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.dependencies import get_usuario_actual
from app.core.paginacion import PaginatedResponse, PaginationParams
from app.core.security import decode_access_token
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import (
    CambiarPasswordRequest,
    EventoSeguridadResponse,
    LoginRequest,
    LoginResponse,
    MensajeResponse,
    RolAsignacionResponse,
    RolAsignarRequest,
    UsuarioCreateRequest,
    UsuarioReadResponse,
    UsuarioRegistroRequest,
    UsuarioYoResponse,
)
from app.modules.usuarios.service import AuthService, UsuarioService
from app.modules.usuarios.unit_of_work import UsuariosUnitOfWork


router = APIRouter(prefix="/auth", tags=["Autenticación"])


def get_usuarios_uow(
    session: AsyncSession = Depends(get_session),
) -> UsuariosUnitOfWork:
    """Provee una instancia de UsuariosUnitOfWork compartiendo la sesión de la petición."""
    return UsuariosUnitOfWork(session=session)


def get_auth_service() -> AuthService:
    """Provee la instancia del servicio de autenticación."""
    return AuthService()


@router.post(
    "/registro",
    status_code=status.HTTP_201_CREATED,
    response_model=MensajeResponse,
)
async def registro(
    datos: UsuarioRegistroRequest,
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
    service: AuthService = Depends(get_auth_service),
) -> MensajeResponse:
    """Auto-registro de clientes en una única transacción atómica (RN-02)."""
    await service.registro(datos=datos, uow=uow)
    return MensajeResponse(mensaje="Usuario registrado exitosamente")


@router.post(
    "/login",
    response_model=LoginResponse,
)
async def login(
    request: Request,
    response: Response,
    datos: LoginRequest,
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Inicio de sesión con rate limit, tiempo constante y cookie HttpOnly (RN-07, RN-08, C-03)."""
    settings = get_settings()

    client_ip = request.client.host if request.client else "127.0.0.1"

    session_factory = getattr(request.app.state, "session_factory", None) or getattr(
        request.app.state,
        "session_maker",
        None,
    )
    dummy_password_hash = getattr(
        request.app.state,
        "dummy_password_hash",
        "$2b$04$dummy_hash_for_constant_time_authentication_verification",
    )

    token, login_resp = await service.login(
        datos=datos,
        client_ip=client_ip,
        uow=uow,
        session_factory=session_factory,
        dummy_password_hash=dummy_password_hash,
    )

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.JWT_EXPIRATION_SECONDS,
        secure=settings.COOKIE_SECURE,
    )

    return login_resp


@router.post(
    "/logout",
    response_model=MensajeResponse,
)
async def logout(response: Response) -> MensajeResponse:
    """Cierre de sesión idempotente eliminando la cookie access_token (C-03)."""
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
    )
    return MensajeResponse(mensaje="Sesión cerrada exitosamente")


@router.get(
    "/yo",
    response_model=UsuarioYoResponse,
)
async def yo(
    request: Request,
    usuario: Usuario = Depends(get_usuario_actual),
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
    service: AuthService = Depends(get_auth_service),
) -> UsuarioYoResponse:
    """Devuelve los datos del usuario autenticado, roles vigentes en BD y roles del token (C-07)."""
    token = request.cookies.get("access_token")
    token_roles: list[str] = []
    if token:
        try:
            payload = decode_access_token(token)
            token_roles = payload.get("roles", [])
        except Exception:
            token_roles = []

    return await service.obtener_yo(
        usuario=usuario,
        token_roles=token_roles,
        uow=uow,
    )


@router.post(
    "/cambiar-password",
    response_model=MensajeResponse,
)
async def cambiar_password(
    datos: CambiarPasswordRequest,
    usuario: Usuario = Depends(get_usuario_actual),
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
    service: AuthService = Depends(get_auth_service),
) -> MensajeResponse:
    """Cambio de contraseña con registro auditable en evento_seguridad (RN-06, RN-16, C-09)."""
    await service.cambiar_password(usuario=usuario, datos=datos, uow=uow)
    return MensajeResponse(mensaje="Contraseña actualizada exitosamente")


def get_usuario_service() -> UsuarioService:
    """Provee la instancia del servicio de usuarios y administración de personal."""
    return UsuarioService()


usuarios_router = APIRouter(prefix="/usuarios", tags=["Usuarios y Personal"])


@usuarios_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=UsuarioReadResponse,
)
async def crear_personal(
    datos: UsuarioCreateRequest,
    admin: Usuario = Depends(get_usuario_actual),
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
    service: UsuarioService = Depends(get_usuario_service),
) -> UsuarioReadResponse:
    """Alta de personal por un administrador (RN-06, RN-16)."""
    usuario = await service.crear_personal(admin_actor=admin, datos=datos, uow=uow)
    return UsuarioReadResponse(
        id=usuario.id,
        email=usuario.email,
        nombre=usuario.nombre,
        activo=usuario.activo,
        debe_cambiar_password=usuario.debe_cambiar_password,
        roles=[datos.rol.upper()],
    )


@usuarios_router.get(
    "/{id}/roles",
    response_model=list[RolAsignacionResponse],
)
async def listar_roles(
    id: int,
    admin: Usuario = Depends(get_usuario_actual),
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
    service: UsuarioService = Depends(get_usuario_service),
) -> list[RolAsignacionResponse]:
    """Consulta el historial de asignaciones de rol de un usuario."""
    roles = await service.listar_roles(usuario_id=id, uow=uow)
    now = datetime.now(timezone.utc)
    items: list[RolAsignacionResponse] = []
    for r in roles:
        vence_en = r.vence_en
        if vence_en is not None and vence_en.tzinfo is None:
            vence_en = vence_en.replace(tzinfo=timezone.utc)
        activa = (r.revocada_en is None and (vence_en is None or vence_en > now))
        items.append(
            RolAsignacionResponse(
                id=r.id,
                usuario_id=r.usuario_id,
                rol=r.rol,
                otorgada_por=r.otorgada_por,
                desde=r.desde,
                vence_en=r.vence_en,
                revocada_en=r.revocada_en,
                activa=activa,
            )
        )
    return items


@usuarios_router.post(
    "/{id}/roles",
    response_model=RolAsignacionResponse,
)
async def asignar_rol(
    id: int,
    datos: RolAsignarRequest,
    admin: Usuario = Depends(get_usuario_actual),
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
    service: UsuarioService = Depends(get_usuario_service),
) -> RolAsignacionResponse:
    """Asignación de rol con vigencia a un usuario (RN-03, RN-16, C-07)."""
    asig = await service.asignar_rol(admin_actor=admin, usuario_id=id, datos=datos, uow=uow)
    return RolAsignacionResponse(
        id=asig.id,
        usuario_id=asig.usuario_id,
        rol=asig.rol,
        otorgada_por=asig.otorgada_por,
        desde=asig.desde,
        vence_en=asig.vence_en,
        revocada_en=asig.revocada_en,
        activa=True,
    )


@usuarios_router.delete(
    "/{id}/roles/{rol}",
    response_model=RolAsignacionResponse,
)
async def revocar_rol(
    id: int,
    rol: str,
    admin: Usuario = Depends(get_usuario_actual),
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
    service: UsuarioService = Depends(get_usuario_service),
) -> RolAsignacionResponse:
    """Revocación lógica de rol con autoprotección de administrador (RN-05, RN-16, C-08)."""
    asig = await service.revocar_rol(admin_actor=admin, usuario_id=id, rol=rol, uow=uow)
    return RolAsignacionResponse(
        id=asig.id,
        usuario_id=asig.usuario_id,
        rol=asig.rol,
        otorgada_por=asig.otorgada_por,
        desde=asig.desde,
        vence_en=asig.vence_en,
        revocada_en=asig.revocada_en,
        activa=False,
    )


eventos_router = APIRouter(prefix="/eventos", tags=["Eventos de Seguridad"])


@eventos_router.get(
    "",
    response_model=PaginatedResponse[EventoSeguridadResponse],
)
async def listar_eventos(
    params: PaginationParams = Depends(),
    admin: Usuario = Depends(get_usuario_actual),
    uow: UsuariosUnitOfWork = Depends(get_usuarios_uow),
    service: UsuarioService = Depends(get_usuario_service),
) -> PaginatedResponse[EventoSeguridadResponse]:
    """Consulta paginada de la bitácora de auditoría de seguridad (RN-16, C-16)."""
    return await service.listar_eventos(params=params, uow=uow)

