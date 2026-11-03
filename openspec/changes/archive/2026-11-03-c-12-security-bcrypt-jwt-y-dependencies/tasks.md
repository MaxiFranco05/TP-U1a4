# Tasks

## 1. Cryptographic Primitives and Password Validation (`app/core/security.py`)

- [x] 1.1 Implement reusable UTF-8 72-byte password validator (`validar_longitud_password`) in `app/core/security.py` and verify via unit tests that ASCII <= 72 bytes pass, multi-byte sequences count byte length, and inputs > 72 bytes raise `ValueError`.
- [x] 1.2 Implement asynchronous password hashing (`hash_password`) and verification (`verify_password`) in `app/core/security.py` with `bcrypt` offloaded via `asyncio.to_thread` and bounded by a global `asyncio.Semaphore`, and verify with async tests that event loop is unblocked and incorrect passwords return `False`.
- [x] 1.3 Implement JWT issuance (`create_access_token`) and decoding (`decode_access_token`) in `app/core/security.py` with `PyJWT` (HS256, embedding `sub`, `exp`, and `roles`), and verify with unit tests that valid tokens decode correctly, expired tokens raise `jwt.ExpiredSignatureError`, and tampered signatures raise `jwt.InvalidTokenError`.

## 2. Request Dependencies and Real-Time Authorization (`app/core/dependencies.py`)

- [x] 2.1 Implement `get_usuario_actual` in `app/core/dependencies.py` extracting token strictly from cookie `access_token`, mapping PyJWT errors to `HTTPException(401)`, resolving `Usuario` from PostgreSQL via `Depends(get_session)` with `activo == True`, ignoring `Authorization: Bearer`, and verify via tests returning 401 on missing cookie, invalid/expired token, absent user, or inactive account.
- [x] 2.2 Implement `requiere_rol(*roles_permitidos)` in `app/core/dependencies.py` querying active assignments in `asignacion_rol` (`revocada_en IS NULL` and unexpired) using the shared `AsyncSession` (`RN-04`), and verify via tests that revoked/expired/missing roles return 403 even if the JWT payload claims them.
- [x] 2.3 Implement `verificar_password_cambiada` in `app/core/dependencies.py` checking `usuario_actual.debe_cambiar_password` (`RN-06`), and verify via tests that users with pending change receive 403 and users with clean status proceed.

## 3. Router Wiring and End-to-End Verification

- [x] 3.1 Mount `verificar_password_cambiada` onto `router_protegido` in `app/main.py` (`protected_group = APIRouter(dependencies=[Depends(verificar_password_cambiada)])`), maintaining legacy Stage 1 domain routers in `open_group` until C-15 to ensure zero regressions in `test_generos_and_migration_002.py`.
- [x] 3.2 Write comprehensive tests in `test/test_security_dependencies.py` covering open route access vs protected route blocking, cookie vs Bearer header rejection, role-based database verification, and shared session execution.
- [x] 3.3 Execute the test suite and verify that all security tests and existing project tests pass.

## Workflow follow-up

- Suggest manual commit: `git commit -m "C-12: security (bcrypt to_thread + semaforo, JWT) y dependencies con sesion compartida"`.
- Archive change `c-12-security-bcrypt-jwt-y-dependencies` and update `CHANGES.md`.
