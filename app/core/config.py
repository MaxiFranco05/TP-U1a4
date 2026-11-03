"""Configuración tipada de la aplicación mediante pydantic-settings."""

from urllib.parse import quote_plus

from pydantic import computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Parámetros de configuración validados al arranque sin secretos por defecto."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "libreria"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    JWT_SECRET: str
    JWT_EXPIRATION_SECONDS: int = 1800
    BCRYPT_ROUNDS: int = 12
    COOKIE_SECURE: bool = False

    DB_POOL_SIZE: int = 5
    SQL_ECHO: bool = False

    @field_validator("POSTGRES_PASSWORD", "JWT_SECRET")
    @classmethod
    def _reject_blank_secrets(cls, value: str) -> str:
        """Impide que credenciales críticas queden vacías o sólo con espacios."""
        if not value or not value.strip():
            raise ValueError("El secreto o contraseña obligatorio no puede estar vacío.")
        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Construye la URL asincrónica PostgreSQL a partir de las variables POSTGRES_*."""
        encoded_password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{encoded_password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_url(self) -> str:
        """Propiedad de compatibilidad hacia atrás con módulos de la Etapa 1 y Alembic."""
        return self.DATABASE_URL

    @property
    def sql_echo(self) -> bool:
        """Propiedad de compatibilidad hacia atrás con módulos de la Etapa 1."""
        return self.SQL_ECHO


def get_settings() -> Settings:
    """Instancia y valida la configuración desde el entorno actual y .env."""
    return Settings()  # type: ignore[call-arg]
