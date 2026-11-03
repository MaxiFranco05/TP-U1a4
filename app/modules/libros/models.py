"""Modelos de persistencia del módulo libros, objeto de asociación LibroAutor y MovimientoStock."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, Column, DateTime, Index, Numeric, func, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.autores.models import Autor
    from app.modules.editoriales.models import Editorial
    from app.modules.generos.models import Genero
    from app.modules.usuarios.models import Usuario
    from app.modules.ventas.models import RenglonVenta, Venta


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
    """Entidad libro del catálogo con baja lógica (borrado_en) e índice único parcial sobre isbn activo."""

    __tablename__ = "libro"
    __table_args__ = (
        CheckConstraint("precio > 0", name="ck_libro_precio_positivo"),
        CheckConstraint("stock >= 0", name="ck_libro_stock_no_negativo"),
        Index(
            "uq_libro_isbn_activo",
            "isbn",
            unique=True,
            postgresql_where=text("borrado_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    isbn: str = Field(nullable=False)
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
    borrado_en: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    editorial: "Editorial" = Relationship(back_populates="libros")
    genero: Optional["Genero"] = Relationship(back_populates="libros")
    autorias: list[LibroAutor] = Relationship(back_populates="libro")
    renglones_venta: list["RenglonVenta"] = Relationship(back_populates="libro")
    movimientos_stock: list["MovimientoStock"] = Relationship(back_populates="libro")


class MovimientoStock(SQLModel, table=True):
    """Movimiento de stock de sólo-agregado (appendOnly, RN-11, RN-12)."""

    __tablename__ = "movimiento_stock"
    __table_args__ = (
        CheckConstraint("cantidad <> 0", name="ck_movimiento_stock_cantidad_no_cero"),
    )

    id: int | None = Field(default=None, primary_key=True)
    libro_id: int = Field(
        foreign_key="libro.id",
        index=True,
        nullable=False,
    )
    venta_id: int | None = Field(
        default=None,
        foreign_key="venta.id",
        index=True,
        nullable=True,
    )
    usuario_id: int = Field(
        foreign_key="usuario.id",
        index=True,
        nullable=False,
    )
    cantidad: int = Field(nullable=False)
    motivo: str = Field(nullable=False)
    cuando: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    libro: Libro = Relationship(back_populates="movimientos_stock")
    venta: Optional["Venta"] = Relationship(back_populates="movimientos_stock")
    usuario: "Usuario" = Relationship(back_populates="movimientos_stock")
