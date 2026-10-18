# Proposal

## Why

This change implements the full catalog CRUD operations (US-010, US-011, US-012, US-013) for the bookstore domain. The existing specs cover `catalog-generos` (genres) and `domain-models` (persistence models), but the catalog capabilities for editorials, authors, and books are not yet specified. This change closes the catalog gap so that users can manage editorials, authors, and books with their relationships.

## What Changes

- Add CRUD endpoints for **editorials** (`POST`, `GET` list/detail, `PATCH`, `GET /editoriales/{id}/libros`)
- Add CRUD endpoints for **authors** (`POST`, `GET` detail, `PATCH`, `GET /autores/{id}/libros` with role and order)
- Add **book creation with authors** in a single operation (`POST /libros/` with nested `autores[]`)
- Add **book listing with filters** (`GET /libros/` with `titulo` and `genero_id` filters) and **book detail** with eager-loaded editorial, genre, and authors
- All endpoints follow established patterns: bounded pagination (RN-10), safe error translation (RN-12), bound parameters (RN-11), Decimal for money, no pre-check `if` before writes (DD-04)
- New Alembic migration is NOT needed (models already defined in C-01/C-02 via `domain-models` spec)

## Capabilities

### New Capabilities

- `catalog-editoriales`: CRUD for editorials and listing books by editorial
- `catalog-autores`: CRUD for authors and listing books by author with role/order
- `catalog-libros`: Book creation with nested authors, paginated listing with filters, and detail with eager-loaded relationships

### Modified Capabilities

- `catalog-generos`: Already covers genres CRUD and books-by-genre — no requirement changes
- `domain-models`: Already defines all persistence models — no requirement changes

## Impact

- **Code**: New modules `app/modules/editoriales/`, `app/modules/autores/`, `app/modules/libros/` with models, schemas, services, routers
- **API**: New endpoints under `/editoriales/`, `/autores/`, `/libros/`
- **Database**: No schema changes (models already exist per `domain-models`)
- **Tests**: New `.http` files for C-04 evidence (creation, 409 on FK violation, listing with filters, detail with fixed query count)