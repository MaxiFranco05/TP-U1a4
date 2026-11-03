"""Repositorio asincrónico para la entidad Genero."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.generos.models import Genero


class GeneroRepository(BaseRepository[Genero]):
    """Repositorio asincrónico para el catálogo de géneros (solo flush, sin commit)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=Genero)
