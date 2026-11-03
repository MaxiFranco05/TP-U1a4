"""Criptografía bcrypt fuera del bucle con semáforo, tokens JWT y validaciones de contraseña."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

# Semáforo global para acotar la concurrencia de hashing y evitar saturar el pool de hilos (DD-10).
_BCRYPT_SEMAPHORE = asyncio.Semaphore(4)

JWT_ALGORITHM = "HS256"


def validar_longitud_password(v: str) -> str:
    """Valida que la contraseña no exceda los 72 bytes en codificación UTF-8 (RN-15).

    Lanza ValueError para que FastAPI / Pydantic responda 422 Unprocessable Entity
    y previene truncamientos o excepciones 500 en bcrypt.
    """
    if len(v.encode("utf-8")) > 72:
        raise ValueError("La contraseña no puede superar los 72 bytes UTF-8.")
    return v


async def hash_password(password: str) -> str:
    """Calcula el hash bcrypt en un hilo separado bajo semáforo global fuera del bucle de eventos (DD-10)."""
    validar_longitud_password(password)
    settings = get_settings()
    async with _BCRYPT_SEMAPHORE:
        hashed_bytes = await asyncio.to_thread(
            bcrypt.hashpw,
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS),
        )
        return hashed_bytes.decode("utf-8")


async def verify_password(password: str, password_hash: str | bytes) -> bool:
    """Verifica una contraseña contra su hash en un hilo separado bajo semáforo global (DD-10)."""
    hash_bytes = (
        password_hash.encode("utf-8")
        if isinstance(password_hash, str)
        else password_hash
    )
    async with _BCRYPT_SEMAPHORE:
        return await asyncio.to_thread(
            bcrypt.checkpw,
            password.encode("utf-8"),
            hash_bytes,
        )


def create_access_token(
    data: dict[str, Any],
    expires_delta: int | timedelta | None = None,
) -> str:
    """Emite un token JWT firmado con HS256 conteniendo claims estándar (sub, exp) y roles informativos."""
    settings = get_settings()
    to_encode = data.copy()
    if isinstance(expires_delta, timedelta):
        expire = datetime.now(timezone.utc) + expires_delta
    elif isinstance(expires_delta, int):
        expire = datetime.now(timezone.utc) + timedelta(seconds=expires_delta)
    else:
        expire = datetime.now(timezone.utc) + timedelta(seconds=settings.JWT_EXPIRATION_SECONDS)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica y valida la firma y vigencia de un token JWT.

    Lanza jwt.ExpiredSignatureError o jwt.InvalidTokenError si el token no es válido o expiró.
    """
    settings = get_settings()
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[JWT_ALGORITHM])
