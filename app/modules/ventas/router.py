"""Router HTTP del módulo ventas y mis-ventas."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_usuario_actual, requiere_rol
from app.core.exceptions import DomainRoute
from app.core.paginacion import PaginatedResponse, PaginationParams
from app.modules.usuarios.models import Usuario
from app.modules.ventas.schemas import (
    VentaCreate,
    VentaListItem,
    VentaRead,
)
from app.modules.ventas.service import (
    _notificar_comprobante,
    crear_venta,
    listar_mis_ventas,
    listar_ventas,
    obtener_venta_autorizada,
)
from app.modules.ventas.unit_of_work import VentasUnitOfWork


def get_ventas_uow(
    session: AsyncSession = Depends(get_session),
) -> VentasUnitOfWork:
    """Provee una instancia de VentasUnitOfWork compartiendo la sesión de la petición."""
    return VentasUnitOfWork(session=session)


router = APIRouter(prefix="/ventas", tags=["ventas"], route_class=DomainRoute)
mis_ventas_router = APIRouter(prefix="/mis-ventas", tags=["ventas"], route_class=DomainRoute)

VentaIdPath = Annotated[int, Path(ge=1)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=VentaRead,
)
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=VentaRead,
    include_in_schema=False,
)
async def post_venta(
    payload: VentaCreate,
    background_tasks: BackgroundTasks,
    uow: VentasUnitOfWork = Depends(get_ventas_uow),
    usuario_actual: Usuario = Depends(requiere_rol("VENDEDOR", "ADMIN")),
) -> VentaRead:
    """Crea una nueva venta con descuento atómico de stock (RN-11)."""
    venta = await crear_venta(uow, payload, usuario_actual_id=usuario_actual.id)
    background_tasks.add_task(_notificar_comprobante, venta.id)
    return venta


@router.get(
    "",
    response_model=PaginatedResponse[VentaListItem],
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/",
    response_model=PaginatedResponse[VentaListItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_ventas(
    uow: VentasUnitOfWork = Depends(get_ventas_uow),
    pagination: PaginationParams = Depends(),
    usuario_actual: Usuario = Depends(requiere_rol("VENDEDOR", "ADMIN")),
) -> PaginatedResponse[VentaListItem]:
    """Lista ventas de forma paginada para el personal (RN-10, RN-13)."""
    return await listar_ventas(uow, page=pagination.page, size=pagination.size)


@router.get("/{venta_id}", response_model=VentaRead)
async def get_venta(
    venta_id: VentaIdPath,
    uow: VentasUnitOfWork = Depends(get_ventas_uow),
    usuario_actual: Usuario = Depends(get_usuario_actual),
) -> VentaRead:
    """Obtiene el detalle de una venta con autorización de dueño o personal (RN-14)."""
    return await obtener_venta_autorizada(uow, venta_id, usuario_actual)


@mis_ventas_router.get(
    "",
    response_model=PaginatedResponse[VentaListItem],
    status_code=status.HTTP_200_OK,
)
@mis_ventas_router.get(
    "/",
    response_model=PaginatedResponse[VentaListItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_mis_ventas(
    uow: VentasUnitOfWork = Depends(get_ventas_uow),
    pagination: PaginationParams = Depends(),
    usuario_actual: Usuario = Depends(get_usuario_actual),
) -> PaginatedResponse[VentaListItem]:
    """Lista las ventas del cliente asociado al usuario actual (RN-14)."""
    return await listar_mis_ventas(
        uow,
        usuario_actual_id=usuario_actual.id,
        page=pagination.page,
        size=pagination.size,
    )
