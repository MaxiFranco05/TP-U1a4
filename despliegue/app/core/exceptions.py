"""Excepciones de dominio puras y traducción de errores de integridad (RN-12, RN-15).

Los servicios lanzan exclusivamente errores de dominio que heredan de DomainError,
manteniéndose completamente desacoplados del protocolo de transporte (HTTP).
El router y FastAPI se encargan de traducir estas excepciones a respuestas y códigos HTTP.
"""

import re

from fastapi import APIRouter, HTTPException
from fastapi.routing import APIRoute
from sqlalchemy.exc import IntegrityError
from starlette.requests import Request
from starlette.responses import Response


class DomainError(Exception):
    """Excepción base del dominio, desacoplada de HTTP."""

    def __init__(
        self,
        detail: str,
        status_code: int = 400,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.headers = headers or {}


class EntityNotFoundError(DomainError):
    """Entidad no encontrada en el repositorio (mapea a HTTP 404)."""

    def __init__(self, detail: str = "Recurso no encontrado") -> None:
        super().__init__(detail=detail, status_code=404)


class ConflictError(DomainError):
    """Conflicto de estado, unicidad o integridad en el dominio (mapea a HTTP 409)."""

    def __init__(self, detail: str = "Conflicto en la operación") -> None:
        super().__init__(detail=detail, status_code=409)


class InsufficientStockError(ConflictError):
    """Stock insuficiente para concretar una venta o egreso (mapea a HTTP 409)."""

    def __init__(self, detail: str = "Stock insuficiente") -> None:
        super().__init__(detail=detail)


class BusinessRuleViolationError(DomainError):
    """Violación de regla de negocio o validación semántica (mapea a HTTP 422)."""

    def __init__(self, detail: str = "Violación de regla de negocio") -> None:
        super().__init__(detail=detail, status_code=422)


class AuthenticationError(DomainError):
    """Fallo de autenticación o credenciales inválidas (mapea a HTTP 401)."""

    def __init__(self, detail: str = "Credenciales inválidas") -> None:
        super().__init__(
            detail=detail,
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermissionDeniedError(DomainError):
    """Acceso denegado o permisos insuficientes (mapea a HTTP 403)."""

    def __init__(self, detail: str = "Acceso denegado") -> None:
        super().__init__(detail=detail, status_code=403)


class RateLimitExceededError(DomainError):
    """Tasa de solicitudes excedida por control de seguridad (mapea a HTTP 429)."""

    def __init__(
        self,
        detail: str = "Demasiados intentos fallidos",
        retry_after: int = 60,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(
            detail=detail,
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )


class ServiceUnavailableError(DomainError):
    """Dependencia o servicio externo no disponible (mapea a HTTP 503)."""

    def __init__(self, detail: str = "Servicio no disponible") -> None:
        super().__init__(detail=detail, status_code=503)


class DomainRoute(APIRoute):
    """Clase de ruta de FastAPI que intercepta DomainError y lo traduce a HTTPException (U-06).

    Garantiza que el router sea quien traduzca los errores del dominio a códigos HTTP,
    manteniendo la capa de servicios completamente pura y desacoplada del protocolo HTTP.
    """

    def get_route_handler(self):
        original = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                return await original(request)
            except DomainError as exc:
                raise HTTPException(
                    status_code=exc.status_code,
                    detail=exc.detail,
                    headers=exc.headers or None,
                ) from exc

        return custom_route_handler


class DomainRouter(APIRouter):
    """APIRouter que utiliza DomainRoute por defecto para traducción automática de errores de dominio."""

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("route_class", DomainRoute)
        super().__init__(*args, **kwargs)


def _extract_constraint_name(exc: IntegrityError) -> str | None:
    """Extrae el nombre de la constraint desde IntegrityError (asyncpg, psycopg2, etc.)."""
    orig = getattr(exc, "orig", None)
    if orig is None:
        return None

    # asyncpg: constraint_name está en driver_exception
    driver_exc = getattr(orig, "driver_exception", None)
    if driver_exc is not None:
        constraint_name = getattr(driver_exc, "constraint_name", None)
        if constraint_name:
            return constraint_name

    # SQLAlchemy asyncpg wrapper: constraint_name puede estar directo en orig
    constraint_name = getattr(orig, "constraint_name", None)
    if constraint_name:
        return constraint_name

    # Intentar extraer de __cause__ (excepción original de asyncpg)
    cause = getattr(orig, "__cause__", None)
    if cause is not None:
        constraint_name = getattr(cause, "constraint_name", None)
        if constraint_name:
            return constraint_name

    # psycopg2 y otros: constraint_name en diag
    diag = getattr(orig, "diag", None)
    if diag is not None:
        constraint_name = getattr(diag, "constraint_name", None)
        if constraint_name:
            return constraint_name

    # Fallback: extraer del mensaje de error (asyncpg incluye 'constraint "name"')
    error_msg = str(orig)
    match = re.search(r'constraint "([^"]+)"', error_msg)
    if match:
        return match.group(1)

    # Fallback 2: extraer del mensaje principal de la IntegrityError
    error_msg = str(exc)
    match = re.search(r'constraint "([^"]+)"', error_msg)
    if match:
        return match.group(1)

    return None


def translate_integrity_error(exc: IntegrityError) -> ConflictError:
    """
    Convierte IntegrityError de SQLAlchemy en ConflictError (dominio) con mensaje en español.

    Mapea nombres de constraints a mensajes controlados sin exponer internos de BD (RN-12, RN-15).
    """
    detail = "Error de integridad de la base de datos"
    constraint_name = _extract_constraint_name(exc)

    if constraint_name:
        mapping = {
            "editorial_nombre_key": "Ya existe una editorial con ese nombre",
            "autor_nombre_key": "Ya existe un autor con ese nombre",
            "libro_isbn_key": "Ya existe un libro con ese ISBN",
            "uq_libro_isbn_activo": "Ya existe un libro con ese ISBN",
            "genero_nombre_key": "Ya existe un género con ese nombre",
            "cliente_email_key": "Email ya registrado",
            "usuario_email_key": "Email ya registrado",
            "ix_usuario_email": "Email ya registrado",
            "uq_asignacion_rol_activa": "El usuario ya tiene ese rol asignado",
            "ix_cliente_usuario_id": "El usuario ya está asociado a un cliente",
            "cliente_usuario_id_key": "El usuario ya está asociado a un cliente",
            "ix_perfil_cliente_cliente_id": "El cliente ya tiene un perfil",
            "fk_libro_editorial": "La editorial referenciada no existe",
            "libro_editorial_id_fkey": "La editorial referenciada no existe",
            "fk_libro_genero": "El género referenciado no existe",
            "fk_libro_genero_id_genero": "El género referenciado no existe",
            "fk_libro_autor_libro": "El libro referenciado no existe",
            "fk_libro_autor_autor": "El autor referenciado no existe",
            "fk_renglon_venta_venta": "La venta referenciada no existe",
            "fk_renglon_venta_libro": "El libro referenciado no existe",
            "venta_cliente_id_fkey": "Cliente no encontrado",
            "perfil_cliente_cliente_id_fkey": "Cliente no encontrado",
            "fk_cliente_usuario_id_usuario": "El usuario referenciado no existe",
            "cliente_usuario_id_fkey": "El usuario referenciado no existe",
            "asignacion_rol_usuario_id_fkey": "El usuario referenciado no existe",
            "asignacion_rol_otorgada_por_fkey": "El usuario referenciado no existe",
            "movimiento_stock_libro_id_fkey": "El libro referenciado no existe",
            "movimiento_stock_venta_id_fkey": "La venta referenciada no existe",
            "movimiento_stock_usuario_id_fkey": "El usuario referenciado no existe",
        }
        detail = mapping.get(constraint_name, detail)

    return ConflictError(detail=detail)
