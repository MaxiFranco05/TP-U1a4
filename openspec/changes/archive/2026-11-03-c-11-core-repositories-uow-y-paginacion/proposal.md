# Proposal

## Why

Los cambios posteriores del Parcial (`C-12` a `C-16`) requieren migrar todos los módulos de dominio a la arquitectura en 5 capas (`Router → Service → UoW → Repository → Model`) con transacciones atómicas, baja lógica en libros y respuestas paginadas uniformes. Sin las abstracciones base en `app/core/` (`BaseRepository[T]`, `SoftDeleteRepository[T]`, `UnitOfWork` y el envoltorio de paginación), cada módulo duplicaría el manejo de `flush()` vs `commit()`, el filtrado de `borrado_en IS NULL` y el cálculo/validación de páginas.

## What Changes

- **Nuevo módulo `app/core/repository.py`**:
  - Implementa `BaseRepository[T]` (`Generic[T]`), que recibe `session: AsyncSession` y `model_cls: type[T]` en su constructor y provee las operaciones CRUD base (`get_by_id`, `get_all`, `count`, `add`, `update`, `delete`) ejecutando únicamente `await self.session.flush()` (nunca `commit()`).
  - Implementa `SoftDeleteRepository[T](BaseRepository[T])`, que filtra por defecto los registros con `borrado_en IS NULL` en `get_by_id`, `get_all` y `count`, y agrega los métodos exclusivos `get_by_id_including_deleted` y `soft_delete` (marca `borrado_en = datetime.now(timezone.utc)` + `flush()`).
- **Nuevo módulo `app/core/unit_of_work.py`**:
  - Implementa `UnitOfWork` como gestor de contexto asincrónico (`__aenter__` / `__aexit__`) que recibe la `AsyncSession` de la petición, ejecuta `await self.session.commit()` al salir sin excepción, ejecuta `await self.session.rollback()` si ocurre cualquier excepción y **nunca cierra la sesión** (responsabilidad exclusiva de `get_session`).
- **Nuevo módulo `app/core/paginacion.py`**:
  - Implementa los parámetros de consulta `PaginationParams` (`page: int = Query(1, ge=1)` y `size: int = Query(20, ge=1, le=100)`), el esquema genérico `PaginatedResponse[T]` (`{items, total, page, size, pages}`) y la función constructora `paginate(...)` que garantiza `pages = 1` cuando `total == 0` y responde `422 Unprocessable Entity` con el mensaje exacto `«La página {page} no existe: hay {pages}»` cuando `page > pages`.

## Capabilities

### New Capabilities
- `core-repositories-uow`: Repositorios genéricos asincrónicos (`BaseRepository[T]` y `SoftDeleteRepository[T]`) sin `commit()` y gestor transaccional `UnitOfWork` sobre sesión compartida sin cierre de sesión.
- `pagination-envelope`: Parámetros de consulta (`page`, `size`), envoltorio genérico `{items, total, page, size, pages}` y validación de rango de páginas con respuesta `422`.

### Modified Capabilities
<!-- No existing capability requirements are modified in this change; module-level adoption happens in C-13..C-16. -->

## Impact

- **Código nuevo**: `app/core/repository.py`, `app/core/unit_of_work.py`, `app/core/paginacion.py`.
- **Tests nuevos**: `test/test_core_repositories_uow_and_paginacion.py` (pruebas unitarias y de integración contra PostgreSQL 16 real).
- **Dependencias habilitadas**: Desbloquea `C-12`, `C-13`, `C-14`, `C-15` y `C-16` (Bloques 2 y 3 del Parcial). No rompe ninguna ruta existente del TP mientras los módulos migran en `C-15` y `C-16`.
