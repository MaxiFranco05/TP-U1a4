from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
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


def test_settings_raises_validation_error_when_postgres_password_missing_or_blank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Missing configuration — POSTGRES_PASSWORD has no default and rejects empty strings."""
    monkeypatch.setenv("JWT_SECRET", "test_secret_key_for_unit_test_32b")
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]

    monkeypatch.setenv("POSTGRES_PASSWORD", "   ")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_raises_validation_error_when_jwt_secret_missing_or_blank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Missing configuration — JWT_SECRET has no default and rejects empty strings."""
    monkeypatch.setenv("POSTGRES_PASSWORD", "valid_test_password")
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]

    monkeypatch.setenv("JWT_SECRET", "   ")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_computes_database_url_and_exposes_expected_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Database URL computed from POSTGRES variables & defaults exposed."""
    monkeypatch.setenv("POSTGRES_USER", "libreria_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "s3cr3t@pass")
    monkeypatch.setenv("POSTGRES_DB", "libreria_test")
    monkeypatch.setenv("POSTGRES_HOST", "db.internal")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("JWT_SECRET", "super_secret_jwt_key_with_32_chars")
    for optional_var in (
        "JWT_EXPIRATION_SECONDS",
        "BCRYPT_ROUNDS",
        "COOKIE_SECURE",
        "DB_POOL_SIZE",
        "SQL_ECHO",
    ):
        monkeypatch.delenv(optional_var, raising=False)

    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert (
        settings.DATABASE_URL
        == "postgresql+asyncpg://libreria_user:s3cr3t%40pass@db.internal:5433/libreria_test"
    )
    assert settings.database_url == settings.DATABASE_URL
    assert settings.JWT_EXPIRATION_SECONDS == 1800
    assert settings.BCRYPT_ROUNDS == 12
    assert settings.COOKIE_SECURE is False
    assert settings.DB_POOL_SIZE == 5
    assert settings.SQL_ECHO is False
    assert settings.sql_echo is False


@pytest.mark.asyncio
async def test_lifespan_creates_engine_and_session_factory_and_disposes_on_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Single initialization & Clean shutdown (app-lifecycle)."""
    import asyncio
    import bcrypt

    monkeypatch.setenv("DB_POOL_SIZE", "9")
    monkeypatch.setenv("SQL_ECHO", "true")
    monkeypatch.setenv("BCRYPT_ROUNDS", "4")

    test_app = create_app()
    with (
        patch("app.main.build_engine") as mock_build_engine,
        patch("app.main.asyncio.to_thread", wraps=asyncio.to_thread) as spy_to_thread,
    ):
        real_engine_mock = MagicMock(spec=AsyncEngine)
        real_engine_mock.dispose = AsyncMock()
        mock_build_engine.return_value = real_engine_mock

        async with test_app.router.lifespan_context(test_app):
            assert hasattr(test_app.state, "engine")
            assert hasattr(test_app.state, "session_factory")
            assert hasattr(test_app.state, "dummy_password_hash")
            assert test_app.state.engine is real_engine_mock
            assert isinstance(test_app.state.session_factory, async_sessionmaker)
            assert test_app.state.session_factory.kw.get("expire_on_commit") is False

            expected_settings = get_settings()
            mock_build_engine.assert_called_once_with(
                database_url=expected_settings.DATABASE_URL,
                sql_echo=True,
                pool_size=9,
            )

            dummy_hash = test_app.state.dummy_password_hash
            dummy_hash_bytes = (
                dummy_hash.encode("utf-8") if isinstance(dummy_hash, str) else dummy_hash
            )
            assert dummy_hash_bytes.startswith(b"$2b$04$")
            assert bcrypt.checkpw(b"dummy-timing-defense-password", dummy_hash_bytes)
            assert not bcrypt.checkpw(b"any-other-password", dummy_hash_bytes)
            spy_to_thread.assert_awaited_once()
            real_engine_mock.dispose.assert_not_awaited()

        # After exiting lifespan context, engine.dispose() must have been awaited once
        real_engine_mock.dispose.assert_awaited_once()


