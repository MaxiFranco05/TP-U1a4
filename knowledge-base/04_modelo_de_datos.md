# Modelo de Datos

Nombres de tablas y columnas **obligatorios** (los usan los casos de prueba y la corrección automática). Se pueden agregar columnas auxiliares si hiciera falta, pero **nunca quitar ni renombrar** las indicadas.

Todas las fechas son `timestamptz` (`DateTime(timezone=True)`). El dinero es siempre `NUMERIC` en PostgreSQL y `Decimal` en Python (nunca `float`). Cada clave foránea lleva un **índice explícito** (`index=True`) porque PostgreSQL no lo crea solo. La navegación `Relationship(back_populates=...)` se declara en los dos extremos.

---

## Dominios y Ubicación de Modelos

| Módulo (`app/modules/<módulo>/models.py`) | Tablas que define | Estado en el Parcial |
|---|---|---|
| `usuarios` | `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad` | **Nuevo en el Parcial (Migración 003)** |
| `editoriales` | `editorial` | Sin cambios respecto del TP |
| `generos` | `genero` | Sin cambios respecto del TP |
| `autores` | `autor` | Sin cambios respecto del TP |
| `libros` | `libro`, `libro_autor`, `movimiento_stock` | **Cambia `libro`** (`borrado_en` + índice único parcial ISBN) y **se agrega `movimiento_stock`** (Migraciones 003 y 004) |
| `clientes` | `cliente`, `perfil_cliente` | **Cambia `cliente`** (se agrega `usuario_id` UNIQUE nullable); `perfil_cliente` sin cambios |
| `ventas` | `venta`, `renglon_venta` | Sin cambios de columnas respecto del TP |

---

## ERD (Diagrama de Relaciones Textual)

```
editorial 1───* libro *───0..1 genero
libro *───* autor vía libro_autor (rol, orden)
libro 1───* movimiento_stock («appendOnly» protegido por TRIGGER)
venta 0..1───* movimiento_stock
usuario 1───* movimiento_stock (actor que ejecutó el movimiento)

usuario 1───* asignacion_rol (roles con vigencia; otorgada_por -> usuario 0..1)
usuario 0..1───0..1 cliente 1───0..1 perfil_cliente
cliente 1───* venta 1───* renglon_venta *───1 libro

intento_acceso   (tabla independiente sin FK: sobrevive al rollback del login)
evento_seguridad (tabla independiente sin FK: actor es texto, ej. "SISTEMA" o email)
```

---

## Detalle de Entidades y Restricciones

### 1. Módulo `usuarios` (`app/modules/usuarios/models.py`)

#### `usuario`
- **Columnas**: `id` (PK), `email` (str), `nombre` (str), `password_hash` (str), `activo` (bool, default `True`), `debe_cambiar_password` (bool, default `False`).
- **Restricciones**: `email` `UNIQUE`.
- **Relaciones**:
  - 1 a 0..1 con `cliente` (`Usuario.cliente` / `Cliente.usuario` devuelve un objeto y no una lista).
  - 1 a * con `asignacion_rol` (por `usuario_id`, y opcionalmente por `otorgada_por`).
  - 1 a * con `movimiento_stock`.

#### `asignacion_rol`
- **Columnas**: `id` (PK), `usuario_id` (FK a `usuario.id` con índice), `rol` (str), `desde` (`timestamptz`), `vence_en` (`timestamptz`, nullable), `revocada_en` (`timestamptz`, nullable), `otorgada_por` (FK a `usuario.id` con índice, nullable).
- **Restricciones**:
  - `CHECK (rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE'))`.
  - **Índice único parcial**: `(usuario_id, rol) WHERE revocada_en IS NULL` declarado con `Index(..., unique=True, postgresql_where=...)` (RN-03: un usuario tiene a lo sumo una asignación abierta por rol, pero puede tener múltiples filas históricas revocadas).

#### `intento_acceso`
- **Columnas**: `id` (PK), `cuando` (`timestamptz`), `email` (str), `ip` (str), `exito` (bool).
- **Restricciones**:
  - **Índice compuesto**: `(email, ip, cuando)` para acelerar el conteo de intentos en la ventana de 60 segundos (RN-07).
  - Sin claves foráneas (se registran también intentos de correos inexistentes).

#### `evento_seguridad`
- **Columnas**: `id` (PK), `cuando` (`timestamptz`), `actor` (str), `accion` (str).
- **Restricciones**: Sin FK ni restricciones extra (`actor` es texto porque el seed registra el evento inicial con el actor `"SISTEMA"`).

