# schema-migrations Specification Delta

## ADDED Requirements

### Requirement: Third evolutionary migration via autogenerate for access, stock, and partial unique indexes

The system SHALL register `app.modules.usuarios.models` in `migrations/env.py` and provide a third reviewed and commented Alembic migration (`003`) generated via `alembic revision --autogenerate` that creates `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`, and `movimiento_stock`, adds `cliente.usuario_id` (`FK`, index, `UNIQUE`) and `libro.borrado_en`, and replaces the global `UNIQUE` on `libro.isbn` with the partial unique index `(isbn) WHERE borrado_en IS NULL`.

#### Scenario: Migration 003 upgrades and downgrades cleanly

- **WHEN** `alembic upgrade 003` (or `head`) is applied after migration `002` and then `alembic downgrade 002` is executed
- **THEN** `upgrade` creates the 5 new tables, new columns, explicit FK indexes, composite index on `intento_acceso`, and partial unique indexes on `libro` and `asignacion_rol`, and `downgrade` reverts the schema back to the 9-table state of migration `002`

### Requirement: Fourth manual migration installing the append-only trigger on movimiento_stock

The system SHALL provide a fourth reviewed and commented Alembic migration (`004`) written by hand that installs in `upgrade()` a PL/pgSQL function and `BEFORE UPDATE OR DELETE ON movimiento_stock` trigger rejecting any row modification or deletion (RN-12), and drops the trigger and function in `downgrade()`, supporting a full `alembic upgrade head` → `alembic downgrade base` → `alembic upgrade head` cycle.

#### Scenario: Full upgrade head, downgrade base, and re-upgrade head cycle succeeds

- **WHEN** `alembic upgrade head`, `alembic downgrade base`, and `alembic upgrade head` are executed sequentially against PostgreSQL 16
- **THEN** all migrations (`001` through `004`) apply, roll back to an empty schema, and re-apply cleanly with the append-only trigger active on `movimiento_stock` and zero pending schema diffs
