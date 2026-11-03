# Proposal

## Why

El esquema del TP (Capítulos 1 a 4) carece de las entidades de identidad, control de acceso con vigencia temporal, auditoría de eventos/intentos de login, trazabilidad inmutable de movimientos de stock (`appendOnly`) y baja lógica de libros exigidas por el Parcial (Capítulos 1 a 6, Ejercicios 2 y 7). Este change extiende el modelo de datos y las migraciones Alembic (`003` autogenerada y `004` escrita a mano) sobre las que se apoyan `UnitOfWork`, autenticación/autorización (`C-12`..`C-14`) y las operaciones de stock y ventas (`C-15`..`C-16`).

## What Changes

- **Nuevos modelos de acceso y seguridad (`app/modules/usuarios/models.py`)**:
  - `Usuario` (`usuario`): `id`, `email` (`UNIQUE`), `nombre`, `password_hash`, `activo` (`bool`, default `True`), `debe_cambiar_password` (`bool`, default `False`), y relaciones con `Cliente`, `AsignacionRol` y `MovimientoStock`.
  - `AsignacionRol` (`asignacion_rol`): `id`, `usuario_id` (FK a `usuario.id` con índice explícito), `rol` (`CHECK rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')`), `desde` (`timestamptz`), `vence_en` (`timestamptz`, nullable), `revocada_en` (`timestamptz`, nullable), `otorgada_por` (FK a `usuario.id` con índice explícito, nullable) e **índice único parcial** `(usuario_id, rol) WHERE revocada_en IS NULL` (`postgresql_where`, RN-03).
  - `IntentoAcceso` (`intento_acceso`): `id`, `cuando` (`timestamptz`), `email`, `ip`, `exito` (`bool`) e **índice compuesto** `(email, ip, cuando)` sin claves foráneas (RN-07).
  - `EventoSeguridad` (`evento_seguridad`): `id`, `cuando` (`timestamptz`), `actor` (`str`), `accion` (`str`) sin claves foráneas (RN-16).
- **Trazabilidad de stock y baja lógica en `app/modules/libros/models.py`**:
  - Nuevo modelo `MovimientoStock` (`movimiento_stock`): `id`, `libro_id` (FK a `libro.id` con índice), `venta_id` (FK a `venta.id` con índice, nullable), `usuario_id` (FK a `usuario.id` con índice), `cantidad` (`int`, `CHECK cantidad <> 0`), `motivo` (`str`), `cuando` (`timestamptz`).
  - **BREAKING** en `Libro` (`libro`): se agrega `borrado_en` (`timestamptz`, nullable) y se reemplaza la restricción `UNIQUE` simple de `isbn` por el **índice único parcial** `uq_libro_isbn_activo` sobre `(isbn) WHERE borrado_en IS NULL` (`postgresql_where`, RN-01, RN-13), conservando `CHECK (precio > 0)` y `CHECK (stock >= 0)`.
- **Vinculación opcional de cliente con usuario en `app/modules/clientes/models.py`**:
  - `Cliente` (`cliente`): se agrega `usuario_id` (FK a `usuario.id` con índice explícito, `nullable=True`, `unique=True`) y navegación bidireccional `Cliente.usuario` / `Usuario.cliente` con `uselist=False` (devuelve un objeto `Usuario | None` y no una lista).
- **Navegación con movimientos en `app/modules/ventas/models.py`**:
  - `Venta` (`venta`): relación `movimientos_stock` (`1 a *`) hacia `MovimientoStock`.
- **Migración Alembic `003` (`migrations/versions/*_003_*.py`)**:
  - Generada con `alembic revision --autogenerate`, leída y comentada antes de aplicarla; crea `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad` y `movimiento_stock`, y altera `cliente` y `libro`.
- **Migración Alembic `004` (`migrations/versions/*_004_*.py`)**:
  - Escrita a mano, leída y comentada; instala en `upgrade()` la función PL/pgSQL y el disparador (`BEFORE UPDATE OR DELETE ON movimiento_stock`) que rechaza cualquier modificación o borrado (RN-12), y los elimina en `downgrade()`.

## Capabilities

### New Capabilities

*(Ninguna capacidad nueva: los requisitos amplían las capacidades existentes `domain-models` y `schema-migrations`.)*

### Modified Capabilities

- `domain-models`: Se modifican los requisitos de `Libro` (baja lógica con `borrado_en` e índice único parcial `WHERE borrado_en IS NULL` sobre `isbn`) y de `Cliente` (FK opcional única `usuario_id` y relación `Cliente.usuario` con `uselist=False`), y se agregan los requisitos para `Usuario`, `AsignacionRol` (con `CHECK` de rol e índice único parcial `WHERE revocada_en IS NULL`), `IntentoAcceso` (con índice compuesto `(email, ip, cuando)`), `EventoSeguridad` y `MovimientoStock` (`CHECK cantidad <> 0` e inmutabilidad `appendOnly`).
- `schema-migrations`: Se agregan los requisitos para la Migración `003` (autogenerada, revisada y comentada con los nuevos modelos e índices parciales) y la Migración `004` (escrita a mano, revisada y comentada con la función PL/pgSQL y el trigger `appendOnly` sobre `movimiento_stock`), incluyendo la verificación completa `upgrade head` → `downgrade base` → `upgrade head`.

## Impact

- **Modelos ORM (`SQLModel`)**: `app/modules/usuarios/models.py` (nuevo), `app/modules/libros/models.py`, `app/modules/clientes/models.py`, `app/modules/ventas/models.py`.
- **Traducción de errores de integridad**: `app/core/exceptions.py` (mapear los nombres de los nuevos índices/constraints como `uq_libro_isbn_activo`, `usuario_email_key`, `uq_asignacion_rol_activa` y `ix_cliente_usuario_id` para mantener compatibilidad 409 sin filtrar detalles internos, RN-15).
- **Migraciones Alembic**: `migrations/env.py` (importar `app.modules.usuarios.models`) y dos nuevos archivos en `migrations/versions/` (`003` y `004`).
- **Tests**: nuevos tests de integración para modelos de acceso, stock, índices únicos parciales, ciclo de migraciones `003`/`004` y rechazo de `UPDATE`/`DELETE` en `movimiento_stock` (`C-14`), preservando en verde la suite existente (`test/test_core_models_and_migration_001.py`, `test/test_generos_and_migration_002.py`, etc.).
