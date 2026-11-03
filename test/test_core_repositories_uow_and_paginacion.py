"""Tests unitarios y de integración bajo Strict TDD para C-11: repositorios base, UnitOfWork y paginación."""

from collections.abc import AsyncGenerator
from decimal import Decimal
import uuid
from unittest.mock import AsyncMock

from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.database import build_engine, build_session_factory
from app.core.paginacion import (
    Page,
    PaginatedResponse,
    PaginationParams,
    calcular_paginas,
    paginate,
    validar_pagina,
)
from app.core.repository import BaseRepository, SoftDeleteRepository
from app.core.unit_of_work import UnitOfWork
from app.modules.editoriales.models import Editorial
from app.modules.libros.models import Libro

EXPECTED_ALL_14_TABLES = {
    "editorial",
    "genero",
    "autor",
    "libro",
    "libro_autor",
    "cliente",
    "perfil_cliente",
    "venta",
    "renglon_venta",
    "usuario",
    "asignacion_rol",
    "intento_acceso",
    "evento_seguridad",
    "movimiento_stock",
}


@pytest.fixture
async def session_factory() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    """Provee la fábrica de sesiones contra PostgreSQL 16 y limpia las tablas al finalizar."""
    settings = get_settings()
    engine = build_engine(settings.database_url, sql_echo=False)
    factory = build_session_factory(engine)
    yield factory
    async with factory() as cleanup_session:
        res = await cleanup_session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
            )
        )
        existing_tables = {row[0] for row in res.fetchall()}
        if EXPECTED_ALL_14_TABLES.issubset(existing_tables):
            await cleanup_session.execute(
                text(
                    "TRUNCATE TABLE movimiento_stock, renglon_venta, venta, asignacion_rol, "
                    "intento_acceso, evento_seguridad, perfil_cliente, cliente, libro_autor, "
                    "libro, genero, autor, editorial, usuario RESTART IDENTITY CASCADE"
                )
            )
            await cleanup_session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_base_repository_add_update_delete_flush_without_commit(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Adding, updating and deleting an entity in BaseRepository flushes without committing."""
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        commit_spy = AsyncMock(wraps=session.commit)
        flush_spy = AsyncMock(wraps=session.flush)
        monkeypatch.setattr(session, "commit", commit_spy)
        monkeypatch.setattr(session, "flush", flush_spy)

        repo = BaseRepository(session, Editorial)
        editorial = Editorial(nombre=f"Editorial Base {suffix}", pais="Argentina")

        created = await repo.add(editorial)
        assert created.id is not None
        assert flush_spy.await_count >= 1
        assert commit_spy.await_count == 0

        # Verificar que desde otra sesión aún NO está confirmado (no hubo commit)
        async with session_factory() as other_session:
            other_repo = BaseRepository(other_session, Editorial)
            assert await other_repo.get_by_id(created.id) is None

        updated = await repo.update(created, {"pais": "Uruguay"})
        assert updated.pais == "Uruguay"
        assert commit_spy.await_count == 0

        await repo.delete(updated)
        assert await repo.get_by_id(created.id) is None
        assert commit_spy.await_count == 0
        await session.rollback()


@pytest.mark.asyncio
async def test_base_repository_get_by_id_get_all_and_count_with_filters_and_pagination(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Standard CRUD lookup (get_by_id, get_all, count) with filters and pagination on active session."""
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        commit_spy = AsyncMock(wraps=session.commit)
        monkeypatch.setattr(session, "commit", commit_spy)

        repo = BaseRepository(session, Editorial)
        e1 = await repo.add(Editorial(nombre=f"Alfa {suffix}", pais="Argentina"))
        e2 = await repo.add(Editorial(nombre=f"Beta {suffix}", pais="Chile"))
        e3 = await repo.add(Editorial(nombre=f"Gamma {suffix}", pais="Argentina"))

        assert e1.id is not None and e2.id is not None and e3.id is not None

        # Lookup por id existente e inexistente
        found = await repo.get_by_id(e2.id)
        assert found is not None
        assert found.nombre == f"Beta {suffix}"
        assert await repo.get_by_id(999999) is None

        # Count total y con filtro
        assert await repo.count() == 3
        assert await repo.count(filters=(Editorial.pais == "Argentina",)) == 2

        # get_all con offset/limit y filtros
        page_1 = await repo.get_all(offset=0, limit=2)
        assert [item.id for item in page_1] == [e1.id, e2.id]
        page_2 = await repo.get_all(offset=2, limit=2)
        assert [item.id for item in page_2] == [e3.id]

        arg_items = await repo.get_all(
            filters=(Editorial.pais == "Argentina",),
            order_by=Editorial.nombre.desc(),
        )
        assert [item.nombre for item in arg_items] == [
            f"Gamma {suffix}",
            f"Alfa {suffix}",
        ]

        assert commit_spy.await_count == 0
        await session.rollback()


def test_base_repository_does_not_expose_soft_delete_methods() -> None:
    """Scenario: BaseRepository does not expose soft_delete or get_by_id_including_deleted."""
    assert not hasattr(BaseRepository, "soft_delete")
    assert not hasattr(BaseRepository, "get_by_id_including_deleted")
    assert issubclass(SoftDeleteRepository, BaseRepository)


@pytest.mark.asyncio
async def test_soft_delete_repository_filters_deleted_and_supports_historical_lookup(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenarios: SoftDeleteRepository filters borrado_en IS NULL in get_by_id, get_all, count; soft_delete flushes UTC timestamp without commit; get_by_id_including_deleted returns deleted records."""
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        commit_spy = AsyncMock(wraps=session.commit)
        flush_spy = AsyncMock(wraps=session.flush)
        monkeypatch.setattr(session, "commit", commit_spy)
        monkeypatch.setattr(session, "flush", flush_spy)

        ed_repo = BaseRepository(session, Editorial)
        editorial = await ed_repo.add(
            Editorial(nombre=f"Ed Soft {suffix}", pais="Argentina")
        )
        assert editorial.id is not None

        libro_repo = SoftDeleteRepository(session, Libro)
        libro_1 = await libro_repo.add(
            Libro(
                isbn=f"978-SD1-{suffix}",
                titulo="Libro Activo 1",
                precio=Decimal("10000.00"),
                stock=5,
                editorial_id=editorial.id,
            )
        )
        libro_2 = await libro_repo.add(
            Libro(
                isbn=f"978-SD2-{suffix}",
                titulo="Libro A Borrar",
                precio=Decimal("12000.00"),
                stock=3,
                editorial_id=editorial.id,
            )
        )
        assert libro_1.id is not None and libro_2.id is not None
        libro_2_id = libro_2.id

        assert await libro_repo.count() == 2
        assert len(await libro_repo.get_all()) == 2

        # Ejecutar soft_delete sobre libro_2
        flush_count_before = flush_spy.await_count
        deleted = await libro_repo.soft_delete(libro_2)
        assert deleted.borrado_en is not None
        assert deleted.borrado_en.tzinfo is not None
        assert flush_spy.await_count > flush_count_before
        assert commit_spy.await_count == 0

        # get_by_id, get_all y count excluyen el libro con borrado_en IS NOT NULL
        assert await libro_repo.get_by_id(libro_2_id) is None
        assert await libro_repo.get_by_id(libro_1.id) is not None
        assert await libro_repo.count() == 1
        assert await libro_repo.count(filters=(Libro.editorial_id == editorial.id,)) == 1
        active_books = await libro_repo.get_all(
            filters=(Libro.editorial_id == editorial.id,)
        )
        assert [b.id for b in active_books] == [libro_1.id]

        # get_by_id_including_deleted recupera tanto el borrado como el activo
        historical = await libro_repo.get_by_id_including_deleted(libro_2_id)
        assert historical is not None
        assert historical.id == libro_2_id
        assert historical.borrado_en is not None
        assert await libro_repo.get_by_id_including_deleted(libro_1.id) is not None
        assert await libro_repo.get_by_id_including_deleted(999999) is None

        await session.rollback()


@pytest.mark.asyncio
async def test_unit_of_work_commits_on_clean_exit_and_never_closes_session(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Clean exit from async with uow: commits the shared session and never closes it."""
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        commit_spy = AsyncMock(wraps=session.commit)
        rollback_spy = AsyncMock(wraps=session.rollback)
        close_spy = AsyncMock(wraps=session.close)
        monkeypatch.setattr(session, "commit", commit_spy)
        monkeypatch.setattr(session, "rollback", rollback_spy)
        monkeypatch.setattr(session, "close", close_spy)

        uow = UnitOfWork(session)
        repo = BaseRepository(session, Editorial)

        async with uow as active_uow:
            assert active_uow is uow
            created = await repo.add(
                Editorial(nombre=f"Ed UoW Commit {suffix}", pais="Argentina")
            )
            assert created.id is not None
            created_id = created.id
            assert commit_spy.await_count == 0

        assert commit_spy.await_count == 1
        assert rollback_spy.await_count == 0
        assert close_spy.await_count == 0

        # Verificar desde una segunda sesión independiente que el cambio quedó persistido en PostgreSQL 16
        async with session_factory() as verify_session:
            verify_repo = BaseRepository(verify_session, Editorial)
            persisted = await verify_repo.get_by_id(created_id)
            assert persisted is not None
            assert persisted.nombre == f"Ed UoW Commit {suffix}"


@pytest.mark.asyncio
async def test_unit_of_work_rolls_back_flushed_changes_on_exception_and_never_closes_session(
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Exception inside async with uow: rolls back all flushed changes, does not close session, and propagates exception."""
    suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        commit_spy = AsyncMock(wraps=session.commit)
        rollback_spy = AsyncMock(wraps=session.rollback)
        close_spy = AsyncMock(wraps=session.close)
        monkeypatch.setattr(session, "commit", commit_spy)
        monkeypatch.setattr(session, "rollback", rollback_spy)
        monkeypatch.setattr(session, "close", close_spy)

        uow = UnitOfWork(session)
        repo = BaseRepository(session, Editorial)
        flushed_id: int | None = None

        with pytest.raises(RuntimeError, match="Fallo simulado mitad de operación"):
            async with uow:
                created = await repo.add(
                    Editorial(nombre=f"Ed UoW Rollback {suffix}", pais="Perú")
                )
                assert created.id is not None
                flushed_id = created.id
                raise RuntimeError("Fallo simulado mitad de operación")

        assert flushed_id is not None
        assert commit_spy.await_count == 0
        assert rollback_spy.await_count == 1
        assert close_spy.await_count == 0

        # Verificar que la fila con flush() fue revertida y no existe en PostgreSQL 16
        assert await repo.get_by_id(flushed_id) is None
        async with session_factory() as verify_session:
            verify_repo = BaseRepository(verify_session, Editorial)
            assert await verify_repo.get_by_id(flushed_id) is None


def test_calcular_paginas_and_paginate_envelope_and_bounds() -> None:
    """Scenarios: calcular_paginas and paginate return {items, total, page, size, pages}; total==0 -> pages==1; page > pages raises 422 with exact message."""
    assert Page is PaginatedResponse
    assert calcular_paginas(0, 20) == 1
    assert calcular_paginas(1, 20) == 1
    assert calcular_paginas(20, 20) == 1
    assert calcular_paginas(21, 20) == 2
    assert calcular_paginas(25, 10) == 3

    # Caso vacío en página 1: devuelve {items: [], total: 0, page: 1, size: 20, pages: 1}
    empty_res = paginate([], total=0, page=1, size=20)
    assert empty_res.model_dump() == {
        "items": [],
        "total": 0,
        "page": 1,
        "size": 20,
        "pages": 1,
    }

    # Caso vacío en página 2: 422 "La página 2 no existe: hay 1"
    with pytest.raises(HTTPException) as exc_empty_p2:
        paginate([], total=0, page=2, size=20)
    assert exc_empty_p2.value.status_code == 422
    assert exc_empty_p2.value.detail == "La página 2 no existe: hay 1"

    # Caso con datos (total=25, size=10 -> pages=3) en página 3 válida y página 4 inválida
    valid_p3 = paginate(["a", "b", "c", "d", "e"], total=25, page=3, size=10)
    assert valid_p3.model_dump() == {
        "items": ["a", "b", "c", "d", "e"],
        "total": 25,
        "page": 3,
        "size": 10,
        "pages": 3,
    }

    with pytest.raises(HTTPException) as exc_overflow:
        paginate([], total=25, page=4, size=10)
    assert exc_overflow.value.status_code == 422
    assert exc_overflow.value.detail == "La página 4 no existe: hay 3"

    # validar_pagina directo
    validar_pagina(1, 1)
    with pytest.raises(HTTPException) as exc_val:
        validar_pagina(5, 2)
    assert exc_val.value.status_code == 422
    assert exc_val.value.detail == "La página 5 no existe: hay 2"


@pytest.mark.asyncio
async def test_pagination_params_dependency_defaults_and_422_query_validation() -> None:
    """Scenarios: PaginationParams applies defaults page=1, size=20 (offset=0, limit=20) and rejects page < 1, size < 1, size > 100 with HTTP 422."""
    app = FastAPI()

    @app.get("/test-paginacion", response_model=PaginatedResponse[int])
    async def endpoint_paginado(
        params: PaginationParams = Depends(),
        total: int = 0,
    ) -> PaginatedResponse[int]:
        assert params.offset == (params.page - 1) * params.size
        assert params.limit == params.size
        items = list(range(params.offset, min(total, params.offset + params.limit)))
        return paginate(items, total=total, page=params.page, size=params.size)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Defaults sin parámetros (page=1, size=20, total=0 -> pages=1)
        r_default = await client.get("/test-paginacion")
        assert r_default.status_code == 200
        assert r_default.json() == {
            "items": [],
            "total": 0,
            "page": 1,
            "size": 20,
            "pages": 1,
        }

        # 2. Valores fuera de rango en query -> 422
        for bad_query in ("page=0", "page=-1", "size=0", "size=-5", "size=101"):
            r_bad = await client.get(f"/test-paginacion?{bad_query}")
            assert r_bad.status_code == 422, f"Esperaba 422 para {bad_query}"

        # 3. Página mayor a pages con total=0 -> 422 con detalle exacto
        r_p2_empty = await client.get("/test-paginacion?page=2&size=20&total=0")
        assert r_p2_empty.status_code == 422
        assert r_p2_empty.json()["detail"] == "La página 2 no existe: hay 1"

        # 4. Página mayor a pages con total=25 y size=10 -> 422 con detalle exacto
        r_p4 = await client.get("/test-paginacion?page=4&size=10&total=25")
        assert r_p4.status_code == 422
        assert r_p4.json()["detail"] == "La página 4 no existe: hay 3"


