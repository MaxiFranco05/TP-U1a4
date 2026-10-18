# Design

## Context

See proposal.md for motivation. Current state:
- Models `Venta` and `RenglonVenta` exist with proper constraints, relationships, and indexes
- Read schemas (`VentaRead`, `RenglonVentaRead`) exist in `app/modules/ventas/schemas.py`
- Router and service are empty skeletons in `app/modules/ventas/`
- Core infrastructure: `get_session` dependency, `translate_integrity_error`, `PaginationParams`, `BackgroundTasks` available
- Existing pattern: Service owns DB logic, router is thin, DTOs separate (Create/Read), async handlers, eager loading declared in queries

## Goals / Non-Goals

**Goals:**
- Implement `POST /ventas/` with nested line items per US-030
- Implement `GET /ventas/{id}` with fixed query count (eager loading)
- Implement `GET /ventas/` paginated list
- Follow project patterns: service layer, DTO separation, IntegrityError translation, BackgroundTasks
- Zero lazy loading; all relationships loaded via `joinedload`/`selectinload`

**Non-Goals:**
- PATCH/DELETE for sales (RN-08: sales are immutable)
- Stock decrement (not in requirements)
- Authentication/authorization (out of scope)
- Email/SMS notification — only in-process background log

## Decisions

### 1. DTO Structure (schemas.py)

**Decision**: Add `RenglonVentaCreate` and `VentaCreate` with validation in the DTO layer.

**Rationale**: 
- Validation of RN-05 (min 1 line, no duplicate books, quantity > 0) belongs in DTO for fast failure before DB hit
- Keeps service focused on business logic (price copying, total calculation)
- Consistent with `LibroCreate` pattern in libros module

**Alternatives considered**: Validate in service only — rejected because DTO validation gives clearer 422 errors and follows FastAPI conventions.

### 2. Service Method Signature

**Decision**: `async def crear_venta(session: AsyncSession, data: VentaCreate, background_tasks: BackgroundTasks) -> VentaRead`

**Rationale**:
- Session injected via `Depends(get_session)` in router
- `BackgroundTasks` passed from router for notification scheduling
- Returns `VentaRead` (not model) for clean separation
- `AsyncSession` for async I/O

### 3. Price Copying & Total Calculation

**Decision**: In service, for each line item:
1. Load `Libro` by ID (single query with `selectinload` for all requested books, or individual loads)
2. Copy `libro.precio` to `RenglonVenta.precio_unitario`
3. Compute `subtotal = cantidad * precio_unitario`
4. Sum subtotals for `Venta.total`

**Rationale**:
- RN-06, RN-07 require server-side copy/calculation
- Loading all books in one query avoids N+1; use `in_` clause with `selectinload` if needed
- `Decimal` arithmetic for money precision

### 4. Transaction & Error Handling

**Decision**: Single `async with session.begin():` block for the entire operation. Catch `IntegrityError` and translate via `translate_integrity_error`.

**Rationale**:
- Atomicity: sale + lines succeed or fail together
- FK violations (missing client/book) → 409 via existing translation map (keys `fk_renglon_venta_venta`, `fk_renglon_venta_libro`, `perfil_cliente_cliente_id_fkey` for client)
- No pre-check `if` statements (DD-04, RN-12)

### 5. Background Notification

**Decision**: Define `async def _notificar_comprobante(venta_id: int)` that does `await asyncio.sleep(0.5)` then logs. Add to `background_tasks.add_task(_notificar_comprobante, venta.id)` after commit.

**Rationale**:
- Requirement: schedule without blocking response
- Simple in-process log satisfies C-06 evidence; real notification would be external service

### 6. Eager Loading for Detail & List

**Decision**: 
- `GET /ventas/{id}`: `select(Venta).options(joinedload(Venta.cliente), selectinload(Venta.renglones).selectinload(RenglonVenta.libro))`
- `GET /ventas/`: paginated list with `joinedload(Venta.cliente)` only (lines not needed in list)

**Rationale**:
- Fixed query count per Flujo 4
- `joinedload` for to-one (client), `selectinload` for collections (lines)
- List endpoint doesn't need lines per US-031

### 6. Response Shape

**Decision**: `VentaRead` includes nested `renglones: list[RenglonVentaRead]` where each has `precio_unitario`. No `subtotal` in response (computed client-side if needed).

**Rationale**: Matches US-030 acceptance criteria: "201 con cliente y renglones (precio copiado, subtotal, total)". Subtotal shown via `cantidad * precio_unitario`.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| N+1 when loading books for price copy | Load all requested `Libro`s in a single query using `where(Libro.id.in_(ids))` before creating lines |
| Race condition: book deleted between price read and line insert | FK constraint on `renglon_venta.libro_id` catches it → 409 |
| `BackgroundTasks` runs after response but before client reads | Acceptable; notification is fire-and-forget log |
| Large number of line items in one sale | DTO validation caps practical size; DB CHECK on `cantidad > 0` |
| Decimal precision in total calculation | Use `Decimal` throughout; `Numeric(12,2)` in DB |

## Migration Plan

1. Add DTOs to `schemas.py`
2. Implement `VentaService.crear_venta()` in `service.py`
3. Implement `VentaService.obtener_venta()` and `listar_ventas()` with eager loading
4. Wire endpoints in `router.py`
5. Register router in `app/main.py` (already done if module imported)
6. Write `.http` test cases for C-06 evidence
7. Run tests, verify query count with `SQL_ECHO=true`

## Open Questions

None — all decisions resolved by existing patterns and KB constraints.