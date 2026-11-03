# Design

## UI Mockups

Decision: no (no UI)

## Context

El proyecto ya cuenta con los modelos del TP (`editorial`, `genero`, `autor`, `libro`, `libro_autor`, `cliente`, `perfil_cliente`, `venta`, `renglon_venta`) y dos migraciones Alembic (`246164acdc52_001_initial_core_models.py` y `05e4652b220e_002_add_genero_and_libro_genero_id.py`), además de `Settings` (`pydantic-settings`) y `lifespan` completados en `C-09` (ver `proposal.md` — Why).

Este change (`C-10`) extiende la capa de persistencia y migraciones para cubrir las 14 tablas del Parcial (Capítulos 1 a 6, Ejercicios 2 y 7) sin alterar todavía la firma de servicios, repositorios ni endpoints (que se abordan en `C-11`..`C-16`), manteniendo la suite actual de 27 tests en verde.

## Goals / Non-Goals

**Goals:**
- Declarar los modelos `Usuario`, `AsignacionRol`, `IntentoAcceso` y `EventoSeguridad` en `app/modules/usuarios/models.py` y `MovimientoStock` en `app/modules/libros/models.py` con tipos `DateTime(timezone=True)`, `CheckConstraint`, índices explícitos en claves foráneas e índices únicos parciales (`postgresql_where`).
- Extender `Libro` (`borrado_en` + índice único parcial `uq_libro_isbn_activo` sobre `(isbn) WHERE borrado_en IS NULL`), `Cliente` (`usuario_id` FK opcional `UNIQUE` con `Cliente.usuario` `uselist=False`) y `Venta` (`movimientos_stock`).
- Generar, leer y comentar la Migración `003` con `alembic revision --autogenerate`, y escribir a mano, leer y comentar la Migración `004` con la función PL/pgSQL y el `TRIGGER` de sólo-agregado (`appendOnly`) sobre `movimiento_stock` (RN-12).
- Garantizar que `alembic upgrade head` → `alembic downgrade base` → `alembic upgrade head` funcione sin errores y que los tests existentes (`C-01`..`C-09`) sigan pasando.

**Non-Goals:**
- No implementar `BaseRepository`, `SoftDeleteRepository`, `UnitOfWork` ni `paginacion.py` (corresponden a `C-11`).
- No implementar `bcrypt`, JWT, dependencias de seguridad ni endpoints `/auth`, `/usuarios` o `/eventos` (`C-12`..`C-14`).
- No refactorizar servicios de catálogo, clientes o ventas a UoW ni agregar endpoints de reposición/baja de libros (`C-15`..`C-16`).

## Decisions

### 1. Declaración de índices únicos parciales (`postgresql_where`) y nombres explícitos de restricciones

- **Decisión**:
  - En `Libro` (`app/modules/libros/models.py`): quitar `unique=True` de `Field` en `isbn`, agregar `borrado_en: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))` y declarar en `__table_args__`:
    ```python
    Index(
        "uq_libro_isbn_activo",
        "isbn",
        unique=True,
        postgresql_where=text("borrado_en IS NULL"),
    )
    ```
    junto con `CheckConstraint("precio > 0", name="ck_libro_precio_positivo")` y `CheckConstraint("stock >= 0", name="ck_libro_stock_no_negativo")`.
  - En `AsignacionRol` (`app/modules/usuarios/models.py`): declarar en `__table_args__`:
    ```python
    CheckConstraint(
        "rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')",
        name="ck_asignacion_rol_rol_valido",
    ),
    Index(
        "uq_asignacion_rol_activa",
        "usuario_id",
        "rol",
        unique=True,
        postgresql_where=text("revocada_en IS NULL"),
    ),
    ```
  - En `IntentoAcceso` (`app/modules/usuarios/models.py`): declarar en `__table_args__`:
    ```python
    Index("ix_intento_acceso_email_ip_cuando", "email", "ip", "cuando")
    ```
  - En `MovimientoStock` (`app/modules/libros/models.py`): declarar en `__table_args__`:
    ```python
    CheckConstraint("cantidad <> 0", name="ck_movimiento_stock_cantidad_no_cero")
    ```
- **Racional**: SQLAlchemy/Alembic serializa `Index(..., unique=True, postgresql_where=sa.text(...))` directamente en `op.create_index(..., unique=True, postgresql_where=sa.text(...))` durante `--autogenerate`. Dar nombres determinísticos (`uq_libro_isbn_activo`, `uq_asignacion_rol_activa`, `ix_intento_acceso_email_ip_cuando`, `ck_*`) permite mapearlos en `app/core/exceptions.py` y referenciarlos sin ambigüedad en `downgrade()`.
- **Alternativas descartadas**: `UniqueConstraint` estándar (no soporta cláusula `WHERE` en PostgreSQL).

