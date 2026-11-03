"""Punto de entrada de la aplicación FastAPI, ciclo de vida (lifespan) y grupos de rutas."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import bcrypt
from fastapi import APIRouter, Depends, FastAPI

from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
from app.core.dependencies import verificar_password_cambiada
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


def _generate_dummy_password_hash(rounds: int) -> bytes:
    """Genera el hash ficticio de login para defensa contra enumeración por timing (RN-08)."""
    return bcrypt.hashpw(
        b"dummy-timing-defense-password",
        bcrypt.gensalt(rounds=rounds),
    )


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Inicializa una única vez motor, fábrica de sesiones y hash ficticio en app.state."""
    settings = get_settings()
    engine = build_engine(
        database_url=settings.DATABASE_URL,
        sql_echo=settings.SQL_ECHO,
        pool_size=settings.DB_POOL_SIZE,
    )
    session_factory = build_session_factory(engine)
    dummy_password_hash = await asyncio.to_thread(
        _generate_dummy_password_hash,
        settings.BCRYPT_ROUNDS,
    )
    application.state.settings = settings
    application.state.engine = engine
    application.state.session_factory = session_factory
    application.state.dummy_password_hash = dummy_password_hash
    try:
        yield
    finally:
        await engine.dispose()


def _build_route_groups() -> tuple[APIRouter, APIRouter]:
    """Construye los dos grupos de rutas de nivel superior: abierto y protegido.

    - router_abierto: sondas de salud (/health/*), autenticación (/auth/*) y lecturas públicas.
    - router_protegido: rutas protegidas donde se montará una sola vez el bloqueo por
      cambio obligatorio de contraseña (debe_cambiar_password).
    """
    open_group = APIRouter()
    protected_group = APIRouter(dependencies=[Depends(verificar_password_cambiada)])

    open_group.include_router(health_router)

    protected_group.include_router(editoriales_router)
    protected_group.include_router(generos_router)
    protected_group.include_router(autores_router)
    protected_group.include_router(libros_router)
    protected_group.include_router(clientes_router)
    protected_group.include_router(ventas_router)
    return open_group, protected_group


router_abierto, router_protegido = _build_route_groups()


def create_app() -> FastAPI:
    """Construye la aplicación FastAPI y registra los grupos de rutas abierto y protegido."""
    application = FastAPI(
        title="API de Librería — TP Unidades 1 a 4 y Parcial Cap. 1 a 6",
        version="0.2.0",
        lifespan=lifespan,
    )
    open_group, protected_group = _build_route_groups()
    application.include_router(open_group)
    application.include_router(protected_group)
    return application


app = create_app()
