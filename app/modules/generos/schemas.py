"""Esquemas DTO del módulo generos."""

from decimal import Decimal

from pydantic import ConfigDict, field_validator
from sqlmodel import SQLModel


def _validate_non_empty_nombre(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("El nombre del género no puede estar vacío")
    return cleaned


class GeneroCreate(SQLModel):
    """DTO de entrada para la creación de un género (sin id)."""

    model_config = ConfigDict(extra="forbid")

    nombre: str

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, value: str) -> str:
        return _validate_non_empty_nombre(value)


class GeneroUpdate(SQLModel):
    """DTO de entrada para actualización parcial (PATCH) de un género."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = None

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_non_empty_nombre(value)


class GeneroRead(SQLModel):
    """DTO de salida para lectura de un género."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    nombre: str


class GeneroLibroRead(SQLModel):
    """DTO de salida para los libros listados dentro de un género."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial_id: int
    genero_id: int | None
