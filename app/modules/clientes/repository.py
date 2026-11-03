"""Repositorio de persistencia para el módulo de clientes."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.clientes.models import Cliente


class ClienteRepository(BaseRepository[Cliente]):
    """Repositorio asincrónico para la entidad Cliente."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=Cliente)

    async def get_by_email(self, email: str) -> Cliente | None:
        """Busca un cliente por su dirección de correo electrónico."""
        stmt = select(Cliente).where(Cliente.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
