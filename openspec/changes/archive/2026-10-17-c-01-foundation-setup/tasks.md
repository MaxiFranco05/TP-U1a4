# Tasks — C-01 foundation-setup

## 1. Entorno Python 3.12 (PA-01)

- [x] 1.1 Instalar Python 3.12 en paralelo a la 3.12/3.14 existente y verificar con `py -3.12 --version` (o ruta completa del ejecutable) que responde 3.12.x
- [x] 1.2 Crear el venv con Python 3.12 (`py -3.12 -m venv .venv`) y verificar que `.venv/Scripts/python --version` responde 3.12.x

## 2. Scaffolding app + core

- [x] 2.1 Crear `app/main.py` (app + lifespan: motor y fábrica de sesiones en `app.state`, cierre del motor al apagar) y `app/core/config.py` (`DATABASE_URL` desde entorno) + `app/core/database.py` (motor async, `async_sessionmaker`, `get_session` con `expire_on_commit=False`); verificar que `python -c "import app.main"` importa sin errores
- [x] 2.2 Crear el esqueleto de los 7 módulos (`health`, `editoriales`, `generos`, `autores`, `libros`, `clientes`, `ventas`) con `models.py`/`schemas.py`/`service.py`/`router.py` y registrar los routers en `main.py`; verificar la estructura con el árbol de directorios esperado en `08_arquitectura_propuesta.md`

## 3. Healthchecks (capability `health`)

- [x] 3.1 Implementar `GET /health/live` → `{"estado": "vivo"}` 200 sin tocar la base; verificar con el servidor levantado y la base apagada que responde 200
- [x] 3.2 Implementar `GET /health/ready` (`SELECT 1` vía `get_session`); verificar 200 con base arriba y fallo controlado sin internos (sin tablas, trazas ni connection strings) con base abajo

## 4. Dependencias, entorno y base local

- [x] 4.1 Escribir `requirements.txt` (mínimos de la consigna) + `.env` (no versionado) + `env.example` (`DATABASE_URL`, `SQL_ECHO`, sin secretos); verificar `pip install -r requirements.txt` termina sin errores dentro del venv 3.12
- [x] 4.2 Escribir `compose.yaml` (PostgreSQL 16, volumen nombrado, healthcheck, puerto 5432 o alternativo si está ocupado); verificar `docker compose up -d` deja el servicio `healthy` y `psql`/`pg_isready` conecta

## 5. Alembic asincrónico

- [x] 5.1 Inicializar Alembic con plantilla asincrónica en `migrations/` (`alembic.ini` sin contraseñas, URL inyectada desde el entorno en `env.py`); verificar `alembic current` corre sin errores y no hay versiones aún

## 6. Verificación de integración

- [x] 6.1 Levantar el stack completo desde cero (venv → install → `docker compose up -d` → `uvicorn app.main:app`) y verificar `/health/live` 200 y `/health/ready` 200, más `ready` en fallo con base detenida
- [x] 6.2 Dejar asentado en un `README.dev.md` (o sección dev del futuro README) el orden de arranque, el puerto final de PG y la decisión PA-02 (VPS solo post-entrega); verificar siguiendo esos pasos en una terminal limpia

## Workflow follow-up

- Proponer el commit sugerido y que el usuario lo ejecute: `git commit -m "C-01: foundation + healthchecks"` (nunca commitear de forma autónoma).
- Archivar el change con `/opsx:archive c-01-foundation-setup` cuando la revisión esté satisfecha.
