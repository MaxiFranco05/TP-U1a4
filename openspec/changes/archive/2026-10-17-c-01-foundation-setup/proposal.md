# Proposal — C-01 foundation-setup

## Why

El proyecto no existe todavía como código: solo hay fundación documental (KB, CHANGES.md, specs vacías). Sin scaffolding, conexión y ciclo de vida no hay base sobre la que construir los 7 changes restantes — C-02 (modelos + migración 001) depende entera de esta base. Además, este change resuelve PA-01 (proveer Python 3.12 en paralelo a la 3.14 instalada) antes de crear el primer venv.

## What Changes

- Estructura obligatoria por módulo: `app/main.py`, `app/core/config.py`, `app/core/database.py` y esqueleto de los 7 módulos (`health`, `editoriales`, `generos`, `autores`, `libros`, `clientes`, `ventas`) con `models.py`/`schemas.py`/`service.py`/`router.py` vacíos o mínimos.
- Motor asincrónico + fábrica de sesiones creados en el `lifespan`, guardados en `app.state`; el motor se cierra al apagar. Sesión por petición vía `Depends(get_session)` con `expire_on_commit=False`.
- `GET /health/live` → `{"estado": "vivo"}` 200 sin tocar la base; `GET /health/ready` → `SELECT 1`, falla controlada si la base no responde (sin traza interna, RN-12).
- `requirements.txt` con versiones mínimas de la consigna, `.env` (no versionado) + `env.example` (`DATABASE_URL`, `SQL_ECHO`), `compose.yaml` con PostgreSQL 16 para dev (PA-04, documentado como comodidad local, no parte de la entrega).
- Alembic inicializado con plantilla asincrónica en `migrations/` (sin versiones aún); `alembic.ini` sin contraseñas.
- Entorno Python 3.12 resuelto (PA-01) y decisión PA-02 asentada (VPS/Easypanel solo deploy opcional post-entrega).

## Capabilities

### New Capabilities

- `app-lifecycle`: ciclo de vida de la aplicación y de la conexión a la base — creación del motor y la fábrica de sesiones en el lifespan, sesión por petición, cierre ordenado al apagar.
- `health`: sondas de salud — liveness sin dependencia de la base y readiness con verificación `SELECT 1`.

### Modified Capabilities

(none — greenfield, sin specs previas que modificar)

## Impact

- Crea el árbol `app/`, `migrations/`, `requirements.txt`, `env.example`, `compose.yaml` — todo el código posterior vive dentro de esta estructura.
- Desbloquea C-02 (modelos + migración 001) y transitivamente todo el camino crítico.
- Sin cambios rompientes: no hay consumidores previos.
