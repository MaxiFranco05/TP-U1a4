"""Carga de configuración desde variables de entorno (.env)."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_UNCONFIGURED_URL = "postgresql+asyncpg://unconfigured:unconfigured@127.0.0.1:59999/unconfigured"


@dataclass(frozen=True)
class Settings:
    """Parámetros de configuración de la aplicación obtenidos del entorno."""

    database_url: str
    sql_echo: bool


def get_settings() -> Settings:
    """Lee DATABASE_URL y SQL_ECHO desde las variables de entorno actuales."""
    raw_url = os.getenv("DATABASE_URL", "").strip()
    database_url = raw_url if raw_url else DEFAULT_UNCONFIGURED_URL
    raw_echo = os.getenv("SQL_ECHO", "false").strip().lower()
    sql_echo = raw_echo in {"1", "true", "yes", "on"}
    return Settings(database_url=database_url, sql_echo=sql_echo)
