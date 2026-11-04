"""Modelos de persistencia del módulo clientes y PerfilCliente (1 a 0..1)."""

from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.ventas.models import Venta


class Cliente(SQLModel, table=True):
    """Entidad cliente con relación 1 a 0..1 hacia PerfilCliente y 1 a * hacia Venta."""

    __tablename__ = "cliente"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(nullable=False)
    email: str = Field(unique=True, nullable=False)

    perfil: Optional["PerfilCliente"] = Relationship(
        back_populates="cliente",
        sa_relationship_kwargs={"uselist": False},
    )
    ventas: list["Venta"] = Relationship(back_populates="cliente")


class PerfilCliente(SQLModel, table=True):
    """Perfil de datos de contacto asociado a un único cliente (RN-09)."""

    __tablename__ = "perfil_cliente"

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(
        foreign_key="cliente.id",
        unique=True,
        index=True,
        nullable=False,
    )
    telefono: str = Field(nullable=False)
    direccion: str = Field(nullable=False)

    cliente: Cliente = Relationship(back_populates="perfil")
