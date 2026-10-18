# Tasks

## 1. DTOs (schemas.py)

- [x] 1.1 Add `RenglonVentaCreate` with fields `libro_id: int`, `cantidad: int` and validation `cantidad > 0`; verify Pydantic rejects `cantidad <= 0` with 422
- [x] 1.2 Add `VentaCreate` with fields `cliente_id: int`, `renglones: list[RenglonVentaCreate]` and root validator ensuring at least one renglón and no duplicate `libro_id`; verify 422 for empty list and duplicate books
- [x] 1.3 Ensure `VentaRead` and `RenglonVentaRead` already exist and include all required fields (`precio_unitario` in line, `total` in sale); verify imports work

## 2. Service Layer (service.py)

- [x] 2.1 Implement `async def _notificar_comprobante(venta_id: int) -> None` with `await asyncio.sleep(0.5)` and log; verify it runs in background without blocking
- [x] 2.2 Implement `async def crear_venta(session: AsyncSession, data: VentaCreate, background_tasks: BackgroundTasks) -> VentaRead`:
  - Extract unique `libro_id`s from renglones
  - Load all `Libro`s in one query: `select(Libro).where(Libro.id.in_(ids))`
  - Build dict `libro_id -> precio`
  - Create `RenglonVenta` objects with `precio_unitario` copied from dict
  - Compute `total = sum(cantidad * precio_unitario)`
  - Create `Venta` with `cliente_id`, `total`, `renglones`
  - Add to session, flush to get IDs
  - Schedule `background_tasks.add_task(_notificar_comprobante, venta.id)`
  - Return `VentaRead` with nested renglones
  - Verify: 201 with correct prices/total, background task scheduled
- [x] 2.3 Add `IntegrityError` handling around commit: catch, call `translate_integrity_error`, re-raise; verify 409 for missing client ("Cliente no encontrado") and missing book ("El libro referenciado no existe")
- [x] 2.4 Implement `async def obtener_venta(session: AsyncSession, venta_id: int) -> VentaRead | None` with `joinedload(Venta.cliente)` + `selectinload(Venta.renglones).selectinload(RenglonVenta.libro)`; verify single query with `SQL_ECHO=true`
- [x] 2.5 Implement `async def listar_ventas(session: AsyncSession, pagination: PaginationParams) -> list[VentaRead]` with `joinedload(Venta.cliente)` and pagination; verify paginated list works

## 3. Router (router.py)

- [x] 3.1 Add `POST /ventas/` endpoint with `VentaCreate` body, `BackgroundTasks` dependency, `get_session`, returning `VentaRead` with status 201; verify endpoint registered and responds
- [x] 3.2 Add `GET /ventas/{venta_id}` endpoint returning `VentaRead` or 404; verify detail with eager loading
- [x] 3.3 Add `GET /ventas/` endpoint with `PaginationParams` dependency returning `list[VentaRead]`; verify pagination works
- [x] 3.4 Ensure no PATCH/DELETE endpoints exist (RN-08); verify not present

## 4. Tests & Evidence (.http files)

- [x] 4.1 Create `test/c-06-ventas.http` with cases:
  - Happy path: valid client + 1 line → 201 with price copied, total correct
  - Happy path: valid client + multiple lines → 201 with summed total
  - 422: empty renglones
  - 422: duplicate libro_id
  - 422: cantidad <= 0
  - 409: non-existent cliente_id
  - 409: non-existent libro_id
  - Verify background task runs (check logs)
- [x] 4.2 Run `.http` file and verify all cases pass; capture evidence for C-06

## 5. Integration Verification

- [x] 5.1 Start app with `SQL_ECHO=true`, run `GET /ventas/{id}` for sale with 1 and 10 renglones; verify exactly 1 query each (fixed count)
- [x] 5.2 Run full test suite (`pytest`) to ensure no regressions in existing modules
- [x] 5.3 Verify `alembic upgrade head` still works (no model changes needed)

## 6. Documentation

- [x] 6.1 Update `README.md` with C-06 endpoint documentation if needed
- [x] 6.2 Ensure `CHANGES.md` has C-06 marked as in-progress (done by apply phase)