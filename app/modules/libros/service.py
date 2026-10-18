"""Lógica de negocio del módulo libros."""

from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.exceptions import translate_integrity_error
from app.modules.libros.models import Libro, LibroAutor
from app.modules.libros.schemas import (
    AutorCreateNested,
    AutorRead,
    AutoriaRead,
    LibroCreate,
    LibroListItem,
    LibroRead,
    EditorialRead,
    GeneroRead,
)


async def create_libro_with_autores(
    session: AsyncSession,
    payload: LibroCreate,
) -> LibroRead:
    """Crea un libro con sus autores en una sola transacción (DD-04, RN-12)."""
    libro = Libro(
        isbn=payload.isbn,
        titulo=payload.titulo,
        precio=payload.precio,
        stock=payload.stock,
        editorial_id=payload.editorial_id,
        genero_id=payload.genero_id,
    )
    session.add(libro)

    try:
        await session.flush()  # Get the libro.id

        # Add LibroAutor entries after flush so libro.id is available
        for autor_data in payload.autores:
            libro_autor = LibroAutor(
                libro_id=libro.id,
                autor_id=autor_data.autor_id,
                rol=autor_data.rol,
                orden=autor_data.orden,
            )
            session.add(libro_autor)

        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise translate_integrity_error(exc) from exc

    # Reload with relationships for response
    await session.refresh(libro)
    stmt = (
        select(Libro)
        .where(Libro.id == libro.id)
        .options(
            joinedload(Libro.editorial),
            joinedload(Libro.genero),
            selectinload(Libro.autorias).joinedload(LibroAutor.autor),
        )
    )
    result = await session.execute(stmt)
    libro_full = result.unique().scalar_one()
    return _libro_to_read(libro_full)


async def list_libros(
    session: AsyncSession,
    limit: int,
    offset: int,
    titulo: Optional[str] = None,
    genero_id: Optional[int] = None,
) -> List[LibroListItem]:
    """Lista libros paginados con filtros opcionales (RN-10, RN-11)."""
    stmt = select(Libro).order_by(Libro.id)

    if titulo:
        stmt = stmt.where(Libro.titulo.ilike(f"%{titulo}%"))
    if genero_id is not None:
        stmt = stmt.where(Libro.genero_id == genero_id)

    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    libros = result.scalars().all()
    return [LibroListItem.model_validate(libro) for libro in libros]


async def get_libro(
    session: AsyncSession,
    libro_id: int,
) -> LibroRead:
    """Obtiene detalle de libro con eager loading (fixed query count)."""
    stmt = (
        select(Libro)
        .where(Libro.id == libro_id)
        .options(
            joinedload(Libro.editorial),
            joinedload(Libro.genero),
            selectinload(Libro.autorias).joinedload(LibroAutor.autor),
        )
    )
    result = await session.execute(stmt)
    libro = result.unique().scalar_one_or_none()

    if libro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Libro no encontrado",
        )

    return _libro_to_read(libro)


def _libro_to_read(libro: Libro) -> LibroRead:
    """Convierte un modelo Libro con relaciones cargadas a LibroRead."""
    editorial_read = None
    if libro.editorial:
        editorial_read = EditorialRead(
            id=libro.editorial.id,
            nombre=libro.editorial.nombre,
            pais=libro.editorial.pais,
        )

    genero_read = None
    if libro.genero:
        genero_read = GeneroRead(
            id=libro.genero.id,
            nombre=libro.genero.nombre,
        )

    autorias_read = []
    for la in libro.autorias:
        if la.autor:
            autor_read = AutorRead(
                id=la.autor.id,
                nombre=la.autor.nombre,
                nacionalidad=la.autor.nacionalidad,
            )
            autoria_read = AutoriaRead(
                autor=autor_read,
                rol=la.rol,
                orden=la.orden,
            )
            autorias_read.append(autoria_read)

    return LibroRead(
        id=libro.id,
        isbn=libro.isbn,
        titulo=libro.titulo,
        precio=libro.precio,
        stock=libro.stock,
        editorial_id=libro.editorial_id,
        genero_id=libro.genero_id,
        editorial=editorial_read,
        genero=genero_read,
        autorias=autorias_read,
    )