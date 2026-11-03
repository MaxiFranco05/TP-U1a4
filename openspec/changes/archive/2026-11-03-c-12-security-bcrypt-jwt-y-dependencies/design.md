# Design: Security, Bcrypt, JWT and Request Dependencies

## Context

The system has completed the data layer foundations (C-09 configuration and lifespan, C-10 database models and migrations, C-11 generic repositories and Unit of Work). See `proposal.md` for background motivation.

In the Parcial architecture:
1. `Usuario`, `AsignacionRol`, `IntentoAcceso`, and `EventoSeguridad` exist as SQLModel entities in `app/modules/usuarios/models.py`.
2. Settings in `app/core/config.py` provide `JWT_SECRET`, `JWT_EXPIRATION_SECONDS`, `BCRYPT_ROUNDS`, and `COOKIE_SECURE`.
3. `app/core/database.py` defines `get_session` providing an `AsyncSession` per request.
4. `app/main.py` defines the two route groups (`open_group` and `protected_group`), currently leaving `protected_group = APIRouter(dependencies=[])` ready to receive the mandatory password-change gate.

This change delivers the foundational security engine in `app/core/security.py` and the reusable request dependencies in `app/core/dependencies.py`.

## Goals / Non-Goals

**Goals:**
- Provide asynchronous, thread-isolated, and semaphore-bounded `bcrypt` hashing and verification.
- Provide a reusable validator enforcing the 72-byte UTF-8 password limit to prevent bcrypt crashes and ensure `422` responses.
- Implement JWT generation and decoding using `PyJWT` with `HS256`, embedding `sub`, `exp`, and active `roles`.
- Implement `get_usuario_actual` reading exclusively from the `access_token` cookie, reusing the request's `AsyncSession`, and enforcing active status.
- Implement `requiere_rol(*roles)` verifying active roles (`RN-04`) directly in PostgreSQL in real time.
- Implement `verificar_password_cambiada` and mount it on `router_protegido` (`RN-06`).
- Comprehensive unit and integration tests covering all positive, negative, and edge-case scenarios.

**Non-Goals:**
- Implement `/auth/*` endpoints (registration, login, logout, password change) — deferred to C-13.
- Implement `/usuarios/*` and `/eventos` endpoints — deferred to C-14.
- Implement specific User repositories or User Unit of Work — deferred to C-13.

## Decisions

### 1. Concurrency-Bounded Bcrypt Hashing via `asyncio.to_thread` and `asyncio.Semaphore` (DD-10)
- **Rationale**: `bcrypt` is intentionally CPU-intensive (~300ms compute time at rounds 12). Running it directly on the async event loop freezes all concurrent requests. Running unconstrained threads under heavy load can exhaust the Python thread pool.
- **Approach**: All `bcrypt.hashpw` and `bcrypt.checkpw` executions are wrapped in `asyncio.to_thread` and gated by a global `asyncio.Semaphore(value=4)` (configurable or default 4 concurrent hashing tasks).
- **Alternatives considered**:
  - *Passlib*: Deprecated and has compatibility issues with newer bcrypt versions.
  - *Unbounded `to_thread`*: Risk of thread pool saturation under concurrent login requests.

### 2. UTF-8 72-Byte Password Validation (RN-15)
- **Rationale**: The underlying `bcrypt` algorithm truncates passwords at 72 bytes. Passwords longer than 72 bytes in `bcrypt>=4.0` can cause runtime exceptions or false security. A multi-byte character (such as `ñ` or emojis) occupies 2 to 4 bytes in UTF-8, so checking `len(password)` by character count is insufficient.
- **Approach**: A helper function `validar_longitud_password(v: str) -> str` validates `len(v.encode("utf-8")) <= 72`. If it exceeds 72 bytes, it raises `ValueError("La contraseña no puede superar los 72 bytes UTF-8.")`, which Pydantic / FastAPI translates to `422 Unprocessable Entity`.
- **Alternatives considered**:
  - *Character length limit*: Fails when multibyte characters push byte count past 72 while char count is under 72.

### 3. Unified Session Sharing Across Auth Dependencies and UoW (DD-08, Hard Rules)
- **Rationale**: If `get_usuario_actual`, `requiere_rol`, and downstream services each acquired their own database session, a single HTTP request would consume 2 or 3 connections from the pool (`DB_POOL_SIZE = 5`), leading to pool exhaustion under minimal concurrency.
- **Approach**: `get_usuario_actual` and `requiere_rol` both declare `session: AsyncSession = Depends(get_session)`. FastAPI's default dependency resolution reuses the cached session yielded by `get_session` within the same request scope.
- **Alternatives considered**:
  - *Creating new session inside dependencies*: Violates Hard Rules and exhausts connection pool.

