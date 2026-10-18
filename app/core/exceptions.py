"""Traducción de errores de integridad a mensajes controlados (RN-12)."""

from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status


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

    # psycopg2 y otros: constraint_name directo o en diag
    constraint_name = getattr(orig, "constraint_name", None)
    if constraint_name:
        return constraint_name

    diag = getattr(orig, "diag", None)
    if diag is not None:
        constraint_name = getattr(diag, "constraint_name", None)
        if constraint_name:
            return constraint_name

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
            "fk_libro_genero": "El género referenciado no existe",
            "fk_libro_autor_libro": "El libro referenciado no existe",
            "fk_libro_autor_autor": "El autor referenciado no existe",
            "fk_renglon_venta_venta": "La venta referenciada no existe",
            "fk_renglon_venta_libro": "El libro referenciado no existe",
            "perfil_cliente_cliente_id_fkey": "Cliente no encontrado",
        }
        detail = mapping.get(constraint_name, detail)

    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)