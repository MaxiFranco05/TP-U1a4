# schema-migrations Specification

## Purpose
Governs how database schema changes are generated, reviewed, and applied exclusively through asynchronous Alembic revisions without using `SQLModel.metadata.create_all`.

## Requirements

### Requirement: Initial core schema migration via autogenerate

The system SHALL register all active persistence models in `migrations/env.py` and provide a first reviewed Alembic migration (`001`) generated with `alembic revision --autogenerate` that creates the 8 core tables (`editorial`, `autor`, `libro` without `genero_id`, `libro_autor`, `cliente`, `perfil_cliente`, `venta`, `renglon_venta`), their primary keys, foreign keys, explicit foreign-key indexes, `UNIQUE` constraints, and `CHECK` constraints, without creating the `genero` table yet.

#### Scenario: Upgrade head on empty database creates the 8 core tables and constraints

- **WHEN** `alembic upgrade head` is executed against an empty PostgreSQL 16 database
- **THEN** the 8 core tables, their `UNIQUE` and `CHECK` constraints, and their explicit foreign-key indexes exist in the database, and the `genero` table and `libro.genero_id` column do not exist yet

#### Scenario: Downgrade to base and re-upgrade are reversible

- **WHEN** `alembic downgrade base` followed by `alembic upgrade head` is executed
- **THEN** `downgrade base` drops the 8 core tables cleanly and `upgrade head` recreates the schema with zero pending differences against `SQLModel.metadata`

### Requirement: Second evolutionary migration adding genre and optional book foreign key

The system SHALL provide a second reviewed Alembic migration (`002`) generated via `alembic revision --autogenerate` that creates the `genero` table (`id`, `nombre` `UNIQUE`) and adds the nullable `genero_id` column, explicit index `ix_libro_genero_id`, and foreign key constraint on `libro`, supporting a clean `alembic downgrade -1` followed by `alembic upgrade head`.

#### Scenario: Downgrade one step and re-upgrade to head

- **WHEN** `alembic downgrade -1` is executed from `head` (`002`) and then `alembic upgrade head` is executed
- **THEN** `downgrade -1` removes `libro.genero_id` and the `genero` table leaving the 8 tables from migration `001` intact, and `upgrade head` restores `genero` and `libro.genero_id` with zero pending schema diffs (`alembic check`)

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
