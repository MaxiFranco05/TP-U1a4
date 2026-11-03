"""Repositorios genéricos asincrónicos (BaseRepository y SoftDeleteRepository) sin confirmación transaccional."""

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """Repositorio base asincrónico que opera sobre la sesión compartida ejecutando sólo flush()."""

    def __init__(self, session: AsyncSession, model_cls: type[T]) -> None:
        self.session = session
        self.model_cls = model_cls

    async def get_by_id(self, entity_id: int) -> T | None:
        """Busca una entidad por su clave primaria id."""
        pk_col = getattr(self.model_cls, "id")
        stmt = select(self.model_cls).where(pk_col == entity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        filters: Sequence[Any] = (),
        order_by: Any | None = None,
        options: Sequence[Any] = (),
    ) -> list[T]:
        """Recupera un listado paginado de entidades aplicando filtros, orden y opciones de carga."""
        stmt = select(self.model_cls)
        for criterion in filters:
            stmt = stmt.where(criterion)
        for opt in options:
            stmt = stmt.options(opt)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        else:
            pk_col = getattr(self.model_cls, "id", None)
            if pk_col is not None:
                stmt = stmt.order_by(pk_col.asc())
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, *, filters: Sequence[Any] = ()) -> int:
        """Cuenta el total de registros que cumplen los filtros indicados."""
        stmt = select(func.count()).select_from(self.model_cls)
        for criterion in filters:
            stmt = stmt.where(criterion)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def add(self, entity: T) -> T:
        """Agrega una entidad a la sesión y ejecuta flush() sin confirmar la transacción."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: T, data: dict[str, Any] | None = None) -> T:
        """Actualiza atributos de una entidad y ejecuta flush() sin confirmar la transacción."""
        if data:
            for field_name, value in data.items():
                setattr(entity, field_name, value)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: T) -> None:
        """Elimina físicamente una entidad en la sesión y ejecuta flush() sin confirmar la transacción."""
        await self.session.delete(entity)
        await self.session.flush()


class SoftDeleteRepository(BaseRepository[T]):
    """Repositorio para entidades con baja lógica mediante columna borrado_en."""

    def _active_criterion(self) -> Any:
        """Condición de vigencia para registros no dados de baja lógica."""
        return getattr(self.model_cls, "borrado_en").is_(None)

    async def get_by_id(self, entity_id: int) -> T | None:
        """Busca una entidad activa (borrado_en IS NULL) por su clave primaria id."""
        pk_col = getattr(self.model_cls, "id")
        stmt = select(self.model_cls).where(
            pk_col == entity_id,
            self._active_criterion(),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        filters: Sequence[Any] = (),
        order_by: Any | None = None,
        options: Sequence[Any] = (),
    ) -> list[T]:
        """Recupera un listado paginado de entidades activas (borrado_en IS NULL)."""
        combined_filters = (self._active_criterion(), *filters)
        return await super().get_all(
            offset=offset,
            limit=limit,
            filters=combined_filters,
            order_by=order_by,
            options=options,
        )

    async def count(self, *, filters: Sequence[Any] = ()) -> int:
        """Cuenta el total de registros activos (borrado_en IS NULL) que cumplen los filtros."""
        combined_filters = (self._active_criterion(), *filters)
        return await super().count(filters=combined_filters)

    async def get_by_id_including_deleted(self, entity_id: int) -> T | None:
        """Busca una entidad por su clave primaria id sin filtrar por borrado_en (uso histórico)."""
        return await super().get_by_id(entity_id)

    async def soft_delete(self, entity: T) -> T:
        """Marca borrado_en con la marca temporal UTC actual y ejecuta flush() sin hacer commit()."""
        setattr(entity, "borrado_en", datetime.now(timezone.utc))
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
