"""Lógica de negocio del módulo autores."""

from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.exceptions import translate_integrity_error
from app.modules.autores.models import Autor
from app.modules.autores.schemas import (
    AutorCreate,
    AutorLibroItem,
    AutorRead,
    AutorUpdate,
)
from app.modules.libros.models import Libro, LibroAutor


async def create_autor(session: AsyncSession, payload: AutorCreate) -> AutorRead:
    """Crea un nuevo autor delegando la unicidad en la base de datos (DD-04, RN-12)."""
    autor = Autor(nombre=payload.nombre, nacionalidad=payload.nacionalidad)
    session.add(autor)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise translate_integrity_error(exc) from exc
    await session.refresh(autor)
    return AutorRead.model_validate(autor)


async def get_autor_or_404(session: AsyncSession, autor_id: int) -> Autor:
    """Obtiene un autor por su clave primaria o lanza HTTP 404."""
    autor = await session.get(Autor, autor_id)
    if autor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Autor no encontrado",
        )
    return autor


async def get_autor(session: AsyncSession, autor_id: int) -> AutorRead:
    """Devuelve el DTO de lectura de un autor existente."""
    autor = await get_autor_or_404(session, autor_id)
    return AutorRead.model_validate(autor)


async def update_autor(
    session: AsyncSession,
    autor_id: int,
    payload: AutorUpdate,
) -> AutorRead:
    """Actualiza parcialmente un autor usando exclude_unset=True y traduce colisiones a 409 (RN-12)."""
    autor = await get_autor_or_404(session, autor_id)
    updates = payload.model_dump(exclude_unset=True)
    for field_name, field_value in updates.items():
        if field_value is not None:
            setattr(autor, field_name, field_value)

    session.add(autor)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise translate_integrity_error(exc) from exc
    await session.refresh(autor)
    return AutorRead.model_validate(autor)


async def list_libros_by_autor(
    session: AsyncSession,
    autor_id: int,
    limit: int,
    offset: int,
) -> list[AutorLibroItem]:
    """Lista los libros de un autor existente con rol y orden de forma paginada (RN-10)."""
    await get_autor_or_404(session, autor_id)
    stmt = (
        select(Libro)
        .join(LibroAutor, Libro.id == LibroAutor.libro_id)
        .where(LibroAutor.autor_id == autor_id)
        .options(
            joinedload(Libro.editorial),
            joinedload(Libro.genero),
        )
        .order_by(Libro.id)
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    libros = result.unique().scalars().all()

    items = []
    for libro in libros:
        # Find the LibroAutor for this autor to get rol and orden
        libro_autor = next((la for la in libro.autorias if la.autor_id == autor_id), None)
        if libro_autor:
            items.append(
                AutorLibroItem(
                    id=libro.id,
                    isbn=libro.isbn,
                    titulo=libro.titulo,
                    precio=float(libro.precio),
                    stock=libro.stock,
                    editorial_id=libro.editorial_id,
                    genero_id=libro.genero_id,
                    rol=libro_autor.rol,
                    orden=libro_autor.orden,
                )
            )
    return items