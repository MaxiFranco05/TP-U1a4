"""Esquemas DTO del módulo clientes."""

from pydantic import EmailStr, field_validator
from sqlmodel import SQLModel


class ClienteCreate(SQLModel):
    """DTO de entrada para la creación de un cliente (sin id)."""

    nombre: str
    email: EmailStr

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("El nombre del cliente no puede estar vacío")
        return cleaned


class ClienteUpdate(SQLModel):
    """DTO de entrada para actualización parcial (PATCH) de un cliente."""

    nombre: str | None = None
    email: EmailStr | None = None

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("El nombre del cliente no puede estar vacío")
        return cleaned


class PerfilClienteCreate(SQLModel):
    """DTO de entrada para la creación de un perfil de cliente."""

    telefono: str
    direccion: str

    @field_validator("telefono")
    @classmethod
    def validate_telefono(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("El teléfono no puede estar vacío")
        return cleaned

    @field_validator("direccion")
    @classmethod
    def validate_direccion(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("La dirección no puede estar vacía")
        return cleaned


class PerfilClienteRead(SQLModel):
    """DTO de salida para lectura de un perfil de cliente."""

    id: int
    cliente_id: int
    telefono: str
    direccion: str


class ClienteListItem(SQLModel):
    """DTO de salida para listado de clientes (sin perfil para evitar N+1)."""

    id: int
    nombre: str
    email: str


class ClienteRead(SQLModel):
    """DTO de salida para lectura de un cliente con perfil anidado."""

    id: int
    nombre: str
    email: str
    perfil: PerfilClienteRead | None = None