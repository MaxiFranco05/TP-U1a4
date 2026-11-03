"""Unit of Work asincrónico para el módulo editoriales."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.editoriales.repository import EditorialRepository
from app.modules.libros.repository import LibroRepository


class EditorialesUnitOfWork(UnitOfWork):
    """Gobierna el límite transaccional para operaciones del catálogo de editoriales."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.editoriales = EditorialRepository(session=self.session)
        self.libros = LibroRepository(session=self.session)
