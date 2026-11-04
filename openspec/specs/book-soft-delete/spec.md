# book-soft-delete Specification

## Purpose
TBD - created by archiving change c-15-catalogo-uow-borrado-logico-y-stock. Update Purpose after archive.

## Requirements

### Requirement: Baja lógica de libros
`DELETE /libros/{id}` (ADMIN) SHALL marcar `borrado_en = now()` sin eliminar la fila y responder `204`; un id inexistente o ya dado de baja SHALL responder `404`. `LibroRepository` SHALL heredar de `SoftDeleteRepository[Libro]`, de modo que las lecturas del catálogo excluyan libros con `borrado_en` no nulo.

#### Scenario: Baja y desaparición del catálogo
- **WHEN** un ADMIN borra un libro vigente
- **THEN** responde `204` y `GET /libros/{id}` responde `404` y el libro no aparece en `GET /libros`

#### Scenario: Baja de libro inexistente
- **WHEN** un ADMIN borra un id que no existe
- **THEN** responde `404`

### Requirement: ISBN reutilizable tras la baja
El ISBN de un libro dado de baja SHALL quedar libre; el índice único parcial (`borrado_en IS NULL`) SHALL permitir un nuevo libro vigente con ese ISBN y rechazar un segundo vigente con `409`.

#### Scenario: Reutilizar ISBN
- **WHEN** se da de baja un libro y luego se crea otro con el mismo ISBN
- **THEN** el alta responde `201`

#### Scenario: Segundo vigente con el mismo ISBN
- **WHEN** se intenta crear un tercer libro con el ISBN de un libro vigente
- **THEN** responde `409`

### Requirement: Libro dado de baja no admite reposición
`POST /libros/{id}/reponer` sobre un libro dado de baja SHALL responder `409` y no escribir movimientos.

#### Scenario: Reponer libro dado de baja
- **WHEN** un ADMIN repone stock de un libro con `borrado_en` no nulo
- **THEN** responde `409` y no se agrega ninguna fila a `movimiento_stock`
