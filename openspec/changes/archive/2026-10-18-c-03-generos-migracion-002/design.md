# Design — C-03 generos-migracion-002

## Context

Tras `C-02`, la base de datos cuenta con las 8 tablas core iniciales bajo la migración `001` (`246164acdc52`). Para satisfacer el Ejercicio 3 de la consigna (US-040: al menos dos migraciones autogeneradas, leídas y comentadas, donde la segunda evoluciona el esquema agregando `genero` y `libro.genero_id`, y verificación de `downgrade -1` + `upgrade head`) y abrir los endpoints de catálogo (US-010), este change incorpora el modelo `Genero`, la FK opcional en `Libro`, la migración `002` y el CRUD completo de `/generos`. Ver `proposal.md` y `specs/` para los requisitos detallados.

## Goals / Non-Goals

**Goals:**
- Incorporar `Genero` (`genero`) y `Libro.genero_id` (`nullable=True`, FK indexada) + relación bidireccional `Libro.genero` ↔ `Genero.libros`.
- Generar con `alembic revision --autogenerate`, revisar manualmente y verificar la **migración 002** (`downgrade -1` + `upgrade head`).
- Implementar los contratos DTO, servicio y router de `/generos` (`POST /generos/`, `GET /generos/`, `GET /generos/{id}`, `PATCH /generos/{id}`, `GET /generos/{id}/libros`) cumpliendo RN-10 y RN-12.

**Non-Goals:**
- CRUD de `editoriales`, `autores` y `libros` (pertenecen a `C-04`).
- CRUD de `clientes` y `perfil_cliente` (pertenecen a `C-05`).

## Decisions

### DD-C03-01 — Relación `Libro`–`Genero` como agregación opcional (`genero_id` nullable con índice explícito)

En `Libro` (`app/modules/libros/models.py`), `genero_id: int | None = Field(default=None, foreign_key="genero.id", index=True, nullable=True)` modela la agregación opcional requerida por `04_modelo_de_datos.md`. El índice explícito `ix_libro_genero_id` acelera tanto `GET /generos/{id}/libros` como el futuro filtro `GET /libros/?genero_id=...` de `C-04`.

### DD-C03-02 — Revisión manual de la migración 002 y orden de `downgrade()`

Al ejecutar `alembic revision --autogenerate -m "002_add_genero_and_libro_genero_id"`, se revisa manualmente el script generado en `migrations/versions/` para asegurar que:
1. `upgrade()` cree primero la tabla `genero` (con `UniqueConstraint('nombre')`), luego agregue la columna `libro.genero_id`, cree el índice `ix_libro_genero_id` y registre la `ForeignKeyConstraint` hacia `genero.id`.
2. `downgrade()` elimine en orden inverso la `ForeignKeyConstraint`, el índice `ix_libro_genero_id`, la columna `libro.genero_id` y finalmente la tabla `genero`, permitiendo ejecutar `alembic downgrade -1` y `alembic upgrade head` sin errores de dependencia.

### DD-C03-03 — DTOs separados (`GeneroCreate`, `GeneroUpdate`, `GeneroRead`, `LibroSimpleRead`)

Siguiendo la arquitectura propuesta (`08_arquitectura_propuesta.md`), los modelos con `table=True` nunca se exponen directamente como esquema de entrada:
- `GeneroCreate`: `nombre: str` validado (`min_length=1`, recortando espacios en blanco o rechazando cadenas vacías con `422`), sin `id`.
- `GeneroUpdate`: `nombre: str | None = None` (validado si se envía), aplicado con `payload.model_dump(exclude_unset=True)` en `PATCH /generos/{id}`.
- `GeneroRead`: `id: int`, `nombre: str`.
- `GeneroLibroRead`: DTO de salida para los elementos de `GET /generos/{id}/libros` (`id`, `isbn`, `titulo`, `precio`, `stock`, `editorial_id`, `genero_id`).

### DD-C03-04 — Traducción de `IntegrityError` a HTTP 409 en el service (RN-12 y DD-04)

Ni `create_genero` ni `update_genero` ejecutan un `SELECT` previo con `if` para verificar si `nombre` ya existe (prohibido por Reglas Duras / DD-04). Se delega la unicidad en el constraint `UNIQUE` de PostgreSQL; si `await session.commit()` lanza `IntegrityError`, el service hace `await session.rollback()` y lanza `HTTPException(status_code=409, detail="Ya existe un género con ese nombre")`, sin exponer jamás mensajes de `asyncpg`, nombres de tablas/constraints ni trazas (RN-12).

### DD-C03-05 — Verificación de existencia del género en `GET /generos/{id}/libros`

Para distinguir entre un género existente sin libros (`200 OK` con `[]`) y un género inexistente (`404 Not Found`), `list_libros_by_genero` verifica primero que el género `{id}` exista mediante `session.get(Genero, genero_id)` (una lectura por PK para un sub-recurso de consulta GET, no una validación previa a escritura) y luego ejecuta la consulta paginada sobre `Libro` filtrada por `Libro.genero_id == genero_id` con `limit` y `offset`.

## Risks / Trade-offs

- [Tests de `C-02` que verificaban que en la base solo existían las 8 tablas iniciales] → Mitigación: actualizar la aserción de esquema en `tests/test_core_models_and_migration_001.py` para que verifique que las 8 tablas core están presentes en `head` y que el archivo de la migración `001` no contiene `genero`, mientras que `tests/test_generos_and_migration_002.py` prueba específicamente el ciclo `downgrade -1` (8 tablas, sin `genero`) y `upgrade head` (9 tablas, con `genero` y `libro.genero_id`).

## Migration Plan

1. Implementar `Genero` en `app/modules/generos/models.py` y agregar `genero_id` + `genero` en `Libro` (`app/modules/libros/models.py`).
2. Registrar `app.modules.generos.models` en `migrations/env.py` y `app/main.py`.
3. Generar la migración `002` con `alembic revision --autogenerate -m "002_add_genero_and_libro_genero_id"`, revisarla manualmente y documentar la revisión.
4. Ejecutar `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` → `alembic check`.
5. Implementar `schemas.py`, `service.py` y `router.py` en `app/modules/generos/`.

## Open Questions

Ninguna.
