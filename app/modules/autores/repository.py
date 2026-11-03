"""Repositorio asincrónico para la entidad Autor."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.autores.models import Autor
from app.modules.libros.models import Libro, LibroAutor


class AutorRepository(BaseRepository[Autor]):
    """Repositorio asincrónico para el catálogo de autores (solo flush, sin commit)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=Autor)

    async def get_libros_autor_paginado(
        self,
        autor_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[tuple[Libro, LibroAutor]], int]:
        """Obtiene los libros activos asociados al autor con datos de autoría y el total para paginación."""
        count_stmt = (
            select(func.count())
            .select_from(Libro)
            .join(LibroAutor, Libro.id == LibroAutor.libro_id)
            .where(LibroAutor.autor_id == autor_id, Libro.borrado_en.is_(None))
        )
        total = int((await self.session.execute(count_stmt)).scalar_one())

        items_stmt = (
            select(Libro, LibroAutor)
            .join(LibroAutor, Libro.id == LibroAutor.libro_id)
            .where(LibroAutor.autor_id == autor_id, Libro.borrado_en.is_(None))
            .order_by(Libro.id.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(items_stmt)
        items = list(result.all())
        return items, total
