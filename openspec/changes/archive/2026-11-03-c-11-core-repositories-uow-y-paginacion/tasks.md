# Tasks

## 1. Safety Net y Repositorios Base (`app/core/repository.py`)

- [x] 1.1 Ejecutar la suite existente (`.\.venv\Scripts\python -m pytest`) como Safety Net y verificar línea base de 35/35 tests en verde contra PostgreSQL 16 (`tp_libreria_pg16`).
- [x] 1.2 Seguir ciclo TDD (RED → GREEN → TRIANGULATE → REFACTOR) para `BaseRepository[T]` en `app/core/repository.py` y sus pruebas en `test/test_core_repositories_uow_and_paginacion.py`: verificar contra PostgreSQL 16 real y con espías de sesión que `add`, `update` y `delete` ejecutan `flush()` y **nunca** `commit()`, y que `get_by_id`, `get_all` y `count` operan correctamente sobre `model_cls`.
- [x] 1.3 Seguir ciclo TDD (RED → GREEN → TRIANGULATE → REFACTOR) para `SoftDeleteRepository[T](BaseRepository[T])` en `app/core/repository.py` y sus pruebas en `test/test_core_repositories_uow_and_paginacion.py`: verificar con `Libro` en PostgreSQL 16 que `get_by_id`, `get_all` y `count` filtran `borrado_en IS NULL`, que `soft_delete` asigna `borrado_en` con zona horaria UTC y hace `flush()` sin `commit()`, que `get_by_id_including_deleted` recupera libros dados de baja, y que `BaseRepository` **no** posee `soft_delete` ni `get_by_id_including_deleted`.

## 2. Unit of Work Base (`app/core/unit_of_work.py`)

- [x] 2.1 Seguir ciclo TDD (RED → GREEN → TRIANGULATE → REFACTOR) para `UnitOfWork` en `app/core/unit_of_work.py` y sus pruebas en `test/test_core_repositories_uow_and_paginacion.py`: verificar que al salir limpio de `async with uow:` ejecuta `await session.commit()` persistiendo cambios en PostgreSQL 16, que ante una excepción dentro del bloque ejecuta `await session.rollback()` revirtiendo los `flush()` previos sin dejar filas sueltas, y que **nunca** invoca `session.close()`.

## 3. Envoltorio y Validación de Paginación (`app/core/paginacion.py`)

- [x] 3.1 Seguir ciclo TDD (RED → GREEN → TRIANGULATE → REFACTOR) para `PaginationParams`, `PaginatedResponse[T]`, `calcular_paginas` y `paginate` en `app/core/paginacion.py` y sus pruebas en `test/test_core_repositories_uow_and_paginacion.py`: verificar la estructura exacta `{items, total, page, size, pages}`, `total == 0` → `pages == 1` (`page=1` devuelve lista vacía y `pages=1`), rechazo `422` con mensaje exacto `"La página {page} no existe: hay {pages}"` cuando `page > pages` (tanto con `total == 0` y `page=2` como con `total > 0`), y rechazo `422` en FastAPI cuando `page < 1`, `size < 1` o `size > 100`.

## 4. Verificación Integral de Regresión

- [x] 4.1 Ejecutar la suite completa (`.\.venv\Scripts\python -m pytest -v`) y verificar que todos los tests (anteriores + nuevos de `C-11`) pasen en verde sin advertencias ni regresiones.
