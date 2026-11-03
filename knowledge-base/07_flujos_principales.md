# Flujos Principales

## Flujo 1: Arranque (`lifespan`), Sesión Compartida y Unit of Work

**Disparador**: arranque del servidor y recepción de cada petición HTTP.
**Pasos**:
1. Al importar, `app/core/config.py` instancia/valida `Settings` con `pydantic-settings`: arma `DATABASE_URL` con `@computed_field` desde `POSTGRES_*` y verifica que `POSTGRES_PASSWORD` y `JWT_SECRET` estén definidos (si faltan, el proceso falla de inmediato antes de levantar).
2. En el `lifespan` de `app/main.py`:
   - Se crea el motor asincrónico (`create_async_engine`) con el tamaño de pool configurado y la fábrica de sesiones (`async_sessionmaker(..., expire_on_commit=False)`), guardándolos en `app.state`.
   - Se calcula **una sola vez** el hash ficticio de `bcrypt` (con el costo `BCRYPT_ROUNDS`) y se guarda en `app.state.dummy_password_hash`.
3. En cada petición:
   - `Depends(get_session)` obtiene una sesión de `app.state.session_maker` y la cierra al finalizar la respuesta.
   - Si la ruta es autenticada o protegida, `get_usuario_actual`, el control de `debe_cambiar_password`, `requiere_rol` y la dependencia que construye el `UnitOfWork` del módulo **reciben esa misma instancia de `AsyncSession`** (gracias al caché por petición de `Depends` en FastAPI), usando una sola conexión del pool.
   - El router pasa el UoW **sin abrir** al servicio; el servicio ejecuta `async with uow:` para abrir el bloque transaccional, que hace `commit()` al salir sin excepción o `rollback()` si ocurre un error, **sin cerrar la sesión**.
4. Al apagar el servidor, el `lifespan` ejecuta `await engine.dispose()`.

---

## Flujo 2: Auto-registro de Cliente en un solo UoW (`POST /auth/registro`, RN-02)

**Disparador**: `POST /auth/registro` con `{nombre, email, password}` (`extra="forbid"`, `password` <= 72 bytes UTF-8).
**Pasos**:
1. El servicio calcula el hash de la contraseña con `await hash_password(datos.password)` (`asyncio.to_thread` + `asyncio.Semaphore`) **antes** de abrir el `UsuariosUnitOfWork`.
2. Abre `async with uow:` y en la misma transacción:
   - Crea `Usuario(email=..., nombre=..., password_hash=..., activo=True, debe_cambiar_password=False)` y hace `flush()`.
   - Crea `AsignacionRol(usuario_id=usuario.id, rol="CLIENTE", desde=now())` y hace `flush()`.
   - Crea `Cliente(nombre=..., email=..., usuario_id=usuario.id)` y hace `flush()`.
3. Al salir del bloque `async with uow:`, se confirma la transacción (`commit()`) y se devuelve `201`.
**Casos de error**:
- Si el correo ya existe en `usuario` o en `cliente` (ej. cliente de mostrador previo), el `flush()`/`commit()` lanza `IntegrityError`, el UoW hace `rollback()` de las tres escrituras y se traduce a `409 Conflict` con mensaje propio, sin apropiarse de la ficha existente ni dejar filas huérfanas (`C-02`).

---

## Flujo 3: Login, Límite de Intentos y Sesión Propia de Auditoría (`POST /auth/login`, RN-07, RN-08, Ej. 7)

**Disparador**: `POST /auth/login` con `{email, password}` (`password` <= 72 bytes UTF-8).
**Pasos en orden estricto**:
1. **Verificación del límite de intentos (RN-07)**:
   - Se consulta en `intento_acceso` cuántos intentos fallidos (`exito = False`) existen para ese `(email, ip)` en los últimos 60 segundos posteriores al último intento exitoso (`exito = True`) de ese mismo `(email, ip)`.
   - Si ya acumula **5 intentos fallidos**, responde inmediatamente **`429 Too Many Requests`** con el encabezado `Retry-After` **sin ejecutar `bcrypt`** (`C-05`).
2. **Búsqueda de usuario y verificación de contraseña en tiempo constante (RN-08)**:
   - Se busca el usuario por `email`.
   - Si el usuario existe, se verifica la contraseña contra `usuario.password_hash` usando `asyncio.to_thread` + `asyncio.Semaphore`.
   - Si el usuario **no existe**, se verifica igualmente la contraseña contra `app.state.dummy_password_hash` para que la petición tarde lo mismo (`~300 ms`) y no revele si el correo está registrado (`C-04`).
   - El intento es válido sólo si el usuario existe, `usuario.activo == True` y la contraseña coincide.