### 2. Columnas `TIMESTAMPTZ` y claves foráneas múltiples hacia `usuario`

- **Decisión**:
  - Todas las columnas de fecha/hora nuevas (`AsignacionRol.desde`, `AsignacionRol.vence_en`, `AsignacionRol.revocada_en`, `IntentoAcceso.cuando`, `EventoSeguridad.cuando`, `MovimientoStock.cuando`, `Libro.borrado_en`) usan `sa_column=Column(DateTime(timezone=True), ...)`. Para las obligatorias (`desde`, `cuando`), se configura `default_factory=lambda: datetime.now(timezone.utc)` y `server_default=func.now()`, igual que en `Venta.fecha`.
  - En `AsignacionRol`, existen dos FKs hacia `usuario.id` (`usuario_id` no nulo y `otorgada_por` nullable). Para evitar `AmbiguousForeignKeysError` en SQLAlchemy al resolver `Relationship`, se especifica explícitamente `sa_relationship_kwargs={"foreign_keys": "[AsignacionRol.usuario_id]"}` en la relación principal `Usuario.asignaciones_rol` ↔ `AsignacionRol.usuario` (y `foreign_keys="[AsignacionRol.otorgada_por]"` si se expone la relación del otorgante).
  - En `Cliente`, `usuario_id: int | None = Field(default=None, foreign_key="usuario.id", unique=True, index=True, nullable=True)`, con:
    ```python
    usuario: Optional["Usuario"] = Relationship(
        back_populates="cliente",
        sa_relationship_kwargs={"uselist": False},
    )
    ```
    y en `Usuario`:
    ```python
    cliente: Optional["Cliente"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"uselist": False},
    )
    ```
- **Racional**: Cumple el requisito de que `Cliente.usuario` devuelva un objeto (`Usuario | None`) y no una lista (`uselist=False`), y evita ambigüedad entre `usuario_id` y `otorgada_por` en `AsignacionRol`.

### 3. Registro en `migrations/env.py` y revisión manual de la Migración `003`

- **Decisión**:
  - Importar `from app.modules.usuarios import models as _usuarios_models  # noqa: F401` en `migrations/env.py`.
  - Generar la revisión `003` con `.\.venv\Scripts\alembic revision --autogenerate -m "003_add_usuarios_acceso_movimiento_stock_and_partial_indexes"`.
  - **Inspección y ajuste obligatorio antes de aplicar**:
    1. Verificar `import sqlmodel` si Alembic emite `sqlmodel.sql.sqltypes.AutoString()`.
    2. Asegurar que la `ForeignKeyConstraint` agregada sobre `cliente.usuario_id` tenga nombre explícito (p. ej. `'fk_cliente_usuario_id_usuario'`) tanto en `op.create_foreign_key(...)` como en `op.drop_constraint(...)`, evitando el problema de `None` detectado en la migración `002`.
    3. Verificar que en `upgrade()` se elimine la constraint `libro_isbn_key` (`op.drop_constraint('libro_isbn_key', 'libro', type_='unique')`) y se cree el índice único parcial `uq_libro_isbn_activo` con `postgresql_where=sa.text('borrado_en IS NULL')`, y que en `downgrade()` se invierta exactamente ese paso antes de borrar `borrado_en`.
    4. Documentar la revisión en el docstring superior de la migración `003` (`Revisión manual:`).

### 4. Función PL/pgSQL y Trigger `appendOnly` en la Migración `004` (escrita a mano)

- **Decisión**:
  - Crear la cuarta revisión sin `--autogenerate` (`.\.venv\Scripts\alembic revision -m "004_movimiento_stock_append_only_trigger"`) y escribir a mano `upgrade()` y `downgrade()` con el siguiente SQL:
    ```sql
    -- En upgrade():
    CREATE OR REPLACE FUNCTION fn_movimiento_stock_append_only()
    RETURNS TRIGGER
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RAISE EXCEPTION 'La tabla movimiento_stock es de sólo agregado (RN-12): no se permite % sobre filas existentes.', TG_OP
            USING ERRCODE = 'integrity_constraint_violation';
    END;
    $$;

    CREATE TRIGGER trg_movimiento_stock_append_only
    BEFORE UPDATE OR DELETE ON movimiento_stock
    FOR EACH ROW
    EXECUTE FUNCTION fn_movimiento_stock_append_only();
    ```
    Y en `downgrade()`:
    ```sql
    DROP TRIGGER IF EXISTS trg_movimiento_stock_append_only ON movimiento_stock;
    DROP FUNCTION IF EXISTS fn_movimiento_stock_append_only();
    ```
  - Usar `ERRCODE = 'integrity_constraint_violation'` (`23000`) o excepción de trigger para que SQLAlchemy la envuelva de forma determinística (`DBAPIError` / `IntegrityError`) y que cualquier intento de `UPDATE` o `DELETE` sea rechazado tanto desde la app como desde SQL directo (`C-14`).

