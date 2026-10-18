"""Esquemas DTO del módulo ventas."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlmodel import SQLModel

if TYPE_CHECKING:
    from app.modules.libros.schemas import LibroRead


class RenglonVentaRead(SQLModel):
    """DTO de salida para un renglón de venta."""

    id: int
    venta_id: int
    libro_id: int
    cantidad: int
    precio_unitario: Decimal


class VentaRead(SQLModel):
    """DTO de salida para una venta con sus renglones."""

    id: int
    cliente_id: int
    fecha: datetime
    total: Decimal
    renglones: list[RenglonVentaRead] = []