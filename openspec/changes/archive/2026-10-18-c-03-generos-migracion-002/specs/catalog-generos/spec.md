# Spec Delta — catalog-generos

## Purpose

Provides the HTTP endpoints and business logic for creating, listing, retrieving, and partially updating literary genres, as well as listing the books belonging to a specific genre with bounded pagination and safe error translation.

## ADDED Requirements

### Requirement: Genre creation and uniqueness enforcement

The system SHALL expose `POST /generos/` accepting a `GeneroCreate` payload (`nombre` non-empty string, without `id`), persisting the new `Genero` and responding with HTTP `201 Created` and a `GeneroRead` body (`id`, `nombre`). If PostgreSQL rejects the insert due to a duplicate `nombre`, the system SHALL catch the `IntegrityError`, roll back the session, and respond with HTTP `409 Conflict` and a controlled Spanish message without exposing internal database details (RN-12).

#### Scenario: Create genre succeeds with 201

- **WHEN** a client sends `POST /generos/` with a valid unique `nombre`
- **THEN** the system persists the genre and responds `201 Created` with `{"id": <int>, "nombre": <str>}`

#### Scenario: Duplicate genre name returns 409 without database internals

- **WHEN** a client sends `POST /generos/` with a `nombre` that already exists in `genero`
- **THEN** the database rejects the `UNIQUE` constraint and the system responds `409 Conflict` with a controlled message and no SQL, constraint names, or tracebacks (RN-12)

#### Scenario: Invalid genre payload returns 422

- **WHEN** a client sends `POST /generos/` with a missing or empty/blank `nombre`
- **THEN** the system responds `422 Unprocessable Entity` before executing persistence logic

### Requirement: Paginated genre listing, detail, and partial update

The system SHALL expose `GET /generos/` with bounded query parameters `limit` (`1..100`, default `20`) and `offset` (`>= 0`) returning HTTP `200 OK` (or `422` when pagination bounds are violated per RN-10), `GET /generos/{id}` returning HTTP `200 OK` or `404 Not Found` if the genre does not exist, and `PATCH /generos/{id}` applying partial updates via `exclude_unset=True` and returning HTTP `200 OK`, `404 Not Found` if missing, or `409 Conflict` on duplicate `nombre` (RN-12).

#### Scenario: Paginated genre list respects RN-10 bounds

- **WHEN** a client requests `GET /generos/?limit=10&offset=0`
- **THEN** the system responds `200 OK` with at most 10 genres ordered deterministically, and responds `422` if `limit < 1`, `limit > 100`, or `offset < 0`

#### Scenario: Genre detail and partial update handle existing, missing, and conflicting records

- **WHEN** a client calls `GET /generos/{id}` or `PATCH /generos/{id}`
- **THEN** the system returns `200 OK` with the genre when found, `404 Not Found` when `{id}` does not exist, and `409 Conflict` without internal leaks when `PATCH` collides with an existing `nombre`

### Requirement: Paginated listing of books by genre

The system SHALL expose `GET /generos/{id}/libros` with bounded query parameters `limit` (`1..100`, default `20`) and `offset` (`>= 0`) returning HTTP `200 OK` with the list of books associated with that genre, or `404 Not Found` if the genre `{id}` does not exist.

#### Scenario: List books for an existing genre

- **WHEN** a client calls `GET /generos/{id}/libros` for an existing genre
- **THEN** the system responds `200 OK` with the paginated books whose `genero_id` matches `{id}`, and responds `404 Not Found` if the genre `{id}` does not exist
