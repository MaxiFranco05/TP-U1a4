# Proposal

## Why

El sistema de la librería requiere mecanismos formales y seguros de autenticación y gestión de identidad para clientes y personal administrativo. Este change implementa los flujos de ciclo de vida de credenciales y sesiones: auto-registro atómico de clientes en una única transacción (RN-02), inicio de sesión con protección contra ataques de fuerza bruta (RN-07), mitigación de enumeración de cuentas mediante respuestas en tiempo constante (RN-08), auditoría obligatoria de intentos de acceso en sesión/transacción independiente (Ej. 7, DD-09), emisión de cookies seguras `HttpOnly` para JWT (C-03), introspección de la identidad actual y cambio de contraseña con registro auditable en `evento_seguridad` (RN-06, RN-16, C-09).

## What Changes

- **Repositorios y Unit of Work de Identidad (`app/modules/usuarios/repository.py`, `app/modules/clientes/repository.py`, `app/modules/usuarios/unit_of_work.py`)**:
  - `ClienteRepository`: repositorio de persistencia para `Cliente` heredando de `BaseRepository[Cliente]`, con método `get_by_email`.
  - `UsuarioRepository`: búsqueda por email, listado y persistencia heredando de `BaseRepository[Usuario]`.
  - `AsignacionRolRepository`: consulta de roles vigentes y persistencia heredando de `BaseRepository[AsignacionRol]`.
  - `IntentoAccesoRepository`: registro de intentos y conteo de fallos recientes por `(email, ip)` desde el último intento exitoso.
  - `EventoSeguridadRepository`: inserción de eventos de auditoría de seguridad heredando de `BaseRepository[EventoSeguridad]`.
  - `UsuariosUnitOfWork`: gestor de contexto asincrónico que agrupa `usuarios`, `asignaciones_rol`, `intentos_acceso`, `eventos_seguridad` y `clientes` (`ClienteRepository`) compartiendo la misma sesión de la petición para operaciones atómicas (RN-02, RN-16).
- **Contratos DTO (`app/modules/usuarios/schemas.py`)**:
  - Esquemas de entrada con `extra="forbid"` y validación estricta de contraseñas de hasta 72 bytes UTF-8 (`validar_longitud_password` $\to$ `422`, RN-15).
  - Ningún esquema expone `password_hash`.
  - DTOs específicos: `UsuarioRegistroRequest`, `LoginRequest`, `LoginResponse`, `UsuarioYoResponse` (`{id, email, nombre, debe_cambiar_password, roles_vigentes, roles_token}`), `CambiarPasswordRequest`, `MensajeResponse`.
- **Servicio y Endpoints `/auth` (`app/modules/usuarios/service.py`, `app/modules/usuarios/router.py`)**:
  - `POST /auth/registro` (201, 409, 422): calcula `hash_password` fuera de la transacción; dentro de `async with uow:` crea `Usuario`, `AsignacionRol(rol="CLIENTE")` y `Cliente`. Conflicto por email existente en usuario o cliente $\to$ `409 Conflict` sin apropiarse de datos existentes ni dejar registros huérfanos (RN-02, C-02).
  - `POST /auth/login` (200, 401, 422, 429):
    1. Si acumula $\ge 5$ fallos para `(email, ip)` en los últimos 60 segundos posteriores al último éxito: registra el intento fallido en `intento_acceso` en sesión independiente y responde inmediatamente `429 Too Many Requests` con header `Retry-After: 60` sin calcular hash con bcrypt (RN-07, C-05).
    2. Si no está bloqueado, verifica la contraseña con `verify_password` contra el hash del usuario o contra `app.state.dummy_password_hash` si el correo no existe, respondiendo `401 Unauthorized` con mensaje uniforme (RN-08, C-04).
    3. Registra el intento (exitoso o fallido) en `intento_acceso` mediante sesión y transacción propias e independientes obtenidas de `request.app.state.session_factory` con el comentario declarativo obligatorio de 3 puntos (Ej. 7, DD-09).
    4. Seteo de cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`, `Secure`) y respuesta `200` con `{mensaje, debe_cambiar_password, expira_en_segundos}` sin token en el cuerpo (C-03).
  - `POST /auth/logout` (200): idempotente; borra la cookie `access_token` devolviendo 200 aun si el token estuviera expirado.
  - `GET /auth/yo` (200, 401): devuelve la información del usuario autenticado (`UsuarioYoResponse`), sus roles vigentes consultados en base de datos y los roles informativos del token JWT (C-07).
  - `POST /auth/cambiar-password` (200, 401, 422): verifica contraseña actual, calcula nuevo hash fuera de la transacción, actualiza `password_hash`, establece `debe_cambiar_password=False` y registra el cambio en `evento_seguridad` dentro de un único UoW (RN-06, RN-16, C-09).
- **Montaje en Rutas**:
  - Router `/auth` registrado en `open_group` en `app/main.py`.

## Capabilities

### New Capabilities
- `user-auth`: Gestión de ciclo de vida de credenciales y sesiones de usuario, incluyendo auto-registro atómico de clientes, inicio de sesión con control de tasa de intentos fallidos y auditoría en sesión aislada, cookie `HttpOnly`, introspección de identidad y cambio de contraseña con bitácora en la misma transacción.

### Modified Capabilities
<!-- Ninguna capacidad existente cambia sus requerimientos -->

## Impact

- **Código Afectado**:
  - `app/modules/clientes/repository.py`: Creación de `ClienteRepository` heredando de `BaseRepository[Cliente]`.
  - `app/modules/usuarios/`: Nuevos archivos `repository.py`, `unit_of_work.py`, `schemas.py`, `service.py`, `router.py`.
  - `app/main.py`: Inclusión de `auth_router` en `open_group`.
  - `test/test_auth_endpoints.py`: Suite exhaustiva de pruebas unitarias y de integración bajo Strict TDD.
- **Riesgo y Gobernanza**: Nivel CRÍTICO (autenticación, rate limiting y sesiones). Requiere estricta adhesión a TDD y verificación exhaustiva de los casos de prueba del parcial (`C-02`, `C-03`, `C-04`, `C-05`, `C-09`).
