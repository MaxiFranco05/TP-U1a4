"""Unit of Work asincrónico para el módulo generos."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.generos.repository import GeneroRepository
from app.modules.libros.repository import LibroRepository


class GenerosUnitOfWork(UnitOfWork):
    """Gobierna el límite transaccional para operaciones del catálogo de géneros."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.generos = GeneroRepository(session=self.session)
        self.libros = LibroRepository(session=self.session)
