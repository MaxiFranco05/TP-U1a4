"""Repositorio de persistencia para el módulo de ventas y renglones."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.repository import BaseRepository
from app.modules.clientes.models import Cliente
from app.modules.ventas.models import RenglonVenta, Venta


class VentaRepository(BaseRepository[Venta]):
    """Repositorio asincrónico para la entidad Venta y sus renglones con precarga optimizada."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=Venta)

    async def get_detalle(self, venta_id: int) -> Venta | None:
        """Obtiene el detalle completo de una venta con cliente, renglones y libros precargados.

        Usa joinedload para cliente y selectinload para renglones con joinedload de libro,
        garantizando un número fijo de consultas SQL independiente de la cantidad de renglones (sin N+1).
        Permite visualizar libros que hayan sido dados de baja lógica después de la venta.
        """
        stmt = (
            select(Venta)
            .where(Venta.id == venta_id)
            .options(
                joinedload(Venta.cliente),
                selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
            )
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def listar(
        self,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Venta]:
        """Lista ventas paginadas ordenadas por fecha descendente con cliente precargado."""
        stmt = (
            select(Venta)
            .options(joinedload(Venta.cliente))
            .order_by(Venta.fecha.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())

    async def listar_por_usuario(
        self,
        usuario_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Venta]:
        """Lista las ventas del cliente asociado a un usuario específico, con paginación."""
        stmt = (
            select(Venta)
            .join(Cliente, Venta.cliente_id == Cliente.id)
            .where(Cliente.usuario_id == usuario_id)
            .options(joinedload(Venta.cliente))
            .order_by(Venta.fecha.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())

    async def count_por_usuario(self, usuario_id: int) -> int:
        """Cuenta el total de ventas del cliente asociado al usuario indicado."""
        stmt = (
            select(func.count())
            .select_from(Venta)
            .join(Cliente, Venta.cliente_id == Cliente.id)
            .where(Cliente.usuario_id == usuario_id)
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def listar_por_cliente(
        self,
        cliente_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Venta]:
        """Lista el historial de ventas de un cliente específico con renglones precargados."""
        stmt = (
            select(Venta)
            .where(Venta.cliente_id == cliente_id)
            .options(
                joinedload(Venta.cliente),
                selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
            )
            .order_by(Venta.fecha.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())

    async def count_por_cliente(self, cliente_id: int) -> int:
        """Cuenta el total de ventas para un cliente específico."""
        stmt = (
            select(func.count())
            .select_from(Venta)
            .where(Venta.cliente_id == cliente_id)
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())