---

### 2. Módulo `libros` y Catálogo (`editoriales`, `generos`, `autores`, `libros`)

#### `editorial`
- **Columnas**: `id` (PK), `nombre` (str, `UNIQUE`), `pais` (str).
- **Relaciones**: 1 a * con `libro`.

#### `genero`
- **Columnas**: `id` (PK), `nombre` (str, `UNIQUE`).
- **Relaciones**: 1 a * opcional con `libro`.

#### `autor`
- **Columnas**: `id` (PK), `nombre` (str), `nacionalidad` (str).
- **Relaciones**: * a * con `libro` vía `libro_autor`.

#### `libro` *(cambia en el Parcial)*
- **Columnas**: `id` (PK), `isbn` (str), `titulo` (str), `precio` (`NUMERIC(10,2)` / `Decimal`), `stock` (int), `editorial_id` (FK a `editorial.id` con índice), `genero_id` (FK a `genero.id` con índice, nullable), **`borrado_en` (`timestamptz`, nullable)**.
- **Restricciones**:
  - **Índice único parcial**: `(isbn) WHERE borrado_en IS NULL` (`postgresql_where`) en reemplazo del `UNIQUE` común del TP (RN-01, RN-13: permite volver a dar de alta un ISBN de un libro dado de baja, pero impide dos vigentes con el mismo ISBN).
  - `CHECK (precio > 0)`.
  - `CHECK (stock >= 0)`.
- **Relaciones**: * a 1 con `editorial` y `genero`; 1 a * con `libro_autor` (`libro.autorias`); 1 a * con `renglon_venta`; 1 a * con `movimiento_stock`.

#### `libro_autor` (objeto de asociación)
- **Columnas**: `libro_id` (FK a `libro.id`, PK, índice), `autor_id` (FK a `autor.id`, PK, índice), `rol` (str), `orden` (int).
- **Restricciones**: PK compuesta `(libro_id, autor_id)`; `CHECK (orden >= 1)`; `CHECK (rol IN ('autor', 'coautor', 'traductor', 'ilustrador'))`.
- **Navegación**: `libro.autorias[i].autor`.

#### `movimiento_stock` *(nuevo en el Parcial — sólo agregado)*
- **Columnas**: `id` (PK), `libro_id` (FK a `libro.id` con índice), `venta_id` (FK a `venta.id` con índice, nullable), `usuario_id` (FK a `usuario.id` con índice), `cantidad` (int), `motivo` (str), `cuando` (`timestamptz`).
- **Restricciones**:
  - `CHECK (cantidad <> 0)`.
  - **Sólo agregado (`appendOnly`, RN-12)**: protegido en PostgreSQL por una función y disparador (`BEFORE UPDATE OR DELETE ON movimiento_stock`) instalados en la **Migración 004** que rechazan con excepción cualquier intento de modificar o borrar filas.
  - **Invariante de dominio (RN-11)**: para todo libro, `libro.stock == SUM(movimiento_stock.cantidad)`.

---

### 3. Módulo `clientes` (`app/modules/clientes/models.py`)

#### `cliente` *(cambia en el Parcial)*
- **Columnas**: `id` (PK), `nombre` (str), `email` (str, `UNIQUE`), **`usuario_id` (FK a `usuario.id` con índice, nullable, `UNIQUE`)**.
- **Relaciones**:
  - 0..1 a 1 con `usuario`: **`Cliente.usuario` devuelve un objeto (o `None`) y no una lista** (`uselist=False`). Un cliente de mostrador (ej. Lucía o Tomás) tiene `usuario_id = NULL`; un cliente registrado en la web (ej. Ana) tiene su `usuario_id`.
  - 1 a 0..1 con `perfil_cliente` (`Cliente.perfil` devuelve objeto, no lista).
  - 1 a * con `venta`.

#### `perfil_cliente`
- **Columnas**: `id` (PK), `cliente_id` (FK a `cliente.id`, `UNIQUE`, índice), `telefono` (str), `direccion` (str).

---

### 4. Módulo `ventas` (`app/modules/ventas/models.py`)

#### `venta`
- **Columnas**: `id` (PK), `cliente_id` (FK a `cliente.id` con índice), `fecha` (`timestamptz`), `total` (`NUMERIC(12,2)` / `Decimal`).
- **Restricciones**: `CHECK (total >= 0)`.
- **Relaciones**: * a 1 con `cliente`; 1 a * con `renglon_venta` (composición); 1 a * con `movimiento_stock`.

