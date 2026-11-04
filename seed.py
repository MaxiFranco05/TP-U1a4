"""Script de seed canónico e idempotente para el Parcial Capítulos 1 a 6 (API Librería).

Vacía todas las tablas con RESTART IDENTITY CASCADE y carga el estado inicial exacto
exigido por la consigna del Parcial para sustentar las pruebas C-01 a C-16:
- 5 usuarios con bcrypt y roles vigentes (ADMIN, VENDEDOR, CLIENTE).
- Catálogo: 3 editoriales, 3 géneros, 6 autores y 5 libros con stock actual exacto.
- 3 clientes (Lucía con perfil, Tomás sin usuario, Ana con usuario_id).
- 1 venta de $69000.00 con 2 renglones registrada por vendedor@example.com.
- 7 movimientos de stock manteniendo la invariante libro.stock == SUM(movimiento_stock.cantidad).
- 1 evento de seguridad de SISTEMA: "Carga de los datos iniciales".

Uso:
    python seed.py
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
from app.core.security import hash_password
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock
from app.modules.usuarios.models import AsignacionRol, EventoSeguridad, Usuario
from app.modules.ventas.models import RenglonVenta, Venta

# Contraseñas ficticias de referencia para pruebas y documentación
PASSWORDS: dict[str, str] = {
    "admin@example.com": "Admin123!",
    "admin2@example.com": "Admin123!",
    "vendedor@example.com": "Vendedor123!",
    "ana@example.com": "Cliente123!",
    "nuevo@example.com": "Nuevo123!",
}


async def seed() -> None:
    """Ejecuta el seed canónico del Parcial."""
    settings = get_settings()
    engine = build_engine(settings.database_url, sql_echo=False)
    session_factory = build_session_factory(engine)

    async with session_factory() as session:
        # Vaciado completo con RESTART IDENTITY CASCADE
        await session.execute(
            text(
                "TRUNCATE TABLE movimiento_stock, renglon_venta, venta, asignacion_rol, "
                "intento_acceso, evento_seguridad, perfil_cliente, cliente, libro_autor, "
                "libro, genero, autor, editorial, usuario RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()

        # 1. Usuarios (5) con hash bcrypt calculado
        usuarios = [
            Usuario(
                email="admin@example.com",
                nombre="Administrador General",
                password_hash=await hash_password(PASSWORDS["admin@example.com"]),
                activo=True,
                debe_cambiar_password=False,
            ),
            Usuario(
                email="admin2@example.com",
                nombre="Segundo Administrador",
                password_hash=await hash_password(PASSWORDS["admin2@example.com"]),
                activo=True,
                debe_cambiar_password=False,
            ),
            Usuario(
                email="vendedor@example.com",
                nombre="Vendedor Mostrador",
                password_hash=await hash_password(PASSWORDS["vendedor@example.com"]),
                activo=True,
                debe_cambiar_password=False,
            ),
            Usuario(
                email="ana@example.com",
                nombre="Ana Paz",
                password_hash=await hash_password(PASSWORDS["ana@example.com"]),
                activo=True,
                debe_cambiar_password=False,
            ),
            Usuario(
                email="nuevo@example.com",
                nombre="Vendedor Nuevo",
                password_hash=await hash_password(PASSWORDS["nuevo@example.com"]),
                activo=True,
                debe_cambiar_password=True,
            ),
        ]
        session.add_all(usuarios)
        await session.commit()
        for u in usuarios:
            await session.refresh(u)

        admin = usuarios[0]
        admin2 = usuarios[1]
        vendedor = usuarios[2]
        ana_user = usuarios[3]
        nuevo = usuarios[4]

        # Roles vigentes para los 5 usuarios
        ahora = datetime.now(timezone.utc)
        roles = [
            AsignacionRol(usuario_id=admin.id, rol="ADMIN", desde=ahora),
            AsignacionRol(usuario_id=admin2.id, rol="ADMIN", desde=ahora),
            AsignacionRol(usuario_id=vendedor.id, rol="VENDEDOR", desde=ahora),
            AsignacionRol(usuario_id=ana_user.id, rol="CLIENTE", desde=ahora),
            AsignacionRol(usuario_id=nuevo.id, rol="VENDEDOR", desde=ahora),
        ]
        session.add_all(roles)
        await session.commit()

        # 2. Catálogo: 3 editoriales, 3 géneros y 6 autores
        editoriales = [
            Editorial(nombre="Editorial Sudamericana", pais="Argentina"),
            Editorial(nombre="Editorial Sur", pais="Argentina"),
            Editorial(nombre="Editorial Alfaguara", pais="España"),
        ]
        session.add_all(editoriales)
        await session.commit()
        for e in editoriales:
            await session.refresh(e)

        generos = [
            Genero(nombre="Ficción"),
            Genero(nombre="Fantástico"),
            Genero(nombre="Policial"),
        ]
        session.add_all(generos)
        await session.commit()
        for g in generos:
            await session.refresh(g)

        autores = [
            Autor(nombre="Jorge Luis Borges", nacionalidad="Argentina"),
            Autor(nombre="Julio Cortázar", nacionalidad="Argentina"),
            Autor(nombre="Adolfo Bioy Casares", nacionalidad="Argentina"),
            Autor(nombre="Silvina Ocampo", nacionalidad="Argentina"),
            Autor(nombre="Ricardo Piglia", nacionalidad="Argentina"),
            Autor(nombre="Gabriel García Márquez", nacionalidad="Colombia"),
        ]
        session.add_all(autores)
        await session.commit()
        for a in autores:
            await session.refresh(a)

        # 3. Libros (5) con stock actual exacto
        libros = [
            Libro(
                isbn="978-950-00-0001-1",
                titulo="Rayuela",
                precio=Decimal("25000.00"),
                stock=10,
                editorial_id=editoriales[0].id,
                genero_id=generos[0].id,
            ),
            Libro(
                isbn="978-950-00-0002-8",
                titulo="Antología de la literatura fantástica",
                precio=Decimal("30000.00"),
                stock=5,
                editorial_id=editoriales[1].id,
                genero_id=generos[1].id,
            ),
            Libro(
                isbn="978-950-00-0003-5",
                titulo="Ficciones",
                precio=Decimal("22000.00"),
                stock=8,
                editorial_id=editoriales[0].id,
                genero_id=generos[0].id,
            ),
            Libro(
                isbn="978-950-00-0004-2",
                titulo="Respiración artificial",
                precio=Decimal("18000.00"),
                stock=3,
                editorial_id=editoriales[2].id,
                genero_id=generos[2].id,
            ),
            Libro(
                isbn="978-950-00-0005-9",
                titulo="Bestiario",
                precio=Decimal("15000.00"),
                stock=1,
                editorial_id=editoriales[0].id,
                genero_id=generos[1].id,
            ),
        ]
        session.add_all(libros)
        await session.commit()
        for l in libros:
            await session.refresh(l)

        rayuela = libros[0]
        antologia = libros[1]
        ficciones = libros[2]
        respiracion = libros[3]
        bestiario = libros[4]

        # Asociaciones LibroAutor
        autorias = [
            LibroAutor(libro_id=rayuela.id, autor_id=autores[1].id, rol="autor", orden=1),
            LibroAutor(libro_id=antologia.id, autor_id=autores[0].id, rol="autor", orden=1),
            LibroAutor(libro_id=antologia.id, autor_id=autores[2].id, rol="coautor", orden=2),
            LibroAutor(libro_id=antologia.id, autor_id=autores[3].id, rol="coautor", orden=3),
            LibroAutor(libro_id=ficciones.id, autor_id=autores[0].id, rol="autor", orden=1),
            LibroAutor(libro_id=respiracion.id, autor_id=autores[4].id, rol="autor", orden=1),
            LibroAutor(libro_id=bestiario.id, autor_id=autores[1].id, rol="autor", orden=1),
        ]
        session.add_all(autorias)
        await session.commit()

        # 4. Clientes (3)
        clientes = [
            Cliente(nombre="Lucía Fernández", email="lucia.fernandez@example.com", usuario_id=None),
            Cliente(nombre="Tomás Ríos", email="tomas.rios@example.com", usuario_id=None),
            Cliente(nombre="Ana Paz", email="ana@example.com", usuario_id=ana_user.id),
        ]
        session.add_all(clientes)
        await session.commit()
        for c in clientes:
            await session.refresh(c)

        lucia = clientes[0]
        tomas = clientes[1]
        ana_cliente = clientes[2]

        perfil_lucia = PerfilCliente(
            cliente_id=lucia.id,
            telefono="11-4567-8901",
            direccion="Av. Corrientes 1234",
        )
        session.add(perfil_lucia)
        await session.commit()

        # 5. Venta 1 de Lucía Fernández (1 Rayuela + 2 Ficciones => $69000.00)
        venta1 = Venta(
            cliente_id=lucia.id,
            total=Decimal("69000.00"),
            fecha=ahora,
        )
        session.add(venta1)
        await session.commit()
        await session.refresh(venta1)

        renglones = [
            RenglonVenta(
                venta_id=venta1.id,
                libro_id=rayuela.id,
                cantidad=1,
                precio_unitario=Decimal("25000.00"),
            ),
            RenglonVenta(
                venta_id=venta1.id,
                libro_id=ficciones.id,
                cantidad=2,
                precio_unitario=Decimal("22000.00"),
            ),
        ]
        session.add_all(renglones)
        await session.commit()

        # 6. Movimientos de stock (7)
        # 5 de Stock Inicial
        # Rayuela +11, Antología +5, Ficciones +10, Respiración +3, Bestiario +1
        # 2 salidas por Venta 1: Rayuela -1, Ficciones -2 ejecutadas por vendedor@example.com
        movimientos = [
            MovimientoStock(
                libro_id=rayuela.id,
                cantidad=11,
                motivo="Stock inicial",
                usuario_id=admin.id,
                venta_id=None,
                cuando=ahora,
            ),
            MovimientoStock(
                libro_id=antologia.id,
                cantidad=5,
                motivo="Stock inicial",
                usuario_id=admin.id,
                venta_id=None,
                cuando=ahora,
            ),
            MovimientoStock(
                libro_id=ficciones.id,
                cantidad=10,
                motivo="Stock inicial",
                usuario_id=admin.id,
                venta_id=None,
                cuando=ahora,
            ),
            MovimientoStock(
                libro_id=respiracion.id,
                cantidad=3,
                motivo="Stock inicial",
                usuario_id=admin.id,
                venta_id=None,
                cuando=ahora,
            ),
            MovimientoStock(
                libro_id=bestiario.id,
                cantidad=1,
                motivo="Stock inicial",
                usuario_id=admin.id,
                venta_id=None,
                cuando=ahora,
            ),
            MovimientoStock(
                libro_id=rayuela.id,
                cantidad=-1,
                motivo="Venta #1",
                usuario_id=vendedor.id,
                venta_id=venta1.id,
                cuando=ahora,
            ),
            MovimientoStock(
                libro_id=ficciones.id,
                cantidad=-2,
                motivo="Venta #1",
                usuario_id=vendedor.id,
                venta_id=venta1.id,
                cuando=ahora,
            ),
        ]
        session.add_all(movimientos)
        await session.commit()

        # 7. Historial de seguridad (1)
        evento = EventoSeguridad(
            actor="SISTEMA",
            accion="Carga de los datos iniciales",
            cuando=ahora,
        )
        session.add(evento)
        await session.commit()

        print("[OK] Seed canónico del Parcial completado exitosamente.")
        print(f"   - 5 usuarios cargados con bcrypt: {', '.join(u.email for u in usuarios)}")
        print(f"   - 5 libros con stock exacto: Rayuela ({rayuela.stock}), Antología ({antologia.stock}), Ficciones ({ficciones.stock}), Respiración ({respiracion.stock}), Bestiario ({bestiario.stock})")
        print(f"   - 3 clientes: Lucía Fernández (con perfil), Tomás Ríos, Ana Paz")
        print(f"   - 1 venta (#1) de Lucía por $69000.00")
        print(f"   - 7 movimientos de stock (invariante stock == SUM(cantidad) verificada)")
        print(f"   - 1 evento de seguridad de SISTEMA")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
