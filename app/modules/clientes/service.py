"""Lógica de negocio del módulo clientes."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.exceptions import translate_integrity_error
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteListItem,
    ClienteRead,
    ClienteUpdate,
    PerfilClienteCreate,
    PerfilClienteRead,
)
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import VentaRead


async def _get_cliente_with_perfil(session: AsyncSession, cliente_id: int) -> Cliente:
    """Obtiene un cliente con su perfil cargado (joinedload)."""
    stmt = (
        select(Cliente)
        .where(Cliente.id == cliente_id)
        .options(joinedload(Cliente.perfil))
    )
    result = await session.execute(stmt)
    return result.unique().scalar_one()


async def crear_cliente(session: AsyncSession, payload: ClienteCreate) -> ClienteRead:
    """Crea un nuevo cliente delegando la unicidad del email en la base de datos (DD-04, RN-12)."""
    cliente = Cliente(nombre=payload.nombre, email=payload.email)
    session.add(cliente)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise translate_integrity_error(exc) from exc
    # Recargar con perfil para que ClienteRead pueda validar la relación
    cliente = await _get_cliente_with_perfil(session, cliente.id)
    return ClienteRead.model_validate(cliente)


async def listar_clientes(
    session: AsyncSession,
    limit: int,
    offset: int,
) -> list[ClienteListItem]:
    """Lista clientes paginados ordenados por ID (RN-10). Sin perfil para evitar N+1."""
    stmt = select(Cliente).order_by(Cliente.id).limit(limit).offset(offset)
    result = await session.execute(stmt)
    clientes = result.scalars().all()
    return [ClienteListItem.model_validate(c) for c in clientes]


async def obtener_cliente_o_404(session: AsyncSession, cliente_id: int) -> Cliente:
    """Obtiene un cliente por su clave primaria o lanza HTTP 404."""
    stmt = (
        select(Cliente)
        .where(Cliente.id == cliente_id)
        .options(joinedload(Cliente.perfil))
    )
    result = await session.execute(stmt)
    cliente = result.unique().scalar_one_or_none()
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    return cliente


async def obtener_cliente(session: AsyncSession, cliente_id: int) -> ClienteRead:
    """Devuelve el DTO de lectura de un cliente existente con su perfil (joinedload)."""
    cliente = await obtener_cliente_o_404(session, cliente_id)
    return ClienteRead.model_validate(cliente)


async def actualizar_cliente(
    session: AsyncSession,
    cliente_id: int,
    payload: ClienteUpdate,
) -> ClienteRead:
    """Actualiza parcialmente un cliente usando exclude_unset=True y traduce colisiones a 409 (RN-12)."""
    cliente = await obtener_cliente_o_404(session, cliente_id)
    updates = payload.model_dump(exclude_unset=True)
    for field_name, field_value in updates.items():
        if field_value is not None:
            setattr(cliente, field_name, field_value)

    session.add(cliente)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise translate_integrity_error(exc) from exc
    # Recargar con perfil para que ClienteRead pueda validar la relación
    cliente = await _get_cliente_with_perfil(session, cliente.id)
    return ClienteRead.model_validate(cliente)


async def crear_perfil(
    session: AsyncSession,
    cliente_id: int,
    payload: PerfilClienteCreate,
) -> PerfilClienteRead:
    """Crea el perfil de un cliente (RN-09: único por cliente). Traduce 409 (perfil único) y 404 (cliente no existe)."""
    # Verificar que el cliente existe
    await obtener_cliente_o_404(session, cliente_id)

    perfil = PerfilCliente(
        cliente_id=cliente_id,
        telefono=payload.telefono,
        direccion=payload.direccion,
    )
    session.add(perfil)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise translate_integrity_error(exc) from exc
    await session.refresh(perfil)
    return PerfilClienteRead.model_validate(perfil)


async def obtener_ventas_cliente(
    session: AsyncSession,
    cliente_id: int,
) -> list[VentaRead]:
    """Obtiene el historial de ventas de un cliente existente (selectinload para renglones y libros)."""
    await obtener_cliente_o_404(session, cliente_id)

    stmt = (
        select(Venta)
        .where(Venta.cliente_id == cliente_id)
        .options(
            joinedload(Venta.cliente),
            selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
        )
        .order_by(Venta.fecha.desc())
    )
    result = await session.execute(stmt)
    ventas = result.unique().scalars().all()
    return [VentaRead.model_validate(v) for v in ventas]