def test_lifespan_build_engine_forwards_pool_size_and_echo() -> None:
    """Scenario: build_engine configures create_async_engine with pool_size and echo."""
    from app.core.database import build_engine

    with patch("app.core.database.create_async_engine") as mock_create_engine:
        build_engine("postgresql+asyncpg://u:p@localhost:5432/db", sql_echo=True, pool_size=7)
        mock_create_engine.assert_called_once_with(
            "postgresql+asyncpg://u:p@localhost:5432/db",
            echo=True,
            pool_size=7,
        )


@pytest.mark.asyncio
async def test_get_session_provides_isolated_session_per_request_and_closes_on_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: Request isolation & Session cleanup (app-lifecycle)."""
    monkeypatch.setenv("POSTGRES_HOST", "127.0.0.1")
    monkeypatch.setenv("POSTGRES_PORT", "59999")
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
    monkeypatch.setenv("POSTGRES_HOST", "127.0.0.1")
    monkeypatch.setenv("POSTGRES_PORT", "59999")
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
    """Scenario: Unreachable host via real lifespan & get_session returns 503 without leaking."""
    monkeypatch.setenv("POSTGRES_HOST", "127.0.0.1")
    monkeypatch.setenv("POSTGRES_PORT", "59999")
    monkeypatch.setenv("POSTGRES_PASSWORD", "unreachable_secret_pass")

    test_app = create_app()
    async with test_app.router.lifespan_context(test_app):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Base de datos no disponible"}
    assert "unreachable_secret_pass" not in response.text
    assert "59999" not in response.text


def test_module_structure_and_env_example_have_no_secrets() -> None:
    """Scenario: No secrets in repo, health module has only router.py, and two route groups exist."""
    import app.main as main_module
    from fastapi import APIRouter

    project_root = Path(__file__).resolve().parent.parent
    modules_dir = project_root / "app" / "modules"

    health_dir = modules_dir / "health"
    assert health_dir.is_dir(), "Missing module directory: health"
    assert (health_dir / "router.py").is_file(), "Missing router.py in app/modules/health"
    for forbidden_health_file in ("models.py", "schemas.py", "service.py"):
        assert not (health_dir / forbidden_health_file).exists(), (
            f"app/modules/health must only contain router.py, found {forbidden_health_file}"
        )

    for module_name in EXPECTED_MODULES:
        if module_name == "health":
            continue
        mod_path = modules_dir / module_name
        assert mod_path.is_dir(), f"Missing module directory: {module_name}"
        for required_file in ("__init__.py", "models.py", "schemas.py", "service.py", "router.py"):
            assert (mod_path / required_file).is_file(), (
                f"Missing {required_file} in app/modules/{module_name}"
            )

    assert hasattr(main_module, "router_abierto"), "app.main must define router_abierto"
    assert hasattr(main_module, "router_protegido"), "app.main must define router_protegido"
    assert isinstance(main_module.router_abierto, APIRouter)
    assert isinstance(main_module.router_protegido, APIRouter)

    assert main_module.router_abierto.url_path_for("get_health_live") == "/health/live"
    assert main_module.router_abierto.url_path_for("get_health_ready") == "/health/ready"
    assert len(main_module.router_protegido.routes) >= 6

    env_example = (project_root / "env.example").read_text(encoding="utf-8")
    for expected_env_var in (
        "POSTGRES_USER=",
        "POSTGRES_PASSWORD=",
        "POSTGRES_DB=",
        "POSTGRES_HOST=",
        "POSTGRES_PORT=",
        "JWT_SECRET=",
        "JWT_EXPIRATION_SECONDS=",
        "BCRYPT_ROUNDS=",
        "COOKIE_SECURE=",
        "DB_POOL_SIZE=",
        "SQL_ECHO=",
    ):
        assert expected_env_var in env_example
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
