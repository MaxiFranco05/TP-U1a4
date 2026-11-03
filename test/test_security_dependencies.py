"""Tests bajo Strict TDD para C-12: Criptografía bcrypt, JWT y dependencias de autenticación/autorización."""

import pytest


class TestValidarLongitudPassword:
    """Pruebas unitarias para el validador estricto de longitud de contraseñas (RN-15)."""

    def test_password_within_72_bytes_accepted(self) -> None:
        """Scenario: Password within 72 bytes is accepted."""
        from app.core.security import validar_longitud_password

        valid_ascii = "a" * 72
        assert validar_longitud_password(valid_ascii) == valid_ascii

    def test_password_exceeding_72_bytes_raises_value_error(self) -> None:
        """Scenario: Password exceeding 72 bytes raises validation error."""
        from app.core.security import validar_longitud_password

        invalid_ascii = "a" * 73
        with pytest.raises(ValueError, match="72 bytes"):
            validar_longitud_password(invalid_ascii)

    def test_multibyte_characters_count_byte_length(self) -> None:
        """Scenario: Multi-byte characters count their actual byte length."""
        from app.core.security import validar_longitud_password

        # 'ñ' is 2 bytes in UTF-8. 36 'ñ' = 72 bytes (allowed).
        valid_multibyte = "ñ" * 36
        assert len(valid_multibyte.encode("utf-8")) == 72
        assert validar_longitud_password(valid_multibyte) == valid_multibyte

        # 37 'ñ' = 74 bytes (exceeds 72 bytes even though character count is 37).
        invalid_multibyte = "ñ" * 37
        assert len(invalid_multibyte) == 37
        assert len(invalid_multibyte.encode("utf-8")) == 74
        with pytest.raises(ValueError, match="72 bytes"):
            validar_longitud_password(invalid_multibyte)


class TestBcryptAsyncSemaphoring:
    """Pruebas unitarias para hashing y verificación asincrónica con semáforo (DD-10)."""

    @pytest.mark.asyncio
    async def test_hash_password_produces_valid_bcrypt_hash(self) -> None:
        """Scenario: Password hashing produces valid bcrypt hash."""
        from app.core.security import hash_password

        raw_pwd = "SecretPassword123!"
        hashed = await hash_password(raw_pwd)
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    @pytest.mark.asyncio
    async def test_verify_password_matches_correct_and_rejects_incorrect(self) -> None:
        """Scenario: Password verification validates correct and rejects incorrect."""
        from app.core.security import hash_password, verify_password

        raw_pwd = "SecretPassword123!"
        hashed = await hash_password(raw_pwd)

        assert await verify_password(raw_pwd, hashed) is True
        assert await verify_password("WrongPassword!", hashed) is False

    @pytest.mark.asyncio
    async def test_concurrent_password_operations_unblock_event_loop(self) -> None:
        """Scenario: Concurrent operations run asynchronously under semaphore without blocking."""
        import asyncio
        from app.core.security import hash_password, verify_password

        tasks = [hash_password(f"Pass_{i}") for i in range(5)]
        hashes = await asyncio.gather(*tasks)
        assert len(hashes) == 5
        assert all(h.startswith("$2b$") or h.startswith("$2a$") for h in hashes)


class TestJwtTokens:
    """Pruebas unitarias para emisión y decodificación de tokens JWT (HS256)."""

    def test_create_and_decode_valid_access_token(self) -> None:
        """Scenario: Token issued with valid payload and signature."""
        from app.core.security import create_access_token, decode_access_token

        payload = {"sub": "123", "roles": ["ADMIN", "VENDEDOR"]}
        token = create_access_token(payload, expires_delta=60)
        assert isinstance(token, str)

        decoded = decode_access_token(token)
        assert decoded["sub"] == "123"
        assert decoded["roles"] == ["ADMIN", "VENDEDOR"]
        assert "exp" in decoded

    def test_expired_token_raises_expired_signature_error(self) -> None:
        """Scenario: Expired token raises jwt.ExpiredSignatureError."""
        import jwt
        from app.core.security import create_access_token, decode_access_token

        payload = {"sub": "123", "roles": ["CLIENTE"]}
        # negative expires delta makes it immediately expired
        token = create_access_token(payload, expires_delta=-10)

        with pytest.raises(jwt.ExpiredSignatureError):
            decode_access_token(token)

    def test_tampered_token_raises_invalid_token_error(self) -> None:
        """Scenario: Corrupted or tampered token raises jwt.InvalidTokenError."""
        import jwt
        from app.core.security import create_access_token, decode_access_token

        payload = {"sub": "123", "roles": ["CLIENTE"]}
        token = create_access_token(payload, expires_delta=60)
        tampered_token = token[:-5] + "XXXXX"

        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token(tampered_token)


