# Proposal

## Why

`clientes` y `ventas` siguen con servicios que reciben `AsyncSession`, hacen `commit()`/`rollback()` por su cuenta, paginan con la lista cruda de `core/pagination.py` y no descuentan stock: `crear_venta` copia precios y calcula el total pero nunca escribe `libro.stock` ni `MovimientoStock`, valida existencia con una consulta previa y no filtra libros dados de baja. Además todas sus rutas son accesibles para cualquier usuario autenticado y no existe autorización de dueño (RN-14). C-15 dejó listo el punto único de stock (`LibrosUnitOfWork.registrar_movimiento_stock`) y el soft delete; ahora se puede cerrar el flujo de venta atómica (RN-10, RN-11, RN-13, RN-14, RN-15).

## What Changes

- `clientes`: `PerfilClienteRepository`, extensión de `ClienteRepository` (precarga de `perfil` y `usuario` dentro del repositorio) y `ClientesUnitOfWork`; servicios reciben el UoW sin abrir y usan `async with uow:`; esquemas con `extra="forbid"`.
- Rutas de `clientes` (`POST /clientes`, `GET /clientes/{id}`, `PATCH /clientes/{id}`, `POST /clientes/{id}/perfil`, `GET /clientes/{id}/ventas`) en el grupo protegido con `requiere_rol("VENDEDOR", "ADMIN")`.
- `ventas`: `VentaRepository` (precarga `cliente`, `renglones`, `renglones.libro`, incluyendo libros dados de baja en el detalle histórico) y `VentasUnitOfWork` que compone `VentaRepository`, `ClienteRepository`, `LibroRepository` y `MovimientoStockRepository` con la misma sesión.
- `POST /ventas` atómico (`VENDEDOR`/`ADMIN`, `201/409/422`): en un solo `async with uow:` verifica libros vigentes y stock, copia `precio_unitario`, calcula `total` (`Decimal`), crea venta y renglones y descuenta stock por renglón invocando el punto único de stock (movimiento `-cantidad`, `venta_id`, `usuario_id` del usuario actual). Cliente/libro inexistente, libro dado de baja o stock insuficiente → `409` con rollback total (`stock == SUM(cantidad)` intacto). El aviso en `BackgroundTasks` se agenda recién tras confirmar.
- `GET /ventas` (`VENDEDOR`/`ADMIN`): envoltorio `{items, total, page, size, pages}`.
- `GET /ventas/{id}` (sin `requiere_rol` en la ruta): `200` si el usuario tiene rol vigente `ADMIN`/`VENDEDOR` o es el cliente dueño (`venta.cliente.usuario_id == usuario_actual.id`); si no, `403`; `404` si no existe. Número fijo de consultas.
- Nuevo `GET /mis-ventas` (autenticado, paginado): ventas del cliente asociado al usuario actual.
- **BREAKING**: `POST /ventas` pasa a descontar stock y rechaza ventas sin stock suficiente; las rutas de `clientes`/`ventas` ahora exigen sesión y rol; los listados cambian de lista a envoltorio paginado.

## Capabilities

### New Capabilities
- `clients-uow-access`: clientes y perfil sobre Repository/UoW, contratos estrictos y acceso restringido a `VENDEDOR`/`ADMIN`.
- `sale-atomic-stock`: alta de venta atómica en UoW con descuento de stock por el punto único, rollback total y aviso posterior al commit.
- `sale-owner-authorization`: lecturas de venta con autorización de dueño (RN-14), `GET /mis-ventas`, listado paginado y detalle sin N+1.

### Modified Capabilities
<!-- Ninguna: los specs archivados `clientes` y `ventas` se reemplazan por comportamiento del código nuevo; los requisitos nuevos se declaran en las capacidades anteriores sin alterar esos archivos. -->

## Impact

- Código: `app/modules/clientes/` y `app/modules/ventas/` (nuevos `unit_of_work.py`, `repository.py`; cambios en `router.py`, `schemas.py`, `service.py`), `app/main.py` (mover rutas, montar `/mis-ventas`).
- Reutiliza `LibrosUnitOfWork.registrar_movimiento_stock` (C-15), `core/paginacion.py`, `requiere_rol` y `get_usuario_actual`; sin migración nueva (usa `cliente.usuario_id`, `movimiento_stock.venta_id`, trigger de solo-agregado de la migración 004).
- Tests y `.http` de clientes/ventas (`c-05-clientes.http`, `c-06-ventas.http`, `c-07-c-08-evidencia.http`) deben actualizarse. Tras esto `core/pagination.py` queda sin usos.
- Governance CRÍTICO: propuesta para revisión antes de implementar.
