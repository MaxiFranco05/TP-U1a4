## Context

Estado observado: `ventas/service.py::crear_venta` recibe `AsyncSession`, carga libros con una consulta, valida existencia con `HTTPException(409)`, hace `flush()` y `commit()` propios, agenda el aviso antes del commit y nunca toca `libro.stock`; `clientes/service.py` y `ventas/router.py` usan `SessionDep` y `core/pagination.py` (lista cruda). `clientes/repository.py` solo define `ClienteRepository` básico. C-15 aportó `LibrosUnitOfWork.registrar_movimiento_stock` (FOR UPDATE, valida `stock + cantidad >= 0`, rechaza libros dados de baja con `ValueError`), `LibroRepository` (soft delete, `get_by_id_including_deleted`) y `MovimientoStockRepository`. `Cliente.usuario_id` ya existe (migración 003) y `usuarios/repository.py::AsignacionRolRepository.get_roles_vigentes_usuario` permite consultar roles vigentes. En `main.py` clientes y ventas están en el grupo protegido sin `requiere_rol`.

## Goals / Non-Goals

**Goals:**
- Clientes y ventas sobre Router → Service → UoW → Repository.
- Venta atómica con descuento de stock por el punto único y rollback total.
- Autorización de dueño en `GET /ventas/{id}` y `GET /mis-ventas`, sin N+1.

**Non-Goals:**
- Migraciones o cambios de esquema.
- Cambios en catálogo (hecho en C-15) o en el flujo de login.
- Borrado/PATCH de ventas (siguen sin existir).

## Decisions

- **`VentasUnitOfWork`** hereda de `UnitOfWork` y compone `VentaRepository`, `ClienteRepository`, `LibroRepository`, `MovimientoStockRepository` (misma sesión) y delega el stock en el mismo método de C-15. Para no duplicar la regla, `registrar_movimiento_stock` se extrae a un mixin/función reutilizable `StockWriter` importable por ambos UoW; **alternativa descartada**: copiar el método (viola el punto único).
- **Orden dentro de `async with uow:`**: (1) cargar libros vigentes con `get_by_id_for_update` en orden de `libro_id` (evita deadlocks), (2) si falta alguno o está de baja → `409`, (3) crear `Venta` + renglones con `precio_unitario` copiado y `total` Decimal, `flush()` (la FK de `cliente_id` rechaza cliente inexistente → `IntegrityError` traducido a `409`, sin consulta previa), (4) por renglón llamar al punto único con `-cantidad`, `venta.id`, `usuario_actual.id`; `ValueError` de stock insuficiente se traduce a `409` y revierte todo.
- **Aviso post-commit**: el servicio devuelve la venta tras salir del `async with`; recién entonces el router agenda `BackgroundTasks` con el aviso. Si el `with` lanza, nunca se agenda.
- **Autorización de dueño**: `GET /ventas/{id}` depende solo de `get_usuario_actual` (misma sesión). El servicio consulta roles vigentes en la base vía `AsignacionRolRepository` (nunca los del token, RN-04); si no es personal compara `venta.cliente.usuario_id == usuario_actual.id`. Un `404` se responde antes que el `403` solo si la venta no existe (no se filtra existencia a no autorizados: se resuelve primero la lectura y luego se autoriza).
- **`GET /mis-ventas`**: `VentaRepository.listar_por_usuario(usuario_id, ...)` filtra por `Cliente.usuario_id`; con envoltorio de paginación y el mismo `count` con los mismos filtros. Ruta registrada en `ventas/router.py` con prefijo propio (`/mis-ventas`) en el grupo protegido sin `requiere_rol`.
- **Precarga**: `VentaRepository.get_detalle` usa `joinedload(Venta.cliente)` y `selectinload(Venta.renglones).joinedload(RenglonVenta.libro)`; la consulta del libro debe incluir dados de baja (usa `select` directo sobre `Libro` vía relación, no `SoftDeleteRepository.get_by_id`).
- **Clientes**: `ClienteRepository` agrega `get_con_perfil`, `PerfilClienteRepository` agrega `get_por_cliente`; unicidad de email y de perfil por `UNIQUE`/FK con `translate_integrity_error`. `GET /clientes` (listado) se mantiene en el grupo protegido con `requiere_rol("VENDEDOR","ADMIN")` y envoltorio de paginación.
- **Paginación**: se usa `core/paginacion.py`; al terminar, `core/pagination.py` queda sin usos (se elimina o se deja marcado como obsoleto, ver Open Questions).

## Risks / Trade-offs

- [Deadlock entre ventas concurrentes con libros cruzados] → Bloquear `Libro` con `FOR UPDATE` en orden de `libro_id`.
- [El `ValueError` del punto único mezcla causas: stock insuficiente vs baja] → Mapear ambas a `409` con mensaje propio, sin texto interno.
- [Cambio BREAKING: los clientes de la API necesitan sesión/rol y nuevo envoltorio] → Actualizar tests y `.http`; documentado en la propuesta.
- [`get_by_id_for_update` excluye libros de baja y oculta la causa] → Resolver ambas ramas en el servicio con `get_by_id_including_deleted`.

## Migration Plan

Sin migración de esquema. Despliegue en un solo paso; rollback revirtiendo el commit.

## Open Questions

- ¿Eliminar `core/pagination.py` al terminar o mantenerlo? Se asume eliminarlo si ningún módulo lo importa (verificar con búsqueda).
- Cliente sin `usuario_id` en `GET /mis-ventas`: se asume listado vacío en lugar de `404`.