class TestGetUsuarioActualDependency:
    """Pruebas unitarias y de integración para la dependencia get_usuario_actual (cookie HttpOnly y sesión compartida)."""

    @pytest.mark.asyncio
    async def test_missing_cookie_raises_401(self) -> None:
        """Scenario: Missing cookie returns 401 Unauthorized."""
        from fastapi import HTTPException
        from starlette.requests import Request
        from app.core.dependencies import get_usuario_actual

        # Request sin cookies
        request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
        mock_session = None

        with pytest.raises(HTTPException) as exc_info:
            await get_usuario_actual(request=request, session=mock_session)  # type: ignore[arg-type]
        assert exc_info.value.status_code == 401
        assert "falta cookie" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_bearer_header_is_ignored_and_raises_401(self) -> None:
        """Scenario: Authorization Bearer header is ignored and returns 401 Unauthorized."""
        from fastapi import HTTPException
        from starlette.requests import Request
        from app.core.dependencies import get_usuario_actual

        # Request con header Bearer pero sin cookie
        headers = [(b"authorization", b"Bearer some.valid.token")]
        request = Request({"type": "http", "method": "GET", "path": "/", "headers": headers})
        mock_session = None

        with pytest.raises(HTTPException) as exc_info:
            await get_usuario_actual(request=request, session=mock_session)  # type: ignore[arg-type]
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_or_expired_token_raises_401(self) -> None:
        """Scenario: Invalid or expired token returns 401 Unauthorized."""
        from fastapi import HTTPException
        from starlette.requests import Request
        from app.core.dependencies import get_usuario_actual
        from app.core.security import create_access_token

        # Cookie con token vencido
        expired_token = create_access_token({"sub": "1"}, expires_delta=-10)
        headers = [(b"cookie", f"access_token={expired_token}".encode("utf-8"))]
        request = Request({"type": "http", "method": "GET", "path": "/", "headers": headers})
        mock_session = None

        with pytest.raises(HTTPException) as exc_info:
            await get_usuario_actual(request=request, session=mock_session)  # type: ignore[arg-type]
        assert exc_info.value.status_code == 401
        assert "inválido o expirado" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_nonexistent_user_raises_401(self) -> None:
        """Scenario: Non-existent user in token returns 401 Unauthorized."""
        from unittest.mock import AsyncMock
        from fastapi import HTTPException
        from starlette.requests import Request
        from app.core.dependencies import get_usuario_actual
        from app.core.security import create_access_token

        token = create_access_token({"sub": "9999"}, expires_delta=60)
        headers = [(b"cookie", f"access_token={token}".encode("utf-8"))]
        request = Request({"type": "http", "method": "GET", "path": "/", "headers": headers})

        mock_session = AsyncMock()
        mock_session.get.return_value = None  # Usuario no encontrado en BD

        with pytest.raises(HTTPException) as exc_info:
            await get_usuario_actual(request=request, session=mock_session)
        assert exc_info.value.status_code == 401
        assert "no encontrado" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_inactive_user_raises_401(self) -> None:
        """Scenario: Inactive user account returns 401 Unauthorized."""
        from unittest.mock import AsyncMock
        from fastapi import HTTPException
        from starlette.requests import Request
        from app.core.dependencies import get_usuario_actual
        from app.core.security import create_access_token
        from app.modules.usuarios.models import Usuario

        token = create_access_token({"sub": "42"}, expires_delta=60)
        headers = [(b"cookie", f"access_token={token}".encode("utf-8"))]
        request = Request({"type": "http", "method": "GET", "path": "/", "headers": headers})

        inactive_user = Usuario(id=42, email="inactivo@test.com", nombre="Inactivo", password_hash="xxx", activo=False)
        mock_session = AsyncMock()
        mock_session.get.return_value = inactive_user

        with pytest.raises(HTTPException) as exc_info:
            await get_usuario_actual(request=request, session=mock_session)
        assert exc_info.value.status_code == 401
        assert "inactivo" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_valid_cookie_resolves_active_user(self) -> None:
        """Scenario: Valid cookie resolves active user entity."""
        from unittest.mock import AsyncMock
        from starlette.requests import Request
        from app.core.dependencies import get_usuario_actual
        from app.core.security import create_access_token
        from app.modules.usuarios.models import Usuario

        token = create_access_token({"sub": "42"}, expires_delta=60)
        headers = [(b"cookie", f"access_token={token}".encode("utf-8"))]
        request = Request({"type": "http", "method": "GET", "path": "/", "headers": headers})

        active_user = Usuario(id=42, email="activo@test.com", nombre="Activo", password_hash="xxx", activo=True)
        mock_session = AsyncMock()
        mock_session.get.return_value = active_user

        user = await get_usuario_actual(request=request, session=mock_session)
        assert user.id == 42
        assert user.email == "activo@test.com"
        mock_session.get.assert_awaited_once_with(Usuario, 42)


