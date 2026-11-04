"""Dependencia de paginación acotada (RN-10)."""

from typing import Annotated

from fastapi import Query


class PaginationParams:
    """Parámetros de paginación validados por FastAPI."""

    def __init__(self, limit: int, offset: int) -> None:
        self.limit = limit
        self.offset = offset


async def get_pagination_params(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginationParams:
    """Dependencia FastAPI que provee parámetros de paginación validados."""
    return PaginationParams(limit=limit, offset=offset)