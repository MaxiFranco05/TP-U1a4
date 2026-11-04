"""Lógica de negocio de las sondas de salud."""

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.health.schemas import HealthLiveResponse, HealthReadyResponse


async def check_liveness() -> HealthLiveResponse:
    """Devuelve estado vivo sin consultar la base de datos."""
    return HealthLiveResponse(estado="vivo")


async def check_readiness(session: AsyncSession) -> HealthReadyResponse:
    """Verifica conectividad con la base de datos ejecutando SELECT 1.

    Ante cualquier falla de conexión o motor, devuelve HTTP 503 con un mensaje
    controlado sin exponer detalles internos, trazas ni cadenas de conexión (RN-12).
    """
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc
    return HealthReadyResponse(estado="listo")
