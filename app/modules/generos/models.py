"""Modelos de persistencia del módulo generos."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.libros.models import Libro


class Genero(SQLModel, table=True):
    """Entidad género literario del catálogo."""

    __tablename__ = "genero"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(unique=True, nullable=False)

    libros: list["Libro"] = Relationship(back_populates="genero")
