## ADDED Requirements

### Requirement: Listado paginado de ventas para el personal
`GET /ventas` (`requiere_rol("VENDEDOR", "ADMIN")`, `200/422`) SHALL responder `{items, total, page, size, pages}` con `page >= 1`, `size` 1..100 y `422` si `page > pages`.

#### Scenario: Listado válido
- **WHEN** un VENDEDOR consulta `GET /ventas?page=1&size=10`
- **THEN** responde `200` con el envoltorio de paginación

#### Scenario: Cliente sin rol de personal
- **WHEN** un usuario `CLIENTE` consulta `GET /ventas`
- **THEN** responde `403`

### Requirement: Detalle de venta con autorización de dueño
`GET /ventas/{id}` SHALL estar en el grupo protegido sin `requiere_rol` en la ruta. El servicio SHALL permitir el acceso si el usuario tiene rol vigente `ADMIN` o `VENDEDOR` en la base, o si es el cliente dueño (`venta.cliente.usuario_id == usuario_actual.id`); en otro caso SHALL responder `403`; una venta inexistente SHALL responder `404`.

#### Scenario: Dueño ve su venta
- **WHEN** el usuario cliente `ana@example.com` consulta una venta de su cliente
- **THEN** responde `200`

#### Scenario: Cliente ve venta ajena
- **WHEN** el mismo usuario consulta la venta de otro cliente
- **THEN** responde `403`

#### Scenario: Personal ve cualquier venta
- **WHEN** un VENDEDOR consulta cualquier venta existente
- **THEN** responde `200`

#### Scenario: Venta inexistente
- **WHEN** se consulta un id que no existe
- **THEN** responde `404`

### Requirement: Ventas propias del cliente
`GET /mis-ventas` (autenticado, `200/422`) SHALL devolver, paginadas con el envoltorio, las ventas del cliente asociado a `usuario_actual` (RN-14); un usuario sin cliente asociado SHALL recibir un listado vacío con `total: 0`.

#### Scenario: Ventas propias
- **WHEN** `ana@example.com` consulta `GET /mis-ventas`
- **THEN** responde `200` solo con las ventas de su cliente

### Requirement: Detalle sin N+1 y con libros dados de baja
El detalle de venta SHALL cargar `cliente`, `renglones` y `renglones.libro` con `joinedload`/`selectinload` declarados dentro de `VentaRepository`, con un número fijo de consultas SQL independiente de la cantidad de renglones, y SHALL mostrar el título de libros dados de baja después de la venta.

#### Scenario: Consultas fijas
- **WHEN** se lee el detalle de una venta con 2 renglones y el de otra con 4
- **THEN** ambas lecturas ejecutan la misma cantidad de consultas SQL

#### Scenario: Libro dado de baja posteriormente
- **WHEN** se lee una venta cuyo libro fue dado de baja después
- **THEN** el renglón muestra el título del libro
