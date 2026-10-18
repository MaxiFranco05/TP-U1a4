# Spec Delta

## Purpose

Provides the HTTP endpoints and business logic for creating, retrieving, and partially updating authors, as well as listing the books authored by a specific author with their role and order in each authorship, using bounded pagination and safe error translation.

## ADDED Requirements

### Requirement: Author creation

The system SHALL expose `POST /autores/` accepting an `AutorCreate` payload (`nombre` non-empty string, `nacionalidad` optional string, without `id`), persisting the new `Autor` and responding with HTTP `201 Created` and an `AutorRead` body (`id`, `nombre`, `nacionalidad`).

#### Scenario: Successful author creation
- **WHEN** client sends `POST /autores/` with valid `nombre` and optional `nacionalidad`
- **THEN** system responds `201 Created` with `AutorRead` containing generated `id`

### Requirement: Author detail, partial update, and non-existent handling

The system SHALL expose `GET /autores/{id}` returning HTTP `200 OK` with `AutorRead` or `404 Not Found` if the author does not exist, and `PATCH /autores/{id}` applying partial updates via `exclude_unset=True` and returning HTTP `200 OK` or `404 Not Found` if missing.

#### Scenario: Get existing author detail
- **WHEN** client sends `GET /autores/{id}` for an existing author
- **THEN** system responds `200 OK` with `AutorRead`

#### Scenario: Get non-existent author
- **WHEN** client sends `GET /autores/{id}` for a non-existent author
- **THEN** system responds `404 Not Found`

#### Scenario: Partial update author
- **WHEN** client sends `PATCH /autores/{id}` with valid fields
- **THEN** system responds `200 OK` with updated `AutorRead`

#### Scenario: Partial update non-existent author
- **WHEN** client sends `PATCH /autores/{id}` for a non-existent author
- **THEN** system responds `404 Not Found`

### Requirement: Paginated listing of books by author with role and order

The system SHALL expose `GET /autores/{id}/libros` with bounded query parameters `limit` (`1..100`, default `20`) and `offset` (`>= 0`) returning HTTP `200 OK` with the list of books authored by that author, where each book entry includes the `rol` (autor, coautor, traductor, ilustrador) and `orden` (>= 1) from the `libro_autor` association, or `404 Not Found` if the author `{id}` does not exist.

#### Scenario: List books by existing author with role and order
- **WHEN** client sends `GET /autores/{id}/libros` for an existing author
- **THEN** system responds `200 OK` with list of books, each containing `rol` and `orden`

#### Scenario: List books by non-existent author
- **WHEN** client sends `GET /autores/{id}/libros` for a non-existent author
- **THEN** system responds `404 Not Found`