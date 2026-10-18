"""Router HTTP del módulo autores."""

from fastapi import APIRouter

router = APIRouter(prefix="/autores", tags=["autores"])
