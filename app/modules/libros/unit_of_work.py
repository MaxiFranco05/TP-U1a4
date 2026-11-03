"""Unit of Work asincrónico para el módulo libros y catálogo asociado."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.autores.repository import AutorRepository
from app.modules.editoriales.repository import EditorialRepository
from app.modules.generos.repository import GeneroRepository
from app.modules.libros.models import Libro, MovimientoStock
from app.modules.libros.repository import LibroRepository, MovimientoStockRepository


class LibrosUnitOfWork(UnitOfWork):
    """Gobierna el límite transaccional para libros, movimientos de stock y relaciones de catálogo."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.libros = LibroRepository(session=self.session)
        self.movimientos = MovimientoStockRepository(session=self.session)
        self.editoriales = EditorialRepository(session=self.session)
        self.autores = AutorRepository(session=self.session)
        self.generos = GeneroRepository(session=self.session)

    async def registrar_movimiento_stock(
        self,
        libro: Libro | int,
        cantidad: int,
        motivo: str,
        usuario_id: int,
        venta_id: int | None = None,
    ) -> MovimientoStock | None:
        """Punto único de escritura de stock (RN-11).

        Actualiza libro.stock y agrega el MovimientoStock correspondiente dentro del mismo UoW.
        Valida que stock + cantidad >= 0. Si cantidad == 0 no inserta movimiento y retorna None.
        Aplica SELECT ... FOR UPDATE sobre el libro para prevenir condiciones de carrera.
        """
        if isinstance(libro, int):
            libro_obj = await self.libros.get_by_id_for_update(libro)
            if libro_obj is None:
                deleted = await self.libros.get_by_id_including_deleted(libro)
                if deleted is not None and deleted.borrado_en is not None:
                    raise ValueError("No se puede registrar movimiento en un libro dado de baja")
                raise ValueError("Libro no encontrado")
        else:
            libro_obj = libro
            if libro_obj.id is not None:
                locked = await self.libros.get_by_id_for_update(libro_obj.id)
                if locked is not None:
                    libro_obj = locked
            if libro_obj.borrado_en is not None:
                raise ValueError("No se puede registrar movimiento en un libro dado de baja")

        if libro_obj.stock + cantidad < 0:
            raise ValueError(
                f"Stock insuficiente: stock actual {libro_obj.stock}, cambio solicitado {cantidad}"
            )

        if cantidad == 0:
            return None

        libro_obj.stock += cantidad
        self.session.add(libro_obj)

        movimiento = MovimientoStock(
            libro_id=libro_obj.id,
            venta_id=venta_id,
            usuario_id=usuario_id,
            cantidad=cantidad,
            motivo=motivo,
        )
        self.session.add(movimiento)
        await self.session.flush()
        await self.session.refresh(libro_obj)
        await self.session.refresh(movimiento)
        return movimiento
