"""Lógica de negocio del módulo editoriales sobre UnitOfWork y Repository."""

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import translate_integrity_error
from app.core.paginacion import PaginatedResponse, PaginationParams, paginate
from app.modules.editoriales.models import Editorial
from app.modules.editoriales.schemas import (
    EditorialCreate,
    EditorialListItem,
    EditorialRead,
    EditorialUpdate,
)
from app.modules.editoriales.unit_of_work import EditorialesUnitOfWork
from app.modules.libros.models import Libro
from app.modules.libros.schemas import LibroListItem


async def create_editorial(
    uow: EditorialesUnitOfWork,
    payload: EditorialCreate,
) -> EditorialRead:
    """Crea una nueva editorial delegando la unicidad en la base de datos (RN-12)."""
    editorial = Editorial(nombre=payload.nombre, pais=payload.pais)
    async with uow:
        try:
            await uow.editoriales.add(editorial)
        except IntegrityError as exc:
            raise translate_integrity_error(exc) from exc
    return EditorialRead.model_validate(editorial)


async def list_editoriales(
    uow: EditorialesUnitOfWork,
    params: PaginationParams,
) -> PaginatedResponse[EditorialListItem]:
    """Lista editoriales de forma paginada con el envoltorio estándar {items, total, page, size, pages}."""
    async with uow:
        total = await uow.editoriales.count()
        items = await uow.editoriales.get_all(
            offset=params.offset,
            limit=params.limit,
        )
        dtos = [EditorialListItem.model_validate(e) for e in items]
        return paginate(items=dtos, total=total, page=params.page, size=params.size)


async def get_editorial(
    uow: EditorialesUnitOfWork,
    editorial_id: int,
) -> EditorialRead:
    """Devuelve el DTO de lectura de una editorial existente o lanza 404."""
    async with uow:
        editorial = await uow.editoriales.get_by_id(editorial_id)
        if editorial is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Editorial no encontrada",
            )
        return EditorialRead.model_validate(editorial)


async def update_editorial(
    uow: EditorialesUnitOfWork,
    editorial_id: int,
    payload: EditorialUpdate,
) -> EditorialRead:
    """Actualiza parcialmente una editorial con exclude_unset=True traduciendo colisiones a 409 (RN-12)."""
    async with uow:
        editorial = await uow.editoriales.get_by_id(editorial_id)
        if editorial is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Editorial no encontrada",
            )
        updates = payload.model_dump(exclude_unset=True)
        try:
            await uow.editoriales.update(editorial, updates)
        except IntegrityError as exc:
            raise translate_integrity_error(exc) from exc
        return EditorialRead.model_validate(editorial)


async def list_libros_by_editorial(
    uow: EditorialesUnitOfWork,
    editorial_id: int,
    params: PaginationParams,
) -> PaginatedResponse[LibroListItem]:
    """Lista los libros activos pertenecientes a una editorial existente con paginación uniforme."""
    async with uow:
        editorial = await uow.editoriales.get_by_id(editorial_id)
        if editorial is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Editorial no encontrada",
            )
        filters = (Libro.editorial_id == editorial_id,)
        total = await uow.libros.count(filters=filters)
        libros = await uow.libros.get_all(
            offset=params.offset,
            limit=params.limit,
            filters=filters,
        )
        dtos = [LibroListItem.model_validate(libro) for libro in libros]
        return paginate(items=dtos, total=total, page=params.page, size=params.size)
