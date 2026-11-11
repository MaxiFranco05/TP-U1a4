"""Lógica de negocio del módulo ventas sobre UnitOfWork."""

import asyncio
from decimal import Decimal
import logging

from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.exceptions import (
    ConflictError,
    EntityNotFoundError,
    InsufficientStockError,
    PermissionDeniedError,
    translate_integrity_error,
)
from app.core.paginacion import PaginatedResponse, calcular_paginas, validar_pagina
from app.modules.libros.models import Libro
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.repository import AsignacionRolRepository
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import (
    RenglonVentaCreate,
    VentaCreate,
    VentaListItem,
    VentaRead,
)
from app.modules.ventas.unit_of_work import VentasUnitOfWork

logger = logging.getLogger(__name__)


async def _notificar_comprobante(venta_id: int) -> None:
    """Notificación de comprobante en segundo plano (simulada) tras confirmar la transacción (RN-08)."""
    await asyncio.sleep(0.5)
    logger.info("Comprobante generado para venta %d", venta_id)


async def crear_venta(
    uow: VentasUnitOfWork,
    data: VentaCreate,
    usuario_actual_id: int,
) -> VentaRead:
    """Crea una venta con sus renglones en una transacción atómica con descuento de stock (RN-11).

    1. Carga libros activos con FOR UPDATE en orden de libro_id para evitar deadlocks (RN-11).
    2. Si algún libro no existe o está dado de baja lógica, responde 409 sin escrituras.
    3. Verifica stock suficiente para cada renglón antes de escribir; si no alcanza responde 409.
    4. Copia precio_unitario del catálogo y calcula total en Decimal (RN-06, RN-07).
    5. Persiste Venta y RenglonVenta con flush (delega existencia de cliente a la FK).
    6. Descuenta stock por renglón invocando el punto único de stock con movimiento negativo.
    7. Si cualquier paso falla, el UoW revierte todo automáticamente.
    """
    async with uow:
        # 1. Bloquear libros en orden ascendente de ID
        libro_ids = sorted({r.libro_id for r in data.renglones})
        libros_dict: dict[int, Libro] = {}
        for lid in libro_ids:
            libro = await uow.libros.get_by_id_for_update(lid)
            if libro is None:
                deleted = await uow.libros.get_by_id_including_deleted(lid)
                if deleted is not None and deleted.borrado_en is not None:
                    raise ConflictError("El libro referenciado fue dado de baja")
                raise ConflictError("El libro referenciado no existe")
            libros_dict[lid] = libro

        # 2. Validar stock suficiente
        for r in data.renglones:
            libro = libros_dict[r.libro_id]
            if libro.stock < r.cantidad:
                raise InsufficientStockError(
                    f"Stock insuficiente para el libro '{libro.titulo}' "
                    f"(disponible: {libro.stock}, solicitado: {r.cantidad})"
                )

        # 3. Construir renglones copiando precio_unitario y calcular total Decimal
        total = Decimal("0.00")
        renglones_models: list[RenglonVenta] = []
        for r in data.renglones:
            libro = libros_dict[r.libro_id]
            precio_unitario = libro.precio
            subtotal = Decimal(str(r.cantidad)) * precio_unitario
            total += subtotal
            renglones_models.append(
                RenglonVenta(
                    libro_id=libro.id,
                    cantidad=r.cantidad,
                    precio_unitario=precio_unitario,
                )
            )

        # 4. Crear venta con renglones
        venta = Venta(
            cliente_id=data.cliente_id,
            total=total,
            renglones=renglones_models,
        )
        try:
            await uow.ventas.add(venta)
        except (IntegrityError, DBAPIError) as exc:
            raise translate_integrity_error(exc) from exc

        # 5. Descontar stock por renglón mediante el punto único
        for r in data.renglones:
            libro = libros_dict[r.libro_id]
            try:
                await uow.registrar_movimiento_stock(
                    libro=libro,
                    cantidad=-r.cantidad,
                    motivo=f"Venta #{venta.id}",
                    usuario_id=usuario_actual_id,
                    venta_id=venta.id,
                )
            except ValueError as exc:
                raise ConflictError(str(exc)) from exc

        # Precargar detalle completo para la respuesta antes de confirmar
        venta_completa = await uow.ventas.get_detalle(venta.id)
        if venta_completa is None:
            raise EntityNotFoundError("Venta no encontrada")
        return VentaRead.model_validate(venta_completa)


async def obtener_venta_autorizada(
    uow: VentasUnitOfWork,
    venta_id: int,
    usuario_actual: Usuario,
) -> VentaRead:
    """Obtiene el detalle de una venta con autorización de dueño o personal (RN-14).

    1. Busca la venta con precarga de cliente, renglones y libros. Si no existe -> 404.
    2. Comprueba si el usuario tiene rol vigente ADMIN o VENDEDOR en la base de datos (RN-04).
    3. Si no es personal, comprueba que venta.cliente.usuario_id == usuario_actual.id.
    4. Si no coincide, responde 403 Forbidden.
    """
    async with uow:
        venta = await uow.ventas.get_detalle(venta_id)
        if venta is None:
            raise EntityNotFoundError("Venta no encontrada")

        # Consultar roles vigentes en la base de datos
        asignaciones_repo = AsignacionRolRepository(session=uow.session)
        roles_vigentes = await asignaciones_repo.get_roles_vigentes_usuario(usuario_actual.id)
        es_personal = bool(set(roles_vigentes).intersection({"ADMIN", "VENDEDOR"}))

        es_duenio = bool(
            venta.cliente
            and venta.cliente.usuario_id is not None
            and venta.cliente.usuario_id == usuario_actual.id
        )

        if not es_personal and not es_duenio:
            raise PermissionDeniedError("No posee los permisos para consultar esta venta.")

        return VentaRead.model_validate(venta)


async def listar_ventas(
    uow: VentasUnitOfWork,
    page: int = 1,
    size: int = 20,
) -> PaginatedResponse[VentaListItem]:
    """Lista ventas paginadas con envoltorio uniforme para el personal (RN-10, RN-13)."""
    async with uow:
        total = await uow.ventas.count()
        pages = calcular_paginas(total, size)
        validar_pagina(page, pages)
        ventas = await uow.ventas.listar(offset=(page - 1) * size, limit=size)
        items = [VentaListItem.model_validate(v) for v in ventas]
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )


async def listar_mis_ventas(
    uow: VentasUnitOfWork,
    usuario_actual_id: int,
    page: int = 1,
    size: int = 20,
) -> PaginatedResponse[VentaListItem]:
    """Lista las ventas del cliente asociado al usuario actual (RN-14)."""
    async with uow:
        total = await uow.ventas.count_por_usuario(usuario_actual_id)
        pages = calcular_paginas(total, size)
        validar_pagina(page, pages)
        ventas = await uow.ventas.listar_por_usuario(
            usuario_id=usuario_actual_id,
            offset=(page - 1) * size,
            limit=size,
        )
        items = [VentaListItem.model_validate(v) for v in ventas]
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
