"""Router HTTP del módulo generos (rutas públicas y protegidas)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import DomainRoute
from app.core.paginacion import PaginatedResponse, PaginationParams
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
from app.modules.generos.unit_of_work import GenerosUnitOfWork


def get_generos_uow(
    session: AsyncSession = Depends(get_session),
) -> GenerosUnitOfWork:
    """Provee una instancia de GenerosUnitOfWork compartiendo la sesión de la petición."""
    return GenerosUnitOfWork(session=session)


public_router = APIRouter(prefix="/generos", tags=["Géneros"], route_class=DomainRoute)
protected_router = APIRouter(prefix="/generos", tags=["Géneros"], route_class=DomainRoute)


# --- Rutas Públicas (Lectura Abierta) ---


@public_router.get(
    "",
    response_model=PaginatedResponse[GeneroRead],
    status_code=status.HTTP_200_OK,
)
@public_router.get(
    "/",
    response_model=PaginatedResponse[GeneroRead],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_generos_list(
    params: PaginationParams = Depends(),
    uow: GenerosUnitOfWork = Depends(get_generos_uow),
) -> PaginatedResponse[GeneroRead]:
    """Lista géneros paginados con envoltorio uniforme (abierto al público)."""
    return await list_generos(uow=uow, params=params)


@public_router.get(
    "/{genero_id}/libros",
    response_model=PaginatedResponse[GeneroLibroRead],
    status_code=status.HTTP_200_OK,
)
async def get_generos_libros(
    genero_id: int,
    params: PaginationParams = Depends(),
    uow: GenerosUnitOfWork = Depends(get_generos_uow),
) -> PaginatedResponse[GeneroLibroRead]:
    """Lista los libros activos pertenecientes a un género (abierto al público)."""
    return await list_libros_by_genero(uow=uow, genero_id=genero_id, params=params)


# --- Rutas Protegidas (Exigen ADMIN) ---


@protected_router.post(
    "",
    response_model=GeneroRead,
    status_code=status.HTTP_201_CREATED,
)
@protected_router.post(
    "/",
    response_model=GeneroRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def post_genero(
    payload: GeneroCreate,
    uow: GenerosUnitOfWork = Depends(get_generos_uow),
) -> GeneroRead:
    """Crea un nuevo género (ADMIN)."""
    return await create_genero(uow=uow, payload=payload)


@protected_router.get(
    "/{genero_id}",
    response_model=GeneroRead,
    status_code=status.HTTP_200_OK,
)
async def get_genero_detail(
    genero_id: int,
    uow: GenerosUnitOfWork = Depends(get_generos_uow),
) -> GeneroRead:
    """Obtiene el detalle de un género (ADMIN)."""
    return await get_genero(uow=uow, genero_id=genero_id)


@protected_router.patch(
    "/{genero_id}",
    response_model=GeneroRead,
    status_code=status.HTTP_200_OK,
)
async def patch_genero(
    genero_id: int,
    payload: GeneroUpdate,
    uow: GenerosUnitOfWork = Depends(get_generos_uow),
) -> GeneroRead:
    """Actualiza parcialmente un género (ADMIN)."""
    return await update_genero(uow=uow, genero_id=genero_id, payload=payload)


# Router combinado para compatibilidad
router = APIRouter()
router.include_router(public_router)
router.include_router(protected_router)
