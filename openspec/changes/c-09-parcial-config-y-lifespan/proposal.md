# Proposal

## Why

La Etapa 2 del proyecto (Parcial Integrador Capítulos 1 a 6, Ejercicio 1) exige endurecer la configuración y el ciclo de vida de la aplicación antes de incorporar los modelos de seguridad, autenticación y el patrón Unit of Work: la configuración debe validarse estrictamente con `pydantic-settings` sin secretos ni valores por defecto para credenciales críticas (`POSTGRES_PASSWORD` y `JWT_SECRET`), el `lifespan` debe configurar el pool del motor asincrónico y precalcular una única vez el hash ficticio de login (`dummy_password_hash`) para mitigar enumeración de usuarios por tiempos de respuesta (RN-08), el módulo `health` debe simplificarse a un único archivo `router.py`, y `app/main.py` debe estructurar los dos grupos de rutas (`abierto` y `protegido`) sobre los que se montará la seguridad del sistema.

## What Changes

- **BREAKING**: Reemplazo de `Settings` (`@dataclass`) en `app/core/config.py` por `Settings(BaseSettings)` basado en `pydantic-settings>=2.0`, leyendo variables `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `JWT_SECRET`, `JWT_EXPIRATION_SECONDS`, `BCRYPT_ROUNDS`, `COOKIE_SECURE`, `DB_POOL_SIZE` y `SQL_ECHO`, y construyendo `DATABASE_URL` (`postgresql+asyncpg://...`) mediante `@computed_field`. Ni `POSTGRES_PASSWORD` ni `JWT_SECRET` tienen valor por defecto: si faltan, la instanciación falla con `ValidationError` e impide que la aplicación arranque.
- Actualización de `requirements.txt` y `env.example` incorporando `pydantic-settings>=2.0`, `bcrypt>=4.0` y `PyJWT>=2.8`, y documentando todas las variables de entorno requeridas sin credenciales reales.
- Actualización de `app/core/database.py` y del `lifespan` en `app/main.py` para construir el motor asincrónico pasando `pool_size=settings.DB_POOL_SIZE` y `echo=settings.SQL_ECHO`, crear la fábrica de sesiones (`async_sessionmaker(..., expire_on_commit=False)`), calcular una única vez el hash ficticio de `bcrypt` al costo `settings.BCRYPT_ROUNDS`, guardar `engine`, `session_factory` y `dummy_password_hash` en `app.state` (nunca al importar el módulo), y cerrar el motor con `await engine.dispose()` al apagar.
- Simplificación de `app/modules/health/` dejando únicamente `router.py` (eliminando `models.py`, `schemas.py` y `service.py` del módulo `health`), manteniendo `GET /health/live` (`200`) sin tocar la base y `GET /health/ready` ejecutando `SELECT 1` (`200` si responde o `503` sin filtrar detalles internos si falla).
- Estructuración de dos grupos de rutas (`router_abierto` y `router_protegido`) en `app/main.py` para centralizar en un único punto el futuro montaje de la dependencia de bloqueo por cambio obligatorio de contraseña (`debe_cambiar_password`).

## Capabilities

### New Capabilities
- *(Ninguna capacidad nueva: se extienden y actualizan las capacidades fundacionales existentes).*

### Modified Capabilities
- `app-lifecycle`: La configuración pasa a componerse desde variables `POSTGRES_*` mediante `pydantic-settings` (`@computed_field` `DATABASE_URL`) exigiendo `POSTGRES_PASSWORD` y `JWT_SECRET` sin valores por defecto al arrancar; el `lifespan` configura `pool_size=DB_POOL_SIZE` en el motor asincrónico, calcula una única vez `app.state.dummy_password_hash` con `bcrypt` y organiza la aplicación en dos grupos de rutas (`abierto` y `protegido`).
- `health`: El módulo `app/modules/health/` pasa a contener exclusivamente `router.py`, manteniendo el contrato de `GET /health/live` (`200`) y `GET /health/ready` (`200` con `SELECT 1` o `503` cuando la base no contesta, sin exponer detalles internos).

## Impact

- **Dependencias (`requirements.txt`)**: Agrega `pydantic-settings>=2.0`, `bcrypt>=4.0` y `PyJWT>=2.8`.
- **Variables de entorno (`env.example`, `.env`)**: Transición de `DATABASE_URL` plana a variables desglosadas `POSTGRES_*` + `JWT_*` + `BCRYPT_ROUNDS` + `COOKIE_SECURE` + `DB_POOL_SIZE` + `SQL_ECHO`.
- **Código afectado**:
  - `app/core/config.py`: Nueva clase `Settings(BaseSettings)` con `@computed_field` `DATABASE_URL` y compatibilidad para `migrations/env.py`.
  - `app/core/database.py`: Parametrización de `pool_size` en `build_engine`.
  - `app/main.py`: Cálculo de `app.state.dummy_password_hash` en `lifespan` y separación de `router_abierto` y `router_protegido`.
  - `app/modules/health/`: Consolidación en `app/modules/health/router.py` y remoción de `models.py`, `schemas.py` y `service.py`.
  - `migrations/env.py`: Uso de `settings.DATABASE_URL` (o propiedad compatible) desde `get_settings()`.
  - `test/test_health_and_lifecycle.py` y `test/conftest.py`: Actualización y ampliación de pruebas para cubrir validación de `Settings` sin secretos por defecto, `dummy_password_hash`, estructura exclusiva de `health/router.py` y grupos de rutas.
