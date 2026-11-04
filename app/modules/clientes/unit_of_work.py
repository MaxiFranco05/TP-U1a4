"""Unit of Work asincrónico para el módulo clientes y sus perfiles asociados."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.repository import ClienteRepository, PerfilClienteRepository


class ClientesUnitOfWork(UnitOfWork):
    """Gobierna el límite transaccional para clientes y perfiles."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.clientes = ClienteRepository(session=self.session)
        self.perfiles = PerfilClienteRepository(session=self.session)
