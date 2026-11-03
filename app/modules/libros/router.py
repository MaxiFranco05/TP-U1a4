"""Router HTTP del módulo libros (rutas públicas y protegidas)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_usuario_actual
from app.core.paginacion import PaginatedResponse, PaginationParams
from app.modules.libros.schemas import (
    LibroCreate,
    LibroListItem,
    LibroRead,
    LibroUpdate,
    MovimientoStockRead,
    ReponerStockRequest,
)
from app.modules.libros.service import (
    create_libro,
    delete_libro,
    get_libro,
    list_libros,
    list_movimientos,
    reponer_stock,
    update_libro,
)
from app.modules.libros.unit_of_work import LibrosUnitOfWork
from app.modules.usuarios.models import Usuario


def get_libros_uow(
    session: AsyncSession = Depends(get_session),
) -> LibrosUnitOfWork:
    """Provee una instancia de LibrosUnitOfWork compartiendo la sesión de la petición."""
    return LibrosUnitOfWork(session=session)


public_router = APIRouter(prefix="/libros", tags=["Libros"])
protected_router = APIRouter(prefix="/libros", tags=["Libros"])


# --- Rutas Públicas (Lectura Abierta) ---


@public_router.get(
    "",
    response_model=PaginatedResponse[LibroListItem],
    status_code=status.HTTP_200_OK,
)
@public_router.get(
    "/",
    response_model=PaginatedResponse[LibroListItem],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_libros_list(
    params: PaginationParams = Depends(),
    titulo: str | None = None,
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> PaginatedResponse[LibroListItem]:
    """Lista libros activos paginados con envoltorio uniforme y búsqueda por título (abierto al público)."""
    return await list_libros(uow=uow, params=params, titulo=titulo)


@public_router.get(
    "/{libro_id}",
    response_model=LibroRead,
    status_code=status.HTTP_200_OK,
)
async def get_libro_detail(
    libro_id: int,
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> LibroRead:
    """Obtiene el detalle completo de un libro activo con editorial, género y autores (abierto al público)."""
    return await get_libro(uow=uow, libro_id=libro_id)


# --- Rutas Protegidas (Exigen ADMIN) ---


@protected_router.post(
    "",
    response_model=LibroRead,
    status_code=status.HTTP_201_CREATED,
)
@protected_router.post(
    "/",
    response_model=LibroRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def post_libro(
    payload: LibroCreate,
    usuario_actual: Usuario = Depends(get_usuario_actual),
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> LibroRead:
    """Crea un nuevo libro con stock_inicial y autores en una transacción atómica (ADMIN)."""
    return await create_libro(uow=uow, payload=payload, usuario_id=usuario_actual.id)


@protected_router.patch(
    "/{libro_id}",
    response_model=LibroRead,
    status_code=status.HTTP_200_OK,
)
async def patch_libro(
    libro_id: int,
    payload: LibroUpdate,
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> LibroRead:
    """Actualiza parcialmente un libro activo (solo título y precio; stock prohibido) (ADMIN)."""
    return await update_libro(uow=uow, libro_id=libro_id, payload=payload)


@protected_router.delete(
    "/{libro_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_libro_endpoint(
    libro_id: int,
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> None:
    """Baja lógica de un libro marcando borrado_en (ADMIN)."""
    await delete_libro(uow=uow, libro_id=libro_id)


@protected_router.post(
    "/{libro_id}/reponer",
    response_model=LibroRead,
    status_code=status.HTTP_200_OK,
)
async def post_reponer_stock(
    libro_id: int,
    payload: ReponerStockRequest,
    usuario_actual: Usuario = Depends(get_usuario_actual),
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> LibroRead:
    """Repone stock mediante el punto único de stock (ADMIN)."""
    return await reponer_stock(
        uow=uow,
        libro_id=libro_id,
        cantidad=payload.cantidad,
        usuario_id=usuario_actual.id,
    )


@protected_router.get(
    "/{libro_id}/movimientos",
    response_model=list[MovimientoStockRead],
    status_code=status.HTTP_200_OK,
)
async def get_movimientos_libro(
    libro_id: int,
    uow: LibrosUnitOfWork = Depends(get_libros_uow),
) -> list[MovimientoStockRead]:
    """Lista cronológicamente los movimientos de stock del libro (ADMIN)."""
    return await list_movimientos(uow=uow, libro_id=libro_id)


# Router combinado para compatibilidad
router = APIRouter()
router.include_router(public_router)
router.include_router(protected_router)
