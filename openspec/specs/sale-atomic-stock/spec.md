# sale-atomic-stock Specification

## Purpose
TBD - created by archiving change c-16-clientes-y-ventas-uow-stock-y-autorizacion. Update Purpose after archive.

## Requirements

### Requirement: Venta atómica sobre VentasUnitOfWork
`POST /ventas` (`requiere_rol("VENDEDOR", "ADMIN")`, `201/409/422`) SHALL ejecutarse en un único bloque `async with uow:` sobre `VentasUnitOfWork`, que compone `VentaRepository`, `ClienteRepository`, `LibroRepository` y `MovimientoStockRepository` con la misma sesión. El DTO de entrada SHALL ser `{cliente_id, renglones: [{libro_id, cantidad}]}` con `extra="forbid"`, al menos un renglón, cantidades `> 0` y sin libros repetidos (`422`); precio, total y fecha no viajan en el DTO.

#### Scenario: Venta válida
- **WHEN** un VENDEDOR vende 1 *Rayuela* y 2 *Ficciones* a un cliente existente
- **THEN** responde `201`, copia `precio_unitario` de cada libro, calcula `total` como `Decimal` y crea la venta con sus renglones

#### Scenario: Renglón repetido
- **WHEN** el cuerpo repite el mismo `libro_id`
- **THEN** responde `422`

### Requirement: Descuento de stock por el punto único
Por cada renglón la venta SHALL invocar `registrar_movimiento_stock` con `cantidad = -renglon.cantidad`, `venta_id = venta.id` y `usuario_id = usuario_actual.id`, preservando `libro.stock == SUM(movimiento_stock.cantidad)`. Ninguna otra escritura de `libro.stock` SHALL existir en el módulo.

#### Scenario: Descuento con movimientos
- **WHEN** se confirma una venta de 2 unidades de un libro con stock 8
- **THEN** el libro queda con stock `6` y existe un movimiento `-2` con `venta_id` de la venta

### Requirement: Rollback total ante conflicto
Cliente inexistente, libro inexistente, libro dado de baja (`borrado_en IS NOT NULL`) o stock insuficiente en cualquier renglón SHALL responder `409` y el UoW SHALL revertir toda la transacción: no queda venta, renglones, descuento de stock ni movimientos. La existencia SHALL delegarse a las FK de la base sin consulta previa de cliente; los errores de integridad se traducen sin texto interno.

#### Scenario: Stock insuficiente en el segundo renglón
- **WHEN** el primer renglón alcanza en stock y el segundo no
- **THEN** responde `409` y el stock del primer libro no cambia, sin venta ni movimientos

#### Scenario: Libro dado de baja
- **WHEN** un renglón referencia un libro con baja lógica
- **THEN** responde `409` sin escrituras

#### Scenario: Cliente inexistente
- **WHEN** `cliente_id` no existe
- **THEN** responde `409` sin escrituras

### Requirement: Aviso de comprobante posterior al commit
El aviso del comprobante (`await asyncio.sleep(0.5)` y mensaje en el log) SHALL agendarse en `BackgroundTasks` únicamente después de confirmar la transacción; la respuesta `201` no espera al aviso. Una venta revertida SHALL NOT agendar aviso.

#### Scenario: Venta confirmada
- **WHEN** la venta se confirma
- **THEN** el log registra el comprobante tras la respuesta

#### Scenario: Venta revertida
- **WHEN** la venta responde `409`
- **THEN** no se registra ningún aviso de comprobante
