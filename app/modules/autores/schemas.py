"""Esquemas DTO del módulo autores."""

from decimal import Decimal

from pydantic import ConfigDict, field_validator
from sqlmodel import SQLModel


def _validate_non_empty_nombre(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("El nombre del autor no puede estar vacío")
    return cleaned


class AutorCreate(SQLModel):
    """DTO de entrada para la creación de un autor (sin id)."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    nacionalidad: str | None = None

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, value: str) -> str:
        return _validate_non_empty_nombre(value)


class AutorUpdate(SQLModel):
    """DTO de entrada para actualización parcial (PATCH) de un autor."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = None
    nacionalidad: str | None = None

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_non_empty_nombre(value)


class AutorRead(SQLModel):
    """DTO de salida para lectura de un autor."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    nombre: str
    nacionalidad: str | None


class AutorLibroItem(SQLModel):
    """DTO de salida para libros listados por autor (incluye rol y orden)."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial_id: int
    genero_id: int | None
    rol: str
    orden: int
