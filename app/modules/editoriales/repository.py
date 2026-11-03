"""Repositorio asincrónico para la entidad Editorial."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.editoriales.models import Editorial


class EditorialRepository(BaseRepository[Editorial]):
    """Repositorio asincrónico para el catálogo de editoriales (solo flush, sin commit)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=Editorial)
