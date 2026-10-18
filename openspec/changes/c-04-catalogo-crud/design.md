# Design

## Context

See proposal.md for motivation. The existing specs cover:
- `domain-models`: All persistence models (editorial, genero, autor, libro, libro_autor, cliente, perfil_cliente, venta, renglon_venta) with constraints
- `catalog-generos`: CRUD for genres and books-by-genre endpoint
- `app-lifecycle` + `health`: Startup, session management, health probes

Models are already defined in SQLModel. This change adds the HTTP layer for editorials, authors, and books following the established module pattern (`app/modules/<domain>/{models,schemas,service,router}.py`).

Key constraints from KB:
- All handlers `async def` + async I/O
- DTOs separate (Create/Update/Read), no `id` on create
- Services own DB logic; handlers thin
- `joinedload` (to-one) / `selectinload` (collections) declared in query
- Never check existence with `if` before write — let DB reject FK/UNIQUE → 409
- Translate `IntegrityError` to custom message + 409/422 (RN-12)
- Pagination: `limit` 1-100 (default 20), `offset >= 0` → 422 (RN-10)
- Money always `Decimal` (NUMERIC)
- `BackgroundTasks` for async side effects (not needed here)
- Bound parameters only (RN-11)

## Goals / Non-Goals

**Goals:**
- Implement three new modules: `editoriales`, `autores`, `libros` with consistent structure
- Reuse existing SQLModel models from `domain-models` spec
- Follow the exact patterns established in `catalog-generos` and architecture docs
- Ensure fixed query count for book detail (C-07 evidence)
- Translate all `IntegrityError` to Spanish messages without DB internals

**Non-Goals:**
- No new database migrations (models exist from C-01/C-02)
- No authentication/authorization (out of scope per DD-01)
- No changes to `catalog-generos` or `domain-models` specs

## Decisions

### Module structure
**Decision**: Create three modules mirroring `catalog-generos` structure:
```
app/modules/editoriales/{models.py, schemas.py, service.py, router.py}
app/modules/autores/{models.py, schemas.py, service.py, router.py}
app/modules/libros/{models.py, schemas.py, service.py, router.py}
```
**Rationale**: Consistency with `catalog-generos` and architecture (DD-03, architecture §7). Each module owns its schemas and router; models can be imported from shared location or re-exported.
**Alternative**: Single `catalogo` module — rejected because architecture mandates one module per domain (editoriales, generos, autores, libros are separate domains).

### Model imports
**Decision**: Re-export SQLModel models from `app/modules/libros/models.py` as the canonical location (since `LibroAutor` lives there per architecture §17), and import in other modules.
**Rationale**: `LibroAutor` is defined in `libros` module per architecture; `Editorial`, `Autor`, `Libro`, `Genero` are referenced across modules. Single source of truth avoids drift.
**Alternative**: Each module defines its own model — rejected (duplication, FK mismatches).

### Error translation strategy
**Decision**: Centralize `IntegrityError` translation in a small helper in `app/core/exceptions.py` (or `app/core/database.py`), used by all three services.
**Rationale**: DRY; RN-12 requires consistent Spanish messages without DB internals. Each service catches `IntegrityError`, inspects constraint name (`editorial_nombre_key`, `autor_nombre_key`, `libro_isbn_key`, FK names), maps to controlled message.
**Alternative**: Inline translation in each service — rejected (duplication, inconsistency risk).

### Pagination dependency
**Decision**: Create a shared `PaginationParams` dependency in `app/core/pagination.py` with `limit: int = Query(20, ge=1, le=100)` and `offset: int = Query(0, ge=0)`.
**Rationale**: RN-10 applies to all list endpoints; single source ensures consistent 422 behavior.
**Alternative**: Inline in each router — rejected (duplication).

### Book creation transaction
**Decision**: Service creates `Libro` + `LibroAutor` objects in memory, adds to session, commits once. No pre-checks.
**Rationale**: DD-04 mandates letting DB reject FK/UNIQUE; single transaction ensures atomicity. Matches Flujo 2 in KB.

### Eager loading for book detail
**Decision**: Service uses `select(Libro).options(joinedload(Libro.editorial), joinedload(Libro.genero), selectinload(Libro.autorias).joinedload(LibroAutor.autor))` for detail.
**Rationale**: `joinedload` for to-one (editorial, genero), `selectinload` for collection (autorias) with nested `joinedload` for `autor`. Fixed query count per Flujo 4 and C-07 evidence.

### Filter implementation for book listing
**Decision**: Use `ilike` with bound parameter for `titulo` filter (`Libro.titulo.ilike(f"%{titulo}%")`), exact match for `genero_id`.
**Rationale**: RN-11 requires bound parameters, case-insensitive. `ilike` is PostgreSQL-specific but acceptable (PG16 target).

## Risks / Trade-offs

- [Risk] Constraint name mapping for `IntegrityError` may differ if migrations generate different names → Mitigation: Use explicit constraint names in models (`__table_args__ = (UniqueConstraint('nombre', name='editorial_nombre_key'), ...)`) and verify against actual migration output
- [Risk] Circular imports between modules if models import each other → Mitigation: Use `TYPE_CHECKING` imports for relationships, or define all models in `libros/models.py` and import from there
- [Risk] `selectinload` + `joinedload` nesting may produce unexpected query shape → Mitigation: Test with `SQL_ECHO=true` and verify fixed query count (C-07 evidence)
- [Trade-off] Three separate modules increase file count but improve separation of concerns and match grading expectations (US-010, US-011, US-012/013 are separate user stories)

## Migration Plan

No database migration needed. Deployment steps:
1. Add three new module directories with code
2. Register routers in `app/main.py`
3. Run existing tests (`.http` files) to verify
4. Add new `.http` tests for C-04 evidence

Rollback: Remove module directories and router registrations.

## Open Questions

None — all decisions resolved from KB and existing specs.