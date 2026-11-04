"""Unit of Work asincrónico para el módulo ventas, composición de clientes, libros y stock."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.repository import ClienteRepository
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.libros.repository import LibroRepository, MovimientoStockRepository
from app.modules.libros.unit_of_work import LibrosUnitOfWork
from app.modules.ventas.repository import VentaRepository


class VentasUnitOfWork(UnitOfWork):
    """Gobierna el límite transaccional para ventas, clientes, libros y movimientos de stock."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.ventas = VentaRepository(session=self.session)
        self.clientes = ClienteRepository(session=self.session)
        self.libros = LibroRepository(session=self.session)
        self.movimientos = MovimientoStockRepository(session=self.session)
        self._libros_uow = LibrosUnitOfWork(session=self.session)

    async def registrar_movimiento_stock(
        self,
        libro: Libro | int,
        cantidad: int,
        motivo: str,
        usuario_id: int,
        venta_id: int | None = None,
    ) -> MovimientoStock | None:
        """Punto único de escritura de stock (RN-11).

        Delega en la implementación canónica de LibrosUnitOfWork compartiendo la misma sesión,
        garantizando que la validación de stock, bloqueo FOR UPDATE y movimientos sean idénticos
        y centralizados.
        """
        return await self._libros_uow.registrar_movimiento_stock(
            libro=libro,
            cantidad=cantidad,
            motivo=motivo,
            usuario_id=usuario_id,
            venta_id=venta_id,
        )
