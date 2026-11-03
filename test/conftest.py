"""Configuración global de pytest para la suite de pruebas."""

import os

from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("POSTGRES_USER", "libreria")
os.environ.setdefault("POSTGRES_PASSWORD", "libreria_dev_local")
os.environ.setdefault("POSTGRES_DB", "libreria")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5433")
os.environ.setdefault(
    "JWT_SECRET",
    "test_jwt_secret_key_for_automated_suite_minimum_32_bytes",
)
os.environ.setdefault("BCRYPT_ROUNDS", "4")

# Registrar todos los modelos SQLModel para que los mappers estén completos en cualquier orden de ejecución
import app.modules.autores.models  # noqa: E402, F401
import app.modules.clientes.models  # noqa: E402, F401
import app.modules.editoriales.models  # noqa: E402, F401
import app.modules.generos.models  # noqa: E402, F401
import app.modules.libros.models  # noqa: E402, F401
import app.modules.usuarios.models  # noqa: E402, F401
import app.modules.ventas.models  # noqa: E402, F401
