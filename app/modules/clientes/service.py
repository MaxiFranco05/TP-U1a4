"""Lógica de negocio del módulo clientes sobre UnitOfWork."""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from app.core.exceptions import translate_integrity_error
from app.core.paginacion import PaginatedResponse, calcular_paginas, validar_pagina
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteListItem,
    ClienteRead,
    ClienteUpdate,
    PerfilClienteCreate,
    PerfilClienteRead,
)
from app.modules.clientes.unit_of_work import ClientesUnitOfWork
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import VentaRead


async def crear_cliente(
    uow: ClientesUnitOfWork,
    payload: ClienteCreate,
) -> ClienteRead:
    """Crea un nuevo cliente delegando la unicidad del email en la base de datos (RN-12, DD-04)."""
    async with uow:
        cliente = Cliente(nombre=payload.nombre, email=payload.email)
        try:
            await uow.clientes.add(cliente)
        except (IntegrityError, DBAPIError) as exc:
            raise translate_integrity_error(exc) from exc

        cliente_cargado = await uow.clientes.get_con_perfil(cliente.id)
        return ClienteRead.model_validate(cliente_cargado)


async def listar_clientes(
    uow: ClientesUnitOfWork,
    page: int = 1,
    size: int = 20,
) -> PaginatedResponse[ClienteListItem]:
    """Lista clientes de forma paginada (RN-10, RN-13) con envoltorio uniforme."""
    async with uow:
        total = await uow.clientes.count()
        pages = calcular_paginas(total, size)
        validar_pagina(page, pages)
        clientes = await uow.clientes.get_all(offset=(page - 1) * size, limit=size)
        items = [ClienteListItem.model_validate(c) for c in clientes]
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )


async def obtener_cliente_o_404(
    uow: ClientesUnitOfWork,
    cliente_id: int,
) -> Cliente:
    """Obtiene un cliente con su perfil precargado o lanza HTTP 404."""
    cliente = await uow.clientes.get_con_perfil(cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado",
        )
    return cliente


async def obtener_cliente(
    uow: ClientesUnitOfWork,
    cliente_id: int,
) -> ClienteRead:
    """Devuelve el DTO de lectura de un cliente existente con su perfil."""
    async with uow:
        cliente = await obtener_cliente_o_404(uow, cliente_id)
        return ClienteRead.model_validate(cliente)


async def actualizar_cliente(
    uow: ClientesUnitOfWork,
    cliente_id: int,
    payload: ClienteUpdate,
) -> ClienteRead:
    """Actualiza parcialmente un cliente existente y traduce colisiones a 409 (RN-12)."""
    async with uow:
        cliente = await obtener_cliente_o_404(uow, cliente_id)
        updates = payload.model_dump(exclude_unset=True)
        if updates:
            try:
                await uow.clientes.update(cliente, updates)
            except (IntegrityError, DBAPIError) as exc:
                raise translate_integrity_error(exc) from exc

        cliente_cargado = await uow.clientes.get_con_perfil(cliente.id)
        return ClienteRead.model_validate(cliente_cargado)


async def crear_perfil(
    uow: ClientesUnitOfWork,
    cliente_id: int,
    payload: PerfilClienteCreate,
) -> PerfilClienteRead:
    """Crea el perfil de un cliente (RN-09: único por cliente). Traduce 409 y 404."""
    async with uow:
        cliente = await uow.clientes.get_by_id(cliente_id)
        if cliente is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado",
            )

        perfil = PerfilCliente(
            cliente_id=cliente_id,
            telefono=payload.telefono,
            direccion=payload.direccion,
        )
        try:
            await uow.perfiles.add(perfil)
        except (IntegrityError, DBAPIError) as exc:
            raise translate_integrity_error(exc) from exc

        return PerfilClienteRead.model_validate(perfil)


async def obtener_ventas_cliente(
    uow: ClientesUnitOfWork,
    cliente_id: int,
    page: int = 1,
    size: int = 20,
) -> PaginatedResponse[VentaRead]:
    """Obtiene el historial paginado de ventas de un cliente existente con precarga."""
    async with uow:
        cliente = await uow.clientes.get_by_id(cliente_id)
        if cliente is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente no encontrado",
            )

        count_stmt = (
            select(func.count())
            .select_from(Venta)
            .where(Venta.cliente_id == cliente_id)
        )
        total = int((await uow.session.execute(count_stmt)).scalar_one())
        pages = calcular_paginas(total, size)
        validar_pagina(page, pages)

        stmt = (
            select(Venta)
            .where(Venta.cliente_id == cliente_id)
            .options(
                joinedload(Venta.cliente),
                selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
            )
            .order_by(Venta.fecha.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await uow.session.execute(stmt)
        ventas = result.unique().scalars().all()
        items = [VentaRead.model_validate(v) for v in ventas]
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
