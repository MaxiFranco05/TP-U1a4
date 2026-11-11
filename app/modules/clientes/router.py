"""Router HTTP del módulo clientes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import DomainRoute
from app.core.paginacion import PaginatedResponse, PaginationParams
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteListItem,
    ClienteRead,
    ClienteUpdate,
    PerfilClienteCreate,
    PerfilClienteRead,
)
from app.modules.clientes.service import (
    actualizar_cliente,
    crear_cliente,
    crear_perfil,
    listar_clientes,
    obtener_cliente,
    obtener_ventas_cliente,
)
from app.modules.clientes.unit_of_work import ClientesUnitOfWork
from app.modules.ventas.schemas import VentaRead


def get_clientes_uow(
    session: AsyncSession = Depends(get_session),
) -> ClientesUnitOfWork:
    """Provee una instancia de ClientesUnitOfWork compartiendo la sesión de la petición."""
    return ClientesUnitOfWork(session=session)


router = APIRouter(prefix="/clientes", tags=["clientes"], route_class=DomainRoute)

ClienteIdPath = Annotated[int, Path(ge=1)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ClienteRead,
)
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ClienteRead,
    include_in_schema=False,
)
async def post_cliente(
    payload: ClienteCreate,
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> ClienteRead:
    """Crea un nuevo cliente (RN-12)."""
    return await crear_cliente(uow, payload)


@router.get(
    "",
    response_model=PaginatedResponse[ClienteListItem],
    status_code=status.HTTP_200_OK,
)
@router.get(
    "/",
    response_model=PaginatedResponse[ClienteListItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_clientes(
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[ClienteListItem]:
    """Lista clientes de forma paginada (RN-10, RN-13)."""
    return await listar_clientes(uow, page=pagination.page, size=pagination.size)


@router.get("/{cliente_id}", response_model=ClienteRead)
async def get_cliente_by_id(
    cliente_id: ClienteIdPath,
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> ClienteRead:
    """Obtiene el detalle de un cliente por su identificador, con perfil anidado."""
    return await obtener_cliente(uow, cliente_id)


@router.patch("/{cliente_id}", response_model=ClienteRead)
async def patch_cliente(
    cliente_id: ClienteIdPath,
    payload: ClienteUpdate,
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> ClienteRead:
    """Actualiza parcialmente un cliente existente."""
    return await actualizar_cliente(uow, cliente_id, payload)


@router.post(
    "/{cliente_id}/perfil",
    status_code=status.HTTP_201_CREATED,
    response_model=PerfilClienteRead,
)
async def post_perfil_cliente(
    cliente_id: ClienteIdPath,
    payload: PerfilClienteCreate,
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
) -> PerfilClienteRead:
    """Crea el perfil de un cliente (máximo uno por cliente, RN-09)."""
    return await crear_perfil(uow, cliente_id, payload)


@router.get(
    "/{cliente_id}/ventas",
    response_model=PaginatedResponse[VentaRead],
    status_code=status.HTTP_200_OK,
)
async def get_ventas_cliente(
    cliente_id: ClienteIdPath,
    uow: ClientesUnitOfWork = Depends(get_clientes_uow),
    pagination: PaginationParams = Depends(),
) -> PaginatedResponse[VentaRead]:
    """Obtiene el historial de ventas paginado de un cliente."""
    return await obtener_ventas_cliente(
        uow,
        cliente_id,
        page=pagination.page,
        size=pagination.size,
    )
