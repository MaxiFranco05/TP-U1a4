"""Dependencias de FastAPI para autenticación, autorización y control de acceso con sesión compartida."""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
import jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import decode_access_token
from app.modules.usuarios.models import AsignacionRol, Usuario


async def get_usuario_actual(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> Usuario:
    """Resuelve el usuario autenticado exclusivamente desde la cookie HttpOnly 'access_token' (DD-10).

    Comparte la misma sesión asincrónica de la petición (Depends(get_session)) para no tomar
    múltiples conexiones del pool (DD-08). Ignora deliberadamente 'Authorization: Bearer'.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado: falta cookie de sesión 'access_token'.",
        )

    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de acceso inválido o expirado.",
            )
        user_id = int(sub)
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso inválido o expirado.",
        ) from exc

    usuario = await session.get(Usuario, user_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado.",
        )

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo.",
        )

    return usuario


UsuarioActualDep = Annotated[Usuario, Depends(get_usuario_actual)]


def requiere_rol(*roles_permitidos: str) -> Callable[..., Any]:
    """Fabrica una dependencia que comprueba roles vigentes en la base de datos en cada petición (RN-04).

    Los roles que viajan en el JWT son sólo informativos. La consulta se realiza directamente
    sobre asignacion_rol (revocada_en IS NULL y vence_en válido) usando la misma sesión compartida.
    """
    roles_set = set(roles_permitidos)

    async def _verificador_rol(
        usuario_actual: Usuario = Depends(get_usuario_actual),
        session: AsyncSession = Depends(get_session),
    ) -> Usuario:
        now_utc = datetime.now(timezone.utc)
        stmt = (
            select(AsignacionRol.rol)
            .where(
                AsignacionRol.usuario_id == usuario_actual.id,
                AsignacionRol.revocada_en.is_(None),
                or_(
                    AsignacionRol.vence_en.is_(None),
                    AsignacionRol.vence_en > now_utc,
                ),
            )
        )
        result = await session.execute(stmt)
        roles_vigentes = set(result.scalars().all())

        if not roles_set.intersection(roles_vigentes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No posee los permisos requeridos para esta operación.",
            )
        return usuario_actual

    return _verificador_rol


def verificar_password_cambiada(
    usuario_actual: Usuario = Depends(get_usuario_actual),
) -> Usuario:
    """Verifica que el usuario no tenga pendiente el cambio obligatorio de contraseña (RN-06).

    Si debe_cambiar_password es True, bloquea el acceso con 403 Forbidden antes de acceder
    a cualquier endpoint del grupo protegido (DD-12).
    """
    if usuario_actual.debe_cambiar_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debe cambiar su contraseña antes de operar en el sistema.",
        )
    return usuario_actual