#### `renglon_venta`
- **Columnas**: `id` (PK), `venta_id` (FK a `venta.id` con índice), `libro_id` (FK a `libro.id` con índice), `cantidad` (int), `precio_unitario` (`NUMERIC(10,2)` / `Decimal`).
- **Restricciones**: `CHECK (cantidad > 0)`; `CHECK (precio_unitario > 0)`.
- **Relaciones**: * a 1 con `venta` y con `libro`.

---

## Historial de Migraciones Alembic (`migrations/versions/`)

1. **Migración 001 (TP — `C-02`)**: Autogenerada; crea el esquema inicial del TP sin la tabla `genero` ni `libro.genero_id`.
2. **Migración 002 (TP — `C-03`)**: Autogenerada; agrega la tabla `genero` y la columna `libro.genero_id` con su FK e índice.
3. **Migración 003 (Parcial — `C-10`)**: Generada con `alembic revision --autogenerate`, leída y comentada antes de aplicarla. Crea `usuario`, `asignacion_rol` (con su CHECK e índice único parcial `WHERE revocada_en IS NULL`), `intento_acceso` (con su índice `(email, ip, cuando)`), `evento_seguridad` y `movimiento_stock` (`CHECK cantidad <> 0`); agrega `cliente.usuario_id` (FK, índice, UNIQUE) y `libro.borrado_en`, reemplazando el UNIQUE común de `libro.isbn` por el índice único parcial `(isbn) WHERE borrado_en IS NULL`.
4. **Migración 004 (Parcial — `C-10`)**: Escrita **a mano**, leída y comentada. Instala en `upgrade()` la función PL/pgSQL y el `TRIGGER` sobre `movimiento_stock` que rechaza cualquier `UPDATE` o `DELETE` (RN-12), y en `downgrade()` elimina el disparador y la función.

> **Requisito de verificación**: `alembic upgrade head` sobre una base vacía, seguido de `alembic downgrade base` y nuevamente `alembic upgrade head` deben ejecutarse sin errores de punta a punta.

---

## Datos Iniciales Obligatorios (`seed.py`)

`seed.py` en la raíz del proyecto vacía todas las tablas y carga este estado exacto y reproducible que usan los casos `C-01` a `C-16`:

| Entidad | Datos iniciales obligatorios |
|---|---|
| **Usuarios (5)** | `admin@example.com` (`ADMIN`), `admin2@example.com` (`ADMIN`), `vendedor@example.com` (`VENDEDOR`), `ana@example.com` (`CLIENTE`), `nuevo@example.com` (`VENDEDOR`, con `debe_cambiar_password=True`). Contraseñas ficticias sólo en `seed.py`. |
| **Catálogo (TP)** | 3 editoriales, 3 géneros y 6 autores del TP. |
| **Libros (5)** | 1. *Rayuela* (stock actual: **10**) · 2. *Antología de la literatura fantástica* (stock actual: **5**) · 3. *Ficciones* (stock actual: **8**) · 4. *Respiración artificial* (stock actual: **3**) · 5. *Bestiario* (stock actual: **1**). |
| **Clientes (3)** | 1. *Lucía Fernández* (con `PerfilCliente`, `usuario_id=None`) · 2. *Tomás Ríos* (`usuario_id=None`) · 3. *Ana Paz* (vinculada a `ana@example.com`). |
| **Venta (1)** | Venta 1 de *Lucía Fernández*, registrada por `vendedor@example.com`: 1 ejemplar de *Rayuela* ($25000.00) + 2 ejemplares de *Ficciones* ($22000.00 c/u) → **`total = 69000.00`**. |
| **Movimientos de stock (7)** | 5 movimientos de `"Stock inicial"` (*Rayuela* `+11`, *Antología* `+5`, *Ficciones* `+10`, *Respiración artificial* `+3`, *Bestiario* `+1`) + 2 movimientos de salida asociados a la Venta 1 (*Rayuela* `-1`, *Ficciones* `-2`, ejecutados por `vendedor@example.com`), garantizando `libro.stock == SUM(cantidad)` en los 5 libros. |
| **Historial de seguridad (1)** | 1 fila en `evento_seguridad` con `actor="SISTEMA"` y `accion="Carga de los datos iniciales"`. |
