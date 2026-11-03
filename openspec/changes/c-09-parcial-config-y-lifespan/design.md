# Design

## UI Mockups

Decision: no (no UI)

## Context

En la Etapa 1 (TP Capítulos 1 a 4), `app/core/config.py` utilizaba un `@dataclass` básico que leía `DATABASE_URL` con `os.getenv` y proveía una URL de respaldo (`DEFAULT_UNCONFIGURED_URL`) cuando faltaba configuración, mientras que `app/modules/health/` estaba dividido en `router.py`, `service.py`, `schemas.py` y `models.py`, y `app/main.py` registraba todos los routers directamente sobre la instancia `FastAPI`.

Para la Etapa 2 (Parcial Capítulos 1 a 6, Ejercicio 1 — ver `proposal.md`), el sistema requiere validación tipada en el arranque mediante `pydantic-settings`, prohibición estricta de secretos por defecto para `POSTGRES_PASSWORD` y `JWT_SECRET`, configuración explícita del tamaño del pool en el motor asincrónico, cálculo único de `dummy_password_hash` en el `lifespan`, consolidación del módulo `health` en un único archivo `router.py` y separación de rutas en dos grupos (`router_abierto` y `router_protegido`).

## Goals / Non-Goals

**Goals:**
- Garantizar mediante `pydantic-settings` que la aplicación falle inmediatamente al instanciar `Settings` si faltan `POSTGRES_PASSWORD` o `JWT_SECRET`, y construir `DATABASE_URL` con `@computed_field` a partir de `POSTGRES_*`.
- Mantener la creación del motor asincrónico (`create_async_engine`), la fábrica de sesiones (`async_sessionmaker(..., expire_on_commit=False)`) y el cálculo del hash ficticio (`bcrypt`) estrictamente dentro del `lifespan` de `app/main.py` (nunca al importar un módulo), guardándolos en `app.state`.
- Consolidar `app/modules/health/` para que contenga únicamente `router.py` (además de `__init__.py` si aplica para paquete), preservando `GET /health/live` (`200`) y `GET /health/ready` (`SELECT 1` → `200` o `503` sin detalles internos).
- Estructurar en `app/main.py` dos `APIRouter` de nivel superior (`router_abierto` y `router_protegido`) listos para que `C-12`/`C-13`/`C-14`/`C-15`/`C-16` monten una sola vez el control de cambio obligatorio de contraseña sobre el grupo protegido.
- Preservar compatibilidad con `migrations/env.py` y la suite de tests existente.

**Non-Goals:**
- Implementar en este change la lógica completa de JWT, el semáforo de `bcrypt` por petición o las dependencias `get_usuario_actual` / `requiere_rol` (corresponden a `C-12`).
- Crear los modelos de `usuarios` o `movimiento_stock` ni las migraciones `003` y `004` (corresponden a `C-10`).
- Refactorizar los módulos de catálogo, clientes y ventas a `Repository` + `UnitOfWork` (corresponde a `C-11`, `C-15` y `C-16`).

## Decisions

### 1. Clase `Settings(BaseSettings)` en `app/core/config.py` con `@computed_field`
- **Decisión**: Implementar `Settings(BaseSettings)` heredando de `pydantic_settings.BaseSettings` con `SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")`.
  - Campos de base de datos:
    - `POSTGRES_USER: str = "postgres"`
    - `POSTGRES_PASSWORD: str` (**sin valor por defecto**, obligatorio)
    - `POSTGRES_DB: str = "libreria"`
    - `POSTGRES_HOST: str = "localhost"`
    - `POSTGRES_PORT: int = 5432`
  - Campo calculado `@computed_field @property def DATABASE_URL(self) -> str`: retorna `f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"`.
  - Campos de seguridad y motor:
    - `JWT_SECRET: str` (**sin valor por defecto**, obligatorio; además se rechaza string vacío/en blanco con validador `min_length=1`)
    - `POSTGRES_PASSWORD: str` (con `min_length=1` para impedir contraseñas vacías silenciosas)
    - `JWT_EXPIRATION_SECONDS: int = 1800`
    - `BCRYPT_ROUNDS: int = 12`
    - `COOKIE_SECURE: bool = False`
    - `DB_POOL_SIZE: int = 5`
    - `SQL_ECHO: bool = False`
  - Compatibilidad con código existente y `migrations/env.py`: exponer propiedades de solo lectura `database_url` (alias a `self.DATABASE_URL`) y `sql_echo` (alias a `self.SQL_ECHO`), o actualizar `migrations/env.py` para leer `settings.DATABASE_URL` manteniendo `database_url` como propiedad puente para no romper importadores previos.
  - Eliminar `DEFAULT_UNCONFIGURED_URL`. `get_settings()` instancia y retorna `Settings()`.
- **Alternativas consideradas**:
  - *Recibir `DATABASE_URL` directo como variable de entorno*: descartado porque las reglas duras y el Ejercicio 1 exigen explícitamente armar `DATABASE_URL` con `@computed_field` desde `POSTGRES_*` y fallar si falta `POSTGRES_PASSWORD` o `JWT_SECRET`.
  - *Instanciar `settings = Settings()` a nivel global al importar `config.py`*: se mantiene `get_settings() -> Settings` llamada desde el `lifespan` (y en el arranque de `app/main.py` o `lifespan`) para permitir que los tests con `monkeypatch` modifiquen variables de entorno y verifiquen limpiamente el fallo de `Settings()` cuando faltan `POSTGRES_PASSWORD` o `JWT_SECRET`.

