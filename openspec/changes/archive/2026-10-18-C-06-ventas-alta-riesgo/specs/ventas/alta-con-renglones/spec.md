# Spec Delta

## Purpose

Enables registering a sale with nested line items in a single atomic operation, copying book prices at sale time, calculating totals server-side, enforcing business rules on line items, and scheduling a background notification without blocking the response.

## ADDED Requirements

### Requirement: Create sale with nested line items

The system SHALL accept a sale creation request containing a client ID and a list of line items (book ID and quantity), and persist the sale with its line items in a single transaction.

#### Scenario: Successful sale creation
- **WHEN** client sends `POST /ventas/` with valid `cliente_id` and at least one `renglon` containing `libro_id` and `cantidad > 0`
- **THEN** system responds `201 Created` with the sale object including `id`, `cliente_id`, `fecha`, `total`, and `renglones` where each line has `id`, `venta_id`, `libro_id`, `cantidad`, `precio_unitario` (copied from book at sale time)

#### Scenario: Sale creation with multiple line items
- **WHEN** client sends `POST /ventas/` with valid `cliente_id` and multiple distinct `renglones`
- **THEN** system responds `201` with all line items, each with correct `precio_unitario` copied from its book, and `total` equals sum of `cantidad * precio_unitario` across all lines

### Requirement: Copy book prices at sale time

The system SHALL read each book's current price from the database at the moment of sale registration and store it as `precio_unitario` in the line item, so that future book price changes do not affect recorded sales.

#### Scenario: Price copied from book at registration
- **WHEN** a sale is created for a book with price `1250.00`
- **THEN** the corresponding `renglon_venta.precio_unitario` equals `1250.00` regardless of subsequent updates to `libro.precio`

### Requirement: Calculate sale total server-side

The system SHALL compute the sale `total` as the sum of `cantidad * precio_unitario` for all line items, and never accept `total` or `precio_unitario` from the client request.

#### Scenario: Total calculated from line items
- **WHEN** sale is created with two lines: (libro A, cantidad 2, precio 100.00) and (libro B, cantidad 1, precio 50.00)
- **THEN** response `total` equals `250.00` (2*100 + 1*50)

### Requirement: Validate minimum one line item

The system SHALL reject sale creation requests with zero line items.

#### Scenario: Empty line items rejected
- **WHEN** client sends `POST /ventas/` with `renglones: []`
- **THEN** system responds `422 Unprocessable Entity`

### Requirement: Reject duplicate books in line items

The system SHALL reject sale creation requests where the same `libro_id` appears in more than one line item.

#### Scenario: Duplicate libro_id rejected
- **WHEN** client sends `POST /ventas/` with `renglones: [{libro_id: 1, cantidad: 1}, {libro_id: 1, cantidad: 2}]`
- **THEN** system responds `422 Unprocessable Entity`

### Requirement: Reject invalid quantity

The system SHALL reject line items with `cantidad <= 0`.

#### Scenario: Zero or negative quantity rejected
- **WHEN** client sends `POST /ventas/` with `renglones: [{libro_id: 1, cantidad: 0}]` or `cantidad: -1`
- **THEN** system responds `422 Unprocessable Entity`

### Requirement: Return 409 for non-existent client

The system SHALL respond `409 Conflict` with a controlled message when the referenced `cliente_id` does not exist, without exposing database internals.

#### Scenario: Non-existent client
- **WHEN** client sends `POST /ventas/` with `cliente_id: 99999` (non-existent)
- **THEN** system responds `409 Conflict` with message "Cliente no encontrado"

### Requirement: Return 409 for non-existent book

The system SHALL respond `409 Conflict` with a controlled message when any referenced `libro_id` does not exist, without exposing database internals.

#### Scenario: Non-existent book
- **WHEN** client sends `POST /ventas/` with valid `cliente_id` but `renglones: [{libro_id: 99999, cantidad: 1}]`
- **THEN** system responds `409 Conflict` with message "El libro referenciado no existe"

### Requirement: Schedule background notification

The system SHALL schedule a background task (notification/comprobante) after successful sale creation, without blocking the HTTP response.

#### Scenario: Background task scheduled
- **WHEN** a sale is successfully created
- **THEN** system responds `201` immediately, and a background task runs after a short delay (e.g., `asyncio.sleep(0.5)`) logging the notification

### Requirement: Sale detail uses fixed query count

The system SHALL serve `GET /ventas/{id}` with a single query using `joinedload` for the client relationship and `selectinload` for the line items collection, ensuring the query count is constant regardless of line item count.

#### Scenario: Detail query count fixed
- **WHEN** requesting `GET /ventas/{id}` for a sale with 1 line item
- **THEN** exactly 1 query executes
- **WHEN** requesting `GET /ventas/{id}` for a sale with 10 line items
- **THEN** exactly 1 query executes (same count)