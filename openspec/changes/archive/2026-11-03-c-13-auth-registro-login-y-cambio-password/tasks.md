# Tasks

## 1. Repositorios y Unit of Work de Identidad (Strict TDD)

- [x] 1.1 Implementar `ClienteRepository` en `app/modules/clientes/repository.py` heredando de `BaseRepository[Cliente]`, con métodos `get_by_id`, `get_by_email` y `add`; escribir primero pruebas unitarias (RED) en `test/test_auth_endpoints.py` que fallen y luego pasar a verde (GREEN).
- [x] 1.2 Implementar `UsuarioRepository`, `AsignacionRolRepository`, `IntentoAccesoRepository` y `EventoSeguridadRepository` en `app/modules/usuarios/repository.py` heredando de `BaseRepository` y agregar el método `contar_fallos_recientes` en `IntentoAccesoRepository`; escribir pruebas unitarias de persistencia y conteo de fallos (RED) y pasar a verde (GREEN).
- [x] 1.3 Implementar `UsuariosUnitOfWork` en `app/modules/usuarios/unit_of_work.py` agrupando los repositorios de usuarios, roles, intentos de acceso, eventos de seguridad y componiendo `ClienteRepository` con la misma sesión; verificar en pruebas transaccionales (RED -> GREEN) el comportamiento atómico de `commit()` y `rollback()`.

## 2. Contratos DTO y Validación Estricta

- [x] 2.1 Escribir pruebas unitarias (RED) para validaciones de esquema y definir en `app/modules/usuarios/schemas.py` los esquemas `UsuarioRegistroRequest`, `LoginRequest`, `LoginResponse`, `UsuarioYoResponse`, `CambiarPasswordRequest` y `MensajeResponse`, asegurando `extra="forbid"`, validación de contraseñas $\le 72$ bytes UTF-8 (`validar_longitud_password` $\to$ 422) y omisión total de `password_hash` (GREEN).

## 3. Servicio de Autenticación y Auditoría Independiente

- [x] 3.1 Escribir pruebas unitarias (RED) para `registro` e implementar en `app/modules/usuarios/service.py`: calcular hash fuera del UoW, crear `Usuario`, `AsignacionRol(rol="CLIENTE")` y `Cliente` en un solo UoW traduciendo `IntegrityError` por email existente en usuario o cliente a 409 con mensaje propio (RN-02, C-02) (GREEN).
- [x] 3.2 Escribir pruebas unitarias (RED) para `login` e implementar en `app/modules/usuarios/service.py`: verificar límite de 5 fallos en 60 segundos desde el último éxito (persistencia de intento fallido en sesión aislada y 429 con header `Retry-After: 60`, RN-07, C-05), validación de contraseña en tiempo constante contra dummy si no existe el usuario (RN-08, C-04), auditoría de intento en `intento_acceso` usando `session_factory` independiente con el comentario declarativo obligatorio de 3 puntos (DD-09, Ej. 7), y emisión de token (GREEN).
- [x] 3.3 Escribir pruebas unitarias (RED) para `obtener_yo` y `cambiar_password` e implementar en `app/modules/usuarios/service.py`: introspección de roles vigentes en base vs token (C-07) y cambio de contraseña con validación previa, nuevo hash fuera del UoW, reseteo de `debe_cambiar_password=False` y registro en `evento_seguridad` en el mismo UoW (RN-16, C-09) (GREEN).

## 4. Router `/auth` e Integración en la Aplicación

- [x] 4.1 Escribir pruebas de integración API (RED) e implementar `app/modules/usuarios/router.py` con los endpoints `POST /registro` (201, 409, 422), `POST /login` (200 con cookie `access_token` `HttpOnly`, 401, 422, 429), `POST /logout` (200 idempotente con borrado de cookie), `GET /yo` (200 autenticado) y `POST /cambiar-password` (200 autenticado, 401, 422), inyectando dependencias con sesión compartida (GREEN).
- [x] 4.2 Montar el router `/auth` en `open_group` y asegurar en `app/main.py` la disponibilidad de `application.state.session_factory` (y alias `session_maker`); verificar que todos los endpoints respondan correctamente en FastAPI (GREEN).

## 5. Verificación Integral y Suite de Pruebas

- [x] 5.1 Ejecutar la suite completa de pruebas unitarias y de integración en `test/test_auth_endpoints.py` validando los casos `C-02` (registro atómico y 409), `C-03` (cookie HttpOnly y logout), `C-04` (tiempo constante contra dummy y 401 genérico), `C-05` (rate limit 429 y reinicio post-éxito) y `C-09` (cambio de password con auditoría en la misma transacción), asegurando 100% de tests en verde sin regresiones en la suite del proyecto.
