"""Router HTTP del módulo ventas."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Path, status

from app.core.database import SessionDep
from app.core.pagination import PaginationParams, get_pagination_params
from app.modules.ventas.schemas import VentaCreate, VentaListItem, VentaRead
from app.modules.ventas.service import crear_venta, listar_ventas, obtener_venta

router = APIRouter(prefix="/ventas", tags=["ventas"])

VentaIdPath = Annotated[int, Path(ge=1)]


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=VentaRead,
)
async def post_venta(
    payload: VentaCreate,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> VentaRead:
    """Crea una nueva venta con renglones (US-030)."""
    return await crear_venta(session, payload, background_tasks)


@router.get("/{venta_id}", response_model=VentaRead)
async def get_venta(
    venta_id: VentaIdPath,
    session: SessionDep,
) -> VentaRead:
    """Obtiene el detalle de una venta por su identificador (eager loading fijo)."""
    venta = await obtener_venta(session, venta_id)
    if venta is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Venta no encontrada")
    return venta


@router.get("/", response_model=list[VentaListItem])
async def get_ventas(
    session: SessionDep,
    pagination: PaginationParams = Depends(get_pagination_params),
) -> list[VentaListItem]:
    """Lista ventas de forma paginada (RN-10)."""
    return await listar_ventas(session, pagination)