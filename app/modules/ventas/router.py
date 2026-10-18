"""Router HTTP del módulo ventas."""

from fastapi import APIRouter

router = APIRouter(prefix="/ventas", tags=["ventas"])
