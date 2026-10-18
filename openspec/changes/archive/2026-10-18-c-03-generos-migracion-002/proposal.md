# Proposal — C-03 generos-migracion-002

## Why

La consigna del trabajo práctico (Ej. 3 / US-040) exige al menos **dos migraciones** reales y revisadas en `migrations/versions/`, donde la segunda agregue la tabla `genero` y la clave foránea opcional `libro.genero_id`. Asimismo, el módulo `generos` (parte de US-010) inaugura el patrón de contratos DTO separados (`Create`/`Update`/`Read`), paginación acotada (RN-10) y traducción de `IntegrityError` sin exponer detalles internos (RN-12), desbloqueando el resto del CRUD de catálogo en `C-04`.

## What Changes

- Modelo `Genero` (`__tablename__ = "genero"`: `id`, `nombre` `UNIQUE`, relación `libros`) en `app/modules/generos/models.py` y ampliación de `Libro` en `app/modules/libros/models.py` con `genero_id: int | None` (`FK` opcional hacia `genero.id` con índice explícito `ix_libro_genero_id`) y relación bidireccional `genero: Optional[Genero]`.
- Registro de `app.modules.generos.models` en `migrations/env.py` y `app/main.py`.
- Segunda migración autogenerada (`002_add_genero_and_libro_genero_id`) en `migrations/versions/`, leída y revisada manualmente (con comentario de revisión en el encabezado) y verificada mediante el ciclo `downgrade -1` → `upgrade head` sobre PostgreSQL 16.
- Contratos DTO en `app/modules/generos/schemas.py` (`GeneroCreate`, `GeneroUpdate` parcial, `GeneroRead`, y esquema de lectura de libros asociados) separados de los modelos de tabla.
- Servicio y router HTTP en `app/modules/generos/{service,router}.py`:
  - `POST /generos/` → `201 Created` (`409 Conflict` ante nombre duplicado traduciendo `IntegrityError` según RN-12, `422` ante cuerpo inválido).
  - `GET /generos/` → `200 OK` paginado con `limit` (1 a 100, defecto 20) y `offset` (`>= 0`) según RN-10 (`422` fuera de rango).
  - `GET /generos/{id}` → `200 OK` (`404 Not Found` si no existe).
  - `PATCH /generos/{id}` → `200 OK` con actualización parcial (`model_dump(exclude_unset=True)`), `404` si no existe, `409` si el nuevo nombre colisiona con otro género (RN-12).
  - `GET /generos/{id}/libros` → `200 OK` listado paginado (RN-10) de los libros asociados al género (`404` si el género no existe).

## Capabilities

### New Capabilities

- `catalog-generos`: CRUD paginado de géneros (`POST /generos/`, `GET /generos/`, `GET /generos/{id}`, `PATCH /generos/{id}` parcial con `exclude_unset`) y consulta paginada de libros por género (`GET /generos/{id}/libros`), con validación de paginación (RN-10) y traducción de errores de integridad sin filtrar detalles internos (RN-12).

### Modified Capabilities

- `domain-models`: incorpora la entidad `Genero` (`genero` con `nombre UNIQUE`) y la agregación opcional `Libro.genero_id` (`FK` nullable con índice explícito) junto con la navegación bidireccional `libro.genero` ↔ `genero.libros`.
- `schema-migrations`: incorpora la segunda migración autogenerada y revisada (`002`) que evoluciona el esquema agregando `genero` y `libro.genero_id`, verificando la reversibilidad con `downgrade -1` seguido de `upgrade head`.

## Impact

- Archivos afectados:
  - `app/modules/generos/{models,schemas,service,router}.py`
  - `app/modules/libros/models.py`
  - `app/main.py` y `migrations/env.py`
  - `migrations/versions/<rev>_002_add_genero_and_libro_genero_id.py`
  - `tests/test_generos_and_migration_002.py` y ajuste de aserciones de esquema a nivel `head` en `tests/test_core_models_and_migration_001.py`
- Desbloquea `C-04` (`catalogo-crud`).
