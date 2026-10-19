"""Tests de integración bajo Strict TDD para C-03: entidad Genero, migración 002 y endpoints /generos."""

from collections.abc import AsyncGenerator
from decimal import Decimal
from pathlib import Path
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import SQLModel

from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
from app.main import create_app
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor
from app.modules.ventas.models import RenglonVenta, Venta

EXPECTED_ALL_9_TABLES = {
    "editorial",
    "genero",
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
    """Provee una sesión asincrónica conectada a PostgreSQL 16 y limpia los datos al finalizar."""
    settings = get_settings()
    engine = build_engine(settings.database_url, sql_echo=False)
    session_factory = build_session_factory(engine)
    async with session_factory() as session:
        yield session
        await session.rollback()
        await session.execute(delete(RenglonVenta))
        await session.execute(delete(Venta))
        await session.execute(delete(PerfilCliente))
        await session.execute(delete(Cliente))
        await session.execute(delete(LibroAutor))
        await session.execute(delete(Libro))
        await session.execute(delete(Genero))
        await session.execute(delete(Autor))
        await session.execute(delete(Editorial))
        await session.commit()
    await engine.dispose()


def test_sqlmodel_metadata_registers_genero_and_libro_genero_id() -> None:
    """Scenario: SQLModel.metadata registra la tabla genero y la FK opcional libro.genero_id."""
    registered_tables = set(SQLModel.metadata.tables.keys())
    assert EXPECTED_ALL_9_TABLES.issubset(registered_tables)
    genero_cols = set(SQLModel.metadata.tables["genero"].columns.keys())
    assert {"id", "nombre"} == genero_cols

    libro_table = SQLModel.metadata.tables["libro"]
    assert "genero_id" in libro_table.columns
    assert libro_table.columns["genero_id"].nullable is True


def test_migration_002_file_exists_and_is_reviewed() -> None:
    """Scenario: Existen al menos 2 migraciones en migrations/versions/ y la 002 documenta su revisión manual."""
    versions_dir = Path(__file__).resolve().parent.parent / "migrations" / "versions"
    migration_files = sorted(versions_dir.glob("*.py"))
    assert len(migration_files) >= 2, (
        "Deben existir al menos 2 migraciones en migrations/versions/ (Ej. 3)"
    )
    mig_002 = [f for f in migration_files if "002" in f.name]
    assert len(mig_002) == 1, "Debe existir el archivo de la migración 002"
    content = mig_002[0].read_text(encoding="utf-8")
    assert "Revisión manual" in content or "Revision manual" in content
    assert "genero" in content
    assert "genero_id" in content
    assert "ix_libro_genero_id" in content


@pytest.mark.asyncio
async def test_database_schema_at_head_has_all_9_tables_and_genero_fk_index(
    db_session: AsyncSession,
) -> None:
    """Scenario: En head (migración 002) existen las 9 tablas y el índice explícito ix_libro_genero_id."""
    result = await db_session.execute(
        text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
        )
    )
    db_tables = {row[0] for row in result.fetchall()}
    assert db_tables == EXPECTED_ALL_9_TABLES

    col_result = await db_session.execute(
        text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'libro' AND column_name = 'genero_id'"
        )
    )
    row = col_result.fetchone()
    assert row is not None
    assert row[0] == "YES"

    idx_result = await db_session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'libro'")
    )
    libro_indexes = "\n".join(r[0] for r in idx_result.fetchall())
    assert "(genero_id)" in libro_indexes