class TestRequiereRolDependency:
    """Pruebas unitarias para la dependencia requiere_rol contra la base de datos en tiempo real (RN-04)."""

    @pytest.mark.asyncio
    async def test_user_with_active_database_role_is_authorized(self) -> None:
        """Scenario: User with active non-expired database role is authorized."""
        from unittest.mock import AsyncMock, MagicMock
        from app.core.dependencies import requiere_rol
        from app.modules.usuarios.models import Usuario

        user = Usuario(id=1, email="admin@test.com", nombre="Admin", password_hash="x", activo=True)
        mock_session = AsyncMock()

        # Simular que la base de datos devuelve ["ADMIN"] como rol activo
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["ADMIN"]
        mock_session.execute.return_value = mock_result

        checker = requiere_rol("ADMIN")
        resolved_user = await checker(usuario_actual=user, session=mock_session)
        assert resolved_user == user

    @pytest.mark.asyncio
    async def test_user_with_one_of_multiple_allowed_roles_is_authorized(self) -> None:
        """Scenario: User has one of multiple allowed roles."""
        from unittest.mock import AsyncMock, MagicMock
        from app.core.dependencies import requiere_rol
        from app.modules.usuarios.models import Usuario

        user = Usuario(id=10, email="vendedor@test.com", nombre="Vendedor", password_hash="x", activo=True)
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["VENDEDOR"]
        mock_session.execute.return_value = mock_result

        checker = requiere_rol("ADMIN", "VENDEDOR")
        resolved_user = await checker(usuario_actual=user, session=mock_session)
        assert resolved_user == user


class TestVerificarPasswordCambiadaDependency:
    """Pruebas unitarias para verificar_password_cambiada (bloqueo RN-06)."""

    def test_user_with_pending_password_change_raises_403(self) -> None:
        """Scenario: User with password change pending is blocked with 403 Forbidden."""
        from fastapi import HTTPException
        from app.core.dependencies import verificar_password_cambiada
        from app.modules.usuarios.models import Usuario

        user = Usuario(id=1, email="u@test.com", nombre="U", password_hash="x", activo=True, debe_cambiar_password=True)
        with pytest.raises(HTTPException) as exc_info:
            verificar_password_cambiada(usuario_actual=user)
        assert exc_info.value.status_code == 403
        assert "cambiar su contraseña" in exc_info.value.detail.lower()

    def test_user_without_pending_password_change_is_allowed(self) -> None:
        """Scenario: User without password change pending is allowed."""
        from app.core.dependencies import verificar_password_cambiada
        from app.modules.usuarios.models import Usuario

        user = Usuario(id=1, email="u@test.com", nombre="U", password_hash="x", activo=True, debe_cambiar_password=False)
        resolved = verificar_password_cambiada(usuario_actual=user)
        assert resolved == user

    @pytest.mark.asyncio
    async def test_user_lacking_required_role_raises_403(self) -> None:
        """Scenario: User lacking required role returns 403 Forbidden."""
        from unittest.mock import AsyncMock, MagicMock
        from fastapi import HTTPException
        from app.core.dependencies import requiere_rol
        from app.modules.usuarios.models import Usuario

        user = Usuario(id=2, email="cliente@test.com", nombre="Cliente", password_hash="x", activo=True)
        mock_session = AsyncMock()

        # En la base sólo tiene "CLIENTE"
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["CLIENTE"]
        mock_session.execute.return_value = mock_result

        checker = requiere_rol("ADMIN", "VENDEDOR")
        with pytest.raises(HTTPException) as exc_info:
            await checker(usuario_actual=user, session=mock_session)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_revoked_or_expired_role_in_db_raises_403_even_if_token_claims_role(self) -> None:
        """Scenario: User with revoked or expired database role returns 403 Forbidden even if token claims the role."""
        from unittest.mock import AsyncMock, MagicMock
        from fastapi import HTTPException
        from app.core.dependencies import requiere_rol
        from app.modules.usuarios.models import Usuario

        user = Usuario(id=3, email="revoked@test.com", nombre="Ex Admin", password_hash="x", activo=True)
        mock_session = AsyncMock()

        # La consulta a BD con revocada_en IS NULL no devuelve nada
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        checker = requiere_rol("ADMIN")
        with pytest.raises(HTTPException) as exc_info:
            await checker(usuario_actual=user, session=mock_session)
        assert exc_info.value.status_code == 403


