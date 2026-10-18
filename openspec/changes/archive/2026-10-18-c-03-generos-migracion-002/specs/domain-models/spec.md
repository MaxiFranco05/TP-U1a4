# Spec Delta — domain-models

## ADDED Requirements

### Requirement: Genre persistence model and optional book genre relationship

The system SHALL define `Genero` (`genero`) with `id` and `nombre` (`UNIQUE`), and extend `Libro` (`libro`) with an optional foreign key `genero_id` (`nullable=True`, `FK` to `genero.id` with explicit index `ix_libro_genero_id`) and bidirectional `Relationship(back_populates=...)` between `Libro.genero` (`Optional[Genero]`) and `Genero.libros` (`list[Libro]`).

#### Scenario: Book persists with or without a genre and navigates bidirectionally

- **WHEN** a `Genero` is persisted and one `Libro` is stored with `genero_id` pointing to that genre while another `Libro` is stored with `genero_id=None`
- **THEN** PostgreSQL stores both books, `libro_con_genero.genero` navigates to the `Genero` instance, `genero.libros` includes `libro_con_genero`, and `libro_sin_genero.genero` is `None`

#### Scenario: Duplicate genre name is rejected at the database level

- **WHEN** a persistence operation attempts to insert a duplicate `genero.nombre`
- **THEN** PostgreSQL rejects the statement with an integrity error on the `UNIQUE` constraint
