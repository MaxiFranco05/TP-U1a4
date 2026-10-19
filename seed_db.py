"""Seed reproducible para TP-U1a4 (API Librería).

C-08: Deja el banco de datos en estado conocido para que los .http sean reproducibles.
Uso: python seed_db.py
Luego: correr los .http contra http://localhost:8000
"""

from decimal import Decimal
from sqlalchemy import insert
from sqlmodel import SQLModel

from app.core.database import engine, get_session
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.autores.models import Autor, LibroAutor
from app.modules.libros.models import Libro
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.ventas.models import Venta, RenglonVenta


def main() -> None:
    # Crear todas las tablas (idempotente si ya existen con Schema)
    SQLModel.metadata.create_all(engine)

    session = next(get_session.__wrapped__())  # get_session dependency

    # 1. Editoriales
    editoriales = [
        Editorial(nombre="Editorial Planeta", pais="Argentina"),
        Editorial(nombre="Editorial Sudamericana", pais="Uruguay"),
        Editorial(nombre="Penguin Random House", pais="EE.UU"),
    ]
    for e in editoriales:
        session.add(e)
    session.commit()

    # 2. Géneros
    generos = [
        Genero(nombre="Ficción"),
        Genero(nombre="No Ficción"),
        Genero(nombre="Ciencia Ficción"),
    ]
    for g in generos:
        session.add(g)
    session.commit()

    # 3. Autores
    autores = [
        Autor(nombre="Jorge Luis Borges", nacionalidad="Argentina"),
        Autor(nombre="Julio Cortázar", nacionalidad="Argentina"),
        Autor(nombre="Isabel Allende", nacionalidad="Chile"),
        Autor(nombre="Gabriel García Márquez", nacionalidad="Colombia"),
    ]
    for a in autores:
        session.add(a)
    session.commit()

    # 4. Libro-Autor associations (with roles and order)
    autoria_data = [
        # Borges books
        (1, 1, "autor", 1),  # Borges - Libro 1
        (1, 2, "coautor", 2),  # Borges - Libro 2
        # Cortázar books
        (2, 3, "autor", 1),  # Cortázar - Libro 3
        # Allende books
        (3, 4, "autor", 1),  # Allende - Libro 4
        (3, 5, "coautor", 2),  # Allende - Libro 5
        # García Márquez books
        (4, 6, "autor", 1),  # García Márquez - Libro 6
        (4, 5, "traductor", 1),  # García Márquez - Libro 7 (already author 5, now translator)
    ]
    for autor_id, libro_id, rol, orden in autoria_data:
        session.add(LibroAutor(libro_id=libro_id, autor_id=autor_id, rol=rol, orden=orden))
    session.commit()

    # 5. Libros
    libros = [
        Libro(
            isbn="978-950-12-3456-7",
            titulo="El Aleph",
            precio=Decimal("45.00"),
            stock=15,
            editorial_id=1,
            genero_id=1,
        ),
        Libro(
            isbn="978-950-12-3456-8",
            titulo="Rayuela",
            precio=Decimal("55.00"),
            stock=10,
            editorial_id=1,
            genero_id=1,
        ),
        Libro(
            isbn="978-950-12-3456-9",
            titulo="La casa de los espíritus",
            precio=Decimal("38.50"),
            stock=20,
            editorial_id=2,
            genero_id=1,
        ),
        Libro(
            isbn="978-950-12-3457-0",
            titulo="Cien años de soledad",
            precio=Decimal("42.00"),
            stock=25,
            editorial_id=3,
            genero_id=2,
        ),
        Libro(
            isbn="978-950-12-3457-1",
            titulo="El examen",
            precio=Decimal("30.00"),
            stock=12,
            editorial_id=2,
            genero_id=1,
        ),
    ]
    for l in libros:
        session.add(l)
    session.commit()
    # Re-fetch IDs after commit
    session.expire_all()

    # Reload autores-libro associations after commit
    from app.modules.libros.models import LibroAutor as LA
    existing = session.query(LA).all()

    # 6. Cliente con perfil único
    cliente = Cliente(nombre="María García", email="maria.garcia@test.com")
    session.add(cliente)
    session.commit()
    session.refresh(cliente)

    perfil = PerfilCliente(
        cliente_id=cliente.id,
        telefono="+54 9 11 1234-5678",
        dirección="Calle Falsa 123, Buenos Aires, Argentina",
    )
    session.add(perfil)
    session.commit()

    # 7. Venta de ejemplo (con renglones)
    # Usamos los libros que creamos: El Aleph (id=1), Rayuela (id=2)
    renglones = [
        RenglonVenta(
            libro_id=1,
            cantidad=2,
            precio_unitario=libros[0].precio,  # El Aleph $45.00
        ),
        RenglonVenta(
            libro_id=2,
            cantidad=1,
            precio_unitario=libros[1].precio,  # Rayuela $55.00
        ),
    ]
    total = Decimal("0")
    for r in renglones:
        total += Decimal(str(r.cantidad)) * r.precio_unitario

    venta = Venta(
        cliente_id=cliente.id,
        total=total,
        renglones=renglones,
    )
    session.add(venta)
    session.commit()

    print("✅ Seed completado exitosamente")
    print(f"   - {len(editoriales)} editoriales")
    print(f"   - {len(generos)} géneros")
    print(f"   - {len(autores)} autores")
    print(f"   - {len(libros)} libros")
    print(f"   - 1 cliente con perfil")
    print(f"   - 1 venta de ejemplo con {len(renglones)} renglones")
    session.close()


if __name__ == "__main__":
    main()