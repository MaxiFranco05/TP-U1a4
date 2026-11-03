# domain-models Specification Delta

## MODIFIED Requirements

### Requirement: Catalog core persistence models and constraints

The system SHALL define `Editorial` (`editorial`), `Autor` (`autor`), `Libro` (`libro`, with nullable `borrado_en` `TIMESTAMPTZ`), and `LibroAutor` (`libro_autor`) with uniqueness on `editorial.nombre`, a partial unique index on `libro(isbn) WHERE borrado_en IS NULL`, check constraints `libro.precio > 0`, `libro.stock >= 0`, `libro_autor.orden >= 1`, and `libro_autor.rol IN ('autor', 'coautor', 'traductor', 'ilustrador')`, composite PK (`libro_id`, `autor_id`) on `libro_autor`, `Decimal` (`NUMERIC(10, 2)`) for `libro.precio`, and explicit indexes on all FKs.

#### Scenario: Valid catalog entities persist and navigate bidirectionally

- **WHEN** an `Editorial`, an `Autor`, a `Libro` with `Decimal` price and non-negative stock, and a `LibroAutor` link with a valid role and `orden >= 1` are persisted
- **THEN** the database stores all records with exact `Decimal` precision and `libro.autorias[i].autor` navigates to the associated `Autor` instance while `editorial.libros` and `autor.autorias` navigate in the opposite direction

#### Scenario: Duplicate editorial name or book ISBN is rejected by the database

- **WHEN** a persistence operation attempts to insert a duplicate `editorial.nombre` or a duplicate active `libro.isbn` (`borrado_en IS NULL`, RN-01)
- **THEN** PostgreSQL rejects the statement with an integrity error on the corresponding `UNIQUE` constraint or partial unique index

#### Scenario: Soft-deleted book ISBN can be reused by a new active book

- **WHEN** an existing `Libro` has a non-null `borrado_en` timestamp and a new `Libro` is inserted with the same `isbn` and `borrado_en=None` (RN-01, RN-13)
- **THEN** PostgreSQL accepts the new active book while rejecting any second active book with that `isbn`

#### Scenario: Invalid book price or stock is rejected by the database

- **WHEN** a persistence operation attempts to store a `Libro` with `precio <= 0` or `stock < 0` (RN-03)
- **THEN** PostgreSQL rejects the statement with an integrity error on the corresponding `CHECK` constraint

#### Scenario: Invalid authorship role or order is rejected by the database

- **WHEN** a persistence operation attempts to store a `LibroAutor` with `orden < 1` or a `rol` outside `('autor', 'coautor', 'traductor', 'ilustrador')` or a duplicate `(libro_id, autor_id)` pair
- **THEN** PostgreSQL rejects the statement with an integrity error

### Requirement: Client and one-to-one profile persistence models

The system SHALL define `Cliente` (`cliente`) with `id`, `nombre`, `email` (`UNIQUE`), and optional `usuario_id` (`FK` to `usuario.id`, `nullable=True`, `UNIQUE`, with explicit index), and `PerfilCliente` (`perfil_cliente`) with `id`, `cliente_id` (`FK` to `cliente.id` with `UNIQUE` constraint and explicit index), `telefono`, and `direccion`, configuring both `Cliente.perfil` and `Cliente.usuario` with `uselist=False` so that each returns a single instance or `None` rather than a list.

#### Scenario: Client profile navigation returns a single object

- **WHEN** a `Cliente`, its `PerfilCliente`, and an optional linked `Usuario` are persisted and loaded
- **THEN** `cliente.perfil` evaluates to a single `PerfilCliente` instance (not a `list`), `cliente.usuario` evaluates to a single `Usuario | None` instance (not a `list`), and `perfil.cliente` evaluates to the owning `Cliente`

#### Scenario: Duplicate client email or second profile for the same client is rejected

- **WHEN** a persistence operation attempts to insert a duplicate `cliente.email` (RN-01), a second `Cliente` referencing the same non-null `usuario_id`, or a second `PerfilCliente` with the same `cliente_id`
- **THEN** PostgreSQL rejects the statement with an integrity error on the corresponding `UNIQUE` constraint

