"""Esquemas DTO del módulo libros."""

from decimal import Decimal
from typing import Annotated, List

from pydantic import Field, field_validator
from sqlmodel import SQLModel


class AutorCreateNested(SQLModel):
    """DTO para autor dentro de creación de libro (autor existente + rol + orden)."""

    autor_id: int
    rol: str
    orden: int

    @field_validator("rol")
    @classmethod
    def validate_rol(cls, value: str) -> str:
        allowed = {"autor", "coautor", "traductor", "ilustrador"}
        if value not in allowed:
            raise ValueError(f"Rol inválido. Valores permitidos: {', '.join(allowed)}")
        return value

    @field_validator("orden")
    @classmethod
    def validate_orden(cls, value: int) -> int:
        if value < 1:
            raise ValueError("El orden debe ser >= 1")
        return value


class LibroCreate(SQLModel):
    """DTO de entrada para la creación de un libro con autores."""

    isbn: str
    titulo: str
    precio: Decimal = Field(gt=0, description="Precio debe ser positivo")
    stock: int = Field(ge=0, description="Stock no puede ser negativo")
    editorial_id: int = Field(ge=1)
    genero_id: int | None = None
    autores: List[AutorCreateNested] = Field(default_factory=list)

    @field_validator("titulo")
    @classmethod
    def validate_titulo(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("El título no puede estar vacío")
        return cleaned


class LibroUpdate(SQLModel):
    """DTO de entrada para la actualización parcial de un libro."""

    isbn: str | None = None
    titulo: str | None = None
    precio: Decimal | None = Field(default=None, gt=0, description="Precio debe ser positivo")
    stock: int | None = Field(default=None, ge=0, description="Stock no puede ser negativo")
    editorial_id: int | None = Field(default=None, ge=1)
    genero_id: int | None = Field(default=None, ge=1)

    @field_validator("titulo")
    @classmethod
    def validate_titulo(cls, value: str | None) -> str | None:
        if value is not None:
            cleaned = value.strip()
            if not cleaned:
                raise ValueError("El título no puede estar vacío")
            return cleaned
        return value


class LibroRead(SQLModel):
    """DTO de salida para detalle completo de un libro."""

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial_id: int
    genero_id: int | None
    editorial: "EditorialRead"
    genero: "GeneroRead | None"
    autorias: List["AutoriaRead"]


class LibroListItem(SQLModel):
    """DTO de salida para listado de libros."""

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial_id: int
    genero_id: int | None


class AutoriaRead(SQLModel):
    """DTO para autoría en detalle de libro."""

    autor: "AutorRead"
    rol: str
    orden: int


class EditorialRead(SQLModel):
    """DTO de editorial en detalle de libro."""

    id: int
    nombre: str
    pais: str | None


class GeneroRead(SQLModel):
    """DTO de género en detalle de libro."""

    id: int
    nombre: str


class AutorRead(SQLModel):
    """DTO de autor en detalle de libro."""

    id: int
    nombre: str
    nacionalidad: str | None


# Resolve forward references
LibroRead.model_rebuild()
AutoriaRead.model_rebuild()