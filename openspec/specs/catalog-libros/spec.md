# catalog-libros Specification

## Purpose

Provides the HTTP endpoints and business logic for creating books with their authors in a single operation, listing books with title and genre filters, and retrieving book details with eagerly loaded editorial, genre, and authors — all with bounded pagination, bound parameters for safety, and safe error translation.

## Requirements

### Requirement: Book creation with authors in a single operation

The system SHALL expose `POST /libros/` accepting a `LibroCreate` payload (`isbn` string, `titulo` non-empty string, `precio` positive `Decimal`, `stock` non-negative integer, `editorial_id` existing editorial id, `genero_id` optional existing genre id, and `autores` array of objects each with `autor_id` existing author id, `rol` in (`autor`, `coautor`, `traductor`, `ilustrador`), `orden` integer >= 1), persisting the `Libro` and associated `LibroAutor` rows in one transaction and responding with HTTP `201 Created` and a `LibroRead` body containing the full detail (editorial, genre, authors with role and order). If PostgreSQL rejects the insert due to a duplicate `isbn`, the system SHALL respond `409 Conflict` with a controlled Spanish message (RN-12). If a referenced `editorial_id`, `genero_id`, or any `autor_id` does not exist, PostgreSQL rejects the FK and the system SHALL respond `409 Conflict` with a controlled Spanish message without pre-checking existence (DD-04, RN-12). If validations fail (price <= 0, stock < 0, orden < 1, invalid rol), the system SHALL respond `422 Unprocessable Entity`.

#### Scenario: Successful book creation with authors
- **WHEN** client sends `POST /libros/` with valid data including `editorial_id`, optional `genero_id`, and `autores[]`
- **THEN** system responds `201 Created` with `LibroRead` containing full detail (editorial, genre, authors with role/order)

#### Scenario: Duplicate ISBN
- **WHEN** client sends `POST /libros/` with an `isbn` that already exists
- **THEN** system responds `409 Conflict` with Spanish message, no database internals

#### Scenario: Non-existent editorial_id
- **WHEN** client sends `POST /libros/` with an `editorial_id` that does not exist
- **THEN** system responds `409 Conflict` with Spanish message (FK violation, no pre-check)

#### Scenario: Non-existent autor_id in autores array
- **WHEN** client sends `POST /libros/` with an `autor_id` that does not exist
- **THEN** system responds `409 Conflict` with Spanish message (FK violation, no pre-check)

#### Scenario: Invalid price or stock
- **WHEN** client sends `POST /libros/` with `precio <= 0` or `stock < 0`
- **THEN** system responds `422 Unprocessable Entity`

#### Scenario: Invalid rol or orden in autores
- **WHEN** client sends `POST /libros/` with `rol` not in allowed values or `orden < 1`
- **THEN** system responds `422 Unprocessable Entity`

### Requirement: Paginated book listing with title and genre filters

The system SHALL expose `GET /libros/` with bounded query parameters `limit` (`1..100`, default `20`) and `offset` (`>= 0`), plus optional filter parameters `titulo` (case-insensitive partial match using bound parameter, RN-11) and `genero_id` (exact match), returning HTTP `200 OK` with a paginated list of `LibroListItem` (each containing `id`, `isbn`, `titulo`, `precio`, `stock`, `editorial_id`, `genero_id`), or `422` when pagination bounds are violated (RN-10).

#### Scenario: List books with default pagination
- **WHEN** client sends `GET /libros/`
- **THEN** system responds `200 OK` with up to 20 books

#### Scenario: List books with custom pagination
- **WHEN** client sends `GET /libros/?limit=50&offset=10`
- **THEN** system responds `200 OK` with up to 50 books starting from offset 10

#### Scenario: List books filtered by title (case-insensitive)
- **WHEN** client sends `GET /libros/?titulo=harry`
- **THEN** system responds `200 OK` with books whose title contains "harry" case-insensitively, using bound parameter

#### Scenario: List books filtered by genre
- **WHEN** client sends `GET /libros/?genero_id=3`
- **THEN** system responds `200 OK` with books of that genre

#### Scenario: List books with combined filters
- **WHEN** client sends `GET /libros/?titulo=harry&genero_id=3&limit=10`
- **THEN** system responds `200 OK` with matching books (max 10)

#### Scenario: Invalid pagination bounds
- **WHEN** client sends `GET /libros/?limit=101` or `GET /libros/?offset=-1`
- **THEN** system responds `422 Unprocessable Entity`

### Requirement: Book detail with eagerly loaded relationships

The system SHALL expose `GET /libros/{id}` returning HTTP `200 OK` with a `LibroRead` body containing the full book detail including `editorial` (object with `id`, `nombre`, `pais`), `genero` (object with `id`, `nombre`, or `null`), and `autorias` (array of objects each with `autor` object containing `id`, `nombre`, `nacionalidad`, plus `rol` and `orden` from `libro_autor`), using a single query with `joinedload` for editorial and genre, and `selectinload` for autorias (and their autores), or `404 Not Found` if the book does not exist. The number of queries is fixed regardless of the number of authors.

#### Scenario: Get existing book detail with all relationships
- **WHEN** client sends `GET /libros/{id}` for an existing book
- **THEN** system responds `200 OK` with `LibroRead` containing editorial, genre, and autores with role/order, using fixed query count

#### Scenario: Get non-existent book
- **WHEN** client sends `GET /libros/{id}` for a non-existent book
- **THEN** system responds `404 Not Found`