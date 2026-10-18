"""Traducción de errores de integridad a mensajes controlados (RN-12)."""

from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status


def translate_integrity_error(exc: IntegrityError) -> HTTPException:
    """
    Convierte IntegrityError de SQLAlchemy en HTTPException con mensaje en español.

    Mapea nombres de constraints a mensajes controlados sin exponer internos de BD.
    """
    detail = "Error de integridad de la base de datos"
    orig = getattr(exc, "orig", None)

    if orig is not None:
        constraint_name = getattr(orig, "constraint_name", None) or getattr(orig, "diag", None)

        if constraint_name is not None and hasattr(constraint_name, "constraint_name"):
            constraint_name = constraint_name.constraint_name

        if isinstance(constraint_name, str):
            mapping = {
                "editorial_nombre_key": "Ya existe una editorial con ese nombre",
                "autor_nombre_key": "Ya existe un autor con ese nombre",
                "libro_isbn_key": "Ya existe un libro con ese ISBN",
                "genero_nombre_key": "Ya existe un género con ese nombre",
                "fk_libro_editorial": "La editorial referenciada no existe",
                "fk_libro_genero": "El género referenciado no existe",
                "fk_libro_autor_libro": "El libro referenciado no existe",
                "fk_libro_autor_autor": "El autor referenciado no existe",
                "fk_renglon_venta_venta": "La venta referenciada no existe",
                "fk_renglon_venta_libro": "El libro referenciado no existe",
            }
            detail = mapping.get(constraint_name, detail)

    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)