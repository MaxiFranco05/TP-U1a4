# Design — C-02 core-models-migracion-001

## Context

Tras `C-01`, el proyecto cuenta con `app/core/database.py` (motor asincrónico + `async_sessionmaker` con `expire_on_commit=False`), `migrations/env.py` apuntando a `SQLModel.metadata` y los 7 paquetes de módulos con `models.py` vacíos. La consigna exige nombres exactos de tablas y columnas (`04_modelo_de_datos.md`), restricciones de unicidad y dominio (`CHECK`, `UNIQUE`, `FK`) impuestas por PostgreSQL 16, tipos `Decimal` (`NUMERIC`) para importes, `TIMESTAMPTZ` para fechas de venta, y al menos **2 migraciones** autogeneradas y revisadas (Ej. 3). Ver `proposal.md` para motivación y `specs/` para los contratos formales de `domain-models` y `schema-migrations`.

## Goals / Non-Goals

**Goals:**
- Implementar los 8 modelos `SQLModel(..., table=True)` iniciales en sus módulos respectivos (`editoriales`, `autores`, `libros`, `clientes`, `ventas`) con todos sus tipos, `CheckConstraint`, `UniqueConstraint`, `Index` explícitos en FKs y `Relationship(back_populates=...)`.
- Generar con `alembic revision --autogenerate`, revisar manualmente y verificar la **migración 001** (8 tablas iniciales, sin `genero`).
- Cubrir con tests de integración sobre PostgreSQL 16 todas las restricciones en base y la navegación de relaciones.

**Non-Goals:**
- Tabla `genero` y columna `libro.genero_id` (reservadas a `C-03` para materializar la segunda migración evolutiva del Ej. 3).
- Esquemas DTO (`Create`/`Update`/`Read`), servicios y endpoints HTTP (`C-04` a `C-07`).

## Decisions

### DD-C02-01 — Exclusión deliberada de `genero` y `libro.genero_id` en la migración 001

La migración `001` crea las 8 tablas del modelo inicial sin `genero` ni `libro.genero_id`; ambos se incorporan en `C-03` mediante la migración `002`. Alternativa: crear las 9 tablas de una vez y fabricar una migración `002` artificial — descartado porque el Ej. 3 evalúa específicamente una evolución real del esquema (agregar `genero` y la FK opcional `genero_id` en `libro`) en al menos dos revisiones.

### DD-C02-02 — `Decimal` con `sa_column=Column(Numeric(p, s), nullable=False)` para importes

Los campos monetarios (`libro.precio` y `renglon_venta.precio_unitario` con `Numeric(10, 2)`; `venta.total` con `Numeric(12, 2)`) se tipan como `Decimal` en Python y se mapean explícitamente con `Column(Numeric(p, s), nullable=False)` en SQLAlchemy/SQLModel. Alternativa: `Field(max_digits=..., decimal_places=...)` sin `sa_column` — se prefiere `Column(Numeric(p, s), nullable=False)` para garantizar que Alembic emita ` sa.Numeric(precision=..., scale=...)` idéntico al modelo de datos sin ambigüedades entre versiones de SQLModel. Prohibido `float`.

### DD-C02-03 — `CheckConstraint` nombrados en `__table_args__` y verificados en la migración 001

Cada regla de dominio en base se declara en `__table_args__` con nombre explícito (`ck_libro_precio_positivo`, `ck_libro_stock_no_negativo`, `ck_libro_autor_orden_minimo`, `ck_libro_autor_rol_valido`, `ck_venta_total_no_negativo`, `ck_renglon_venta_cantidad_positiva`, `ck_renglon_venta_precio_unitario_positivo`). Dado que el soporte de `autogenerate` en Alembic para `CheckConstraint` puede omitirlos en la detección automática inicial si no forman parte del `CreateTable`, se verifica que todos los `sa.CheckConstraint(...)` queden incluidos dentro de cada `op.create_table(...)` de la migración `001`, documentando la revisión en el encabezado del archivo de migración.

### DD-C02-04 — Índices explícitos en todas las claves foráneas (`index=True`)

