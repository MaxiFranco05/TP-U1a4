#!/usr/bin/env python
"""Script de seed para datos de prueba reproducibles (C-05)."""

import asyncio
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
# Import all models to register relationships
from app.modules.autores.models import Autor  # noqa: F401
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero  # noqa: F401
from app.modules.libros.models import Libro, LibroAutor  # noqa: F401
from app.modules.ventas.models import Venta, RenglonVenta


async def seed(session: AsyncSession) -> None:
    """Inserta datos de ejemplo para clientes, perfiles y ventas."""
    # Cliente 1: con perfil y ventas
    cliente1 = Cliente(nombre="Juan Pérez", email="juan.perez@example.com")
    session.add(cliente1)
    await session.flush()

    perfil1 = PerfilCliente(
        cliente_id=cliente1.id,
        telefono="+54 11 1234-5678",
        direccion="Av. Corrientes 1234, CABA",
    )
    session.add(perfil1)

    # Cliente 2: sin perfil, sin ventas
    cliente2 = Cliente(nombre="María González", email="maria.gonzalez@example.com")
    session.add(cliente2)
    await session.flush()

    # Cliente 3: para probar email duplicado
    cliente3 = Cliente(nombre="Pedro López", email="pedro.lopez@example.com")
    session.add(cliente3)
    await session.flush()

    # Buscar o crear editorial para ventas
    result = await session.execute(select(Editorial).where(Editorial.nombre == "Editorial Seed C05"))
    editorial = result.scalar_one_or_none()
    if editorial is None:
        editorial = Editorial(nombre="Editorial Seed C05", pais="Argentina")
        session.add(editorial)
        await session.flush()

    # Buscar o crear libro
    result = await session.execute(select(Libro).where(Libro.isbn == "978-0123456789"))
    libro = result.scalar_one_or_none()
    if libro is None:
        libro = Libro(
            isbn="978-0123456789",
            titulo="Libro de Prueba",
            precio=Decimal("1500.00"),
            stock=10,
            editorial_id=editorial.id,
        )
        session.add(libro)
        await session.flush()

    # Venta para cliente1 (verificar si ya existe)
    result = await session.execute(select(Venta).where(Venta.cliente_id == cliente1.id))
    venta = result.scalar_one_or_none()
    if venta is None:
        venta = Venta(
            cliente_id=cliente1.id,
            fecha=datetime.now(timezone.utc),
            total=Decimal("3000.00"),
        )
        session.add(venta)
        await session.flush()

        renglon = RenglonVenta(
            venta_id=venta.id,
            libro_id=libro.id,
            cantidad=2,
            precio_unitario=Decimal("1500.00"),
        )
        session.add(renglon)

    await session.commit()
    print("Seed completado: 3 clientes, 1 perfil, 1 venta con 1 renglón")


async def main() -> None:
    settings = get_settings()
    engine = build_engine(settings.database_url, settings.sql_echo)
    session_factory = build_session_factory(engine)

    async with session_factory() as session:
        await seed(session)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())