"""Router HTTP del módulo generos."""

from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.core.database import SessionDep
from app.modules.generos.schemas import (
    GeneroCreate,
    GeneroLibroRead,
    GeneroRead,
    GeneroUpdate,
)
from app.modules.generos.service import (
    create_genero,
    get_genero,
    list_generos,
    list_libros_by_genero,
    update_genero,
)

router = APIRouter(prefix="/generos", tags=["generos"])

LimitQuery = Annotated[int, Query(ge=1, le=100)]
OffsetQuery = Annotated[int, Query(ge=0)]
GeneroIdPath = Annotated[int, Path(ge=1)]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def post_genero(
    payload: GeneroCreate,
    session: SessionDep,
) -> GeneroRead:
    """Crea un nuevo género literario."""
    return await create_genero(session, payload)


@router.get("/")
async def get_generos(
    session: SessionDep,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
) -> list[GeneroRead]:
    """Lista géneros de forma paginada (RN-10)."""
    return await list_generos(session, limit=limit, offset=offset)


@router.get("/{genero_id}")
async def get_genero_by_id(
    genero_id: GeneroIdPath,
    session: SessionDep,
) -> GeneroRead:
    """Obtiene el detalle de un género por su identificador."""
    return await get_genero(session, genero_id)


@router.patch("/{genero_id}")
async def patch_genero(
    genero_id: GeneroIdPath,
    payload: GeneroUpdate,
    session: SessionDep,
) -> GeneroRead:
    """Actualiza parcialmente un género existente."""
    return await update_genero(session, genero_id, payload)


@router.get("/{genero_id}/libros")
async def get_libros_by_genero(
    genero_id: GeneroIdPath,
    session: SessionDep,
    limit: LimitQuery = 20,
    offset: OffsetQuery = 0,
) -> list[GeneroLibroRead]:
    """Lista los libros asociados a un género de forma paginada (RN-10)."""
    return await list_libros_by_genero(session, genero_id, limit=limit, offset=offset)
