# Tasks

## 1. Shared Infrastructure

- [ ] 1.1 Create `app/core/pagination.py` with `PaginationParams` dependency (`limit: int = Query(20, ge=1, le=100)`, `offset: int = Query(0, ge=0)`) and verify it returns 422 for out-of-bounds values
- [ ] 1.2 Create `app/core/exceptions.py` with `translate_integrity_error(exc: IntegrityError) -> HTTPException` mapping constraint names to Spanish messages (editorial_nombre_key, autor_nombre_key, libro_isbn_key, FK names) and verify it raises 409/422 without DB internals
- [ ] 1.3 Update `app/main.py` to import and register the three new routers (editoriales, autores, libros) and verify server starts without errors

## 2. Editoriales Module

- [ ] 2.1 Create `app/modules/editoriales/models.py` re-exporting `Editorial` from `app.modules.libros.models` (or defining if not yet present) and verify import works
- [ ] 2.2 Create `app/modules/editoriales/schemas.py` with `EditorialCreate` (nombre, pais?), `EditorialUpdate` (all optional), `EditorialRead` (id, nombre, pais), `EditorialListItem` and verify Pydantic validation
- [ ] 2.3 Create `app/modules/editoriales/service.py` with `create`, `get`, `list`, `update`, `list_libros` methods using session param, `joinedload`/`selectinload` where needed, calling `translate_integrity_error` on `IntegrityError` and verify each method works with unit tests
- [ ] 2.4 Create `app/modules/editoriales/router.py` with `POST /editoriales/`, `GET /editoriales/`, `GET /editoriales/{id}`, `PATCH /editoriales/{id}`, `GET /editoriales/{id}/libros` using `PaginationParams` dependency and verify all endpoints return correct status codes via `.http` tests
- [ ] 2.5 Write `test/editoriales.http` covering: create (201), duplicate name (409), list pagination (200, 422), detail (200, 404), update (200, 404, 409), books by editorial (200, 404) and verify all pass

## 3. Autores Module

- [ ] 3.1 Create `app/modules/autores/models.py` re-exporting `Autor` from `app.modules.libros.models` and verify import works
- [ ] 3.2 Create `app/modules/autores/schemas.py` with `AutorCreate` (nombre, nacionalidad?), `AutorUpdate` (all optional), `AutorRead` (id, nombre, nacionalidad), `AutorLibroItem` (with rol, orden) and verify Pydantic validation
- [ ] 3.3 Create `app/modules/autores/service.py` with `create`, `get`, `update`, `list_libros` methods using session param, calling `translate_integrity_error` on `IntegrityError` and verify each method works
- [ ] 3.4 Create `app/modules/autores/router.py` with `POST /autores/`, `GET /autores/{id}`, `PATCH /autores/{id}`, `GET /autores/{id}/libros` using `PaginationParams` and verify all endpoints return correct status codes
- [ ] 3.5 Write `test/autores.http` covering: create (201), detail (200, 404), update (200, 404), books by author with rol/orden (200, 404) and verify all pass

## 4. Libros Module

- [ ] 4.1 Ensure `app/modules/libros/models.py` has `Libro`, `LibroAutor`, `Genero` (if not in generos), with all constraints (ISBN unique, precio>0, stock>=0, orden>=1, rol enum, composite PK, FK indexes) and verify models match `domain-models` spec
- [ ] 4.2 Create `app/modules/libros/schemas.py` with `LibroCreate` (isbn, titulo, precio: Decimal, stock: int, editorial_id, genero_id?, autores: list[AutorCreateNested]), `LibroRead` (full detail with editorial, genero, autorias[]), `LibroListItem` (id, isbn, titulo, precio, stock, editorial_id, genero_id), `AutorCreateNested` (autor_id, rol, orden) and verify validation (precio>0, stock>=0, orden>=1, rol enum)
- [ ] 4.3 Create `app/modules/libros/service.py` with `create_with_autores`, `list`, `get` methods; `create_with_autores` builds `Libro` + `LibroAutor` objects in single transaction, no pre-checks; `get` uses `joinedload(editorial)`, `joinedload(genero)`, `selectinload(autorias).joinedload(autor)`; `list` supports `titulo` (ilike bound param) and `genero_id` filters; all catch `IntegrityError` → `translate_integrity_error` and verify each method works
- [ ] 4.4 Create `app/modules/libros/router.py` with `POST /libros/`, `GET /libros/`, `GET /libros/{id}` using `PaginationParams` and verify all endpoints return correct status codes
- [ ] 4.5 Write `test/libros.http` covering: create with authors (201), duplicate ISBN (409), non-existent editorial/autor (409), invalid precio/stock/rol/orden (422), list with filters (200, 422), detail with fixed query count (200, 404) and verify all pass; run with `SQL_ECHO=true` to confirm query count

## 5. Integration Verification

- [ ] 5.1 Run all `.http` tests (editoriales, autores, libros) sequentially and verify no regressions
- [ ] 5.2 Verify C-04 evidence requirements: 409 on FK violation without pre-check, fixed query count for detail, bound parameter for title filter (test `' OR '1'='1` returns empty list not error)
- [ ] 5.3 Confirm `alembic upgrade head` still works on clean DB and seed script runs (no migration changes needed)