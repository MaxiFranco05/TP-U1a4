# Spec Delta — domain-models

## Purpose

Defines the relational persistence models, database constraints (`UNIQUE`, `CHECK`, `FK` with explicit indexes), monetary (`Decimal` / `NUMERIC`) and timezone-aware timestamp (`TIMESTAMPTZ`) types, and bidirectional ORM navigation across the catalog, client, and sales domains.

## ADDED Requirements

### Requirement: Catalog core persistence models and constraints

The system SHALL define `Editorial` (`editorial`), `Autor` (`autor`), `Libro` (`libro`, without `genero_id`), and `LibroAutor` (`libro_autor`) with uniqueness on `editorial.nombre` and `libro.isbn`, check constraints `libro.precio > 0`, `libro.stock >= 0`, `libro_autor.orden >= 1`, and `libro_autor.rol IN ('autor', 'coautor', 'traductor', 'ilustrador')`, composite PK (`libro_id`, `autor_id`) on `libro_autor`, `Decimal` (`NUMERIC(10, 2)`) for `libro.precio`, and explicit indexes on all FKs.

#### Scenario: Valid catalog entities persist and navigate bidirectionally

- **WHEN** an `Editorial`, an `Autor`, a `Libro` with `Decimal` price and non-negative stock, and a `LibroAutor` link with a valid role and `orden >= 1` are persisted
- **THEN** the database stores all records with exact `Decimal` precision and `libro.autorias[i].autor` navigates to the associated `Autor` instance while `editorial.libros` and `autor.autorias` navigate in the opposite direction

#### Scenario: Duplicate editorial name or book ISBN is rejected by the database

- **WHEN** a persistence operation attempts to insert a duplicate `editorial.nombre` or a duplicate `libro.isbn` (RN-01)
- **THEN** PostgreSQL rejects the statement with an integrity error on the corresponding `UNIQUE` constraint

#### Scenario: Invalid book price or stock is rejected by the database

- **WHEN** a persistence operation attempts to store a `Libro` with `precio <= 0` or `stock < 0` (RN-03)
- **THEN** PostgreSQL rejects the statement with an integrity error on the corresponding `CHECK` constraint

#### Scenario: Invalid authorship role or order is rejected by the database

- **WHEN** a persistence operation attempts to store a `LibroAutor` with `orden < 1` or a `rol` outside `('autor', 'coautor', 'traductor', 'ilustrador')` or a duplicate `(libro_id, autor_id)` pair
- **THEN** PostgreSQL rejects the statement with an integrity error

### Requirement: Client and one-to-one profile persistence models

The system SHALL define `Cliente` (`cliente`) with `id`, `nombre`, and `email` (`UNIQUE`), and `PerfilCliente` (`perfil_cliente`) with `id`, `cliente_id` (`FK` to `cliente.id` with `UNIQUE` constraint and explicit index), `telefono`, and `direccion`, configuring `Cliente.perfil` with `uselist=False` so that it returns a single `PerfilCliente | None` object rather than a list.

#### Scenario: Client profile navigation returns a single object

- **WHEN** a `Cliente` and its `PerfilCliente` are persisted and loaded
- **THEN** `cliente.perfil` evaluates to a single `PerfilCliente` instance (not a `list`) and `perfil.cliente` evaluates to the owning `Cliente`

#### Scenario: Duplicate client email or second profile for the same client is rejected

- **WHEN** a persistence operation attempts to insert a duplicate `cliente.email` (RN-02) or a second `PerfilCliente` with the same `cliente_id` (RN-09)
- **THEN** PostgreSQL rejects the statement with an integrity error on the corresponding `UNIQUE` constraint

### Requirement: Sales and line-item persistence models

The system SHALL define `Venta` (`venta`: `id`, `cliente_id` FK with explicit index, `fecha` `TIMESTAMPTZ`, `total` `Decimal` `NUMERIC(12, 2)` with `CHECK total >= 0`) and `RenglonVenta` (`renglon_venta`: `id`, `venta_id` and `libro_id` FKs with explicit indexes, `cantidad` with `CHECK cantidad > 0`, `precio_unitario` `Decimal` `NUMERIC(10, 2)` with `CHECK precio_unitario > 0`), with bidirectional `Relationship(back_populates=...)` on all endpoints.

#### Scenario: Valid sale with line items persists with Decimal and timezone-aware timestamp

- **WHEN** a `Venta` with timezone-aware `fecha`, `Decimal` `total >= 0`, and one or more `RenglonVenta` items (`cantidad > 0`, `precio_unitario > 0`) are persisted for an existing `Cliente` and `Libro`
- **THEN** PostgreSQL stores the `TIMESTAMPTZ` and `NUMERIC` values accurately and `venta.renglones`, `venta.cliente`, `cliente.ventas`, and `renglon.libro` navigate bidirectionally

#### Scenario: Invalid sale total, line quantity, or unit price is rejected by the database

- **WHEN** a persistence operation attempts to store a `Venta` with `total < 0` or a `RenglonVenta` with `cantidad <= 0` or `precio_unitario <= 0`
- **THEN** PostgreSQL rejects the statement with an integrity error on the corresponding `CHECK` constraint
