"""Parámetros de consulta, envoltorio genérico y validación de paginación (RN-13)."""

from collections.abc import Sequence
import math
from typing import Generic, TypeVar

from fastapi import HTTPException, Query
from sqlmodel import SQLModel

T = TypeVar("T")


class PaginationParams:
    """Dependencia de consulta para endpoints paginados (page >= 1, 1 <= size <= 100)."""

    def __init__(
        self,
        page: int = Query(
            default=1,
            ge=1,
            description="Número de página (empieza en 1)",
        ),
        size: int = Query(
            default=20,
            ge=1,
            le=100,
            description="Tamaño de página (1 a 100)",
        ),
    ) -> None:
        self.page = page
        self.size = size

    @property
    def offset(self) -> int:
        """Desplazamiento (OFFSET) calculado a partir de page y size."""
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        """Límite (LIMIT) equivalente a size."""
        return self.size


class PaginatedResponse(SQLModel, Generic[T]):
    """Envoltorio uniforme de respuesta paginada {items, total, page, size, pages}."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int


Page = PaginatedResponse


def calcular_paginas(total: int, size: int) -> int:
    """Calcula la cantidad total de páginas garantizando al menos 1 página cuando total == 0."""
    if size < 1 or size > 100:
        raise HTTPException(
            status_code=422,
            detail="El tamaño de página debe estar entre 1 y 100",
        )
    if total <= 0:
        return 1
    return max(1, math.ceil(total / size))


def validar_pagina(page: int, pages: int) -> None:
    """Valida que la página solicitada exista dentro del rango [1, pages]."""
    if page < 1:
        raise HTTPException(
            status_code=422,
            detail="El número de página debe ser mayor o igual a 1",
        )
    if page > pages:
        raise HTTPException(
            status_code=422,
            detail=f"La página {page} no existe: hay {pages}",
        )


def paginate(
    items: Sequence[T],
    total: int,
    page: int,
    size: int,
) -> PaginatedResponse[T]:
    """Construye el envoltorio PaginatedResponse validando rango de página y tamaño."""
    pages = calcular_paginas(total, size)
    validar_pagina(page, pages)
    return PaginatedResponse(
        items=list(items),
        total=total,
        page=page,
        size=size,
        pages=pages,
    )
