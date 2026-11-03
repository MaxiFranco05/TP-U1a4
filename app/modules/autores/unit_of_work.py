"""Unit of Work asincrónico para el módulo autores."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.autores.repository import AutorRepository
from app.modules.libros.repository import LibroRepository


class AutoresUnitOfWork(UnitOfWork):
    """Gobierna el límite transaccional para operaciones del catálogo de autores."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.autores = AutorRepository(session=self.session)
        self.libros = LibroRepository(session=self.session)
