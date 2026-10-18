"""Router HTTP del módulo libros."""

from fastapi import APIRouter

router = APIRouter(prefix="/libros", tags=["libros"])
