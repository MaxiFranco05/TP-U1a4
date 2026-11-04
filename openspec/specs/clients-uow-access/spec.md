# clients-uow-access Specification

## Purpose
TBD - created by archiving change c-16-clientes-y-ventas-uow-stock-y-autorizacion. Update Purpose after archive.

## Requirements

### Requirement: Clientes sobre Repository y UnitOfWork
El módulo `clientes` SHALL tener `repository.py` (`ClienteRepository`, `PerfilClienteRepository`, con la precarga de `perfil` y `usuario` declarada dentro del repositorio) y `unit_of_work.py` (`ClientesUnitOfWork`). El router construye el UoW por dependencia con la sesión de `get_session`; el servicio lo recibe sin abrir y lo abre con `async with uow:`. Los repositorios SHALL ejecutar solo `flush()`.

#### Scenario: Alta de cliente confirmada por el UoW
- **WHEN** un VENDEDOR crea un cliente válido
- **THEN** responde `201` y el `commit()` lo ejecuta el UoW

#### Scenario: Email repetido
- **WHEN** se crea un cliente con un email ya existente
- **THEN** responde `409` con mensaje propio, sin texto interno de la base

### Requirement: Contratos de entrada estrictos en clientes
Los esquemas de entrada de clientes y perfil SHALL declarar `extra="forbid"`; un campo no declarado SHALL responder `422`.

#### Scenario: Campo desconocido en el alta
- **WHEN** `POST /clientes` incluye un campo no declarado
- **THEN** responde `422`

### Requirement: Rutas de clientes restringidas al personal
`POST /clientes`, `GET /clientes/{id}`, `PATCH /clientes/{id}`, `POST /clientes/{id}/perfil` y `GET /clientes/{id}/ventas` SHALL exigir `requiere_rol("VENDEDOR", "ADMIN")` evaluado contra `asignacion_rol` vigentes.

#### Scenario: Sin sesión
- **WHEN** un visitante anónimo consulta `GET /clientes/1`
- **THEN** responde `401`

#### Scenario: Rol insuficiente
- **WHEN** un usuario con rol `CLIENTE` envía `POST /clientes`
- **THEN** responde `403`

### Requirement: Perfil único por cliente
`POST /clientes/{id}/perfil` SHALL crear a lo sumo un perfil por cliente (RN-09): un segundo perfil responde `409` y un cliente inexistente responde `404`/`409` según la convención de FK.

#### Scenario: Segundo perfil
- **WHEN** se crea un perfil para un cliente que ya tiene uno
- **THEN** responde `409`

### Requirement: Historial de ventas del cliente
`GET /clientes/{id}/ventas` SHALL devolver el historial de ventas del cliente con envoltorio de paginación; un cliente inexistente SHALL responder `404`.

#### Scenario: Cliente inexistente
- **WHEN** se consulta el historial de un cliente que no existe
- **THEN** responde `404`
