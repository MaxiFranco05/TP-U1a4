"""Modelos de persistencia del módulo editoriales."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.libros.models import Libro


class Editorial(SQLModel, table=True):
    """Entidad editorial del catálogo."""

    __tablename__ = "editorial"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(unique=True, nullable=False)
    pais: str = Field(nullable=False)

    libros: list["Libro"] = Relationship(back_populates="editorial")
