"""Modelos de persistencia del módulo libros y objeto de asociación LibroAutor."""

from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, Column, Numeric
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.autores.models import Autor
    from app.modules.editoriales.models import Editorial
    from app.modules.generos.models import Genero
    from app.modules.ventas.models import RenglonVenta


class LibroAutor(SQLModel, table=True):
    """Objeto de asociación entre Libro y Autor con atributos propios (rol, orden)."""

    __tablename__ = "libro_autor"
    __table_args__ = (
        CheckConstraint("orden >= 1", name="ck_libro_autor_orden_minimo"),
        CheckConstraint(
            "rol IN ('autor', 'coautor', 'traductor', 'ilustrador')",
            name="ck_libro_autor_rol_valido",
        ),
    )

    libro_id: int = Field(
        foreign_key="libro.id",
        primary_key=True,
        index=True,
        nullable=False,
    )
    autor_id: int = Field(
        foreign_key="autor.id",
        primary_key=True,
        index=True,
        nullable=False,
    )
    rol: str = Field(nullable=False)
    orden: int = Field(nullable=False)

    libro: "Libro" = Relationship(back_populates="autorias")
    autor: "Autor" = Relationship(back_populates="autorias")


class Libro(SQLModel, table=True):
    """Entidad libro del catálogo con agregación opcional hacia Genero."""

    __tablename__ = "libro"
    __table_args__ = (
        CheckConstraint("precio > 0", name="ck_libro_precio_positivo"),
        CheckConstraint("stock >= 0", name="ck_libro_stock_no_negativo"),
    )

    id: int | None = Field(default=None, primary_key=True)
    isbn: str = Field(unique=True, nullable=False)
    titulo: str = Field(nullable=False)
    precio: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    stock: int = Field(nullable=False)
    editorial_id: int = Field(
        foreign_key="editorial.id",
        index=True,
        nullable=False,
    )
    genero_id: int | None = Field(
        default=None,
        foreign_key="genero.id",
        index=True,
        nullable=True,
    )

    editorial: "Editorial" = Relationship(back_populates="libros")
    genero: Optional["Genero"] = Relationship(back_populates="libros")
    autorias: list[LibroAutor] = Relationship(back_populates="libro")
    renglones_venta: list["RenglonVenta"] = Relationship(back_populates="libro")