### 5. Compatibilidad con `app/core/exceptions.py` y con la suite de tests existente

- **Decisión**:
  - En `app/core/exceptions.py`, agregar en `mapping` de `translate_integrity_error`:
    - `"uq_libro_isbn_activo": "Ya existe un libro con ese ISBN"` (mantiene `POST /libros` devolviendo `409` con el mismo mensaje cuando un ISBN activo se repite, preservando todos los tests de `C-04`..`C-08`).
    - `"usuario_email_key": "Email ya registrado"`, `"uq_asignacion_rol_activa": "El usuario ya tiene ese rol asignado"`, `"ix_cliente_usuario_id": "El usuario ya está asociado a un cliente"`.
  - En `test/test_generos_and_migration_002.py` (línea 101), `test_database_schema_at_head_has_all_9_tables_and_genero_fk_index` hace `assert db_tables == EXPECTED_ALL_9_TABLES`. Al igual que en `test/test_core_models_and_migration_001.py` (línea 89, que usa `assert EXPECTED_CORE_TABLES.issubset(db_tables)`), actualizar esa aserción a `assert EXPECTED_ALL_9_TABLES.issubset(db_tables)` para que valide que las 9 tablas hasta la migración `002` están presentes en `head` sin romperse cuando `head` avanza a `004` con las 5 tablas nuevas del Parcial (total 14 tablas).
  - **Estrategia de limpieza en tests con `movimiento_stock`**: dado que el trigger de la migración `004` prohíbe `DELETE FROM movimiento_stock`, pero en PostgreSQL los triggers `BEFORE DELETE ... FOR EACH ROW` no se disparan con `TRUNCATE`, la limpieza en los fixtures de los nuevos tests que inserten filas en `movimiento_stock` usará `TRUNCATE TABLE movimiento_stock RESTART IDENTITY CASCADE` (o `TRUNCATE TABLE movimiento_stock, renglon_venta, venta, asignacion_rol, intento_acceso, evento_seguridad, perfil_cliente, cliente, libro_autor, libro, genero, autor, editorial, usuario RESTART IDENTITY CASCADE`).

## Risks / Trade-offs

- **[Risk] Autogenerate de Alembic omite nombres de `ForeignKeyConstraint` en `op.create_foreign_key` al alterar tablas existentes (`cliente.usuario_id`)** → **Mitigación**: Inspeccionar el archivo `003` generado y fijar explícitamente el nombre `'fk_cliente_usuario_id_usuario'` en `upgrade()` y `downgrade()`, verificando con el ciclo `upgrade head` → `downgrade base` → `upgrade head`.
- **[Risk] `DELETE FROM libro` o `DELETE FROM movimiento_stock` falla en fixtures de tests cuando existen movimientos por el trigger `appendOnly`** → **Mitigación**: Los tests existentes (`C-01`..`C-09`) no insertan filas en `movimiento_stock`, por lo que sus `delete(Libro)` no disparan nada sobre `movimiento_stock`; los nuevos tests de `C-10` que insertan en `movimiento_stock` limpian con `TRUNCATE TABLE movimiento_stock RESTART IDENTITY CASCADE`.
- **[Risk] El cambio de constraint `libro_isbn_key` a índice único parcial `uq_libro_isbn_activo` cambia el `constraint_name` reportado por `asyncpg`** → **Mitigación**: Mantener ambas claves (`"libro_isbn_key"` y `"uq_libro_isbn_activo"`) en `app/core/exceptions.py`.

## Migration Plan

1. Registrar `app.modules.usuarios.models` en `migrations/env.py`.
2. Generar la Migración `003` con `alembic revision --autogenerate`, revisarla manualmente, ajustar nombres de constraints si corresponde y agregar comentario de revisión.
3. Crear la Migración `004` manual con `alembic revision`, escribir la función y el trigger PL/pgSQL en `upgrade()` y su eliminación en `downgrade()`, y agregar comentario de revisión.
4. Ejecutar el ciclo completo de verificación sobre PostgreSQL 16:
   - `.\.venv\Scripts\alembic upgrade head`
   - `.\.venv\Scripts\alembic downgrade base`
   - `.\.venv\Scripts\alembic upgrade head`
   - `.\.venv\Scripts\alembic check`
