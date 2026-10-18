# Tasks — C-03 generos-migracion-002

## 1. Modelo `Genero` y relación opcional en `Libro` (`domain-models`)

- [x] 1.1 Implementar `Genero` (`__tablename__ = "genero"`: `id`, `nombre` `UNIQUE`, relación `libros`) en `app/modules/generos/models.py` y extender `Libro` en `app/modules/libros/models.py` con `genero_id: int | None` (`FK` a `genero.id`, `nullable=True`, `index=True`) y relación `genero: Optional[Genero]`; verificar que `SQLModel.metadata.tables` registra `genero` y la columna `libro.genero_id`

## 2. Migración 002 autogenerada, revisada y reversible (`schema-migrations`)

- [x] 2.1 Registrar `app.modules.generos.models` en `migrations/env.py` y `app/main.py` y generar la segunda migración con `.\.venv\Scripts\alembic revision --autogenerate -m "002_add_genero_and_libro_genero_id"`
- [x] 2.2 Leer y revisar manualmente el archivo generado en `migrations/versions/`, verificando `create_table('genero')`, `add_column('libro', 'genero_id')`, índice explícito `ix_libro_genero_id`, `ForeignKeyConstraint` hacia `genero.id` y el orden inverso en `downgrade()` (documentando la revisión en el encabezado del archivo)
- [x] 2.3 Ejecutar `.\.venv\Scripts\alembic upgrade head`, `.\.venv\Scripts\alembic downgrade -1`, `.\.venv\Scripts\alembic upgrade head` y `.\.venv\Scripts\alembic check` contra PostgreSQL 16, verificando que el ciclo es reversible y no quedan diferencias pendientes

## 3. Contratos DTO, service y router de `/generos` (`catalog-generos`)

- [x] 3.1 Implementar `GeneroCreate`, `GeneroUpdate`, `GeneroRead` y `GeneroLibroRead` en `app/modules/generos/schemas.py` con validación de `nombre` no vacío y sin `id` en el alta
- [x] 3.2 Implementar `create_genero`, `list_generos`, `get_genero_or_404`, `update_genero` (con `exclude_unset=True`) y `list_libros_by_genero` en `app/modules/generos/service.py`, traduciendo `IntegrityError` a HTTP 409 con mensaje propio sin detalles internos (RN-12) y sin `SELECT` previo a escrituras (DD-04)
- [x] 3.3 Implementar los endpoints `POST /generos/` (`201`), `GET /generos/` (`200` paginado con `limit` 1..100 def. 20 y `offset >= 0` según RN-10), `GET /generos/{id}` (`200`/`404`), `PATCH /generos/{id}` (`200`/`404`/`409`) y `GET /generos/{id}/libros` (`200` paginado / `404`) en `app/modules/generos/router.py`

## 4. Tests de integración bajo ciclo TDD (`catalog-generos`, `domain-models`, `schema-migrations`)

- [x] 4.1 Escribir y ejecutar `tests/test_generos_and_migration_002.py` (y actualizar las aserciones de esquema a nivel `head` en `tests/test_core_models_and_migration_001.py`) verificando: existencia y revisión de la migración 002, persistencia y navegación `libro.genero` ↔ `genero.libros` (con y sin `genero_id`), CRUD completo de `/generos` (`201`, `200`, `404`, `409` RN-12 sin internos, `422`), `PATCH` parcial con `exclude_unset`, y paginación de `GET /generos/` y `GET /generos/{id}/libros` (RN-10)

## Workflow follow-up

- Proponer el commit sugerido y que el usuario lo ejecute: `git commit -m "C-03: generos + migracion 002"` (nunca commitear de forma autónoma).
- Archivar el change con `/opsx:archive c-03-generos-migracion-002` cuando la revisión esté satisfecha.
