import os, sys
from logging.config import fileConfig
from sqlalchemy import create_engine
from alembic import context
from dotenv import load_dotenv

load_dotenv()
config = context.config
fileConfig(config.config_file_name)

from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.autores.models import Autor
from app.modules.libros.models import Libro, LibroAutor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.ventas.models import Venta, RenglonVenta
from sqlmodel import SQLModel

target_metadata = SQLModel.metadata

def run_migrations_online():
    db_url = os.getenv("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    connectable = create_engine(db_url)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
