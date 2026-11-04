# stock-single-write-point Specification

## Purpose
TBD - created by archiving change c-15-catalogo-uow-borrado-logico-y-stock. Update Purpose after archive.

## Requirements

### Requirement: Punto único de escritura de stock
`libro.stock` SHALL modificarse únicamente mediante un método único del módulo `libros` que, dentro del mismo UoW, actualiza `libro.stock` y agrega la fila correspondiente en `MovimientoStock`, preservando `libro.stock == SUM(movimiento_stock.cantidad)`. Ninguna otra ruta SHALL escribir `libro.stock` ni modificar o borrar filas de `movimiento_stock`.

#### Scenario: Invariante tras varias operaciones
- **WHEN** se crea un libro con `stock_inicial=5` y se repone 3
- **THEN** `libro.stock == 8` y la suma de `cantidad` de sus movimientos es `8`

### Requirement: Alta de libro con stock inicial
`POST /libros` (ADMIN, `201`/`409`/`422`) SHALL recibir `stock_inicial` (no `stock`) y `autores`, crear el libro y registrar por el punto único un movimiento con motivo `"Stock inicial"` y `usuario_id` del usuario actual en el mismo UoW.

#### Scenario: Alta con movimiento inicial
- **WHEN** un ADMIN crea un libro con `stock_inicial=10`
- **THEN** responde `201` con `stock=10` y existe un movimiento `+10` con motivo `"Stock inicial"`

#### Scenario: Enviar stock en el alta
- **WHEN** el cuerpo incluye `stock`
- **THEN** responde `422`

#### Scenario: Stock inicial negativo
- **WHEN** `stock_inicial` es `-1`
- **THEN** responde `422`

#### Scenario: Atomicidad del alta
- **WHEN** el alta falla (por ejemplo ISBN vigente repetido) después de preparar el movimiento inicial
- **THEN** responde `409` y no queda ni libro ni movimiento de stock

### Requirement: Edición parcial sin stock
`PATCH /libros/{id}` (ADMIN, `200`/`404`/`409`/`422`) SHALL permitir solo `titulo` y `precio` con `exclude_unset=True`; enviar `stock` SHALL responder `422`.

#### Scenario: PATCH parcial
- **WHEN** se envía `{"titulo": "Nuevo"}`
- **THEN** responde `200`, cambia solo el título y el precio permanece

#### Scenario: PATCH con stock
- **WHEN** se envía `{"stock": 99}` o `{"stock_inicial": 5}`
- **THEN** responde `422` y el stock no cambia

### Requirement: Reposición de stock
`POST /libros/{id}/reponer` (ADMIN, `200`/`404`/`409`/`422`) SHALL sumar una `cantidad` positiva mediante el punto único y registrar un `MovimientoStock` positivo; cantidad `<= 0` SHALL responder `422`; libro inexistente `404`.

#### Scenario: Reposición correcta
- **WHEN** un ADMIN repone `cantidad=4` a un libro con stock 6
- **THEN** responde `200` con `stock=10` y un movimiento `+4`

#### Scenario: Cantidad inválida
- **WHEN** la cantidad es `0`
- **THEN** responde `422`

### Requirement: Consulta de movimientos
`GET /libros/{id}/movimientos` (ADMIN, `200`/`404`) SHALL listar los movimientos de stock del libro.

#### Scenario: Listado de movimientos
- **WHEN** un ADMIN consulta los movimientos de un libro repuesto una vez
- **THEN** responde `200` con el movimiento inicial y el de reposición

#### Scenario: Libro inexistente
- **WHEN** se consulta un id inexistente
- **THEN** responde `404`
