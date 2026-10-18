"""Router HTTP del módulo libros."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Path, Query, status

from app.core.database import SessionDep
from app.core.pagination import PaginationParams, get_pagination_params
from app.modules.libros.schemas import (
    LibroCreate,
    LibroListItem,
    LibroRead,
)
from app.modules.libros.service import (
    create_libro_with_autores,
    get_libro,
    list_libros,
)

router = APIRouter(prefix="/libros", tags=["libros"])

LibroIdPath = Annotated[int, Path(ge=1)]
TituloQuery = Annotated[Optional[str], Query()]
GeneroIdQuery = Annotated[Optional[int], Query(ge=1)]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def post_libro(
    payload: LibroCreate,
    session: SessionDep,
) -> LibroRead:
    """Crea un nuevo libro con sus autores en una sola operación."""
    return await create_libro_with_autores(session, payload)


@router.get("/")
async def get_libros(
    session: SessionDep,
    titulo: TituloQuery = None,
    genero_id: GeneroIdQuery = None,
    pagination: PaginationParams = Depends(get_pagination_params),
) -> list[LibroListItem]:
    """Lista libros de forma paginada con filtros opcionales (RN-10, RN-11)."""
    return await list_libros(
        session,
        limit=pagination.limit,
        offset=pagination.offset,
        titulo=titulo,
        genero_id=genero_id,
    )


@router.get("/{libro_id}")
async def get_libro_by_id(
    libro_id: LibroIdPath,
    session: SessionDep,
) -> LibroRead:
    """Obtiene el detalle completo de un libro con relaciones eager-loaded."""
    return await get_libro(session, libro_id)