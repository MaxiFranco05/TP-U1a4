"""Contratos de datos (DTOs) para los endpoints de autenticación (/auth), usuarios (/usuarios) y auditoría (/eventos)."""

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import validar_longitud_password


class UsuarioRegistroRequest(BaseModel):
    """Contrato de entrada para el auto-registro de clientes (RN-02, RN-15)."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        return validar_longitud_password(v)


class LoginRequest(BaseModel):
    """Contrato de entrada para inicio de sesión (RN-08, RN-15)."""

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        return validar_longitud_password(v)


class LoginResponse(BaseModel):
    """Contrato de respuesta exitosa de login (C-03). No incluye el token JWT."""

    model_config = ConfigDict(extra="forbid")

    mensaje: str = "Inicio de sesión exitoso"
    debe_cambiar_password: bool
    expira_en_segundos: int


class UsuarioYoResponse(BaseModel):
    """Contrato de respuesta para introspección de usuario actual (/auth/yo, C-07)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    email: str
    nombre: str
    debe_cambiar_password: bool
    roles_vigentes: list[str]
    roles_token: list[str]


class CambiarPasswordRequest(BaseModel):
    """Contrato de entrada para cambio voluntario u obligatorio de contraseña (RN-06, RN-15, RN-16)."""

    model_config = ConfigDict(extra="forbid")

    password_actual: str = Field(min_length=1)
    password_nueva: str = Field(min_length=1)

    @field_validator("password_actual", "password_nueva")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        return validar_longitud_password(v)


class MensajeResponse(BaseModel):
    """Contrato genérico para respuestas informativas de éxito."""

    model_config = ConfigDict(extra="forbid")

    mensaje: str


class UsuarioCreateRequest(BaseModel):
    """Contrato de entrada para alta de personal por administradores (RN-06, RN-16)."""

    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=1)
    rol: str = Field(pattern=r"^(ADMIN|VENDEDOR|CLIENTE)$")

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        return validar_longitud_password(v)


class UsuarioReadResponse(BaseModel):
    """Contrato de lectura de usuario sin exponer password_hash."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    email: str
    nombre: str
    activo: bool
    debe_cambiar_password: bool
    creado_en: datetime | None = None
    roles: list[str] = Field(default_factory=list)



class RolAsignarRequest(BaseModel):
    """Contrato de entrada para asignación de roles con vigencia (RN-03, C-07)."""

    model_config = ConfigDict(extra="forbid")

    rol: str = Field(pattern=r"^(ADMIN|VENDEDOR|CLIENTE)$")
    vence_en: datetime | None = None

    @field_validator("vence_en")
    @classmethod
    def validate_vence_en(cls, v: datetime | None) -> datetime | None:
        if v is not None:
            if v.tzinfo is None:
                raise ValueError("La fecha de vencimiento debe incluir zona horaria")
            if v <= datetime.now(timezone.utc):
                raise ValueError("La fecha de vencimiento debe ser posterior al momento actual")
        return v


class RolAsignacionResponse(BaseModel):
    """Contrato de respuesta para detalle de asignación de rol y trazabilidad."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    usuario_id: int
    rol: str
    otorgada_por: int | None = None
    desde: datetime
    vence_en: datetime | None = None
    revocada_en: datetime | None = None
    activa: bool = True


class EventoSeguridadResponse(BaseModel):
    """Contrato de lectura para bitácora de auditoría de seguridad (RN-16, C-16)."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    actor: str
    accion: str
    cuando: datetime