### 2. Motor con `pool_size`, fábrica de sesiones y `dummy_password_hash` en `lifespan`
- **Decisión**:
  - En `app/core/database.py`: actualizar `build_engine(database_url: str, sql_echo: bool = False, pool_size: int = 5) -> AsyncEngine` para pasar `echo=sql_echo` y `pool_size=pool_size` a `create_async_engine`. Mantener `build_session_factory(engine)` con `async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)` y `get_session(request: Request)` leyendo `request.app.state.session_factory`. Ningún motor ni fábrica se crea al importar `database.py`.
  - En el `lifespan` de `app/main.py`:
    1. Obtener `settings = get_settings()`.
    2. Crear `engine = build_engine(database_url=settings.DATABASE_URL, sql_echo=settings.SQL_ECHO, pool_size=settings.DB_POOL_SIZE)` y `session_factory = build_session_factory(engine)`.
    3. Calcular **una única vez** el hash ficticio de login usando `bcrypt.hashpw(b"dummy-password-parcial", bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode("utf-8")` (ejecutado con `await asyncio.to_thread(...)` para respetar la regla dura de nunca correr `bcrypt` en el event loop).
    4. Guardar `application.state.settings = settings`, `application.state.engine = engine`, `application.state.session_factory = session_factory` y `application.state.dummy_password_hash = dummy_password_hash`.
    5. En el bloque `finally:`, ejecutar `await engine.dispose()`.
- **Alternativas consideradas**:
  - *Calcular el hash ficticio en cada login fallido sin usuario*: descartado porque duplica el trabajo de generación de sal y la consigna (Ej. 1 y Flujo 1) exige calcularlo una sola vez en el `lifespan` y guardarlo en `app.state.dummy_password_hash`.

### 3. Simplificación de `app/modules/health/` a sólo `router.py`
- **Decisión**:
  - Eliminar `app/modules/health/models.py`, `app/modules/health/schemas.py` y `app/modules/health/service.py`.
  - Concentrar en `app/modules/health/router.py` los esquemas de respuesta (`HealthLiveResponse`, `HealthReadyResponse`) y los dos endpoints:
    - `GET /health/live` → retorna `{"estado": "vivo"}` con HTTP `200` sin tocar la base de datos.
    - `GET /health/ready` → recibe `session: SessionDep`, ejecuta `await session.execute(text("SELECT 1"))` y retorna `{"estado": "listo"}` (`200`); ante cualquier excepción captura el error y lanza `HTTPException(status_code=503, detail="Base de datos no disponible")` sin exponer cadenas de conexión, nombres de tablas ni trazas (RN-15).
- **Alternativas consideradas**:
  - *Mantener `service.py` y `schemas.py` en `health`*: descartado porque la consigna del Parcial y `AGENTS.md` especifican taxativamente: *"El módulo `health` sólo tiene `router.py`"*.

### 4. Dos grupos de rutas (`router_abierto` y `router_protegido`) en `app/main.py`
- **Decisión**:
  - Definir en `app/main.py` (o función constructora en `app/main.py`) dos `APIRouter`:
    - `router_abierto = APIRouter()`: agrupa las rutas públicas/abiertas que no exigen rol ni bloquean por cambio obligatorio de contraseña (`/health/*`, y en próximos changes `/auth/*` y las lecturas públicas del catálogo).
    - `router_protegido = APIRouter(dependencies=[...])`: agrupa las rutas que requerirán sesión activa y tendrán montada **una sola vez** la dependencia de bloqueo por `debe_cambiar_password=True` (en `C-09` se deja la lista `dependencies=[]` o un gancho claro listo para que `C-12` conecte la dependencia sin reestructurar `main.py`, y mientras no esté `C-15`/`C-16`, los routers actuales se montan manteniendo la compatibilidad de los tests existentes del TP).
  - Ambos grupos se registran en `application` mediante `application.include_router(router_abierto)` y `application.include_router(router_protegido)`.
- **Alternativas consideradas**:
  - *Agregar la dependencia en cada endpoint individual en `C-12..C-16`*: descartado porque viola la regla de arquitectura del Parcial ("montar una sola vez el control de cambio obligatorio de contraseña en el grupo protegido").

## Risks / Trade-offs

- **[Risk] Los tests existentes de la Etapa 1 pueden correr en entornos donde no estén definidas `POSTGRES_PASSWORD` o `JWT_SECRET`** → **Mitigation**: Configurar en `test/conftest.py` (mediante `os.environ.setdefault` o fixture `autouse`) valores de prueba seguros para `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `JWT_SECRET` y `BCRYPT_ROUNDS=4` (rondas mínimas de `bcrypt` en tests para no penalizar la velocidad de la suite), mientras que los tests específicos de `C-09` usan `monkeypatch.delenv` para probar explícitamente el fallo de arranque cuando faltan `POSTGRES_PASSWORD` o `JWT_SECRET`.
- **[Risk] Test `test_module_structure_and_env_example_have_no_secrets` en `test/test_health_and_lifecycle.py` exigía que `health` tuviera `models.py`, `schemas.py` y `service.py`** → **Mitigation**: Actualizar ese test en `test/test_health_and_lifecycle.py` para verificar la nueva regla del Parcial: `app/modules/health/` sólo debe contener `router.py` (sin `models.py`, `schemas.py` ni `service.py`), y `env.example` debe documentar las nuevas variables `POSTGRES_*`, `JWT_*`, `BCRYPT_ROUNDS`, `COOKIE_SECURE`, `DB_POOL_SIZE` y `SQL_ECHO`.
