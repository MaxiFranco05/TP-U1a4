"""Endpoints HTTP de las sondas de salud (/health/live y /health/ready)."""

from fastapi import APIRouter

from app.core.database import SessionDep
from app.modules.health.schemas import HealthLiveResponse, HealthReadyResponse
from app.modules.health.service import check_liveness, check_readiness

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def get_health_live() -> HealthLiveResponse:
    """Sonda de vida: responde 200 sin depender de la base de datos."""
    return await check_liveness()


@router.get("/ready")
async def get_health_ready(session: SessionDep) -> HealthReadyResponse:
    """Sonda de disponibilidad: verifica conectividad con PostgreSQL vía SELECT 1."""
    return await check_readiness(session)
