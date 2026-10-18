"""Contratos de respuesta para las sondas de salud."""

from typing import Literal

from sqlmodel import SQLModel


class HealthLiveResponse(SQLModel):
    """Respuesta de la sonda de liveness."""

    estado: Literal["vivo"] = "vivo"


class HealthReadyResponse(SQLModel):
    """Respuesta de la sonda de readiness."""

    estado: Literal["listo"] = "listo"
