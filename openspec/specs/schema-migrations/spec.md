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
