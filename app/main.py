"""Punto de entrada de la aplicación FastAPI y gestión del ciclo de vida (lifespan)."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
from app.modules.autores import models as _autores_models  # noqa: F401
from app.modules.autores.router import router as autores_router
from app.modules.clientes import models as _clientes_models  # noqa: F401
from app.modules.clientes.router import router as clientes_router
from app.modules.editoriales import models as _editoriales_models  # noqa: F401
from app.modules.editoriales.router import router as editoriales_router
from app.modules.generos import models as _generos_models  # noqa: F401
from app.modules.generos.router import router as generos_router
from app.modules.health.router import router as health_router
from app.modules.libros import models as _libros_models  # noqa: F401
from app.modules.libros.router import router as libros_router
from app.modules.ventas import models as _ventas_models  # noqa: F401
from app.modules.ventas.router import router as ventas_router


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Inicializa una única vez el motor y la fábrica de sesiones en app.state y libera al apagar."""
    settings = get_settings()
    engine = build_engine(
        database_url=settings.database_url,
        sql_echo=settings.sql_echo,
    )
    session_factory = build_session_factory(engine)
    application.state.engine = engine
    application.state.session_factory = session_factory
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    """Construye la aplicación FastAPI y registra los routers de los 7 módulos."""
    application = FastAPI(
        title="API de Librería — TP Unidades 1 a 4",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(health_router)
    application.include_router(editoriales_router)
    application.include_router(generos_router)
    application.include_router(autores_router)
    application.include_router(libros_router)
    application.include_router(clientes_router)
    application.include_router(ventas_router)
    return application


app = create_app()
