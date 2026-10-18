"""Router HTTP del módulo autores."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.core.database import SessionDep
from app.core.pagination import PaginationParams, get_pagination_params
from app.modules.autores.schemas import (
    AutorCreate,
    AutorLibroItem,
    AutorRead,
    AutorUpdate,
)
from app.modules.autores.service import (
    create_autor,
    get_autor,
    list_libros_by_autor,
    update_autor,
)

router = APIRouter(prefix="/autores", tags=["autores"])

AutorIdPath = Annotated[int, Path(ge=1)]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def post_autor(
    payload: AutorCreate,
    session: SessionDep,
) -> AutorRead:
    """Crea un nuevo autor."""
    return await create_autor(session, payload)


@router.get("/{autor_id}")
async def get_autor_by_id(
    autor_id: AutorIdPath,
    session: SessionDep,
) -> AutorRead:
    """Obtiene el detalle de un autor por su identificador."""
    return await get_autor(session, autor_id)


@router.patch("/{autor_id}")
async def patch_autor(
    autor_id: AutorIdPath,
    payload: AutorUpdate,
    session: SessionDep,
) -> AutorRead:
    """Actualiza parcialmente un autor existente."""
    return await update_autor(session, autor_id, payload)


@router.get("/{autor_id}/libros")
async def get_libros_by_autor(
    autor_id: AutorIdPath,
    session: SessionDep,
    pagination: PaginationParams = Depends(get_pagination_params),
) -> list[AutorLibroItem]:
    """Lista los libros asociados a un autor con rol y orden de forma paginada (RN-10)."""
    return await list_libros_by_autor(session, autor_id, limit=pagination.limit, offset=pagination.offset)