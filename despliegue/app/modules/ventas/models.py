"""Modelos de persistencia del módulo ventas y composición RenglonVenta."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, DateTime, Numeric, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.clientes.models import Cliente
    from app.modules.libros.models import Libro


class Venta(SQLModel, table=True):
    """Cabecera de una venta registrada con marca de tiempo con zona horaria (TIMESTAMPTZ)."""

    __tablename__ = "venta"
    __table_args__ = (
        CheckConstraint("total >= 0", name="ck_venta_total_no_negativo"),
    )

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(
        foreign_key="cliente.id",
        index=True,
        nullable=False,
    )
    fecha: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
    total: Decimal = Field(sa_column=Column(Numeric(12, 2), nullable=False))

    cliente: "Cliente" = Relationship(back_populates="ventas")
    renglones: list["RenglonVenta"] = Relationship(back_populates="venta")


class RenglonVenta(SQLModel, table=True):
    """Renglón individual de una venta (composición)."""

    __tablename__ = "renglon_venta"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_renglon_venta_cantidad_positiva"),
        CheckConstraint(
            "precio_unitario > 0",
            name="ck_renglon_venta_precio_unitario_positivo",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    venta_id: int = Field(
        foreign_key="venta.id",
        index=True,
        nullable=False,
    )
    libro_id: int = Field(
        foreign_key="libro.id",
        index=True,
        nullable=False,
    )
    cantidad: int = Field(nullable=False)
    precio_unitario: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))

    venta: Venta = Relationship(back_populates="renglones")
    libro: "Libro" = Relationship(back_populates="renglones_venta")

    @property
    def titulo(self) -> str:
        return self.libro.titulo if self.libro else ""

    @property
    def subtotal(self) -> Decimal:
        return Decimal(str(self.cantidad)) * self.precio_unitario

