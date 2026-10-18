# catalog-editoriales Specification

## Purpose

Provides the HTTP endpoints and business logic for creating, listing, retrieving, and partially updating publishing houses (editorials), as well as listing the books belonging to a specific editorial with bounded pagination and safe error translation.

## Requirements

### Requirement: Editorial creation and uniqueness enforcement

The system SHALL expose `POST /editoriales/` accepting an `EditorialCreate` payload (`nombre` non-empty string, `pais` optional string, without `id`), persisting the new `Editorial` and responding with HTTP `201 Created` and an `EditorialRead` body (`id`, `nombre`, `pais`). If PostgreSQL rejects the insert due to a duplicate `nombre`, the system SHALL catch the `IntegrityError`, roll back the session, and respond with HTTP `409 Conflict` and a controlled Spanish message without exposing internal database details (RN-12).

#### Scenario: Successful editorial creation
- **WHEN** client sends `POST /editoriales/` with valid `nombre` and optional `pais`
- **THEN** system responds `201 Created` with `EditorialRead` containing generated `id`

#### Scenario: Duplicate editorial name
- **WHEN** client sends `POST /editoriales/` with a `nombre` that already exists
- **THEN** system responds `409 Conflict` with a Spanish message, no database internals exposed

### Requirement: Paginated editorial listing, detail, and partial update

The system SHALL expose `GET /editoriales/` with bounded query parameters `limit` (`1..100`, default `20`) and `offset` (`>= 0`) returning HTTP `200 OK` (or `422` when pagination bounds are violated per RN-10), `GET /editoriales/{id}` returning HTTP `200 OK` or `404 Not Found` if the editorial does not exist, and `PATCH /editoriales/{id}` applying partial updates via `exclude_unset=True` and returning HTTP `200 OK`, `404 Not Found` if missing, or `409 Conflict` on duplicate `nombre` (RN-12).

#### Scenario: List editorials with default pagination
- **WHEN** client sends `GET /editoriales/`
- **THEN** system responds `200 OK` with list of editorials (max 20)

#### Scenario: List editorials with custom pagination
- **WHEN** client sends `GET /editoriales/?limit=50&offset=10`
- **THEN** system responds `200 OK` with up to 50 editorials starting from offset 10

#### Scenario: Invalid pagination bounds
- **WHEN** client sends `GET /editoriales/?limit=101` or `GET /editoriales/?offset=-1`
- **THEN** system responds `422 Unprocessable Entity`

#### Scenario: Get existing editorial detail
- **WHEN** client sends `GET /editoriales/{id}` for an existing editorial
- **THEN** system responds `200 OK` with `EditorialRead`

#### Scenario: Get non-existent editorial
- **WHEN** client sends `GET /editoriales/{id}` for a non-existent editorial
- **THEN** system responds `404 Not Found`

#### Scenario: Partial update editorial
- **WHEN** client sends `PATCH /editoriales/{id}` with valid fields
- **THEN** system responds `200 OK` with updated `EditorialRead`

#### Scenario: Partial update with duplicate name
- **WHEN** client sends `PATCH /editoriales/{id}` with a `nombre` that already exists on another editorial
- **THEN** system responds `409 Conflict` with a Spanish message

### Requirement: Paginated listing of books by editorial

The system SHALL expose `GET /editoriales/{id}/libros` with bounded query parameters `limit` (`1..100`, default `20`) and `offset` (`>= 0`) returning HTTP `200 OK` with the list of books associated with that editorial, or `404 Not Found` if the editorial `{id}` does not exist.

#### Scenario: List books by existing editorial
- **WHEN** client sends `GET /editoriales/{id}/libros` for an existing editorial
- **THEN** system responds `200 OK` with list of books (paginated)

#### Scenario: List books by non-existent editorial
- **WHEN** client sends `GET /editoriales/{id}/libros` for a non-existent editorial
- **THEN** system responds `404 Not Found`