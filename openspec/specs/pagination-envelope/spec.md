# pagination-envelope Specification

## Purpose
Provee el contrato uniforme de paginación para todos los listados del sistema: validación de parámetros de consulta (`page >= 1`, `1 <= size <= 100`), envoltorio genérico `{items, total, page, size, pages}` y rechazo con `422` cuando se solicita una página inexistente.

## Requirements

### Requirement: Pagination Query Parameters Validation
The system SHALL accept `page` (default `1`, integer `>= 1`) and `size` (default `20`, integer between `1` and `100` inclusive) as query parameters on paginated endpoints and reject out-of-range values with HTTP `422`.

#### Scenario: Default pagination parameters applied
- **WHEN** a client requests a paginated endpoint without specifying `page` or `size`
- **THEN** the system uses `page = 1` and `size = 20` (corresponding to `offset = 0` and `limit = 20`)

#### Scenario: Out-of-bounds page or size rejected with 422
- **WHEN** a client sends `page < 1`, `size < 1`, or `size > 100`
- **THEN** the system responds with HTTP `422 Unprocessable Entity`

### Requirement: Uniform Paginated Response Envelope and Page Bounds Check
The system SHALL wrap paginated results in `{items, total, page, size, pages}`, compute `pages = 1` when `total == 0` and `pages = ceil(total / size)` when `total > 0`, and reject any request where `page > pages` with HTTP `422` and message `"La página {page} no existe: hay {pages}"`.

#### Scenario: Empty result set on page 1 returns 1 empty page
- **WHEN** a paginated query matches `total == 0` records and the client requests `page = 1` with `size = 20`
- **THEN** the system returns `{items: [], total: 0, page: 1, size: 20, pages: 1}`

#### Scenario: Requesting page 2 or higher on empty result set returns 422
- **WHEN** a paginated query matches `total == 0` records and the client requests `page = 2`
- **THEN** the system responds with HTTP `422` and detail `"La página 2 no existe: hay 1"`

#### Scenario: Requesting a page beyond available pages returns 422
- **WHEN** a paginated query matches `total = 25` records with `size = 10` (`pages = 3`) and the client requests `page = 4`
- **THEN** the system responds with HTTP `422` and detail `"La página 4 no existe: hay 3"`
