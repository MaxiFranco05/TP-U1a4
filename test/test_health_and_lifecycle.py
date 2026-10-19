from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import DEFAULT_UNCONFIGURED_URL, get_settings
from app.core.database import get_session
from app.main import app, create_app

EXPECTED_MODULES = (
    "health",
    "editoriales",
    "generos",
    "autores",
    "libros",
    "clientes",
    "ventas",
)


@pytest.mark.asyncio
async def test_lifespan_creates_engine_and_session_factory_and_disposes_on_shutdown() -> None:
    """Scenario: Single initialization & Clean shutdown (app-lifecycle)."""
    test_app = create_app()
    with patch("app.main.build_engine") as mock_build_engine:
        real_engine_mock = MagicMock(spec=AsyncEngine)
        real_engine_mock.dispose = AsyncMock()
        mock_build_engine.return_value = real_engine_mock

        async with test_app.router.lifespan_context(test_app):
            assert hasattr(test_app.state, "engine")
            assert hasattr(test_app.state, "session_factory")
            assert test_app.state.engine is real_engine_mock
            assert isinstance(test_app.state.session_factory, async_sessionmaker)
            assert test_app.state.session_factory.kw.get("expire_on_commit") is False
            mock_build_engine.assert_called_once()
            real_engine_mock.dispose.assert_not_awaited()

        # After exiting lifespan context, engine.dispose() must have been awaited once
        real_engine_mock.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_session_provides_isolated_session_per_request_and_closes_on_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Request isolation & Session cleanup (app-lifecycle)."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://nobody:wrong@127.0.0.1:59999/nonexistent_db",
    )
    test_app = create_app()
    async with test_app.router.lifespan_context(test_app):
        fake_request_1 = MagicMock(spec=Request)
        fake_request_1.app = test_app
        fake_request_2 = MagicMock(spec=Request)
        fake_request_2.app = test_app

        gen_1 = get_session(fake_request_1)
        gen_2 = get_session(fake_request_2)

        session_1 = await anext(gen_1)
        session_2 = await anext(gen_2)

        assert isinstance(session_1, AsyncSession)
        assert isinstance(session_2, AsyncSession)
        assert session_1 is not session_2, "Each request must receive an isolated session"
        assert session_1.sync_session.expire_on_commit is False
        assert session_2.sync_session.expire_on_commit is False

        with patch.object(session_1, "close", wraps=session_1.close) as spy_close_1:
            with pytest.raises(StopAsyncIteration):
                await anext(gen_1)
            spy_close_1.assert_awaited_once()

        with patch.object(session_2, "close", wraps=session_2.close) as spy_close_2:
            with pytest.raises(StopAsyncIteration):
                await anext(gen_2)
            spy_close_2.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_live_returns_200_vivo_without_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Alive without database (health)."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://nobody:wrong@127.0.0.1:59999/nonexistent_db",
    )
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"estado": "vivo"}


@pytest.mark.asyncio
async def test_health_ready_returns_200_when_database_responds() -> None:
    """Scenario: Ready with database (health)."""
    mock_session = AsyncMock(spec=AsyncSession)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield mock_session

    app.dependency_overrides[get_session] = override_get_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"estado": "listo"}
    mock_session.execute.assert_awaited_once()
    executed_clause = str(mock_session.execute.call_args[0][0])
    assert executed_clause.strip().upper() == "SELECT 1"


@pytest.mark.asyncio
async def test_health_ready_returns_503_without_leaking_internals_on_db_error() -> None:
    """Scenario: Not ready without database & RN-12 no internal details leaked (health)."""
    mock_session = AsyncMock(spec=AsyncSession)
    sensitive_internal_error = OperationalError(
        statement="SELECT 1 FROM secret_table WHERE constraint_name = 'uq_libro_isbn'",
        params={"secret": "super_secret_password_123"},
        orig=Exception(
            "FATAL: password authentication failed for user 'admin_prod' "
            "at postgresql+asyncpg://admin_prod:super_secret_password_123@10.0.0.42:5432/prod_db"
        ),
    )
    mock_session.execute.side_effect = sensitive_internal_error

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield mock_session

    app.dependency_overrides[get_session] = override_get_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    body_text = response.text
    assert response.json() == {"detail": "Base de datos no disponible"}
    for forbidden_fragment in (
        "secret_table",
        "uq_libro_isbn",
        "super_secret_password_123",
        "admin_prod",
        "postgresql+asyncpg",
        "OperationalError",
        "Traceback",
    ):
        assert forbidden_fragment not in body_text


@pytest.mark.asyncio
async def test_health_ready_fails_cleanly_when_database_url_missing_or_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Missing configuration / unreachable host via real lifespan & get_session."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = get_settings()
    assert settings.database_url == DEFAULT_UNCONFIGURED_URL

    test_app = create_app()
    async with test_app.router.lifespan_context(test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Base de datos no disponible"}
    assert "unconfigured" not in response.text
    assert "59999" not in response.text


def test_module_structure_and_env_example_have_no_secrets() -> None:
    """Scenario: No secrets in repo & 7-module architecture verification."""
    project_root = Path(__file__).resolve().parent.parent
    modules_dir = project_root / "app" / "modules"

    for module_name in EXPECTED_MODULES:
        mod_path = modules_dir / module_name
        assert mod_path.is_dir(), f"Missing module directory: {module_name}"
        for required_file in ("__init__.py", "models.py", "schemas.py", "service.py", "router.py"):
            assert (mod_path / required_file).is_file(), (
                f"Missing {required_file} in app/modules/{module_name}"
            )

    env_example = (project_root / "env.example").read_text(encoding="utf-8")
    assert "DATABASE_URL=" in env_example
    assert "SQL_ECHO=" in env_example
    assert "libreria_dev_local" not in env_example

    alembic_ini = (project_root / "alembic.ini").read_text(encoding="utf-8")
    assert "libreria_dev_local" not in alembic_ini
    assert "driver://user:pass" not in alembic_ini


@pytest.mark.asyncio
async def test_health_ready_integration_with_live_postgres() -> None:
    """Integration Scenario: Ready with live PostgreSQL 16 container via real lifespan and get_session."""
    test_app = create_app()
    async with test_app.router.lifespan_context(test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            live_resp = await client.get("/health/live")
            ready_resp = await client.get("/health/ready")

    assert live_resp.status_code == 200
    assert live_resp.json() == {"estado": "vivo"}
    assert ready_resp.status_code == 200
    assert ready_resp.json() == {"estado": "listo"}
