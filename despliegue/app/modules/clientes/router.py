"""Router HTTP del módulo clientes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.core.database import SessionDep
from app.core.pagination import PaginationParams, get_pagination_params
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
from app.modules.ventas.schemas import VentaRead

router = APIRouter(prefix="/clientes", tags=["clientes"])

ClienteIdPath = Annotated[int, Path(ge=1)]


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ClienteRead)
async def post_cliente(
    payload: ClienteCreate,
    session: SessionDep,
) -> ClienteRead:
    """Crea un nuevo cliente."""
    return await crear_cliente(session, payload)


@router.get("/", response_model=list[ClienteListItem])
async def get_clientes(
    session: SessionDep,
    pagination: PaginationParams = Depends(get_pagination_params),
) -> list[ClienteListItem]:
    """Lista clientes de forma paginada (RN-10)."""
    return await listar_clientes(session, limit=pagination.limit, offset=pagination.offset)


@router.get("/{cliente_id}", response_model=ClienteRead)
async def get_cliente_by_id(
    cliente_id: ClienteIdPath,
    session: SessionDep,
) -> ClienteRead:
    """Obtiene el detalle de un cliente por su identificador, con perfil anidado."""
    return await obtener_cliente(session, cliente_id)


@router.patch("/{cliente_id}", response_model=ClienteRead)
async def patch_cliente(
    cliente_id: ClienteIdPath,
    payload: ClienteUpdate,
    session: SessionDep,
) -> ClienteRead:
    """Actualiza parcialmente un cliente existente."""
    return await actualizar_cliente(session, cliente_id, payload)


@router.post("/{cliente_id}/perfil", status_code=status.HTTP_201_CREATED, response_model=PerfilClienteRead)
async def post_perfil_cliente(
    cliente_id: ClienteIdPath,
    payload: PerfilClienteCreate,
    session: SessionDep,
) -> PerfilClienteRead:
    """Crea el perfil de un cliente (máximo uno por cliente, RN-09)."""
    return await crear_perfil(session, cliente_id, payload)


@router.get("/{cliente_id}/ventas", response_model=list[VentaRead])
async def get_ventas_cliente(
    cliente_id: ClienteIdPath,
    session: SessionDep,
) -> list[VentaRead]:
    """Obtiene el historial de ventas de un cliente."""
    return await obtener_ventas_cliente(session, cliente_id)