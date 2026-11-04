## Context

Estado observado: `libros/service.py` expone funciones que reciben `AsyncSession`, ejecutan `session.commit()` y paginan con `app/core/pagination.py` (devuelve lista cruda). `libros/models.py` ya incluye `borrado_en`, el índice único parcial de `isbn` y `MovimientoStock` (migración 004, solo-agregado). Existen `core/repository.py` (`BaseRepository`, `SoftDeleteRepository`), `core/unit_of_work.py`, `core/paginacion.py` (`PaginatedResponse`, `paginate`, `calcular_paginas`, `validar_pagina`) y `requiere_rol`. `usuarios/unit_of_work.py` es el patrón de referencia. En `app/main.py` los routers de catálogo están hoy todos en el grupo protegido. Conviven `pagination.py` (legacy) y `paginacion.py`.

## Goals / Non-Goals

**Goals:**
- Catálogo íntegro sobre Router → Service → UoW → Repository.
- Un único método de escritura de stock; invariante `stock == SUM(movimientos)`.
- Baja lógica de libros y paginación con envoltorio.

**Non-Goals:**
- `clientes` y `ventas` (C-16); la venta reutilizará el punto único de stock.
- Migraciones nuevas o cambios de esquema.
- Eliminar `pagination.py` si otro módulo aún lo usa.

## Decisions

- **UoW por módulo**: `EditorialesUnitOfWork`, `GenerosUnitOfWork`, `AutoresUnitOfWork`, `LibrosUnitOfWork`, heredando de `UnitOfWork` como `UsuariosUnitOfWork`. `LibrosUnitOfWork` compone `LibroRepository`, `MovimientoStockRepository`, `EditorialRepository`, `AutorRepository` y `GeneroRepository`, todos con la misma sesión. Alternativa descartada: un UoW único de catálogo (acopla módulos sin necesidad).
- **Punto único de stock (RN-11)**: método `registrar_movimiento_stock(libro, cantidad, motivo, usuario_id, venta_id=None)` en `LibrosUnitOfWork`, que valida `stock + cantidad >= 0`, actualiza `libro.stock` y agrega el `MovimientoStock`, ambos con `flush()`. Alta, reposición y (en C-16) venta lo llaman. Alternativa descartada: triggers de BD que sincronicen `stock` (oculta la regla y fuera del alcance de la migración 004).
- **Flujo de stock inicial**: `POST /libros` recibe `stock_inicial` en el request body (no `stock`; entero `>= 0`). En un único bloque `async with uow:` el servicio (1) crea el `Libro` con `stock=0` y sus autorías, y (2) llama al punto único con `+stock_inicial`, motivo `"Stock inicial"` y `usuario_id` del ADMIN actual, que inserta el primer `MovimientoStock`. Si `stock_inicial == 0` no se inserta movimiento (`cantidad <> 0` por CHECK) y el invariante sigue valiendo. Libro y movimiento se confirman o se revierten juntos (atomicidad: un fallo del movimiento o del ISBN duplicado no deja libro huérfano). No hay otro camino que escriba `stock`.
- **PATCH sin stock**: `LibroUpdate` solo declara `titulo` y `precio` con `extra="forbid"`; cualquier alteración directa de `stock` (o `stock_inicial`) da `422` antes de ejecutar el handler. El stock solo cambia por alta, reposición y venta.
- **Unicidad delegada a la base**: ISBN y FK por `UNIQUE`/índice parcial/`FOREIGN KEY`; `IntegrityError` se traduce con `translate_integrity_error` dentro del servicio (la excepción propagada hace que el UoW revierta).
- **Paginación**: `size`/`page` con `paginate(...)`; `total` con `count(filters=...)` usando los mismos filtros que `get_all`; `422` si `page > pages` (pero `page=1` válido con `total=0`).
- **Grupos de rutas**: dividir cada router de catálogo en un `APIRouter` público (solo GET de lectura) y uno protegido con `dependencies=[Depends(requiere_rol("ADMIN"))]`, montados en `open_group` y `protected_group` de `main.py`. `GET /autores` (listado) y `GET /autores/{id}/libros` son **públicos**: los clientes finales necesitan listar autores para explorar el catálogo. `GET /autores/{id}` y `GET /libros/{id}/movimientos` quedan protegidos (ADMIN) por no estar en la lista de lecturas abiertas.
- **Precarga**: `LibroRepository.get_detalle` y `listar` declaran `joinedload(editorial)`, `joinedload(genero)` y `selectinload(autorias).joinedload(autor)`.
- **Autoría y bajas**: los renglones de ventas históricas siguen leyendo libros dados de baja en C-16; aquí `get_by_id` del soft-delete oculta libros de baja en el catálogo.

## Risks / Trade-offs

- [El cambio `stock` → `stock_inicial` y el envoltorio rompen clientes y tests actuales] → Actualizar tests y `.http` en el mismo grupo de tareas; marcado **BREAKING** en la propuesta.
- [Condición de carrera en reposición/ventas concurrentes] → Leer el libro con `SELECT ... FOR UPDATE` al registrar el movimiento; `CHECK stock >= 0` es la red de seguridad de la base.
- [Mover rutas públicas puede dejar escrituras expuestas] → Test que verifica `401/403` en cada escritura y `200` anónimo en cada lectura abierta.
- [`pagination.py` legacy usado por `clientes`/`ventas`] → Se mantiene hasta C-16.

## Migration Plan

Sin migración de esquema. Despliegue en un solo paso. Rollback: revertir el commit; los datos no cambian de forma.

## Open Questions

- Motivo textual de la reposición (`"Reposición"`): se asume ese valor fijo.
