# Design

## Context

Este diseño define la arquitectura e implementación de la capa de autenticación, gestión de sesiones y repositorios de identidad para el módulo `app/modules/usuarios/`.
Se basa en las primitivas criptográficas implementadas en C-12 (`app/core/security.py`, `app/core/dependencies.py`), los modelos de persistencia de C-10 (`app/modules/usuarios/models.py`) y la infraestructura de repositorios y UoW de C-11 (`app/core/repository.py`, `app/core/unit_of_work.py`).
Ver `proposal.md` para la motivación y `specs/user-auth/spec.md` para los requerimientos funcionales observables.

## Goals / Non-Goals

**Goals:**
- Implementar la persistencia de usuarios en 5 capas limpias (`Router -> Service -> UoW -> Repository -> Model`).
- Crear `ClienteRepository` en `app/modules/clientes/repository.py` extendiendo `BaseRepository[Cliente]`.
- Proveer `UsuarioRepository`, `AsignacionRolRepository`, `IntentoAccesoRepository`, `EventoSeguridadRepository` y `UsuariosUnitOfWork`.
- Auto-registro de clientes en una única transacción atómica componiendo `ClienteRepository` en `UsuariosUnitOfWork` (RN-02).
- Login con verificación en orden estricto:
  1. Rate limit en `intento_acceso` (RN-07): si hay $\ge 5$ fallos en 60 s desde el último éxito, registra el intento fallido en sesión aislada y responde `429 Too Many Requests` con header `Retry-After: 60` sin calcular bcrypt.
  2. Búsqueda y verificación de credenciales con `bcrypt` en hilo con semáforo contra usuario o dummy en tiempo constante (RN-08).
  3. Auditoría en `intento_acceso` con sesión y transacción independientes obtenidas de `request.app.state.session_factory` con el comentario declarativo obligatorio de 3 puntos (DD-09, Ej. 7).
  4. Cookie `access_token` `HttpOnly` (`SameSite=Lax`, `Max-Age`, `Secure` configurable) y respuesta 200 sin JWT en el cuerpo (C-03).
- Endpoints de `/auth/logout` (idempotente) y `/auth/yo` (introspección con roles de base vs token, C-07).
- Endpoint `/auth/cambiar-password` con auditoría en `evento_seguridad` dentro de la misma transacción (RN-06, RN-16, C-09).
- Validación de contraseñas $\le 72$ bytes UTF-8 con `extra="forbid"` en todos los DTOs de entrada (RN-15).

**Non-Goals:**
- Rutas administrativas `/usuarios/*` (alta de personal, administración de roles, consulta de bitácora de seguridad) son responsabilidad de `C-14`.
- Autorización de ventas y reglas de stock son responsabilidad de `C-15` y `C-16`.

## Decisions

### Decisión 1: Creación de `ClienteRepository` y su composición en `UsuariosUnitOfWork`
- **Decisión**: Se implementa `ClienteRepository` en `app/modules/clientes/repository.py` heredando de `BaseRepository[Cliente]`, con métodos `get_by_id`, `get_by_email` y `add`. `UsuariosUnitOfWork` gestiona las instancias de `UsuarioRepository`, `AsignacionRolRepository`, `IntentoAccesoRepository`, `EventoSeguridadRepository` y compone además `ClienteRepository(session=self.session)`.
- **Razón**: Permite que el flujo de auto-registro (`POST /auth/registro`) cree `Usuario`, `AsignacionRol(rol="CLIENTE")` y `Cliente` dentro del mismo bloque transaccional `async with uow:`, garantizando que se persistan las 3 entidades juntas o ninguna en caso de conflicto por email (RN-02, C-02).
- **Alternativas consideradas**:
  - Inyectar dos UoWs independientes en el servicio: Descartado porque violaría la regla de sesión única compartida por petición y rompería la atomicidad transaccional.

### Decisión 2: Sesión y transacción separadas para `intento_acceso` con comentario declarativo obligatorio (DD-09, Ej. 7)
- **Decisión**: En `POST /auth/login`, el registro del intento se realiza instanciando una sesión independiente a través de `session_factory = request.app.state.session_factory` (disponible también como alias `session_maker`). Aplica tanto para intentos fallidos que disparan 429, fallidos que dan 401, como exitosos que dan 200.
- **Comentario obligatorio en el código**:
  ```python
  # SESIÓN Y TRANSACCIÓN INDEPENDIENTES PARA INTENTO_ACCESO (DD-09, Ej. 7):
  # 1. Qué hace distinto: Abre una AsyncSession separada y ejecuta una transacción
  #    aislada con commit() forzoso, sin reutilizar la sesión del request.
  # 2. Por qué no comparte la transacción de la petición: Si compartiera la sesión/transacción
  #    de la petición, cualquier fallo de autenticación (401), rate limit (429) o error
  #    inesperado provocaría un rollback que borraría el registro del intento fallido,
  #    inutilizando por completo la protección de fuerza bruta (RN-07).
  # 3. Cuál es su costo: Adquiere temporalmente una conexión adicional del pool durante
  #    la escritura y persiste filas en la base de datos aun si la petición HTTP falla.
  ```
