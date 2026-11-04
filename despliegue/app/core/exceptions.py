"""Traducción de errores de integridad a mensajes controlados (RN-12)."""

from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status


import re


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

    # Fallback: extraer del mensaje de error (asyncpg incluye "constraint \"name\"")
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


def translate_integrity_error(exc: IntegrityError) -> HTTPException:
    """
    Convierte IntegrityError de SQLAlchemy en HTTPException con mensaje en español.

    Mapea nombres de constraints a mensajes controlados sin exponer internos de BD.
    """
    detail = "Error de integridad de la base de datos"
    constraint_name = _extract_constraint_name(exc)

    if constraint_name:
        mapping = {
            "editorial_nombre_key": "Ya existe una editorial con ese nombre",
            "autor_nombre_key": "Ya existe un autor con ese nombre",
            "libro_isbn_key": "Ya existe un libro con ese ISBN",
            "genero_nombre_key": "Ya existe un género con ese nombre",
            "cliente_email_key": "Email ya registrado",
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
        }
        detail = mapping.get(constraint_name, detail)

    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)