3. **Registro en `intento_acceso` con sesión y transacción propias (Ej. 7)**:
   - Se abre una **sesión y transacción independientes** desde `session_maker` (que incluye el comentario obligatorio explicando: 1. qué hace distinto, 2. por qué no puede compartir la transacción de la petición, y 3. cuál es su costo: deja filas aunque la petición falle) y se guarda `IntentoAcceso(cuando=now(), email=..., ip=..., exito=...)` haciendo `commit()` siempre.
   - Si el login falló, se responde `401 Unauthorized` con un mensaje único (`"Credenciales inválidas"`).
4. **Emisión de JWT y Cookie `HttpOnly` (`C-03`)**:
   - Si el login tuvo éxito, se consultan los roles vigentes del usuario en `asignacion_rol`, se firma el JWT (`sub`, `exp`, `roles`) y se envía en la cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age=JWT_EXPIRATION_SECONDS`, `Secure=settings.COOKIE_SECURE`).
   - El cuerpo de la respuesta devuelve `200` con `{mensaje, debe_cambiar_password, expira_en_segundos}` **sin incluir el token**.

---

## Flujo 4: Autorización por Petición, Cambio Obligatorio de Clave y Gestión de Roles (RN-03 a RN-06, RN-16)

**Disparador**: Petición a ruta protegida o administración de roles/contraseña.
**Pasos**:
1. `get_usuario_actual` lee exclusivamente `request.cookies.get("access_token")` (ignora `Authorization: Bearer`, `C-03`). Si no hay cookie, el JWT es inválido/vencido o el usuario no existe/está inactivo → responde `401`.
2. Si la ruta pertenece al **grupo protegido** en `app/main.py`, la dependencia de grupo verifica `usuario.debe_cambiar_password`: si es `True`, responde `403` (`C-09`).
3. Si la ruta exige `requiere_rol(...)`, la dependencia consulta `asignacion_rol` en la base de datos (usando la misma sesión del request) filtrando `usuario_id == usuario.id`, `revocada_en IS NULL` y `(vence_en IS NULL OR vence_en > now())`. Si no posee ninguno de los roles requeridos → responde `403` (`C-06`, `C-07`).
4. **Revocación de rol (`DELETE /usuarios/{id}/roles/{rol}`)**:
   - El servicio verifica RN-05 (que el admin no se revoque su propio `ADMIN` y que quede al menos un `ADMIN` vigente en la base → si no, `409`, `C-08`).
   - En un solo UoW marca `revocada_en = now()` en la fila abierta (nunca la borra) e inserta la fila en `evento_seguridad` (RN-16). En la petición siguiente, la cookie que ya tenía ese usuario recibe `403` (`C-07`).

---

## Flujo 5: Punto Único de Escritura de Stock y Baja Lógica de Libros (RN-11, RN-12, RN-13)

**Disparador**: `POST /libros`, `POST /libros/{id}/reponer` o `DELETE /libros/{id}` (`ADMIN`).
**Pasos**:
1. **Punto único de escritura de stock (RN-11)**: toda variación de `libro.stock` pasa por una única función/método de dominio dentro de la transacción del UoW que modifica `libro.stock` y agrega simultáneamente la fila correspondiente en `MovimientoStock(libro_id=..., venta_id=..., usuario_id=..., cantidad=..., motivo=..., cuando=now())`.
   - En `POST /libros` con `stock_inicial`: nace con `stock = 0` y, si `stock_inicial > 0`, aplica el punto único con `cantidad = stock_inicial` y `motivo = "Stock inicial"`.
   - En `POST /libros/{id}/reponer`: verifica que el libro exista y no esté dado de baja (si está dado de baja → `409`, RN-13); aplica el punto único con `cantidad > 0` y el motivo indicado (`C-13`).
2. **Baja lógica (`DELETE /libros/{id}`)**:
   - `SoftDeleteRepository.soft_delete` marca `libro.borrado_en = now()` dentro del UoW y devuelve `204 No Content`.
   - El libro deja de aparecer en `GET /libros` y `GET /libros/{id}` (`404`), pero la fila permanece en la tabla para las ventas históricas y el índice único parcial `(isbn) WHERE borrado_en IS NULL` permite dar de alta otro libro vigente con ese mismo ISBN (`C-13`).

---

## Flujo 6: Registro de Venta con Descuento de Stock en un solo UoW (`POST /ventas`, RN-09, RN-10, RN-11, RN-13)

**Disparador**: `POST /ventas` (`VENDEDOR` o `ADMIN`) con `{cliente_id, renglones: [{libro_id, cantidad}]}`.
**Pasos**:
1. El DTO valida `extra="forbid"`, al menos un renglón, `cantidad > 0` y ausencia de `libro_id` duplicados (`422` si falla, RN-09).
2. El servicio abre `async with uow:` (`VentasUnitOfWork`):
   - Verifica/obtiene los libros vigentes solicitados. Si algún libro no existe o está dado de baja (`borrado_en IS NOT NULL`), o si para algún renglón `libro.stock < cantidad`, lanza error de conflicto (`409`) y el UoW hace **`rollback()` completo**: no queda ni la venta, ni ningún renglón, ni ningún descuento de stock, ni ningún movimiento (`C-11`, `C-12`, RN-10).
   - Copia `precio_unitario = libro.precio` en cada `RenglonVenta`, calcula `total = sum(cantidad * precio_unitario)` y crea la `Venta` con sus renglones (`flush()` para obtener `venta.id`).
   - Por cada renglón, invoca el **punto único de escritura de stock** con `cantidad = -renglon.cantidad`, `venta_id = venta.id`, `usuario_id = usuario_actual.id` y motivo de venta.
3. Al salir de `async with uow:`, se confirma la transacción (`commit()`).
4. Recién después de confirmar la transacción, se agenda en `BackgroundTasks` el aviso simulado (`await asyncio.sleep(0.5)` + log visible en consola normal de `uvicorn`) y se devuelve `201 Created` con la venta precargada (`C-10`).

---

## Flujo 7: Detalle de Venta Autorizado y Sin N+1 (`GET /ventas/{id}`, RN-13, RN-14, Ej. 8)

**Disparador**: `GET /ventas/{id}` por cualquier usuario autenticado (con cambio de clave al día).
**Pasos**:
1. La ruta pertenece al grupo protegido pero **no lleva `requiere_rol`**.
2. El repositorio carga la venta en un número fijo de consultas declarando precarga (`joinedload` para `Venta.cliente` y `RenglonVenta.libro`, `selectinload` para `Venta.renglones`), **sin filtrar `borrado_en`** en los libros de los renglones para que las ventas viejas sigan mostrando los libros dados de baja (`C-13`, `C-15`).
3. El servicio verifica quién pide la venta:
   - Si el usuario tiene rol vigente `ADMIN` o `VENDEDOR`, permite verla.
   - Si no es personal, verifica si `venta.cliente.usuario_id == usuario_actual.id` (cliente dueño). Si no es ni personal ni dueño → responde **`403 Forbidden`** (`C-06`, RN-14).
4. Devuelve `200 OK` con cliente, renglones y datos del libro de cada renglón.

---

## Flujo 8: Construcción y Despliegue del Contenedor en el VPS (`despliegue/`, Ej. 9 y Ej. 10)

**Disparador**: Empaquetado y puesta en línea del TP (capítulos 1 a 4) en el VPS de la cátedra.
**Pasos**:
1. En la carpeta `despliegue/` (que contiene el código del TP 1-4), el `Dockerfile` parte de `python:3.12-alpine` (<100 MB, `D-01`), copia e instala `requirements.txt` con `pip install --no-cache-dir` antes de copiar el código, crea y activa un usuario sin privilegios (`USER`, `D-07`), expone el puerto `8000`, declara `HEALTHCHECK` usando `wget -qO- http://127.0.0.1:8000/health/ready`, y al iniciar ejecuta `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000` (`D-02`).
2. El `.dockerignore` excluye `.env`, `.venv`, `.git` y `__pycache__` para que ningún secreto quede horneado en las capas (`D-06`).
3. En el VPS se construye la imagen (`docker build -t libreria .`) y se corre con `docker run -d --name libreria -p <puerto>:8000 --restart unless-stopped --env-file <archivo-env-servidor> libreria` (`D-02`, `D-04`, `D-05`).
4. Se cargan los datos iniciales con `docker exec libreria python seed.py` y se verifican desde afuera los casos `D-01` a `D-08`, guardando las salidas en `despliegue/evidencia/` y documentando todo en `despliegue/DEPLOY.md`.