@pytest.mark.asyncio
async def test_genero_and_libro_optional_relationship_and_unique_constraint(
    db_session: AsyncSession,
) -> None:
    """Scenarios: Book persists with or without a genre and navigates bidirectionally; duplicate genero.nombre rejected."""
    suffix = uuid.uuid4().hex[:8]
    editorial = Editorial(nombre=f"Minotauro {suffix}", pais="Argentina")
    genero = Genero(nombre=f"Ciencia Ficción {suffix}")
    db_session.add_all([editorial, genero])
    await db_session.commit()
    assert editorial.id is not None
    assert genero.id is not None
    editorial_id = editorial.id
    genero_id = genero.id

    libro_con_genero = Libro(
        isbn=f"978-CF-1-{suffix}",
        titulo="Fundación",
        precio=Decimal("19500.00"),
        stock=8,
        editorial_id=editorial_id,
        genero_id=genero_id,
    )
    libro_sin_genero = Libro(
        isbn=f"978-SG-2-{suffix}",
        titulo="Libro Sin Clasificar",
        precio=Decimal("12000.00"),
        stock=3,
        editorial_id=editorial_id,
        genero_id=None,
    )
    db_session.add_all([libro_con_genero, libro_sin_genero])
    await db_session.commit()

    stmt_con = (
        select(Libro).where(Libro.id == libro_con_genero.id).options(joinedload(Libro.genero))
    )
    loaded_con = (await db_session.execute(stmt_con)).scalar_one()
    assert loaded_con.genero is not None
    assert loaded_con.genero.nombre == f"Ciencia Ficción {suffix}"

    stmt_sin = (
        select(Libro).where(Libro.id == libro_sin_genero.id).options(joinedload(Libro.genero))
    )
    loaded_sin = (await db_session.execute(stmt_sin)).scalar_one()
    assert loaded_sin.genero is None

    stmt_gen = select(Genero).where(Genero.id == genero_id).options(selectinload(Genero.libros))
    loaded_gen = (await db_session.execute(stmt_gen)).scalar_one()
    assert [b.isbn for b in loaded_gen.libros] == [f"978-CF-1-{suffix}"]

    # Duplicate genero.nombre rejected at DB level
    db_session.add(Genero(nombre=f"Ciencia Ficción {suffix}"))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_post_generos_201_409_rn12_and_422(db_session: AsyncSession) -> None:
    """Scenarios: Create genre 201, duplicate name 409 without DB internals (RN-12), invalid payload 422."""
    suffix = uuid.uuid4().hex[:8]
    test_app = create_app()
    async with test_app.router.lifespan_context(test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. 201 Created
            resp_201 = await client.post("/generos/", json={"nombre": f"Fantasía {suffix}"})
            assert resp_201.status_code == 201
            data_201 = resp_201.json()
            assert isinstance(data_201["id"], int)
            assert data_201["nombre"] == f"Fantasía {suffix}"

            # 2. 409 Conflict on duplicate nombre (RN-12: no DB internals leaked)
            resp_409 = await client.post("/generos/", json={"nombre": f"Fantasía {suffix}"})
            assert resp_409.status_code == 409
            body_text = resp_409.text
            for forbidden in (
                "UniqueViolationError",
                "IntegrityError",
                "genero_nombre_key",
                "INSERT INTO",
                "Traceback",
                "asyncpg",
            ):
                assert forbidden not in body_text

            # 3. 422 Unprocessable Entity on empty / blank / missing nombre
            for invalid_payload in ({}, {"nombre": ""}, {"nombre": "   "}):
                resp_422 = await client.post("/generos/", json=invalid_payload)
                assert resp_422.status_code == 422


@pytest.mark.asyncio
async def test_get_generos_pagination_and_rn10_bounds(db_session: AsyncSession) -> None:
    """Scenario: Paginated genre list respects RN-10 bounds (limit 1..100 default 20, offset >= 0)."""
    suffix = uuid.uuid4().hex[:8]
    test_app = create_app()
    async with test_app.router.lifespan_context(test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for idx in range(3):
                r = await client.post("/generos/", json={"nombre": f"Gen {suffix} {idx}"})
                assert r.status_code == 201

            resp_page_1 = await client.get("/generos/?limit=2&offset=0")
            assert resp_page_1.status_code == 200
            assert len(resp_page_1.json()) == 2

            resp_page_2 = await client.get("/generos/?limit=2&offset=2")
            assert resp_page_2.status_code == 200
            assert len(resp_page_2.json()) >= 1

            for invalid_query in ("limit=0", "limit=101", "offset=-1"):
                resp_422 = await client.get(f"/generos/?{invalid_query}")
                assert resp_422.status_code == 422


@pytest.mark.asyncio
async def test_get_and_patch_genero_by_id_200_404_409_exclude_unset(
    db_session: AsyncSession,
) -> None:
    """Scenario: Genre detail and partial update handle existing, missing, and conflicting records."""
    suffix = uuid.uuid4().hex[:8]
    test_app = create_app()
    async with test_app.router.lifespan_context(test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r1 = await client.post("/generos/", json={"nombre": f"Policial {suffix}"})
            r2 = await client.post("/generos/", json={"nombre": f"Terror {suffix}"})
            id_1 = r1.json()["id"]
            id_2 = r2.json()["id"]

            # GET by ID -> 200
            get_ok = await client.get(f"/generos/{id_1}")
            assert get_ok.status_code == 200
            assert get_ok.json() == {"id": id_1, "nombre": f"Policial {suffix}"}

            # GET missing -> 404
            get_404 = await client.get("/generos/99999999")
            assert get_404.status_code == 404

            # PATCH with empty body (exclude_unset=True) preserves existing nombre -> 200
            patch_noop = await client.patch(f"/generos/{id_1}", json={})
            assert patch_noop.status_code == 200
            assert patch_noop.json() == {"id": id_1, "nombre": f"Policial {suffix}"}

            # PATCH updating nombre -> 200
            patch_ok = await client.patch(
                f"/generos/{id_1}",
                json={"nombre": f"Novela Negra {suffix}"},
            )
            assert patch_ok.status_code == 200
            assert patch_ok.json() == {"id": id_1, "nombre": f"Novela Negra {suffix}"}

            # PATCH missing -> 404
            patch_404 = await client.patch(
                "/generos/99999999",
                json={"nombre": f"Inexistente {suffix}"},
            )
            assert patch_404.status_code == 404

            # PATCH colliding with existing nombre -> 409 without DB internals (RN-12)
            patch_409 = await client.patch(
                f"/generos/{id_2}",
                json={"nombre": f"Novela Negra {suffix}"},
            )
            assert patch_409.status_code == 409
            assert "genero_nombre_key" not in patch_409.text
            assert "IntegrityError" not in patch_409.text


@pytest.mark.asyncio
async def test_get_generos_id_libros_paginated_and_404(db_session: AsyncSession) -> None:
    """Scenario: List books for an existing genre (paginated per RN-10) and 404 when genre missing."""
    suffix = uuid.uuid4().hex[:8]
    editorial = Editorial(nombre=f"Alfaguara {suffix}", pais="España")
    gen_con_libros = Genero(nombre=f"Ensayo {suffix}")
    gen_vacio = Genero(nombre=f"Poesía {suffix}")
    db_session.add_all([editorial, gen_con_libros, gen_vacio])
    await db_session.commit()
    assert editorial.id is not None
    assert gen_con_libros.id is not None
    assert gen_vacio.id is not None

    for idx in range(3):
        db_session.add(
            Libro(
                isbn=f"978-ENS-{idx}-{suffix}",
                titulo=f"Ensayo {idx}",
                precio=Decimal("14000.00"),
                stock=5,
                editorial_id=editorial.id,
                genero_id=gen_con_libros.id,
            )
        )
    db_session.commit_id_con = gen_con_libros.id
    id_vacio = gen_vacio.id
    await db_session.commit()

    test_app = create_app()
    async with test_app.router.lifespan_context(test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Page 1 (limit=2, offset=0) -> 2 books
            resp_p1 = await client.get(
                f"/generos/{db_session.commit_id_con}/libros?limit=2&offset=0"
            )
            assert resp_p1.status_code == 200
            books_p1 = resp_p1.json()
            assert len(books_p1) == 2
            assert all(b["genero_id"] == db_session.commit_id_con for b in books_p1)

            # Page 2 (limit=2, offset=2) -> 1 book
            resp_p2 = await client.get(
                f"/generos/{db_session.commit_id_con}/libros?limit=2&offset=2"
            )
            assert resp_p2.status_code == 200
            assert len(resp_p2.json()) == 1

            # Empty genre -> 200 []
            resp_empty = await client.get(f"/generos/{id_vacio}/libros")
            assert resp_empty.status_code == 200
            assert resp_empty.json() == []

            # Nonexistent genre -> 404
            resp_404 = await client.get("/generos/99999999/libros")
            assert resp_404.status_code == 404

            # Invalid pagination -> 422 (RN-10)
            for bad_q in ("limit=0", "limit=101", "offset=-1"):
                resp_422 = await client.get(f"/generos/{db_session.commit_id_con}/libros?{bad_q}")
                assert resp_422.status_code == 422
