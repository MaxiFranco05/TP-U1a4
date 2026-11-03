"""Esquemas DTO del módulo libros."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import ConfigDict, Field, field_validator
from sqlmodel import SQLModel

from app.modules.autores.schemas import AutorRead
from app.modules.editoriales.schemas import EditorialRead
from app.modules.generos.schemas import GeneroRead


class AutorCreateNested(SQLModel):
    """DTO para autor dentro de la creación de libro (autor existente + rol + orden)."""

    model_config = ConfigDict(extra="forbid")

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
    """DTO de entrada para la creación de un libro con stock inicial y autores."""

    model_config = ConfigDict(extra="forbid")

    isbn: str
    titulo: str
    precio: Decimal = Field(gt=0, description="Precio debe ser positivo")
    stock_inicial: int = Field(default=0, ge=0, description="Stock inicial no puede ser negativo")
    editorial_id: int = Field(ge=1)
    genero_id: int | None = None
    autores: list[AutorCreateNested] = Field(default_factory=list)

    @field_validator("titulo")
    @classmethod
    def validate_titulo(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("El título no puede estar vacío")
        return cleaned


class LibroUpdate(SQLModel):
    """DTO de entrada para la actualización parcial (PATCH) de un libro (solo título y precio)."""

    model_config = ConfigDict(extra="forbid")

    titulo: str | None = None
    precio: Decimal | None = Field(default=None, gt=0, description="Precio debe ser positivo")

    @field_validator("titulo")
    @classmethod
    def validate_titulo(cls, value: str | None) -> str | None:
        if value is not None:
            cleaned = value.strip()
            if not cleaned:
                raise ValueError("El título no puede estar vacío")
            return cleaned
        return value


class ReponerStockRequest(SQLModel):
    """DTO de entrada para reposición de stock (ADMIN)."""

    model_config = ConfigDict(extra="forbid")

    cantidad: int = Field(gt=0, description="Cantidad a reponer (debe ser mayor a 0)")


class MovimientoStockRead(SQLModel):
    """DTO de salida para consulta de movimientos de stock."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    libro_id: int
    venta_id: int | None = None
    usuario_id: int
    cantidad: int
    motivo: str
    cuando: datetime


class AutoriaRead(SQLModel):
    """DTO para autoría en detalle de libro."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    autor: AutorRead
    rol: str
    orden: int


class LibroRead(SQLModel):
    """DTO de salida para detalle completo de un libro."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial_id: int
    genero_id: int | None
    editorial: EditorialRead
    genero: GeneroRead | None
    autorias: list[AutoriaRead]


class LibroListItem(SQLModel):
    """DTO de salida para listado de libros."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial_id: int
    genero_id: int | None


LibroRead.model_rebuild()
AutoriaRead.model_rebuild()