### 4. Cookie-Only Token Delivery and Retrieval (DD-10, Hard Rules)
- **Rationale**: Tokens transmitted in request bodies or `Authorization: Bearer` headers are vulnerable to XSS token theft in browser contexts.
- **Approach**: `get_usuario_actual` strictly inspects `request.cookies.get("access_token")`. If the cookie is absent, it immediately raises `HTTPException(status_code=401, detail="No autenticado: falta cookie de sesión.")`. If a client sends an `Authorization: Bearer` header, it is completely ignored.
- **Alternatives considered**:
  - *Dual header/cookie fallback*: Insecure; violates explicit architectural contract.

### 5. Real-Time Database Role Authorization (`RN-04`)
- **Rationale**: Tokens are stateless and have a lifetime (`JWT_EXPIRATION_SECONDS = 1800`). If role permissions were checked from token claims, revoking a rogue user's `ADMIN` or `VENDEDOR` role would not take effect until their token expired (30 minutes later).
- **Approach**: `requiere_rol(*roles_permitidos)` queries the `asignacion_rol` table in PostgreSQL on every request:
  ```python
  select(AsignacionRol.rol).where(
      AsignacionRol.usuario_id == usuario_actual.id,
      AsignacionRol.revocada_en.is_(None),
      or_(AsignacionRol.vence_en.is_(None), AsignacionRol.vence_en > func.now()),
  )
  ```
  If none of the returned roles match `roles_permitidos`, it raises `HTTPException(status_code=403, detail="No posee los permisos requeridos para esta operación.")`.
- **Alternatives considered**:
  - *Validating roles against JWT payload*: Fast, but breaks `RN-04` and prevents immediate revocation.

### 6. Router-Level Password Change Guard on `router_protegido` (`RN-06`, DD-12) and Transition Strategy
- **Rationale**: When personal accounts are created, they start with `debe_cambiar_password = True`. Leaving the password change check to individual endpoint handlers is error-prone.
- **Approach**: In `app/main.py`, `protected_group = APIRouter(dependencies=[Depends(verificar_password_cambiada)])`. The dependency checks `usuario_actual.debe_cambiar_password`. If `True`, it raises `HTTPException(status_code=403, detail="Debe cambiar su contraseña antes de operar en el sistema.")`. Open routes (`router_abierto`) do not include this dependency.
- **Transition strategy for legacy Stage 1 routes**: In Stage 1 (TP Capítulos 1 a 4), catalog routers (`generos_router`, `editoriales_router`, etc.) were completely unauthenticated and are verified by tests like `test/test_generos_and_migration_002.py`. In Stage 2, C-15 and C-16 will segregate these endpoints into public reads (mounted in `open_group`) and administrative writes (mounted in `protected_group`). Therefore, in C-12, `_build_route_groups()` sets up `protected_group = APIRouter(dependencies=[Depends(verificar_password_cambiada)])` while temporarily keeping legacy Stage 1 domain routers in `open_group` (or attaching test verification routers to `protected_group`), guaranteeing zero regression on existing Stage 1 test suites while establishing the exact production wiring for C-14, C-15, and C-16.
- **Alternatives considered**:
  - *Per-route decorators*: High risk of developer omission.
  - *Premature locking of legacy routers*: Causes immediate regressions in `test/test_generos_and_migration_002.py` before C-15 splits public vs protected catalog endpoints.

## Risks / Trade-offs

- **[Risk] High concurrency overhead on DB for role checks** → *Mitigation*: The `asignacion_rol` table has an index on `usuario_id` and a partial unique index `uq_asignacion_rol_activa` on `(usuario_id, rol) WHERE revocada_en IS NULL`. The query is an index scan matching 0 to 3 rows per user.
- **[Risk] Cookie handling across CORS/dev environments** → *Mitigation*: `settings.COOKIE_SECURE` is boolean (False in dev, True in prod), and cookie uses `SameSite=Lax`.
- **[Risk] Bcrypt semaphore contention** → *Mitigation*: Hashing is only required during password change and login. Normal authenticated requests only perform fast JWT signature verification and an indexed DB read.
- **[Risk] Regression in Stage 1 test suites upon mounting protected router dependency** → *Mitigation*: Documented transition strategy keeping un-segregated legacy routers in `open_group` until C-15 performs the public-read vs admin-write router segregation.

## Migration Plan

No database schema migration is required for C-12 because `Usuario` and `AsignacionRol` tables, columns, and partial indexes were already applied in Migrations 003 and 004 (C-10).
The change only adds core utility files (`app/core/security.py`, `app/core/dependencies.py`) and configures dependencies on `app/main.py`.
