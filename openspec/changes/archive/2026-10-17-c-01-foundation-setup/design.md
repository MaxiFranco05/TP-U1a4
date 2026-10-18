# Design — C-01 foundation-setup

## Context

Greenfield: no hay código, solo fundación documental. La consigna fija stack (Python 3.12, FastAPI ≥ 0.111, SQLModel, SQLAlchemy 2.0 async, asyncpg, PG16, Alembic async) y estructura por módulo. Entorno real: Windows, Docker 29.7 disponible, Python 3.14 instalado (falta 3.12 — PA-01), sin servidor PG16. Ver proposal.md (Why) y `specs/` (requisitos de `app-lifecycle` y `health`).

## Goals / Non-Goals

**Goals:** dejar el esqueleto ejecutable (app levanta, healthchecks responden, Alembic inicializado, PG16 en Docker) y el entorno Python 3.12 resuelto.

**Non-Goals:** modelos de dominio (C-02), endpoints de negocio (C-04+), seed y `.http` (C-08), deploy en VPS (PA-02, post-entrega).

## Decisions

### DD-C01-01 — Python 3.12 instalado en paralelo vía instalador oficial

Usar el instalador de python.org (3.12.x) junto a la 3.14 existente y crear el venv con `py -3.12 -m venv .venv`. Alternativas: `pyenv-win` (más piezas móviles en Windows), Docker también para Python (el TP se desarrolla y corrige con Python local; el contenedor solo lleva la base). Se elige lo más simple y reversible.

### DD-C01-02 — PostgreSQL 16 en Docker vía `compose.yaml` solo-dev

Servicio `postgres:16` con volumen nombrado, puerto 5432 y healthcheck; `DATABASE_URL` apunta a localhost. Alternativas: PG instalado en Windows (instalación pesada, versión a gestionar), PG remoto en Easypanel (red, latencia, credenciales remotas — DD-02 ya lo descartó para dev). El `compose.yaml` se documenta como comodidad local, no parte de la entrega (PA-04).

### DD-C01-03 — Lifespan con motor y sesiones en `app.state`

El `lifespan` crea `create_async_engine` + `async_sessionmaker` y los guarda en `app.state`; al salir, `engine.dispose()`. Alternativa: crear el motor a nivel de módulo (acopla import-time con configuración y dificulta tests). El lifespan es lo que evalúa el Ej.1.

### DD-C01-04 — `get_session` con `Depends()` y `expire_on_commit=False`

Una sesión por petición, cerrada al responder. Sin `expire_on_commit=False`, los objetos devueltos tras commit dispararían IO perezoso (prohibido por Ej.6). Sin alternativa razonable dentro de la consigna.

### DD-C01-05 — Alembic con plantilla asincrónica desde el día uno

`alembic init -t async migrations` ahora, sin versiones (llegan en C-02/C-03). Alternativa: inicializar después — pero el Ej.3 exige plantilla async y es más barato dejarla lista. `alembic.ini` sin secretos (la URL la inyecta `env.py` desde el entorno).

### DD-C01-06 — Esqueleto de los 7 módulos, solo `health` funcional

Se crean las carpetas y archivos de los 7 módulos para fijar la estructura; solo `health` trae router real. Alternativa: crear módulos a medida que se necesitan — dispersa la decisión estructural y C-02 la necesita ya fijada.

### DD-C01-07 — `requirements.txt` con mínimos de la consigna

Pines `>=` según la tabla del stack (no `==` exactos que se pudran, no rangos abiertos que sorprendan). `SQL_ECHO` por env para la evidencia C-07 futura.

## Risks / Trade-offs

- [Puerto 5432 ocupado por otro Postgres local] → Mitigación: antes de levantar, verificar qué escucha en 5432; si hay conflicto, mapear otro puerto en `compose.yaml` y ajustar `DATABASE_URL`.
- [Docker daemon apagado en Windows] → Mitigación: documentar el arranque de Docker Desktop como paso 0 del README de dev.
- [`py` launcher sin 3.12 registrado] → Mitigación: reinstalar marcando "py launcher" o usar la ruta completa del ejecutable 3.12.
- [asyncpg compilación en Windows] → Mitigación: hay wheels para 3.12; si falla, el fallback es `psycopg[binary]` async — cambiaría el driver pero no los requisitos de comportamiento.

## Migration Plan

No aplica (greenfield, sin datos). Secuencia de puesta en marcha: instalar Python 3.12 → venv + `pip install -r requirements.txt` → `docker compose up -d` → `uvicorn app.main:app` → verificar `/health/live` (200 sin base) y `/health/ready` (200 con base). Rollback: `docker compose down -v` + borrar `.venv`.

## Open Questions

Ninguna que cambie specs, enfoque o tareas. PA-03 (contenido del seed) pertenece a C-08; PA-02 quedó asentada como deploy post-entrega.
