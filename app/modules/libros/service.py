"""Lógica de negocio del módulo libros sobre UnitOfWork, Repository y punto único de stock."""

from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    BusinessRuleViolationError,
    ConflictError,
    DomainError,
    EntityNotFoundError,
    translate_integrity_error,
)
from app.core.paginacion import PaginatedResponse, PaginationParams, paginate
from app.modules.libros.models import Libro, LibroAutor
from app.modules.libros.schemas import (
    LibroCreate,
    LibroListItem,
    LibroRead,
    LibroUpdate,
    MovimientoStockRead,
)
from app.modules.libros.unit_of_work import LibrosUnitOfWork


async def create_libro(
    uow: LibrosUnitOfWork,
    payload: LibroCreate,
    usuario_id: int,
) -> LibroRead:
    """Crea un libro con stock=0 y registra stock inicial por el punto único de stock (RN-11, RN-12)."""
    libro = Libro(
        isbn=payload.isbn,
        titulo=payload.titulo,
        precio=payload.precio,
        stock=0,
        editorial_id=payload.editorial_id,
        genero_id=payload.genero_id,
    )

    async with uow:
        try:
            await uow.libros.add(libro)

            for autor_data in payload.autores:
                la = LibroAutor(
                    libro_id=libro.id,
                    autor_id=autor_data.autor_id,
                    rol=autor_data.rol,
                    orden=autor_data.orden,
                )
                uow.session.add(la)

            await uow.session.flush()

            if payload.stock_inicial > 0:
                await uow.registrar_movimiento_stock(
                    libro=libro,
                    cantidad=payload.stock_inicial,
                    motivo="Stock inicial",
                    usuario_id=usuario_id,
                )
        except IntegrityError as exc:
            raise translate_integrity_error(exc) from exc

        detalle = await uow.libros.get_detalle(libro.id)
        if detalle is None:
            raise DomainError(
                detail="Error al recuperar el libro creado",
                status_code=500,
            )
        return LibroRead.model_validate(detalle)


# Alias para retrocompatibilidad con tests existentes si fuera necesario
create_libro_with_autores = create_libro


async def list_libros(
    uow: LibrosUnitOfWork,
    params: PaginationParams,
    titulo: str | None = None,
) -> PaginatedResponse[LibroListItem]:
    """Lista libros activos paginados con envoltorio uniforme y filtrado parametrizado seguro."""
    async with uow:
        filters = []
        if titulo is not None:
            filters.append(Libro.titulo.ilike(f"%{titulo}%"))

        total = await uow.libros.count(filters=filters)
        items = await uow.libros.get_all(
            offset=params.offset,
            limit=params.limit,
            filters=filters,
        )
        dtos = [LibroListItem.model_validate(l) for l in items]
        return paginate(items=dtos, total=total, page=params.page, size=params.size)


async def get_libro(
    uow: LibrosUnitOfWork,
    libro_id: int,
) -> LibroRead:
    """Obtiene el detalle completo de un libro activo o lanza EntityNotFoundError."""
    async with uow:
        libro = await uow.libros.get_detalle(libro_id)
        if libro is None:
            raise EntityNotFoundError("Libro no encontrado")
        return LibroRead.model_validate(libro)


async def update_libro(
    uow: LibrosUnitOfWork,
    libro_id: int,
    payload: LibroUpdate,
) -> LibroRead:
    """Actualiza parcialmente un libro activo (solo título y precio) traduciendo errores a ConflictError (RN-12)."""
    async with uow:
        libro = await uow.libros.get_by_id(libro_id)
        if libro is None:
            raise EntityNotFoundError("Libro no encontrado")
        updates = payload.model_dump(exclude_unset=True)
        try:
            await uow.libros.update(libro, updates)
        except IntegrityError as exc:
            raise translate_integrity_error(exc) from exc

        detalle = await uow.libros.get_detalle(libro_id)
        return LibroRead.model_validate(detalle)


async def delete_libro(
    uow: LibrosUnitOfWork,
    libro_id: int,
) -> None:
    """Realiza la baja lógica de un libro marcando borrado_en (RN-13) o lanza EntityNotFoundError."""
    async with uow:
        libro = await uow.libros.get_by_id(libro_id)
        if libro is None:
            raise EntityNotFoundError("Libro no encontrado")
        await uow.libros.soft_delete(libro)


async def reponer_stock(
    uow: LibrosUnitOfWork,
    libro_id: int,
    cantidad: int,
    usuario_id: int,
) -> LibroRead:
    """Repone stock a un libro activo mediante el punto único de stock (RN-11)."""
    if cantidad <= 0:
        raise BusinessRuleViolationError("La cantidad a reponer debe ser mayor a 0")

    async with uow:
        libro = await uow.libros.get_by_id(libro_id)
        if libro is None:
            hist = await uow.libros.get_by_id_including_deleted(libro_id)
            if hist is not None and hist.borrado_en is not None:
                raise ConflictError("No se puede reponer stock de un libro dado de baja")
            raise EntityNotFoundError("Libro no encontrado")

        try:
            await uow.registrar_movimiento_stock(
                libro=libro,
                cantidad=cantidad,
                motivo="Reposición",
                usuario_id=usuario_id,
            )
        except ValueError as exc:
            raise ConflictError(str(exc)) from exc

        detalle = await uow.libros.get_detalle(libro_id)
        return LibroRead.model_validate(detalle)


async def list_movimientos(
    uow: LibrosUnitOfWork,
    libro_id: int,
) -> list[MovimientoStockRead]:
    """Lista cronológicamente todos los movimientos de stock del libro (ADMIN) o lanza EntityNotFoundError."""
    async with uow:
        hist = await uow.libros.get_by_id_including_deleted(libro_id)
        if hist is None:
            raise EntityNotFoundError("Libro no encontrado")
        movimientos = await uow.movimientos.get_movimientos_by_libro(libro_id)
        return [MovimientoStockRead.model_validate(m) for m in movimientos]
