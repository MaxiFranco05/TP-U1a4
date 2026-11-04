"""Repositorio de persistencia para el módulo de clientes y perfiles."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.repository import BaseRepository
from app.modules.clientes.models import Cliente, PerfilCliente


class ClienteRepository(BaseRepository[Cliente]):
    """Repositorio asincrónico para la entidad Cliente."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=Cliente)

    async def get_by_email(self, email: str) -> Cliente | None:
        """Busca un cliente por su dirección de correo electrónico."""
        stmt = select(Cliente).where(Cliente.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_con_perfil(self, cliente_id: int) -> Cliente | None:
        """Obtiene un cliente con su perfil y usuario precargados (joinedload)."""
        stmt = (
            select(Cliente)
            .where(Cliente.id == cliente_id)
            .options(
                joinedload(Cliente.perfil),
                joinedload(Cliente.usuario),
            )
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()


class PerfilClienteRepository(BaseRepository[PerfilCliente]):
    """Repositorio asincrónico para la entidad PerfilCliente."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=PerfilCliente)

    async def get_por_cliente(self, cliente_id: int) -> PerfilCliente | None:
        """Busca el perfil asociado a un cliente específico."""
        stmt = select(PerfilCliente).where(PerfilCliente.cliente_id == cliente_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
