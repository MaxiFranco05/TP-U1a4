"""Endpoints y contratos de las sondas de salud (/health/live y /health/ready)."""

from typing import Literal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlmodel import SQLModel

from app.core.database import SessionDep


class HealthLiveResponse(SQLModel):
    """Respuesta de la sonda de liveness."""

    estado: Literal["vivo"] = "vivo"


class HealthReadyResponse(SQLModel):
    """Respuesta de la sonda de readiness."""

    estado: Literal["listo"] = "listo"


# Alias compatibles con convención LiveHealthResponse / ReadyHealthResponse
LiveHealthResponse = HealthLiveResponse
ReadyHealthResponse = HealthReadyResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def get_health_live() -> HealthLiveResponse:
    """Sonda de vida: responde 200 sin depender de la base de datos."""
    return HealthLiveResponse(estado="vivo")


@router.get("/ready")
async def get_health_ready(session: SessionDep) -> HealthReadyResponse:
    """Sonda de disponibilidad: verifica conectividad con PostgreSQL vía SELECT 1.

    Ante cualquier falla de conexión o motor, devuelve HTTP 503 con un mensaje
    controlado sin exponer detalles internos, trazas ni cadenas de conexión (RN-15).
    """
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc
    return HealthReadyResponse(estado="listo")
