# Proposal

## Why

El catálogo (`editoriales`, `generos`, `autores`, `libros`) sigue usando funciones de servicio que reciben `AsyncSession`, hacen `commit()` por su cuenta, paginan con la lista cruda de `core/pagination.py` y tratan `libro.stock` como un campo editable. Eso contradice la arquitectura de 5 capas del Parcial (Router → Service → UoW → Repository → Model) y las reglas RN-11 (punto único de stock), RN-13 (baja lógica) y RN-10/Ej. 3 (paginación con envoltorio). C-11 (repositorios/UoW) y C-12 (`requiere_rol`) ya existen, así que ahora se puede migrar el catálogo; C-16 (ventas) depende de este punto único de stock.

## What Changes

- Nuevos `repository.py` y `unit_of_work.py` en `editoriales`, `generos`, `autores` y `libros`; los servicios dejan de recibir la sesión, reciben un UoW sin abrir y lo abren con `async with uow:`. Ningún repositorio hace `commit()`.
- Contratos de entrada con `extra="forbid"` y listados con envoltorio `{items, total, page, size, pages}` (`page >= 1`, `size` 1..100, `422` si `page > pages`, `total` con los mismos filtros que la página), usando `app/core/paginacion.py`.
- Separación en grupo abierto (lecturas públicas de catálogo) y grupo protegido (`requiere_rol("ADMIN")` en escrituras) en `app/main.py`.
- `LibroRepository` hereda de `SoftDeleteRepository[Libro]` y declara toda precarga (`editorial`, `genero`, `autorias.autor`) dentro de sus métodos.
- **Punto único de escritura de stock** (RN-11): un único método que actualiza `libro.stock` y agrega la fila de `MovimientoStock` en el mismo UoW.
- `POST /libros` recibe `stock_inicial` (reemplaza `stock`) y registra el movimiento `"Stock inicial"`.
- `PATCH /libros/{id}` solo edita `titulo` y `precio`; enviar `stock` da `422`. **BREAKING**: el campo `stock` deja de aceptarse en `POST` y `PATCH`.
- `DELETE /libros/{id}` hace baja lógica (`borrado_en = now()`, `204`); el ISBN queda libre para un nuevo libro vigente.
- Nuevos `POST /libros/{id}/reponer` y `GET /libros/{id}/movimientos` (ADMIN).
- Errores de integridad traducidos a `409`/`422` sin texto interno de la base (RN-15).

## Capabilities

### New Capabilities
- `catalog-uow-pagination`: catálogo sobre Repository/UoW, contratos `extra="forbid"`, paginación con envoltorio y reparto grupo abierto / grupo protegido.
- `book-soft-delete`: baja lógica de libros, exclusión del catálogo y liberación del ISBN (RN-13).
- `stock-single-write-point`: único camino de escritura de `libro.stock` con `MovimientoStock` (alta con `stock_inicial`, reposición, consulta de movimientos; RN-11).

### Modified Capabilities
<!-- Ninguna: no se altera el contrato de specs ya archivadas en openspec/specs/; el comportamiento previo de catalog-* se reemplaza vía código y se cubre con los specs nuevos. -->

## Impact

- Código: `app/modules/{editoriales,generos,autores,libros}/` (nuevos `repository.py`, `unit_of_work.py`; cambios en `router.py`, `schemas.py`, `service.py`), `app/main.py` (reparto de routers).
- Reutiliza `app/core/{repository,unit_of_work,paginacion,dependencies}.py` y `MovimientoStock` (migración 004, solo-agregado) sin tocar el esquema: no hay migración nueva.
- Tests existentes de catálogo (`test_generos_and_migration_002.py`, `.http` de libros/editoriales/autores) deberán actualizarse al nuevo envoltorio y a `stock_inicial`.
- Governance ALTO: propuesta para revisión antes de implementar. No cambia `clientes`/`ventas` (C-16).
