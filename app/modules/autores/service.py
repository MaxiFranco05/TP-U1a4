"""Lógica de negocio del módulo autores sobre UnitOfWork y Repository."""

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import translate_integrity_error
from app.core.paginacion import PaginatedResponse, PaginationParams, paginate
from app.modules.autores.models import Autor
from app.modules.autores.schemas import (
    AutorCreate,
    AutorLibroItem,
    AutorRead,
    AutorUpdate,
)
from app.modules.autores.unit_of_work import AutoresUnitOfWork


async def create_autor(
    uow: AutoresUnitOfWork,
    payload: AutorCreate,
) -> AutorRead:
    """Crea un nuevo autor delegando la unicidad en la base de datos (RN-12)."""
    autor = Autor(nombre=payload.nombre, nacionalidad=payload.nacionalidad)
    async with uow:
        try:
            await uow.autores.add(autor)
        except IntegrityError as exc:
            raise translate_integrity_error(exc) from exc
    return AutorRead.model_validate(autor)


async def list_autores(
    uow: AutoresUnitOfWork,
    params: PaginationParams,
) -> PaginatedResponse[AutorRead]:
    """Lista autores paginados con envoltorio estándar {items, total, page, size, pages}."""
    async with uow:
        total = await uow.autores.count()
        items = await uow.autores.get_all(
            offset=params.offset,
            limit=params.limit,
        )
        dtos = [AutorRead.model_validate(a) for a in items]
        return paginate(items=dtos, total=total, page=params.page, size=params.size)


async def get_autor(
    uow: AutoresUnitOfWork,
    autor_id: int,
) -> AutorRead:
    """Devuelve el DTO de lectura de un autor existente o lanza 404."""
    async with uow:
        autor = await uow.autores.get_by_id(autor_id)
        if autor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Autor no encontrado",
            )
        return AutorRead.model_validate(autor)


async def update_autor(
    uow: AutoresUnitOfWork,
    autor_id: int,
    payload: AutorUpdate,
) -> AutorRead:
    """Actualiza parcialmente un autor con exclude_unset=True traduciendo colisiones a 409 (RN-12)."""
    async with uow:
        autor = await uow.autores.get_by_id(autor_id)
        if autor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Autor no encontrado",
            )
        updates = payload.model_dump(exclude_unset=True)
        try:
            await uow.autores.update(autor, updates)
        except IntegrityError as exc:
            raise translate_integrity_error(exc) from exc
        return AutorRead.model_validate(autor)


async def list_libros_by_autor(
    uow: AutoresUnitOfWork,
    autor_id: int,
    params: PaginationParams,
) -> PaginatedResponse[AutorLibroItem]:
    """Lista los libros activos de un autor con rol y orden de forma paginada."""
    async with uow:
        autor = await uow.autores.get_by_id(autor_id)
        if autor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Autor no encontrado",
            )
        pairs, total = await uow.autores.get_libros_autor_paginado(
            autor_id=autor_id,
            offset=params.offset,
            limit=params.limit,
        )
        items: list[AutorLibroItem] = []
        for libro, libro_autor in pairs:
            items.append(
                AutorLibroItem(
                    id=libro.id,
                    isbn=libro.isbn,
                    titulo=libro.titulo,
                    precio=libro.precio,
                    stock=libro.stock,
                    editorial_id=libro.editorial_id,
                    genero_id=libro.genero_id,
                    rol=libro_autor.rol,
                    orden=libro_autor.orden,
                )
            )
        return paginate(items=items, total=total, page=params.page, size=params.size)
