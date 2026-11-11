"""Router HTTP del módulo editoriales (rutas públicas y protegidas)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import DomainRoute
from app.core.paginacion import PaginatedResponse, PaginationParams
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
from app.modules.editoriales.unit_of_work import EditorialesUnitOfWork
from app.modules.libros.schemas import LibroListItem


def get_editoriales_uow(
    session: AsyncSession = Depends(get_session),
) -> EditorialesUnitOfWork:
    """Provee una instancia de EditorialesUnitOfWork compartiendo la sesión de la petición."""
    return EditorialesUnitOfWork(session=session)


public_router = APIRouter(prefix="/editoriales", tags=["Editoriales"], route_class=DomainRoute)
protected_router = APIRouter(prefix="/editoriales", tags=["Editoriales"], route_class=DomainRoute)


# --- Rutas Públicas (Lectura Abierta) ---


@public_router.get(
    "",
    response_model=PaginatedResponse[EditorialListItem],
    status_code=status.HTTP_200_OK,
)
@public_router.get(
    "/",
    response_model=PaginatedResponse[EditorialListItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_editoriales_list(
    params: PaginationParams = Depends(),
    uow: EditorialesUnitOfWork = Depends(get_editoriales_uow),
) -> PaginatedResponse[EditorialListItem]:
    """Lista editoriales paginadas con envoltorio uniforme (abierto al público)."""
    return await list_editoriales(uow=uow, params=params)


@public_router.get(
    "/{editorial_id}/libros",
    response_model=PaginatedResponse[LibroListItem],
    status_code=status.HTTP_200_OK,
)
async def get_editoriales_libros(
    editorial_id: int,
    params: PaginationParams = Depends(),
    uow: EditorialesUnitOfWork = Depends(get_editoriales_uow),
) -> PaginatedResponse[LibroListItem]:
    """Lista los libros activos pertenecientes a una editorial (abierto al público)."""
    return await list_libros_by_editorial(uow=uow, editorial_id=editorial_id, params=params)


# --- Rutas Protegidas (Exigen ADMIN) ---


@protected_router.post(
    "",
    response_model=EditorialRead,
    status_code=status.HTTP_201_CREATED,
)
@protected_router.post(
    "/",
    response_model=EditorialRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def post_editorial(
    payload: EditorialCreate,
    uow: EditorialesUnitOfWork = Depends(get_editoriales_uow),
) -> EditorialRead:
    """Crea una nueva editorial (ADMIN)."""
    return await create_editorial(uow=uow, payload=payload)


@protected_router.get(
    "/{editorial_id}",
    response_model=EditorialRead,
    status_code=status.HTTP_200_OK,
)
async def get_editorial_detail(
    editorial_id: int,
    uow: EditorialesUnitOfWork = Depends(get_editoriales_uow),
) -> EditorialRead:
    """Obtiene el detalle de una editorial (ADMIN)."""
    return await get_editorial(uow=uow, editorial_id=editorial_id)


@protected_router.patch(
    "/{editorial_id}",
    response_model=EditorialRead,
    status_code=status.HTTP_200_OK,
)
async def patch_editorial(
    editorial_id: int,
    payload: EditorialUpdate,
    uow: EditorialesUnitOfWork = Depends(get_editoriales_uow),
) -> EditorialRead:
    """Actualiza parcialmente una editorial (ADMIN)."""
    return await update_editorial(uow=uow, editorial_id=editorial_id, payload=payload)


# Router combinado para compatibilidad
router = APIRouter()
router.include_router(public_router)
router.include_router(protected_router)
