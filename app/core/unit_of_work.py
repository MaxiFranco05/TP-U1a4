"""Gestor de contexto transaccional asincrónico (UnitOfWork) sobre la sesión compartida de la petición."""

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWork:
    """Gobierna el límite transaccional (commit / rollback) sobre la AsyncSession sin cerrarla."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is None:
            await self.session.commit()
        else:
            await self.session.rollback()

    async def commit(self) -> None:
        """Confirma explícitamente la transacción activa."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Revierte explícitamente la transacción activa."""
        await self.session.rollback()
