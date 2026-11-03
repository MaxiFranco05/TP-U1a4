# Spec Delta

## Purpose

Provee las abstracciones base de acceso a datos (`BaseRepository[T]` y `SoftDeleteRepository[T]`) sin confirmación transaccional propia y el gestor de contexto asincrónico `UnitOfWork` que gobierna `commit()` y `rollback()` sobre la sesión compartida de la petición sin cerrarla.

## ADDED Requirements

### Requirement: Generic Base Repository Without Commit
The system SHALL provide a generic asynchronous repository base class parameterized with the entity model class at construction time that executes `flush()` on mutations (`add`, `update`, `delete`) and MUST NEVER call `commit()`.

#### Scenario: Adding and updating an entity flushes without committing
- **WHEN** an entity is added via `add(entity)` or modified via `update(entity, data)` in a base repository
- **THEN** the repository executes `flush()` on the active `AsyncSession`, populates database-generated primary keys on the entity, and leaves the transaction uncommitted until the surrounding `UnitOfWork` exits

#### Scenario: Standard CRUD lookup and counting on active session
- **WHEN** `get_by_id(entity_id)`, `get_all(offset, limit)`, `count()`, or `delete(entity)` is invoked on a base repository
- **THEN** the repository executes the corresponding SQLAlchemy 2.0 query or deletion against its bound `model_cls` and `AsyncSession` without committing the transaction

### Requirement: Soft Delete Repository Hierarchy Segregation
The system SHALL provide a specialized repository subclass for soft-deletable entities (`borrado_en`) that automatically excludes logically deleted rows (`borrado_en IS NULL`) in `get_by_id`, `get_all`, and `count`, and exposes `get_by_id_including_deleted` and `soft_delete` exclusively on that subclass.

#### Scenario: Default queries filter out logically deleted records
- **WHEN** `soft_delete(entity)` is called on an entity and subsequently `get_by_id`, `get_all`, or `count` is called on the soft-delete repository
- **THEN** `entity.borrado_en` is set to a timezone-aware UTC timestamp with `flush()`, and the entity is omitted from `get_by_id` (returns `None`), `get_all`, and `count`

#### Scenario: Historical lookup includes logically deleted records
- **WHEN** `get_by_id_including_deleted(entity_id)` is called for an entity whose `borrado_en` is not null
- **THEN** the soft-delete repository returns the entity instance with its persisted attributes intact

#### Scenario: Base repository does not expose soft-delete methods
- **WHEN** an instance of the standard base repository is inspected
- **THEN** it MUST NOT define `soft_delete` or `get_by_id_including_deleted` methods

### Requirement: Asynchronous Unit of Work Transaction Boundary
The system SHALL provide an asynchronous context manager (`UnitOfWork`) bound to the request's `AsyncSession` that commits on normal block exit, rolls back when an exception escapes the block, and MUST NEVER close the underlying session.

#### Scenario: Clean exit commits the shared session
- **WHEN** execution leaves an `async with uow:` block without raising an exception
- **THEN** the `UnitOfWork` calls `await session.commit()` and leaves the `AsyncSession` open for the request dependency lifecycle (`get_session`) to close

#### Scenario: Exception inside block rolls back all flushed changes
- **WHEN** an exception is raised inside an `async with uow:` block after one or more repository `flush()` operations
- **THEN** the `UnitOfWork` calls `await session.rollback()`, leaves no partial writes persisted, does not close the `AsyncSession`, and propagates the exception
