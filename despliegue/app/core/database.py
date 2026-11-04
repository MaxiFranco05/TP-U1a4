"""Motor asincrónico, fábrica de sesiones y dependencia por petición."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(database_url: str, sql_echo: bool = False) -> AsyncEngine:
    """Construye el motor asincrónico de SQLAlchemy 2.0."""
    return create_async_engine(database_url, echo=sql_echo)


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Construye la fábrica de sesiones asincrónicas con expire_on_commit=False."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Provee una sesión asincrónica aislada por petición y la cierra al finalizar."""
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
