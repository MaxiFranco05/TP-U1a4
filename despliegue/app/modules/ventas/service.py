"""Lógica de negocio del módulo ventas."""

import asyncio
import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.exceptions import translate_integrity_error
from app.core.pagination import PaginationParams
from app.modules.libros.models import Libro
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import RenglonVentaCreate, VentaCreate, VentaListItem, VentaRead

if TYPE_CHECKING:
    from app.modules.clientes.models import Cliente

logger = logging.getLogger(__name__)


async def _notificar_comprobante(venta_id: int) -> None:
    """Notificación de comprobante en segundo plano (simulada)."""
    await asyncio.sleep(0.5)
    logger.info("Comprobante generado para venta %d", venta_id)


async def crear_venta(
    session: AsyncSession,
    data: VentaCreate,
    background_tasks: BackgroundTasks,
) -> VentaRead:
    """
    Crea una venta con sus renglones en una transacción atómica.

    - Copia el precio del libro al momento de la venta (RN-06)
    - Calcula el total server-side (RN-07)
    - Programa notificación en background (RN-08)
    - Traduce errores de FK a 409 controlado (RN-12, DD-04)
    """
    # 1. Extraer IDs de libros únicos
    libro_ids = {r.libro_id for r in data.renglones}

    # 2. Cargar todos los libros en una sola query (evita N+1)
    stmt_libros = select(Libro).where(Libro.id.in_(libro_ids))
    result_libros = await session.execute(stmt_libros)
    libros = result_libros.scalars().all()

    # 3. Validar que todos los libros existen (lectura para obtener precios)
    libros_dict = {libro.id: libro for libro in libros}
    missing_libros = [lid for lid in libro_ids if lid not in libros_dict]
    if missing_libros:
        # Lanzar error controlado para libro no encontrado (RN-12)
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El libro referenciado no existe"
        )

    # 4. Construir renglones con precio_unitario copiado del libro
    renglones_models = []
    total = Decimal("0")
    for renglon_data in data.renglones:
        libro = libros_dict[renglon_data.libro_id]
        precio_unitario = libro.precio
        subtotal = Decimal(str(renglon_data.cantidad)) * precio_unitario
        total += subtotal

        renglon = RenglonVenta(
            libro_id=renglon_data.libro_id,
            cantidad=renglon_data.cantidad,
            precio_unitario=precio_unitario,
        )
        renglones_models.append(renglon)

    # 5. Crear venta con renglones
    venta = Venta(
        cliente_id=data.cliente_id,
        total=total,
        renglones=renglones_models,
    )
    session.add(venta)

    # 6. Flush para obtener IDs antes del commit (puede lanzar errores de FK)
    try:
        await session.flush()
    except (IntegrityError, DBAPIError) as exc:
        await session.rollback()
        raise translate_integrity_error(exc) from exc

    # 7. Programar notificación en background (después del flush, antes del commit)
    background_tasks.add_task(_notificar_comprobante, venta.id)

    # 8. Commit y manejar errores de integridad
    try:
        await session.commit()
    except (IntegrityError, DBAPIError) as exc:
        await session.rollback()
        raise translate_integrity_error(exc) from exc

    # 9. Recargar con eager loading para el response
    stmt = (
        select(Venta)
        .where(Venta.id == venta.id)
        .options(
            joinedload(Venta.cliente),
            selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
        )
    )
    result = await session.execute(stmt)
    venta_completa = result.unique().scalar_one()

    return VentaRead.model_validate(venta_completa)


async def obtener_venta(session: AsyncSession, venta_id: int) -> VentaRead | None:
    """
    Obtiene una venta por ID con eager loading fijo (1 query).

    Usa joinedload para cliente (to-one) y selectinload para renglones+libro (colección).
    """
    stmt = (
        select(Venta)
        .where(Venta.id == venta_id)
        .options(
            joinedload(Venta.cliente),
            selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
        )
    )
    result = await session.execute(stmt)
    venta = result.unique().scalar_one_or_none()

    if venta is None:
        return None

    return VentaRead.model_validate(venta)


async def listar_ventas(
    session: AsyncSession,
    pagination: PaginationParams,
) -> list[VentaListItem]:
    """
    Lista ventas paginadas con cliente cargado (joinedload).

    No carga renglones para evitar N+1 en listado (US-031).
    """
    stmt = (
        select(Venta)
        .options(joinedload(Venta.cliente))
        .order_by(Venta.fecha.desc())
        .limit(pagination.limit)
        .offset(pagination.offset)
    )
    result = await session.execute(stmt)
    ventas = result.unique().scalars().all()

    return [VentaListItem.model_validate(v) for v in ventas]