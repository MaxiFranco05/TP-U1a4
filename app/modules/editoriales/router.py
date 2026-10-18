"""Router HTTP del módulo editoriales."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.core.database import SessionDep
from app.core.pagination import PaginationParams, get_pagination_params
from app.modules.editoriales.schemas import (
    EditorialCreate,
    EditorialListItem,
    EditorialRead,
    EditorialUpdate,
)
from app.modules.editoriales.service import (
    create_editorial,
    get_editorial,
    list_editoriales,
    list_libros_by_editorial,
    update_editorial,
)
from app.modules.libros.schemas import LibroListItem

router = APIRouter(prefix="/editoriales", tags=["editoriales"])

EditorialIdPath = Annotated[int, Path(ge=1)]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def post_editorial(
    payload: EditorialCreate,
    session: SessionDep,
) -> EditorialRead:
    """Crea una nueva editorial."""
    return await create_editorial(session, payload)


@router.get("/")
async def get_editoriales(
    session: SessionDep,
    pagination: PaginationParams = Depends(get_pagination_params),
) -> list[EditorialRead]:
    """Lista editoriales de forma paginada (RN-10)."""
    return await list_editoriales(session, limit=pagination.limit, offset=pagination.offset)


@router.get("/{editorial_id}")
async def get_editorial_by_id(
    editorial_id: EditorialIdPath,
    session: SessionDep,
) -> EditorialRead:
    """Obtiene el detalle de una editorial por su identificador."""
    return await get_editorial(session, editorial_id)


@router.patch("/{editorial_id}")
async def patch_editorial(
    editorial_id: EditorialIdPath,
    payload: EditorialUpdate,
    session: SessionDep,
) -> EditorialRead:
    """Actualiza parcialmente una editorial existente."""
    return await update_editorial(session, editorial_id, payload)


@router.get("/{editorial_id}/libros")
async def get_libros_by_editorial(
    editorial_id: EditorialIdPath,
    session: SessionDep,
    pagination: PaginationParams = Depends(get_pagination_params),
) -> list[LibroListItem]:
    """Lista los libros asociados a una editorial de forma paginada (RN-10)."""
    return await list_libros_by_editorial(session, editorial_id, limit=pagination.limit, offset=pagination.offset)