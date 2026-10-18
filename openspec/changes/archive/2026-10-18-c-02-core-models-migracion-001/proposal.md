# Proposal — C-02 core-models-migracion-001

## Why

Con el scaffolding, ciclo de vida y Alembic asincrónico ya operativos tras `C-01`, la aplicación todavía carece de modelos de persistencia y de esquema en PostgreSQL 16. Definir los modelos core del dominio y generar la primera migración (`001`) es requisito bloqueante para el cambio de evolución de esquema (`C-03`, que agrega `genero` y `libro.genero_id` en una segunda migración para cumplir el requisito de al menos 2 migraciones del Ej. 3) y para todos los endpoints de negocio (`C-04` a `C-08`).

## What Changes

- Definición de los 8 modelos `SQLModel(..., table=True)` iniciales del dominio repartidos en sus respectivos módulos (`editoriales`, `autores`, `libros`, `clientes`, `ventas`), dejando deliberadamente `genero` y `libro.genero_id` para `C-03`:
  - `Editorial` (`editorial`): `id`, `nombre` (`UNIQUE`), `pais`.
  - `Autor` (`autor`): `id`, `nombre`, `nacionalidad`.
  - `Libro` (`libro`, aún sin `genero_id`): `id`, `isbn` (`UNIQUE`), `titulo`, `precio` (`Decimal` / `NUMERIC(10, 2)`, `CHECK precio > 0`), `stock` (`CHECK stock >= 0`), `editorial_id` (`FK` a `editorial.id` con índice explícito).
  - `LibroAutor` (`libro_autor`, objeto de asociación en `app/modules/libros/models.py`): clave primaria compuesta (`libro_id`, `autor_id`), `rol` (`CHECK rol IN ('autor', 'coautor', 'traductor', 'ilustrador')`), `orden` (`CHECK orden >= 1`), índices explícitos en FKs y navegación `libro.autorias[i].autor`.
  - `Cliente` (`cliente`): `id`, `nombre`, `email` (`UNIQUE`), relación 1 a 0..1 `Cliente.perfil` que devuelve un objeto único (no lista) y 1 a * con `Venta`.
  - `PerfilCliente` (`perfil_cliente`, en `app/modules/clientes/models.py`): `id`, `cliente_id` (`FK` a `cliente.id` + `UNIQUE` para garantizar RN-09), `telefono`, `direccion`.
  - `Venta` (`venta`): `id`, `cliente_id` (`FK` a `cliente.id` con índice explícito), `fecha` (`TIMESTAMPTZ`), `total` (`Decimal` / `NUMERIC(12, 2)`, `CHECK total >= 0`), relación de composición con `RenglonVenta`.
  - `RenglonVenta` (`renglon_venta`, en `app/modules/ventas/models.py`): `id`, `venta_id` (`FK` a `venta.id` con índice explícito), `libro_id` (`FK` a `libro.id` con índice explícito), `cantidad` (`CHECK cantidad > 0`), `precio_unitario` (`Decimal` / `NUMERIC(10, 2)`, `CHECK precio_unitario > 0`).
- Registro de todos los modelos de tabla en `migrations/env.py` para que `SQLModel.metadata` los exponga a Alembic.
- Generación de la **migración 001** mediante `alembic revision --autogenerate`, revisión manual documentada (ajustando cualquier omisión de `CHECK` o tipos específicos de PostgreSQL si fuera necesario) y verificación del ciclo completo `upgrade head` → `downgrade base` → `upgrade head` sobre la base vacía de PostgreSQL 16.
- Suite de pruebas de integración contra PostgreSQL 16 verificando constraints en la base (`UNIQUE`, `CHECK`, `FK`) y navegación bidireccional de relaciones (`libro.autorias[i].autor`, `cliente.perfil` como instancia única).

## Capabilities

### New Capabilities

- `domain-models`: modelos de tabla del dominio core (`editorial`, `autor`, `libro` sin `genero_id`, `libro_autor`, `cliente`, `perfil_cliente`, `venta`, `renglon_venta`), restricciones de integridad en base (`UNIQUE`, `CHECK`, `FK` con índices explícitos), tipos monetarios `Decimal` (`NUMERIC`) y temporales con zona horaria (`TIMESTAMPTZ`), y navegación bidireccional de relaciones (`Relationship(back_populates=...)`, `libro.autorias[i].autor`, `Cliente.perfil` como objeto único).
- `schema-migrations`: versionado evolutivo del esquema con Alembic asincrónico (`--autogenerate`), primera migración (`001`) con las 8 tablas iniciales (sin `genero`), revisión manual documentada del script autogenerado y verificación de `upgrade head` / `downgrade base` sobre base vacía.

### Modified Capabilities

(none — no se modifican los requisitos de `app-lifecycle` ni `health`)

## Impact

- Archivos afectados:
  - `app/modules/editoriales/models.py`
  - `app/modules/autores/models.py`
  - `app/modules/libros/models.py`
  - `app/modules/clientes/models.py`
  - `app/modules/ventas/models.py`
  - `migrations/env.py` y `migrations/versions/<rev>_001_initial_core_models.py`
  - `tests/test_core_models_and_migration_001.py`
- Desbloquea `C-03` (`genero-migracion-002`), `C-04` (`catalogos-base-crud`) y `C-05` (`clientes-y-perfil`).
- Sin cambios rompientes sobre `health` ni `app-lifecycle`.
