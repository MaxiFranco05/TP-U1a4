# Proposal

## Why

Implement the "Alta de venta con renglones" (US-030), which is the **principal risk (riesgo principal)** of the project. This capability registers a sale with its line items in a single atomic operation, copying prices from books at the moment of sale, calculating totals server-side, and scheduling a background notification. It is the core transactional flow of the sales domain and must handle concurrency, data integrity, and business rules correctly.

## What Changes

- **New endpoint**: `POST /ventas/` accepting `{cliente_id, renglones: [{libro_id, cantidad}]}` and returning `201` with the created sale including copied prices, subtotals, and total
- **DTO layer**: Add `VentaCreate`, `RenglonVentaCreate`, and enhanced `VentaRead`/`RenglonVentaRead` schemas with proper validation
- **Service layer**: Implement `VentaService.crear_venta()` with:
  - Validation of business rules (RN-04, RN-05): at least one line item, no duplicate books
  - Read book prices from DB, compute subtotals and total (RN-06, RN-07)
  - Persist `Venta` + `RenglonVenta` in a single transaction (composition)
  - Translate `IntegrityError` for missing client/book → `409` (RN-12, C-05)
  - Schedule background task for notification (`asyncio.sleep(0.5)` + log) without blocking response
- **Router layer**: Wire the endpoint with proper dependencies (`get_session`, `BackgroundTasks`)
- **Eager loading**: Ensure `GET /ventas/{id}` uses `joinedload` for client + `selectinload` for lines (fixed query count)

## Capabilities

### New Capabilities

- `ventas/alta-con-renglones`: Covers the end-to-end creation of a sale with nested line items, price copying, total calculation, FK integrity, and background notification scheduling. This is a cohesive system behavior that owns the transactional sale registration flow.

### Modified Capabilities

- `ventas`: Existing capability for sales queries (US-031) — the read behavior is unchanged, but the same capability's spec should be extended to include the fixed-query-count detail view requirement (already covered by US-031 criteria)

## Impact

- **Code**: `app/modules/ventas/schemas.py` (add create DTOs), `app/modules/ventas/service.py` (implement business logic), `app/modules/ventas/router.py` (add POST endpoint)
- **Models**: Already exist (`Venta`, `RenglonVenta` with proper constraints and relationships)
- **DB**: No schema changes needed — tables `venta` and `renglon_venta` exist with FKs, CHECK constraints, and indexes
- **Dependencies**: Uses `app.core.exceptions.translate_integrity_error` for 409 mapping, `BackgroundTasks` for async notification
- **Tests**: New `.http` test cases for C-06 evidence (201 with prices/total, 409 for missing client/book, 422 for invalid input)