- **Alternativas consideradas**:
  - Registrar el intento en la misma sesión del request: Descartado, porque al retornar 401/429 o lanzar una excepción se perdería el registro de auditoría y el límite de 5 intentos nunca dispararía el bloqueo.

### Decisión 3: Algoritmo de conteo de fallos recientes en `IntentoAccesoRepository` y manejo seguro de IP
- **Decisión**:
  - Extracción de IP cliente segura: `client_ip = request.client.host if request.client else "127.0.0.1"`.
  - Método `IntentoAccesoRepository.contar_fallos_recientes(email, ip, ventana_segundos=60)`:
    1. Busca el `cuando` del último intento exitoso (`exito == True`) para ese par `(email, ip)`.
    2. Define el umbral temporal como `max(ahora - 60s, ultimo_exito.cuando if ultimo_exito else epoch)`.
    3. Cuenta los registros donde `email == email`, `ip == ip`, `exito == False` y `cuando >= umbral`.
- **Razón**: Cumple estrictamente con RN-07: tras un login exitoso, la cuenta de fallos se reinicia (los fallos anteriores quedan guardados en la tabla para auditoría pero ya no cuentan para el bloqueo). Si el conteo es $\ge 5$, se persiste el intento fallido en sesión aislada y se responde `429 Too Many Requests` con header `Retry-After: 60`.

### Decisión 4: Verificación en tiempo constante contra dummy password hash (RN-08, DD-10)
- **Decisión**: Si el usuario no existe al autenticar en `/auth/login`, el servicio ejecuta `await verify_password(datos.password, app.state.dummy_password_hash)` antes de responder `401 Unauthorized` con el mensaje exacto `"Credenciales inválidas"`.
- **Razón**: Garantiza que tanto para emails existentes como inexistentes el servidor ejecute `bcrypt` consumiendo aproximadamente el mismo tiempo de procesamiento (~300 ms), evitando que atacantes descubran qué correos están registrados mediante análisis de latencia.

### Decisión 5: Manejo de cookies HttpOnly en FastAPI (`Response`) e Idempotencia de Logout
- **Decisión**: Los endpoints `/auth/login` y `/auth/logout` reciben el objeto `Response` de FastAPI para configurar directamente las cabeceras `Set-Cookie`.
  - Login: `response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax", max_age=settings.JWT_EXPIRATION_SECONDS, secure=settings.COOKIE_SECURE)`.
  - Logout: `response.delete_cookie(key="access_token", httponly=True, samesite="lax")`. El endpoint de logout no exige que el token sea válido; limpia la cookie y responde 200 de forma idempotente para permitir desloguear sesiones vencidas o inconsistentes.
- **Razón**: Cumple con la regla dura de no emitir JWT en el cuerpo de la respuesta y protegerlo contra ataques XSS mediante `HttpOnly`.

### Decisión 6: Contratos DTO, `UsuarioYoResponse` y validación de 72 bytes UTF-8
- **Decisión**: Todos los DTOs en `app/modules/usuarios/schemas.py` utilizan `extra="forbid"` y validadores `@field_validator` invocando `validar_longitud_password`.
  - `UsuarioYoResponse` declara: `id: int`, `email: str`, `nombre: str`, `debe_cambiar_password: bool`, `roles_vigentes: list[str]`, `roles_token: list[str]`.
  - `LoginResponse` declara: `mensaje: str`, `debe_cambiar_password: bool`, `expira_en_segundos: int`.
  - Ningún DTO de respuesta expone `password_hash`.
- **Razón**: Previene excepciones internas 500 en `bcrypt` ante entradas mayores a 72 bytes UTF-8 (RN-15) y provee contratos claros y tipados para el frontend y tests.

## Risks / Trade-offs

- **[Riesgo] Consumo de conexiones por sesión independiente en login**:
  - *Mitigación*: La sesión de auditoría realiza un único `INSERT` y `COMMIT` dentro de un bloque acotado, liberando la conexión inmediatamente.
- **[Riesgo] Saturación de CPU por bcrypt en ráfagas de login**:
  - *Mitigación*: El rate limiting de 5 fallos se verifica en el paso 1 (consulta indexada) ANTES de ejecutar bcrypt (RN-07). Además, todo hash corre bajo el `asyncio.Semaphore(4)` global implementado en C-12.
- **[Riesgo] Fugas de información en errores de integridad**:
  - *Mitigación*: Se capturan `IntegrityError` en los servicios traduciéndolos a `409 Conflict` con mensajes propios, sin filtrar texto interno de PostgreSQL (RN-15).
