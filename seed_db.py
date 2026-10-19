"""Seed reproducible para TP-U1a4 (API Librería).

C-08: Deja el banco de datos en estado conocido para que los .http sean reproducibles.
Uso: python seed_db.py (ejecutado tras `alembic upgrade head`)
Luego: correr los .http contra http://localhost:8000
"""

import asyncio
from decimal import Decimal

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor
from app.modules.ventas.models import RenglonVenta, Venta


async def seed() -> None:
    settings = get_settings()
    engine = build_engine(settings.database_url, sql_echo=False)
    session_factory = build_session_factory(engine)

    async with session_factory() as session:
        # Limpieza previa para que el seed sea idempotente y reproducible
        await session.execute(
            text(
                "TRUNCATE TABLE renglon_venta, venta, perfil_cliente, cliente, "
                "libro_autor, libro, genero, autor, editorial RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()

        # 1. Editoriales
        editoriales = [
            Editorial(nombre="Editorial Planeta", pais="Argentina"),
            Editorial(nombre="Editorial Sudamericana", pais="Uruguay"),
            Editorial(nombre="Penguin Random House", pais="EE.UU"),
        ]
        session.add_all(editoriales)
        await session.commit()
        for e in editoriales:
            await session.refresh(e)

        # 2. Géneros
        generos = [
            Genero(nombre="Ficción"),
            Genero(nombre="No Ficción"),
            Genero(nombre="Ciencia Ficción"),
        ]
        session.add_all(generos)
        await session.commit()
        for g in generos:
            await session.refresh(g)

        # 3. Autores
        autores = [
            Autor(nombre="Jorge Luis Borges", nacionalidad="Argentina"),
            Autor(nombre="Julio Cortázar", nacionalidad="Argentina"),
            Autor(nombre="Isabel Allende", nacionalidad="Chile"),
            Autor(nombre="Gabriel García Márquez", nacionalidad="Colombia"),
        ]
        session.add_all(autores)
        await session.commit()
        for a in autores:
            await session.refresh(a)

        # 4. Libros (deben insertarse antes de LibroAutor por foreign keys)
        libros = [
            Libro(
                isbn="978-950-12-3456-7",
                titulo="El Aleph",
                precio=Decimal("45.00"),
                stock=15,
                editorial_id=editoriales[0].id,
                genero_id=generos[0].id,
            ),
            Libro(
                isbn="978-950-12-3456-8",
                titulo="Rayuela",
                precio=Decimal("55.00"),
                stock=10,
                editorial_id=editoriales[0].id,
                genero_id=generos[0].id,
            ),
            Libro(
                isbn="978-950-12-3456-9",
                titulo="La casa de los espíritus",
                precio=Decimal("38.50"),
                stock=20,
                editorial_id=editoriales[1].id,
                genero_id=generos[0].id,
            ),
            Libro(
                isbn="978-950-12-3457-0",
                titulo="Cien años de soledad",
                precio=Decimal("42.00"),
                stock=25,
                editorial_id=editoriales[2].id,
                genero_id=generos[1].id,
            ),
            Libro(
                isbn="978-950-12-3457-1",
                titulo="El examen",
                precio=Decimal("30.00"),
                stock=12,
                editorial_id=editoriales[1].id,
                genero_id=generos[0].id,
            ),
        ]
        session.add_all(libros)
        await session.commit()
        for l in libros:
            await session.refresh(l)

        # 5. Libro-Autor associations (con roles y orden)
        autorias = [
            LibroAutor(libro_id=libros[0].id, autor_id=autores[0].id, rol="autor", orden=1),
            LibroAutor(libro_id=libros[1].id, autor_id=autores[1].id, rol="autor", orden=1),
            LibroAutor(libro_id=libros[1].id, autor_id=autores[0].id, rol="coautor", orden=2),
            LibroAutor(libro_id=libros[2].id, autor_id=autores[2].id, rol="autor", orden=1),
            LibroAutor(libro_id=libros[3].id, autor_id=autores[3].id, rol="autor", orden=1),
            LibroAutor(libro_id=libros[4].id, autor_id=autores[1].id, rol="autor", orden=1),
        ]
        session.add_all(autorias)
        await session.commit()

        # 6. Cliente con perfil único (1 a 0..1)
        cliente = Cliente(nombre="María García", email="maria.garcia@test.com")
        session.add(cliente)
        await session.commit()
        await session.refresh(cliente)

        perfil = PerfilCliente(
            cliente_id=cliente.id,
            telefono="+54 9 11 1234-5678",
            direccion="Calle Falsa 123, Buenos Aires, Argentina",
        )
        session.add(perfil)
        await session.commit()

        # 7. Venta de ejemplo (con renglones)
        renglones = [
            RenglonVenta(
                libro_id=libros[0].id,
                cantidad=2,
                precio_unitario=libros[0].precio,  # $45.00
            ),
            RenglonVenta(
                libro_id=libros[1].id,
                cantidad=1,
                precio_unitario=libros[1].precio,  # $55.00
            ),
        ]
        total = (Decimal("2") * libros[0].precio) + (Decimal("1") * libros[1].precio)

        venta = Venta(
            cliente_id=cliente.id,
            total=total,
            renglones=renglones,
        )
        session.add(venta)
        await session.commit()

        print("[OK] Seed completado exitosamente")
        print(f"   - {len(editoriales)} editoriales")
        print(f"   - {len(generos)} géneros")
        print(f"   - {len(autores)} autores")
        print(f"   - {len(libros)} libros")
        print(f"   - {len(autorias)} autorías asignadas")
        print("   - 1 cliente con perfil")
        print(f"   - 1 venta de ejemplo con {len(renglones)} renglones (Total: ${total})")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())