"""Router HTTP del módulo autores (rutas públicas y protegidas)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import DomainRoute
from app.core.paginacion import PaginatedResponse, PaginationParams
from app.modules.autores.schemas import (
    AutorCreate,
    AutorLibroItem,
    AutorRead,
    AutorUpdate,
)
from app.modules.autores.service import (
    create_autor,
    get_autor,
    list_autores,
    list_libros_by_autor,
    update_autor,
)
from app.modules.autores.unit_of_work import AutoresUnitOfWork


def get_autores_uow(
    session: AsyncSession = Depends(get_session),
) -> AutoresUnitOfWork:
    """Provee una instancia de AutoresUnitOfWork compartiendo la sesión de la petición."""
    return AutoresUnitOfWork(session=session)


public_router = APIRouter(prefix="/autores", tags=["Autores"], route_class=DomainRoute)
protected_router = APIRouter(prefix="/autores", tags=["Autores"], route_class=DomainRoute)


# --- Rutas Públicas (Lectura Abierta) ---


@public_router.get(
    "",
    response_model=PaginatedResponse[AutorRead],
    status_code=status.HTTP_200_OK,
)
@public_router.get(
    "/",
    response_model=PaginatedResponse[AutorRead],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_autores_list(
    params: PaginationParams = Depends(),
    uow: AutoresUnitOfWork = Depends(get_autores_uow),
) -> PaginatedResponse[AutorRead]:
    """Lista autores paginados con envoltorio uniforme (abierto al público)."""
    return await list_autores(uow=uow, params=params)


@public_router.get(
    "/{autor_id}/libros",
    response_model=PaginatedResponse[AutorLibroItem],
    status_code=status.HTTP_200_OK,
)
async def get_autores_libros(
    autor_id: int,
    params: PaginationParams = Depends(),
    uow: AutoresUnitOfWork = Depends(get_autores_uow),
) -> PaginatedResponse[AutorLibroItem]:
    """Lista los libros activos pertenecientes a un autor con rol y orden (abierto al público)."""
    return await list_libros_by_autor(uow=uow, autor_id=autor_id, params=params)


# --- Rutas Protegidas (Exigen ADMIN) ---


@protected_router.post(
    "",
    response_model=AutorRead,
    status_code=status.HTTP_201_CREATED,
)
@protected_router.post(
    "/",
    response_model=AutorRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def post_autor(
    payload: AutorCreate,
    uow: AutoresUnitOfWork = Depends(get_autores_uow),
) -> AutorRead:
    """Crea un nuevo autor (ADMIN)."""
    return await create_autor(uow=uow, payload=payload)


@protected_router.get(
    "/{autor_id}",
    response_model=AutorRead,
    status_code=status.HTTP_200_OK,
)
async def get_autor_detail(
    autor_id: int,
    uow: AutoresUnitOfWork = Depends(get_autores_uow),
) -> AutorRead:
    """Obtiene el detalle de un autor (ADMIN)."""
    return await get_autor(uow=uow, autor_id=autor_id)


@protected_router.patch(
    "/{autor_id}",
    response_model=AutorRead,
    status_code=status.HTTP_200_OK,
)
async def patch_autor(
    autor_id: int,
    payload: AutorUpdate,
    uow: AutoresUnitOfWork = Depends(get_autores_uow),
) -> AutorRead:
    """Actualiza parcialmente un autor (ADMIN)."""
    return await update_autor(uow=uow, autor_id=autor_id, payload=payload)


# Router combinado para compatibilidad
router = APIRouter()
router.include_router(public_router)
router.include_router(protected_router)
