"""Esquemas DTO del módulo ventas."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Annotated

from pydantic import Field, field_validator, model_validator
from sqlmodel import SQLModel

if TYPE_CHECKING:
    from app.modules.libros.schemas import LibroRead


class RenglonVentaCreate(SQLModel):
    """DTO de entrada para la creación de un renglón de venta."""

    libro_id: int = Field(ge=1, description="ID del libro")
    cantidad: int = Field(gt=0, description="Cantidad debe ser positiva")

    @field_validator("cantidad")
    @classmethod
    def validate_cantidad(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("La cantidad debe ser mayor a 0")
        return value


class VentaCreate(SQLModel):
    """DTO de entrada para la creación de una venta con renglones."""

    cliente_id: int = Field(ge=1, description="ID del cliente")
    renglones: Annotated[list[RenglonVentaCreate], Field(min_length=1, description="Al menos un renglón")]

    @model_validator(mode="after")
    def validate_no_duplicate_libros(self) -> "VentaCreate":
        libro_ids = [r.libro_id for r in self.renglones]
        if len(libro_ids) != len(set(libro_ids)):
            raise ValueError("No se permiten libros duplicados en los renglones")
        return self


class ClienteVentaRead(SQLModel):
    """DTO simplificado del cliente dentro del detalle de venta (PDF pág. 9)."""

    id: int
    nombre: str
    email: str


class RenglonVentaRead(SQLModel):
    """DTO de salida para un renglón de venta (PDF pág. 9)."""

    libro_id: int
    titulo: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


class VentaRead(SQLModel):
    """DTO de salida para una venta con cliente y renglones detallados (PDF pág. 9)."""

    id: int
    fecha: datetime
    total: Decimal
    cliente: ClienteVentaRead
    renglones: list[RenglonVentaRead] = []


class VentaListItem(SQLModel):
    """DTO de salida para listado de ventas (sin renglones para evitar N+1)."""

    id: int
    cliente_id: int
    fecha: datetime
    total: Decimal