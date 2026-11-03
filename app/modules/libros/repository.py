"""Repositorios asincrónicos para Libro y MovimientoStock."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.repository import BaseRepository, SoftDeleteRepository
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock


class LibroRepository(SoftDeleteRepository[Libro]):
    """Repositorio asincrónico para Libro con soporte de baja lógica y precarga de relaciones."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=Libro)

    @staticmethod
    def _preload_options() -> tuple[Any, ...]:
        """Opciones de precarga para evitar consultas N+1 en lecturas del catálogo."""
        return (
            joinedload(Libro.editorial),
            joinedload(Libro.genero),
            selectinload(Libro.autorias).joinedload(LibroAutor.autor),
        )

    async def get_detalle(self, libro_id: int) -> Libro | None:
        """Obtiene un libro activo por ID con editorial, género y autorías precargadas."""
        stmt = (
            select(Libro)
            .where(Libro.id == libro_id, self._active_criterion())
            .options(*self._preload_options())
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, libro_id: int) -> Libro | None:
        """Obtiene un libro activo con bloqueo pesimista (SELECT ... FOR UPDATE) para actualización de stock."""
        stmt = (
            select(Libro)
            .where(Libro.id == libro_id, self._active_criterion())
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_detallado(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        filters: Sequence[Any] = (),
        order_by: Any | None = None,
    ) -> list[Libro]:
        """Lista libros activos con relaciones precargadas para evitar N+1 en listados."""
        return await self.get_all(
            offset=offset,
            limit=limit,
            filters=filters,
            order_by=order_by,
            options=self._preload_options(),
        )


class MovimientoStockRepository(BaseRepository[MovimientoStock]):
    """Repositorio asincrónico para MovimientoStock (sólo-agregado, sin commit)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model_cls=MovimientoStock)

    async def get_movimientos_by_libro(self, libro_id: int) -> list[MovimientoStock]:
        """Obtiene los movimientos de stock asociados a un libro ordenados cronológicamente."""
        stmt = (
            select(MovimientoStock)
            .where(MovimientoStock.libro_id == libro_id)
            .order_by(MovimientoStock.cuando.asc(), MovimientoStock.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def sum_cantidad_by_libro(self, libro_id: int) -> int:
        """Calcula la suma de cantidades de movimientos para verificar el invariante de stock."""
        stmt = (
            select(func.coalesce(func.sum(MovimientoStock.cantidad), 0))
            .where(MovimientoStock.libro_id == libro_id)
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())
