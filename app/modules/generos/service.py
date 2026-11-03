"""Lógica de negocio del módulo generos sobre UnitOfWork y Repository."""

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import translate_integrity_error
from app.core.paginacion import PaginatedResponse, PaginationParams, paginate
from app.modules.generos.models import Genero
from app.modules.generos.schemas import (
    GeneroCreate,
    GeneroLibroRead,
    GeneroRead,
    GeneroUpdate,
)
from app.modules.generos.unit_of_work import GenerosUnitOfWork
from app.modules.libros.models import Libro


async def create_genero(
    uow: GenerosUnitOfWork,
    payload: GeneroCreate,
) -> GeneroRead:
    """Crea un nuevo género delegando la unicidad en la base de datos (RN-12)."""
    genero = Genero(nombre=payload.nombre)
    async with uow:
        try:
            await uow.generos.add(genero)
        except IntegrityError as exc:
            raise translate_integrity_error(exc) from exc
    return GeneroRead.model_validate(genero)


async def list_generos(
    uow: GenerosUnitOfWork,
    params: PaginationParams,
) -> PaginatedResponse[GeneroRead]:
    """Lista géneros paginados con envoltorio estándar {items, total, page, size, pages}."""
    async with uow:
        total = await uow.generos.count()
        items = await uow.generos.get_all(
            offset=params.offset,
            limit=params.limit,
        )
        dtos = [GeneroRead.model_validate(g) for g in items]
        return paginate(items=dtos, total=total, page=params.page, size=params.size)


async def get_genero(
    uow: GenerosUnitOfWork,
    genero_id: int,
) -> GeneroRead:
    """Devuelve el DTO de lectura de un género existente o lanza 404."""
    async with uow:
        genero = await uow.generos.get_by_id(genero_id)
        if genero is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Género no encontrado",
            )
        return GeneroRead.model_validate(genero)


async def update_genero(
    uow: GenerosUnitOfWork,
    genero_id: int,
    payload: GeneroUpdate,
) -> GeneroRead:
    """Actualiza parcialmente un género traduciendo colisiones de unicidad a 409 (RN-12)."""
    async with uow:
        genero = await uow.generos.get_by_id(genero_id)
        if genero is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Género no encontrado",
            )
        updates = payload.model_dump(exclude_unset=True)
        try:
            await uow.generos.update(genero, updates)
        except IntegrityError as exc:
            raise translate_integrity_error(exc) from exc
        return GeneroRead.model_validate(genero)


async def list_libros_by_genero(
    uow: GenerosUnitOfWork,
    genero_id: int,
    params: PaginationParams,
) -> PaginatedResponse[GeneroLibroRead]:
    """Lista los libros activos pertenecientes a un género existente con paginación uniforme."""
    async with uow:
        genero = await uow.generos.get_by_id(genero_id)
        if genero is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Género no encontrado",
            )
        filters = (Libro.genero_id == genero_id,)
        total = await uow.libros.count(filters=filters)
        libros = await uow.libros.get_all(
            offset=params.offset,
            limit=params.limit,
            filters=filters,
        )
        dtos = [GeneroLibroRead.model_validate(libro) for libro in libros]
        return paginate(items=dtos, total=total, page=params.page, size=params.size)
