# Proposal: Security, Bcrypt, JWT and Request Dependencies

## Why

The system has transitioned from an open catalog (TP Capítulos 1 a 4) to an enterprise-grade multi-role architecture (Parcial Capítulos 1 a 6) requiring secure credentials, role-based access control, and route segmentation. Before implementing user authentication endpoints (C-13) and administration endpoints (C-14), the core cryptographic primitives and request-scoped dependency injection layer must be established.

This change solves four critical architectural challenges:
1. **Event loop & pool protection**: isolates CPU-heavy `bcrypt` hashing outside the async event loop using `asyncio.to_thread` constrained by a global `asyncio.Semaphore`, and ensures all authentication and authorization checks reuse the exact same `AsyncSession` (`Depends(get_session)`) as the request's Unit of Work (DD-08, DD-10).
2. **Timing & length security**: enforces a strict 72-byte UTF-8 password limit to prevent bcrypt truncation vulnerabilities and runtime errors (`422`, RN-15), while preparing timing attack defense foundations (RN-08).
3. **Real-time database authorization**: enforces `RN-04` by validating active roles directly in PostgreSQL (`asignacion_rol` with `revocada_en IS NULL` and `(vence_en IS NULL OR vence_en > now())`) on every request rather than trusting stale token claims.
4. **Mandatory password change enforcement**: enforces `RN-06` by blocking accounts with `debe_cambiar_password = True` from accessing any protected endpoint (`403 Forbidden`) via router-level dependency on `router_protegido`.

## What Changes

- **Create `app/core/security.py`**:
  - `hash_password(password: str) -> str`: asynchronous hashing using `bcrypt` and `settings.BCRYPT_ROUNDS`, run via `asyncio.to_thread` and guarded by a module-level `asyncio.Semaphore`.
  - `verify_password(password: str, password_hash: str | bytes) -> bool`: asynchronous verification using `bcrypt.checkpw`, run via `asyncio.to_thread` and guarded by the same `asyncio.Semaphore`.
  - `validar_longitud_password(v: str) -> str`: reusable field validator enforcing `len(v.encode('utf-8')) <= 72`, raising `ValueError` (FastAPI translates to `422 Unprocessable Entity`).
  - `create_access_token(data: dict, expires_delta: int | None = None) -> str`: JWT token generation signed with `settings.JWT_SECRET` and algorithm `HS256`, embedding `sub`, `exp`, and active role list.
  - `decode_access_token(token: str) -> dict`: JWT token decoding and validation with proper error handling for expired or invalid signatures.
- **Create `app/core/dependencies.py`**:
  - `get_usuario_actual(request: Request, session: AsyncSession = Depends(get_session)) -> Usuario`: extracts token strictly from the `access_token` cookie (`request.cookies.get("access_token")`), ignoring `Authorization: Bearer`. Validates token signature, expiration, and queries `Usuario` in PostgreSQL via the shared session. Raises `401 Unauthorized` if cookie is missing, token is invalid, user does not exist, or `usuario.activo == False`.
  - `verificar_password_cambiada(usuario_actual: Usuario = Depends(get_usuario_actual)) -> Usuario`: verifies `usuario_actual.debe_cambiar_password is False`. Raises `403 Forbidden` with a clean error message if `True` (`RN-06`).
  - `requiere_rol(*roles_permitidos: str)`: factory returning an async dependency function that takes `usuario_actual = Depends(get_usuario_actual)` and `session = Depends(get_session)`. Queries `AsignacionRol` for active assignments (`revocada_en IS NULL` and valid expiration). Raises `403 Forbidden` if the user does not possess any of `roles_permitidos`.
- **Update `app/main.py`**:
  - Mount `verificar_password_cambiada` onto `router_protegido` dependencies: `protected_group = APIRouter(dependencies=[Depends(verificar_password_cambiada)])`.

## Capabilities

### New Capabilities
- `security-and-dependencies`: Core cryptographic utilities (non-blocking bcrypt with semaphore, 72-byte UTF-8 validator, JWT issuance/validation) and unified FastAPI dependencies for cookie-based authentication, database-backed role authorization (`RN-04`), and mandatory password change gate (`RN-06`).

### Modified Capabilities
*(None: existing capabilities remain intact; `app-lifecycle` already declared the two-group structure where this gate is attached).*

## Impact

- **Affected files**:
  - `app/core/security.py` (new)
  - `app/core/dependencies.py` (new)
  - `app/main.py` (wire dependency to `router_protegido`)
  - `test/test_security_dependencies.py` (new comprehensive tests)
- **APIs & Contracts**:
  - All endpoints included in `router_protegido` will now require a valid authenticated session whose password change is not pending (`401` if not authenticated, `403` if `debe_cambiar_password=True`).
  - Endpoints in `router_abierto` remain unblocked by `verificar_password_cambiada`.
- **Security & Performance**:
  - Protects the ASGI event loop from CPU-bound bcrypt denial of service.
  - Ensures a single database connection is used across authentication, authorization, and business logic transactions.
  - Cookie `access_token` with `HttpOnly` and `SameSite=Lax` ensures XSS resilience and CSRF hygiene.
