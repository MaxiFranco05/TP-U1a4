"""Tests de integración para C-02: modelos core del dominio y migración 001."""

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import uuid

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import SQLModel

from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro, LibroAutor
from app.modules.ventas.models import RenglonVenta, Venta

EXPECTED_CORE_TABLES = {
    "editorial",
    "autor",
    "libro",
    "libro_autor",
    "cliente",
    "perfil_cliente",
    "venta",
    "renglon_venta",
}


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provee una sesión asincrónica conectada a PostgreSQL 16 y limpia los datos de prueba al salir."""
    settings = get_settings()
    engine = build_engine(settings.database_url, sql_echo=False)
    session_factory = build_session_factory(engine)
    async with session_factory() as session:
        yield session
        await session.rollback()
        # Limpieza ordenada respetando FKs
        await session.execute(delete(RenglonVenta))
        await session.execute(delete(Venta))
        await session.execute(delete(PerfilCliente))
        await session.execute(delete(Cliente))
        await session.execute(delete(LibroAutor))
        await session.execute(delete(Libro))
        await session.execute(delete(Autor))
        await session.execute(delete(Editorial))
        await session.commit()
    await engine.dispose()


def test_sqlmodel_metadata_registers_8_core_tables_without_genero() -> None:
    """Scenario: SQLModel.metadata registra las 8 tablas core iniciales."""
    registered_tables = set(SQLModel.metadata.tables.keys())
    assert EXPECTED_CORE_TABLES.issubset(registered_tables)
    libro_columns = set(SQLModel.metadata.tables["libro"].columns.keys())
    assert {"id", "isbn", "titulo", "precio", "stock", "editorial_id"}.issubset(libro_columns)


def test_migration_001_file_exists_and_is_reviewed() -> None:
    """Scenario: Existe la revisión 001 en migrations/versions/ sin genero y con constancia de revisión manual."""
    versions_dir = Path(__file__).resolve().parent.parent / "migrations" / "versions"
    migration_files = sorted(f for f in versions_dir.glob("*.py") if "001" in f.name)
    assert len(migration_files) == 1, "Debe existir la migración 001 en migrations/versions/"
    content = migration_files[0].read_text(encoding="utf-8")
    assert "Revisión manual" in content or "Revision manual" in content
    for table_name in EXPECTED_CORE_TABLES:
        assert f'"{table_name}"' in content or f"'{table_name}'" in content
    assert "create_table('genero'" not in content


@pytest.mark.asyncio
async def test_database_schema_has_8_core_tables_and_explicit_fk_indexes(
    db_session: AsyncSession,
) -> None:
    """Scenario: Upgrade head includes the 8 core tables and their explicit FK indexes."""
    result = await db_session.execute(
        text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename != 'alembic_version'"
        )
    )
    db_tables = {row[0] for row in result.fetchall()}
    assert EXPECTED_CORE_TABLES.issubset(db_tables)

    idx_result = await db_session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE schemaname = 'public'")
    )
    index_defs = "\n".join(row[0] for row in idx_result.fetchall())
    for fk_col in ("editorial_id", "libro_id", "autor_id", "cliente_id", "venta_id"):
        assert f"({fk_col})" in index_defs, f"Falta índice explícito para FK {fk_col}"



@pytest.mark.asyncio
async def test_catalog_client_sales_persistence_and_bidirectional_navigation(
    db_session: AsyncSession,
) -> None:
    """Scenarios: Valid catalog/client/sales persistence, Decimal & TIMESTAMPTZ, libro.autorias[i].autor & cliente.perfil."""
    suffix = uuid.uuid4().hex[:8]
    editorial = Editorial(nombre=f"Editorial Sudamericana {suffix}", pais="Argentina")
    autor = Autor(nombre=f"Julio Cortázar {suffix}", nacionalidad="Argentina")
    db_session.add_all([editorial, autor])
    await db_session.flush()

    assert editorial.id is not None
    assert autor.id is not None

    libro = Libro(
        isbn=f"978-950-07-{suffix[:4]}",
        titulo="Rayuela",
        precio=Decimal("24500.50"),
        stock=15,
        editorial_id=editorial.id,
    )
    db_session.add(libro)
    await db_session.flush()
    assert libro.id is not None

    autoria = LibroAutor(
        libro_id=libro.id,
        autor_id=autor.id,
        rol="autor",
        orden=1,
    )
    cliente = Cliente(
        nombre="María Elena Walsh",
        email=f"maria.{suffix}@example.com",
    )
    db_session.add_all([autoria, cliente])
    await db_session.flush()
    assert cliente.id is not None

    perfil = PerfilCliente(
        cliente_id=cliente.id,
        telefono="+54 11 4444-5555",
        direccion="Av. Corrientes 1234, CABA",
    )
    fecha_venta = datetime(2026, 10, 17, 15, 30, 0, tzinfo=timezone.utc)
    venta = Venta(
        cliente_id=cliente.id,
        fecha=fecha_venta,
        total=Decimal("49001.00"),
    )
    db_session.add_all([perfil, venta])
    await db_session.flush()
    assert venta.id is not None

    renglon = RenglonVenta(
        venta_id=venta.id,
        libro_id=libro.id,
        cantidad=2,
        precio_unitario=Decimal("24500.50"),
    )
    db_session.add(renglon)
    await db_session.commit()

    # Verificar lectura con eager loading (sin lazy loading)
    stmt_libro = (
        select(Libro)
        .where(Libro.id == libro.id)
        .options(
            joinedload(Libro.editorial),
            selectinload(Libro.autorias).joinedload(LibroAutor.autor),
        )
    )
    loaded_libro = (await db_session.execute(stmt_libro)).scalar_one()
    assert isinstance(loaded_libro.precio, Decimal)
    assert loaded_libro.precio == Decimal("24500.50")
    assert loaded_libro.editorial.nombre == editorial.nombre
    assert len(loaded_libro.autorias) == 1
    assert loaded_libro.autorias[0].autor.nombre == autor.nombre
    assert loaded_libro.autorias[0].rol == "autor"
    assert loaded_libro.autorias[0].orden == 1

    # Verificar Cliente.perfil devuelve un objeto único (no lista)
    stmt_cliente = (
        select(Cliente)
        .where(Cliente.id == cliente.id)
        .options(joinedload(Cliente.perfil), selectinload(Cliente.ventas))
    )
    loaded_cliente = (await db_session.execute(stmt_cliente)).scalar_one()
    assert loaded_cliente.perfil is not None
    assert not isinstance(loaded_cliente.perfil, list)
    assert isinstance(loaded_cliente.perfil, PerfilCliente)
    assert loaded_cliente.perfil.direccion == "Av. Corrientes 1234, CABA"

    # Verificar Venta y RenglonVenta con TIMESTAMPTZ y Decimal
    stmt_venta = (
        select(Venta)
        .where(Venta.id == venta.id)
        .options(
            joinedload(Venta.cliente),
            selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
        )
    )
    loaded_venta = (await db_session.execute(stmt_venta)).scalar_one()
    assert isinstance(loaded_venta.total, Decimal)
    assert loaded_venta.total == Decimal("49001.00")
    assert loaded_venta.fecha.tzinfo is not None
    assert len(loaded_venta.renglones) == 1
    assert isinstance(loaded_venta.renglones[0].precio_unitario, Decimal)
    assert loaded_venta.renglones[0].precio_unitario == Decimal("24500.50")
    assert loaded_venta.renglones[0].libro.isbn == libro.isbn


@pytest.mark.asyncio
async def test_unique_constraints_rejected_by_database(db_session: AsyncSession) -> None:
    """Scenarios: Duplicate editorial.nombre, libro.isbn (RN-01), cliente.email (RN-02), perfil_cliente.cliente_id (RN-09)."""
    suffix = uuid.uuid4().hex[:8]
    ed1 = Editorial(nombre=f"Planeta {suffix}", pais="España")
    db_session.add(ed1)
    await db_session.commit()
    assert ed1.id is not None
    ed1_id = ed1.id

    # 1. Duplicate editorial.nombre
    db_session.add(Editorial(nombre=f"Planeta {suffix}", pais="Argentina"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # 2. Duplicate libro.isbn (RN-01)
    libro1 = Libro(
        isbn=f"978-84-{suffix}",
        titulo="Libro Uno",
        precio=Decimal("100.00"),
        stock=5,
        editorial_id=ed1_id,
    )
    db_session.add(libro1)
    await db_session.commit()

    db_session.add(
        Libro(
            isbn=f"978-84-{suffix}",
            titulo="Libro Dos Mismo ISBN",
            precio=Decimal("200.00"),
            stock=3,
            editorial_id=ed1_id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # 3. Duplicate cliente.email (RN-02)
    cli1 = Cliente(nombre="Cliente 1", email=f"unico.{suffix}@test.com")
    db_session.add(cli1)
    await db_session.commit()
    assert cli1.id is not None
    cli1_id = cli1.id

    db_session.add(Cliente(nombre="Cliente 2", email=f"unico.{suffix}@test.com"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # 4. Duplicate perfil_cliente.cliente_id (RN-09)
    p1 = PerfilCliente(cliente_id=cli1_id, telefono="111", direccion="Dir 1")
    db_session.add(p1)
    await db_session.commit()

    db_session.add(PerfilCliente(cliente_id=cli1_id, telefono="222", direccion="Dir 2"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_check_constraints_rejected_by_database(db_session: AsyncSession) -> None:
    """Scenarios: Invalid precio, stock (RN-03), orden, rol, total, cantidad, precio_unitario rejected by CHECK."""
    suffix = uuid.uuid4().hex[:8]
    editorial = Editorial(nombre=f"Anagrama {suffix}", pais="España")
    autor = Autor(nombre=f"Roberto Bolaño {suffix}", nacionalidad="Chile")
    cliente = Cliente(nombre="Lector", email=f"lector.{suffix}@test.com")
    db_session.add_all([editorial, autor, cliente])
    await db_session.commit()
    assert editorial.id is not None
    assert autor.id is not None
    assert cliente.id is not None
    editorial_id = editorial.id
    autor_id = autor.id
    cliente_id = cliente.id

    # 1. libro.precio <= 0 (RN-03)
    db_session.add(
        Libro(
            isbn=f"ISBN-P0-{suffix}",
            titulo="Precio Cero",
            precio=Decimal("0.00"),
            stock=1,
            editorial_id=editorial_id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # 2. libro.stock < 0 (RN-03)
    db_session.add(
        Libro(
            isbn=f"ISBN-S0-{suffix}",
            titulo="Stock Negativo",
            precio=Decimal("10.00"),
            stock=-1,
            editorial_id=editorial_id,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # Crear libro válido para probar LibroAutor y RenglonVenta
    libro_valido = Libro(
        isbn=f"ISBN-OK-{suffix}",
        titulo="Los detectives salvajes",
        precio=Decimal("15000.00"),
        stock=10,
        editorial_id=editorial_id,
    )
    db_session.add(libro_valido)
    await db_session.commit()
    assert libro_valido.id is not None
    libro_valido_id = libro_valido.id

    # 3. libro_autor.orden < 1
    db_session.add(
        LibroAutor(
            libro_id=libro_valido_id,
            autor_id=autor_id,
            rol="autor",
            orden=0,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # 4. libro_autor.rol fuera de ('autor', 'coautor', 'traductor', 'ilustrador')
    db_session.add(
        LibroAutor(
            libro_id=libro_valido_id,
            autor_id=autor_id,
            rol="prologuista_invalido",
            orden=1,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # 5. venta.total < 0
    db_session.add(
        Venta(
            cliente_id=cliente_id,
            fecha=datetime.now(timezone.utc),
            total=Decimal("-0.01"),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    venta_valida = Venta(
        cliente_id=cliente_id,
        fecha=datetime.now(timezone.utc),
        total=Decimal("15000.00"),
    )
    db_session.add(venta_valida)
    await db_session.commit()
    assert venta_valida.id is not None
    venta_valida_id = venta_valida.id

    # 6. renglon_venta.cantidad <= 0
    db_session.add(
        RenglonVenta(
            venta_id=venta_valida_id,
            libro_id=libro_valido_id,
            cantidad=0,
            precio_unitario=Decimal("15000.00"),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    # 7. renglon_venta.precio_unitario <= 0
    db_session.add(
        RenglonVenta(
            venta_id=venta_valida_id,
            libro_id=libro_valido_id,
            cantidad=1,
            precio_unitario=Decimal("0.00"),
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_composite_pk_and_foreign_key_constraints_rejected_by_database(
    db_session: AsyncSession,
) -> None:
    """Scenario: Duplicate (libro_id, autor_id) pair and nonexistent FKs are rejected by PostgreSQL."""
    suffix = uuid.uuid4().hex[:8]
    editorial = Editorial(nombre=f"Tusquets {suffix}", pais="España")
    autor = Autor(nombre=f"Haruki Murakami {suffix}", nacionalidad="Japón")
    db_session.add_all([editorial, autor])
    await db_session.commit()
    assert editorial.id is not None
    assert autor.id is not None
    editorial_id = editorial.id
    autor_id = autor.id

    libro = Libro(
        isbn=f"ISBN-PK-{suffix}",
        titulo="Kafka en la orilla",
        precio=Decimal("18000.00"),
        stock=4,
        editorial_id=editorial_id,
    )
    db_session.add(libro)
    await db_session.commit()
    assert libro.id is not None
    libro_id = libro.id

    autoria_1 = LibroAutor(
        libro_id=libro_id,
        autor_id=autor_id,
        rol="autor",
        orden=1,
    )
    db_session.add(autoria_1)
    await db_session.commit()

    # Duplicate composite PK (libro_id, autor_id) in new session state
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text(
                "INSERT INTO libro_autor (libro_id, autor_id, rol, orden) "
                "VALUES (:libro_id, :autor_id, 'coautor', 2)"
            ),
            {"libro_id": libro_id, "autor_id": autor_id},
        )
    await db_session.rollback()


    # Nonexistent FK editorial_id
    db_session.add(
        Libro(
            isbn=f"ISBN-FK-{suffix}",
            titulo="Huérfano",
            precio=Decimal("100.00"),
            stock=1,
            editorial_id=99999999,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


