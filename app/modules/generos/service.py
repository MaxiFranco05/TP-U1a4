"""Lógica de negocio del módulo generos."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.generos.models import Genero
from app.modules.generos.schemas import (
    GeneroCreate,
    GeneroLibroRead,
    GeneroRead,
    GeneroUpdate,
)
from app.modules.libros.models import Libro


async def create_genero(session: AsyncSession, payload: GeneroCreate) -> GeneroRead:
    """Crea un nuevo género delegando la unicidad en la base de datos (DD-04, RN-12)."""
    genero = Genero(nombre=payload.nombre)
    session.add(genero)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un género con ese nombre",
        ) from exc
    await session.refresh(genero)
    return GeneroRead.model_validate(genero)


async def list_generos(
    session: AsyncSession,
    limit: int,
    offset: int,
) -> list[GeneroRead]:
    """Lista géneros paginados ordenados por ID (RN-10)."""
    stmt = select(Genero).order_by(Genero.id).limit(limit).offset(offset)
    result = await session.execute(stmt)
    generos = result.scalars().all()
    return [GeneroRead.model_validate(g) for g in generos]


async def get_genero_or_404(session: AsyncSession, genero_id: int) -> Genero:
    """Obtiene un género por su clave primaria o lanza HTTP 404."""
    genero = await session.get(Genero, genero_id)
    if genero is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Género no encontrado",
        )
    return genero


async def get_genero(session: AsyncSession, genero_id: int) -> GeneroRead:
    """Devuelve el DTO de lectura de un género existente."""
    genero = await get_genero_or_404(session, genero_id)
    return GeneroRead.model_validate(genero)


async def update_genero(
    session: AsyncSession,
    genero_id: int,
    payload: GeneroUpdate,
) -> GeneroRead:
    """Actualiza parcialmente un género usando exclude_unset=True y traduce colisiones a 409 (RN-12)."""
    genero = await get_genero_or_404(session, genero_id)
    updates = payload.model_dump(exclude_unset=True)
    for field_name, field_value in updates.items():
        if field_value is not None:
            setattr(genero, field_name, field_value)

    session.add(genero)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un género con ese nombre",
        ) from exc
    await session.refresh(genero)
    return GeneroRead.model_validate(genero)


async def list_libros_by_genero(
    session: AsyncSession,
    genero_id: int,
    limit: int,
    offset: int,
) -> list[GeneroLibroRead]:
    """Lista los libros pertenecientes a un género existente de forma paginada (RN-10)."""
    await get_genero_or_404(session, genero_id)
    stmt = (
        select(Libro)
        .where(Libro.genero_id == genero_id)
        .order_by(Libro.id)
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    libros = result.scalars().all()
    return [GeneroLibroRead.model_validate(libro) for libro in libros]