PostgreSQL no crea índices automáticos sobre columnas con `FOREIGN KEY` (solo sobre `PRIMARY KEY` y `UNIQUE`). Por ello, toda columna FK (`libro.editorial_id`, `libro_autor.libro_id`, `libro_autor.autor_id`, `perfil_cliente.cliente_id` vía `unique=True`, `venta.cliente_id`, `renglon_venta.venta_id`, `renglon_venta.libro_id`) declara `index=True` (o `unique=True` en el caso 1:1 de `perfil_cliente.cliente_id`), evitando sequential scans en joins y verificaciones de integridad referencial.

### DD-C02-05 — Relación 1 a 0..1 `Cliente.perfil` con `uselist=False` y `UNIQUE` en `perfil_cliente.cliente_id`

En `Cliente`, la relación `perfil: Optional["PerfilCliente"]` se declara con `Relationship(back_populates="cliente", sa_relationship_kwargs={"uselist": False})`, y en `PerfilCliente` la columna `cliente_id` lleva `unique=True` y `foreign_key="cliente.id"`. Esto cumple simultáneamente RN-09 (en base) y el requisito del modelo de datos (`Cliente.perfil` devuelve objeto, no lista).

### DD-C02-06 — Objeto de asociación `LibroAutor` con PK compuesta (`libro_id`, `autor_id`) y navegación `libro.autorias[i].autor`

`LibroAutor` (`__tablename__ = "libro_autor"`) vive en `app/modules/libros/models.py`, define `libro_id` y `autor_id` con `primary_key=True`, y expone las relaciones `libro: "Libro" = Relationship(back_populates="autorias")` y `autor: "Autor" = Relationship(back_populates="autorias")`. Así se preserva la carga con atributos propios (`rol`, `orden`) y la expresión de navegación obligatoria `libro.autorias[i].autor`.

### DD-C02-07 — `TIMESTAMPTZ` en `venta.fecha` y registro centralizado de modelos en `migrations/env.py`

`venta.fecha` se define con `sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now())` y default en Python `datetime.now(timezone.utc)`, garantizando `TIMESTAMPTZ` en PostgreSQL 16. Para que `alembic revision --autogenerate` descubra las 8 tablas sin acoplar módulos innecesariamente, `migrations/env.py` importa explícitamente los módulos de modelos (`editoriales`, `autores`, `libros`, `clientes`, `ventas`) antes de asignar `target_metadata = SQLModel.metadata`.

## Risks / Trade-offs

- [Referencias circulares entre módulos al tipar `Relationship` (`Libro` ↔ `Editorial`, `Libro` ↔ `LibroAutor` ↔ `Autor`, `Venta` ↔ `Cliente`, `RenglonVenta` ↔ `Libro`)] → Mitigación: usar `from __future__ import annotations` y `TYPE_CHECKING` para los imports cruzados de anotaciones de tipo, e importar los módulos de modelos en `app/main.py` / `migrations/env.py` para que el registro de mappers de SQLAlchemy resuelva los nombres en string al inicializar.
- [Alembic `autogenerate` emite tipos `sqlmodel.sql.sqltypes.AutoString` en la migración] → Mitigación: en la revisión manual de la migración `001`, importar `sqlmodel` en el script de migración o reemplazar por `sa.String()` / `sa.Text()` estándar y dejar constancia en un comentario de revisión al inicio del archivo (requerido por Ej. 3).

## Migration Plan

1. Implementar modelos en `app/modules/{editoriales,autores,libros,clientes,ventas}/models.py`.
2. Importar los modelos en `migrations/env.py`.
3. Ejecutar `.\.venv\Scripts\alembic revision --autogenerate -m "001_initial_core_models"`.
4. Leer y revisar manualmente el archivo generado en `migrations/versions/`, documentando la revisión en el docstring/comentario superior.
5. Ejecutar `.\.venv\Scripts\alembic upgrade head`, verificar `alembic downgrade base` y volver a aplicar `alembic upgrade head`.
6. Rollback: `.\.venv\Scripts\alembic downgrade base`.

## Open Questions

Ninguna.
