"""Router HTTP del módulo clientes."""

from fastapi import APIRouter

router = APIRouter(prefix="/clientes", tags=["clientes"])
