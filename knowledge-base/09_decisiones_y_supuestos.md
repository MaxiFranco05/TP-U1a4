# Decisiones y Supuestos

## Decisiones de Diseño — TP Capítulos 1 a 4 (DD-01 a DD-06, vigentes)

### DD-01 — Alcance exacto a consigna
**Decisión**: implementar exactamente lo pedido por la cátedra, respetando nombres de tablas, columnas, rutas y códigos HTTP. **Justificación**: los casos de prueba (`C-01`..`C-16` y `D-01`..`D-08`) verifican nombres y contratos fijos.

### DD-02 — PostgreSQL 16 en Docker local para desarrollo
**Decisión**: usar PostgreSQL 16 en contenedor local para el desarrollo y pruebas del parcial; el despliegue del TP 1-4 en el VPS se conecta al PostgreSQL ya instalado en el servidor de la cátedra.

### DD-03 — `libro_autor` como entidad propia
**Decisión**: objeto de asociación con `rol` y `orden`, navegación bidireccional `libro.autorias[i].autor`.

### DD-04 — Unicidad y claves foráneas garantizadas por la base (409)
**Decisión**: no verificar existencias ni unicidad con consultas previas antes de insertar cuando la base lo garantiza con una restricción (`UNIQUE`, índice único parcial o `FOREIGN KEY`); atrapar `IntegrityError` y traducirlo a `409 Conflict` con mensaje propio (RN-01, RN-15).

### DD-05 — Carga anticipada (`joinedload` / `selectinload`) declarada en el repositorio
**Decisión**: `joinedload` para relaciones a uno (`editorial`, `genero`, `cliente`, `perfil`, `renglon.libro`) y `selectinload` para colecciones (`autorias`, `renglones`). En el parcial, toda precarga se declara **adentro del método del repositorio** que la necesita (Ej. 6 y Ej. 8).

### DD-06 — `Decimal` para dinero y `expire_on_commit=False`
**Decisión**: precios y totales siempre con `Decimal` (`NUMERIC`); fábrica de sesiones con `expire_on_commit=False` para evitar IO perezoso tras `commit()`.

---

## Decisiones de Diseño — Parcial Capítulos 1 a 6 (DD-07 a DD-14)

### DD-07 — Dos jerarquías de repositorios (`BaseRepository[T]` y `SoftDeleteRepository[T]`) sin `commit()`
**Decisión**: `BaseRepository[T]` recibe `session` y `model_cls` en su `__init__` y ejecuta `flush()` en `add`/`update`, nunca `commit()`. `SoftDeleteRepository[T]` hereda de `BaseRepository[T]`, es usado por `LibroRepository`, filtra `borrado_en IS NULL` en las lecturas habituales y agrega `get_by_id_including_deleted` y `soft_delete`.
**Justificación**: separa la persistencia de entidades con borrado físico vs lógico y delega la confirmación transaccional exclusivamente al Unit of Work (Ej. 6).

### DD-08 — Unit of Work construido en el Router y abierto en el Service, compartiendo sesión con Auth
**Decisión**: el router construye el `UnitOfWork` mediante una dependencia que recibe `session: AsyncSession = Depends(get_session)` —la misma que reciben `get_usuario_actual` y `requiere_rol`— y se lo pasa al servicio sin abrir. El servicio lo abre con `async with uow:`, que confirma al salir o revierte en excepción y **no cierra la sesión**.
**Justificación**: garantiza que toda la petición autenticada use una sola conexión del pool y que operaciones multi-tabla (RN-02, RN-10, RN-16) sean atómicas (Ej. 6).

### DD-09 — Sesión y transacción independientes para `intento_acceso` con comentario obligatorio
**Decisión**: cada intento de login (`POST /auth/login`), exitoso o fallido, se registra en `intento_acceso` abriendo una sesión y transacción propias desde `app.state.session_maker` que hacen `commit()` siempre. Incluye un comentario obligatorio en el código explicando: (1) qué hace distinto, (2) por qué no puede compartir la transacción de la petición y (3) cuál es su costo (deja filas aunque la petición falle).
**Justificación**: si compartiera la transacción de la petición, el fallo de login revertiría el propio registro del intento y el límite de 5 fallos en 60 segundos (RN-07) nunca se activaría (Ej. 7).

### DD-10 — `bcrypt` fuera del bucle (`to_thread`), bajo `Semaphore`, antes de la transacción y con hash ficticio en `lifespan`
**Decisión**: toda llamada a `bcrypt` corre en un hilo (`asyncio.to_thread`) protegida por un `asyncio.Semaphore` global, y el hash se calcula **antes** de abrir `async with uow:`. Además, el `lifespan` precalcula un hash ficticio en `app.state` para verificar contra él cuando el correo del login no existe (RN-08). Todo contrato de entrada limita las contraseñas a **72 bytes UTF-8** (`422`).
**Justificación**: evita bloquear el event loop, evita retener una conexión de base de datos durante los ~300 ms de CPU de `bcrypt`, impide enumerar usuarios por tiempo de respuesta y evita errores `500` de `bcrypt>=5` con claves largas (Ej. 4).

### DD-11 — Punto único de escritura de stock y trigger PostgreSQL de sólo-agregado
**Decisión**: `libro.stock` sólo se modifica a través de una única operación de dominio que actualiza `libro.stock` y crea el `MovimientoStock` en el mismo UoW (usada en alta de libro con `stock_inicial`, reposición y venta). Además, la Migración `004` escrita a mano instala una función y `TRIGGER` en PostgreSQL que prohíbe `UPDATE` y `DELETE` sobre `movimiento_stock` (RN-11, RN-12).
**Justificación**: mantiene invariante la igualdad `libro.stock == SUM(movimiento_stock.cantidad)` e impide adulterar la auditoría de stock incluso desde fuera de la aplicación (`psql`).

### DD-12 — Dos grupos de rutas en `app/main.py` y autorización de dueño en el servicio
**Decisión**: montar en `app/main.py` un grupo de rutas **abierto** y un grupo **protegido** (que aplica una sola vez el bloqueo `403` cuando `debe_cambiar_password=True`, RN-06). En `GET /ventas/{id}`, no usar `requiere_rol` en la ruta sino validar en el servicio si el usuario es personal (`ADMIN`/`VENDEDOR`) o el cliente dueño de la venta (`403` si no es ninguno, RN-14).

### DD-13 — Entrega dual en carpetas `parcial/` y `despliegue/`
**Decisión**: mantener el desarrollo del parcial en el árbol principal del proyecto (que constituirá la carpeta `parcial/` del `.zip`) y crear la carpeta `despliegue/` con la foto limpia del TP de los capítulos 1 a 4 más `Dockerfile` (`python:3.12-alpine`), `.dockerignore`, `env.example`, `DEPLOY.md` y `evidencia/` (`D-01` a `D-08`).

---

## Supuestos Inferidos y Validados

### SU-01 — Python 3.12 y entorno local (`Resuelto`)
El entorno cuenta con Python 3.12 y PostgreSQL 16 en Docker local verificados durante la entrega del TP (`C-01` a `C-08`).

### SU-02 — Despliegue en VPS provisto por la cátedra
El VPS ya cuenta con PostgreSQL instalado y la cátedra provee los datos de acceso y el puerto asignado al grupo para correr el contenedor de `despliegue/` con `docker run` y `--env-file`.

### SU-03 — Flujo de corrección reproducible con `seed.py`
Antes de correr cada archivo `.http` de `test/` (`C-01` a `C-16`), se ejecuta `python seed.py` sobre el esquema migrado con `alembic upgrade head`.