## ADDED Requirements

### Requirement: User identity and role assignment persistence models

The system SHALL define `Usuario` (`usuario`: `id`, `email` `UNIQUE`, `nombre`, `password_hash`, `activo` default `True`, `debe_cambiar_password` default `False`) and `AsignacionRol` (`asignacion_rol`: `id`, `usuario_id` FK with index, `rol` with `CHECK (rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE'))`, `desde` `TIMESTAMPTZ`, nullable `vence_en` and `revocada_en` `TIMESTAMPTZ`, nullable `otorgada_por` FK with index) with partial unique index `(usuario_id, rol) WHERE revocada_en IS NULL` (RN-03).

#### Scenario: User and active role assignment persist and reject duplicate open role

- **WHEN** a `Usuario` and an open `AsignacionRol` (`revocada_en=None`) for role `'VENDEDOR'` are persisted and a second open `AsignacionRol` for the same `(usuario_id, 'VENDEDOR')` is inserted
- **THEN** the first assignment persists with timezone-aware timestamps and PostgreSQL rejects the second open assignment via the partial unique index

#### Scenario: Revoked role assignment allows a new open assignment for the same role

- **WHEN** an existing `AsignacionRol` has a non-null `revocada_en` timestamp and a new `AsignacionRol` with `revocada_en=None` is inserted for the same `(usuario_id, rol)`
- **THEN** PostgreSQL stores both the historical revoked row and the new active row

#### Scenario: Invalid role name or duplicate user email is rejected

- **WHEN** a persistence operation attempts to insert a `Usuario` with a duplicate `email` or an `AsignacionRol` with `rol` outside `('ADMIN', 'VENDEDOR', 'CLIENTE')`
- **THEN** PostgreSQL rejects the statement with an integrity error

### Requirement: Access attempt and security event audit models without foreign keys

The system SHALL define `IntentoAcceso` (`intento_acceso`: `id`, `cuando` `TIMESTAMPTZ`, `email`, `ip`, `exito` `bool`) with a composite index on `(email, ip, cuando)` and no foreign keys, and `EventoSeguridad` (`evento_seguridad`: `id`, `cuando` `TIMESTAMPTZ`, `actor` `str`, `accion` `str`) with no foreign keys (RN-07, RN-16).

#### Scenario: Access attempts and security events persist for arbitrary emails and system actors

- **WHEN** an `IntentoAcceso` for a non-existent email and an `EventoSeguridad` with `actor="SISTEMA"` are persisted
- **THEN** PostgreSQL stores both records with timezone-aware `cuando` timestamps without requiring a matching `usuario` row, and `(email, ip, cuando)` is indexed on `intento_acceso`

### Requirement: Append-only stock movement persistence model

The system SHALL define `MovimientoStock` (`movimiento_stock`: `id`, `libro_id` FK to `libro.id` with index, nullable `venta_id` FK to `venta.id` with index, `usuario_id` FK to `usuario.id` with index, `cantidad` `int` with `CHECK (cantidad <> 0)`, `motivo` `str`, `cuando` `TIMESTAMPTZ`), enforcing at the PostgreSQL level that rows in `movimiento_stock` cannot be updated or deleted (RN-11, RN-12).

#### Scenario: Valid positive and negative stock movements persist and zero quantity is rejected

- **WHEN** a `MovimientoStock` with `cantidad != 0` is inserted for an existing `Libro` and `Usuario`
- **THEN** PostgreSQL persists the movement and navigates bidirectionally to `libro`, `usuario`, and optional `venta`, whereas inserting `cantidad = 0` fails on the `CHECK (cantidad <> 0)` constraint

#### Scenario: Updating or deleting a stock movement is rejected by PostgreSQL trigger

- **WHEN** an `UPDATE` or `DELETE` statement is executed against an existing row in `movimiento_stock` (RN-12, `C-14`)
- **THEN** the PostgreSQL trigger on `movimiento_stock` raises an exception and leaves the stored row unchanged
