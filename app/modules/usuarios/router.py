"""Rutas de la API para autenticación y gestión de identidad (/auth)."""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.dependencies import get_usuario_actual
from app.core.security import decode_access_token
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import (
    CambiarPasswordRequest,
    LoginRequest,
    LoginResponse,
    MensajeResponse,
    UsuarioRegistroRequest,
    UsuarioYoResponse,
)
from app.modules.usuarios.service import AuthService
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
