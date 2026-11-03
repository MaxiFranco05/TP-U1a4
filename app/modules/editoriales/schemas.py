"""Esquemas DTO del módulo editoriales."""

from pydantic import ConfigDict, field_validator
from sqlmodel import SQLModel


def _validate_non_empty_nombre(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("El nombre de la editorial no puede estar vacío")
    return cleaned


class EditorialCreate(SQLModel):
    """DTO de entrada para la creación de una editorial (sin id)."""

    model_config = ConfigDict(extra="forbid")

    nombre: str
    pais: str | None = None

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, value: str) -> str:
        return _validate_non_empty_nombre(value)


class EditorialUpdate(SQLModel):
    """DTO de entrada para actualización parcial (PATCH) de una editorial."""

    model_config = ConfigDict(extra="forbid")

    nombre: str | None = None
    pais: str | None = None

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_non_empty_nombre(value)


class EditorialRead(SQLModel):
    """DTO de salida para lectura de una editorial."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    nombre: str
    pais: str | None


class EditorialListItem(SQLModel):
    """DTO de salida para listado de editoriales."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    nombre: str
    pais: str | None
