"""Lógica de negocio del módulo editoriales."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import translate_integrity_error
from app.modules.editoriales.models import Editorial
from app.modules.editoriales.schemas import (
    EditorialCreate,
    EditorialListItem,
    EditorialRead,
    EditorialUpdate,
)
from app.modules.libros.models import Libro
from app.modules.libros.schemas import LibroListItem


async def create_editorial(session: AsyncSession, payload: EditorialCreate) -> EditorialRead:
    """Crea una nueva editorial delegando la unicidad en la base de datos (DD-04, RN-12)."""
    editorial = Editorial(nombre=payload.nombre, pais=payload.pais)
    session.add(editorial)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise translate_integrity_error(exc) from exc
    await session.refresh(editorial)
    return EditorialRead.model_validate(editorial)


async def list_editoriales(
    session: AsyncSession,
    limit: int,
    offset: int,
) -> list[EditorialListItem]:
    """Lista editoriales paginadas ordenadas por ID (RN-10)."""
    stmt = select(Editorial).order_by(Editorial.id).limit(limit).offset(offset)
    result = await session.execute(stmt)
    editoriales = result.scalars().all()
    return [EditorialListItem.model_validate(e) for e in editoriales]


async def get_editorial_or_404(session: AsyncSession, editorial_id: int) -> Editorial:
    """Obtiene una editorial por su clave primaria o lanza HTTP 404."""
    editorial = await session.get(Editorial, editorial_id)
    if editorial is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Editorial no encontrada",
        )
    return editorial


async def get_editorial(session: AsyncSession, editorial_id: int) -> EditorialRead:
    """Devuelve el DTO de lectura de una editorial existente."""
    editorial = await get_editorial_or_404(session, editorial_id)
    return EditorialRead.model_validate(editorial)


async def update_editorial(
    session: AsyncSession,
    editorial_id: int,
    payload: EditorialUpdate,
) -> EditorialRead:
    """Actualiza parcialmente una editorial usando exclude_unset=True y traduce colisiones a 409 (RN-12)."""
    editorial = await get_editorial_or_404(session, editorial_id)
    updates = payload.model_dump(exclude_unset=True)
    for field_name, field_value in updates.items():
        if field_value is not None:
            setattr(editorial, field_name, field_value)

    session.add(editorial)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise translate_integrity_error(exc) from exc
    await session.refresh(editorial)
    return EditorialRead.model_validate(editorial)


async def list_libros_by_editorial(
    session: AsyncSession,
    editorial_id: int,
    limit: int,
    offset: int,
) -> list[LibroListItem]:
    """Lista los libros pertenecientes a una editorial existente de forma paginada (RN-10)."""
    await get_editorial_or_404(session, editorial_id)
    stmt = (
        select(Libro)
        .where(Libro.editorial_id == editorial_id)
        .order_by(Libro.id)
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    libros = result.scalars().all()
    return [LibroListItem.model_validate(libro) for libro in libros]