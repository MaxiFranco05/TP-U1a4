# Spec Delta — schema-migrations

## ADDED Requirements

### Requirement: Second evolutionary migration adding genre and optional book foreign key

The system SHALL provide a second reviewed Alembic migration (`002`) generated via `alembic revision --autogenerate` that creates the `genero` table (`id`, `nombre` `UNIQUE`) and adds the nullable `genero_id` column, explicit index `ix_libro_genero_id`, and foreign key constraint on `libro`, supporting a clean `alembic downgrade -1` followed by `alembic upgrade head`.

#### Scenario: Downgrade one step and re-upgrade to head

- **WHEN** `alembic downgrade -1` is executed from `head` (`002`) and then `alembic upgrade head` is executed
- **THEN** `downgrade -1` removes `libro.genero_id` and the `genero` table leaving the 8 tables from migration `001` intact, and `upgrade head` restores `genero` and `libro.genero_id` with zero pending schema diffs (`alembic check`)
