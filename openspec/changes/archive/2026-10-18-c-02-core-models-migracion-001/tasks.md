# Tasks — C-02 core-models-migracion-001

## 1. Modelos del dominio Catálogo (`editoriales`, `autores`, `libros` sin `genero`)

- [x] 1.1 Implementar `Editorial` (`__tablename__ = "editorial"`: `id`, `nombre` `UNIQUE`, `pais`, relación `libros`) en `app/modules/editoriales/models.py` y `Autor` (`__tablename__ = "autor"`: `id`, `nombre`, `nacionalidad`, relación `autorias`) en `app/modules/autores/models.py`; verificar importación limpia de ambos módulos
- [x] 1.2 Implementar `Libro` (`__tablename__ = "libro"`, sin `genero_id`: `id`, `isbn` `UNIQUE`, `titulo`, `precio` `Decimal`/`NUMERIC(10, 2)` con `CHECK precio > 0`, `stock` con `CHECK stock >= 0`, `editorial_id` `FK` a `editorial.id` con índice explícito, relaciones `editorial`, `autorias` y `renglones_venta`) y `LibroAutor` (`__tablename__ = "libro_autor"`: PK compuesta `libro_id`/`autor_id` con índices explícitos en FKs, `rol` con `CHECK rol IN ('autor', 'coautor', 'traductor', 'ilustrador')`, `orden` con `CHECK orden >= 1`, relaciones `libro` y `autor`) en `app/modules/libros/models.py`; verificar que `SQLModel.metadata.tables` registra `editorial`, `autor`, `libro` y `libro_autor`

## 2. Modelos del dominio Clientes (`cliente` y `perfil_cliente`)

- [x] 2.1 Implementar `Cliente` (`__tablename__ = "cliente"`: `id`, `nombre`, `email` `UNIQUE`, relación `perfil` con `uselist=False` y relación `ventas`) y `PerfilCliente` (`__tablename__ = "perfil_cliente"`: `id`, `cliente_id` `FK` a `cliente.id` con `UNIQUE` e índice explícito, `telefono`, `direccion`, relación `cliente`) en `app/modules/clientes/models.py`; verificar que `SQLModel.metadata.tables` registra `cliente` y `perfil_cliente`

## 3. Modelos del dominio Ventas (`venta` y `renglon_venta`)

- [x] 3.1 Implementar `Venta` (`__tablename__ = "venta"`: `id`, `cliente_id` `FK` a `cliente.id` con índice explícito, `fecha` `TIMESTAMPTZ`, `total` `Decimal`/`NUMERIC(12, 2)` con `CHECK total >= 0`, relaciones `cliente` y `renglones`) y `RenglonVenta` (`__tablename__ = "renglon_venta"`: `id`, `venta_id` `FK` a `venta.id` con índice explícito, `libro_id` `FK` a `libro.id` con índice explícito, `cantidad` con `CHECK cantidad > 0`, `precio_unitario` `Decimal`/`NUMERIC(10, 2)` con `CHECK precio_unitario > 0`, relaciones `venta` y `libro`) en `app/modules/ventas/models.py`; verificar que `SQLModel.metadata.tables` contiene exactamente las 8 tablas core (sin `genero`)

## 4. Registro en Alembic y Migración 001 (`schema-migrations`)

- [x] 4.1 Registrar los módulos de modelos (`editoriales`, `autores`, `libros`, `clientes`, `ventas`) en `migrations/env.py` (y en el arranque de la aplicación para resolver los mappers de `Relationship`) y generar la migración 001 con `.\.venv\Scripts\alembic revision --autogenerate -m "001_initial_core_models"`
- [x] 4.2 Leer y revisar manualmente el archivo generado en `migrations/versions/`, verificando que incluya las 8 tablas, todas las restricciones `UNIQUE`, `CHECK` y `FK`, los tipos `Numeric(10, 2)` / `Numeric(12, 2)` y `DateTime(timezone=True)` (`TIMESTAMPTZ`), y los índices explícitos en FKs (dejando constancia de la revisión en comentario del archivo)
- [x] 4.3 Ejecutar `.\.venv\Scripts\alembic upgrade head`, `.\.venv\Scripts\alembic downgrade base` y `.\.venv\Scripts\alembic upgrade head` contra PostgreSQL 16, verificando que el ciclo es reversible y que `alembic check` (o inspección del esquema) confirma ausencia de diferencias pendientes y ausencia de `genero`

## 5. Tests de integración de constraints y navegación (`domain-models` + `schema-migrations`)

- [x] 5.1 Escribir y ejecutar `tests/test_core_models_and_migration_001.py` bajo ciclo TDD verificando sobre PostgreSQL 16: existencia de las 8 tablas (y ausencia de `genero` / `libro.genero_id`), rechazo por `IntegrityError` ante duplicados en `editorial.nombre`, `libro.isbn` (RN-01), `cliente.email` (RN-02) y `perfil_cliente.cliente_id` (RN-09), rechazo por `IntegrityError` ante violaciones de `CHECK` (`precio <= 0`, `stock < 0` RN-03, `orden < 1`, `rol` inválido, `total < 0`, `cantidad <= 0`, `precio_unitario <= 0`), exactitud `Decimal` y `TIMESTAMPTZ`, navegación `libro.autorias[i].autor`, y `cliente.perfil` como objeto único (no lista)

## Workflow follow-up

- Proponer el commit sugerido y que el usuario lo ejecute: `git commit -m "C-02: modelos core + migracion 001 (sin genero)"` (nunca commitear de forma autónoma).
- Archivar el change con `/opsx:archive c-02-core-models-migracion-001` cuando la implementación y verificación estén completas.