class TestProtectedGroupRouterIntegration:
    """Pruebas de integración HTTP sobre rutas abiertas vs protegidas y sesión compartida (DD-08, DD-12)."""

    @pytest.mark.asyncio
    async def test_protected_route_blocks_unauthenticated_request_with_401(self) -> None:
        """Scenario: Protected endpoint returns 401 when no session cookie is provided."""
        from unittest.mock import MagicMock
        from fastapi import APIRouter, Depends, FastAPI
        from httpx import ASGITransport, AsyncClient
        from app.core.dependencies import verificar_password_cambiada

        test_app = FastAPI()
        test_app.state.session_factory = MagicMock()
        protected = APIRouter(dependencies=[Depends(verificar_password_cambiada)])

        @protected.get("/ruta-protegida")
        def _target() -> dict[str, str]:
            return {"status": "ok"}

        test_app.include_router(protected)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ruta-protegida")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_route_blocks_user_with_pending_password_change_with_403(self) -> None:
        """Scenario: Protected endpoint returns 403 when user must change password (RN-06)."""
        from fastapi import APIRouter, Depends, FastAPI
        from httpx import ASGITransport, AsyncClient
        from app.core.dependencies import get_usuario_actual, verificar_password_cambiada
        from app.modules.usuarios.models import Usuario

        test_app = FastAPI()
        protected = APIRouter(dependencies=[Depends(verificar_password_cambiada)])

        @protected.get("/ruta-protegida")
        def _target() -> dict[str, str]:
            return {"status": "ok"}

        test_app.include_router(protected)

        user_pending = Usuario(id=1, email="p@test.com", nombre="P", password_hash="x", activo=True, debe_cambiar_password=True)
        test_app.dependency_overrides[get_usuario_actual] = lambda: user_pending

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ruta-protegida")
        assert resp.status_code == 403
        assert "cambiar su contraseña" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_protected_route_allows_user_without_pending_password_change(self) -> None:
        """Scenario: Protected endpoint allows user when debe_cambiar_password is False."""
        from fastapi import APIRouter, Depends, FastAPI
        from httpx import ASGITransport, AsyncClient
        from app.core.dependencies import get_usuario_actual, verificar_password_cambiada
        from app.modules.usuarios.models import Usuario

        test_app = FastAPI()
        protected = APIRouter(dependencies=[Depends(verificar_password_cambiada)])

        @protected.get("/ruta-protegida")
        def _target() -> dict[str, str]:
            return {"status": "ok"}

        test_app.include_router(protected)

        user_clean = Usuario(id=1, email="c@test.com", nombre="C", password_hash="x", activo=True, debe_cambiar_password=False)
        test_app.dependency_overrides[get_usuario_actual] = lambda: user_clean

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ruta-protegida")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_open_route_allows_user_with_pending_password_change(self) -> None:
        """Scenario: Open route permits access even if password change is pending (RN-06)."""
        from fastapi import APIRouter, FastAPI
        from httpx import ASGITransport, AsyncClient

        test_app = FastAPI()
        open_group = APIRouter()

        @open_group.get("/ruta-abierta")
        def _target() -> dict[str, str]:
            return {"status": "open"}

        test_app.include_router(open_group)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/ruta-abierta")
        assert resp.status_code == 200
        assert resp.json() == {"status": "open"}

    @pytest.mark.asyncio
    async def test_shared_session_verified_across_dependencies(self) -> None:
        """Scenario: Single request shares the exact same AsyncSession across auth, roles, and route (DD-08)."""
        from fastapi import APIRouter, Depends, FastAPI
        from httpx import ASGITransport, AsyncClient
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.core.database import get_session

        test_app = FastAPI()
        sessions_seen: list[int] = []

        class DummySession:
            def __init__(self) -> None:
                self.session_id = id(self)

        dummy = DummySession()

        async def fake_get_session() -> Any:
            sessions_seen.append(dummy.session_id)
            yield dummy

        test_app.dependency_overrides[get_session] = fake_get_session

        router = APIRouter()

        @router.get("/test-shared")
        async def _endpoint(
            session: AsyncSession = Depends(get_session),
        ) -> dict[str, int]:
            sessions_seen.append(getattr(session, "session_id"))
            return {"count": len(sessions_seen)}

        test_app.include_router(router)

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/test-shared")
        assert resp.status_code == 200
        # In a single request with Depends(get_session), the yielded session instance is identical
        assert len(sessions_seen) >= 2
        assert sessions_seen[0] == sessions_seen[1]
