"""Contratos de datos (DTOs) para los endpoints de autenticación (/auth)."""

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
