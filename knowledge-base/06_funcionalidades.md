# Funcionalidades (Historias de Usuario)

> Las épicas 1 a 5 documentan la base construida en el TP (Capítulos 1 a 4) y cómo evoluciona en el **Parcial (Capítulos 1 a 6)**. Las épicas 6 a 9 cubren las capacidades nuevas del Parcial y el despliegue en el VPS.

---

## Épica 1: Configuración, Ciclo de Vida y Salud (Ej. 1)

### US-001 — Healthchecks con estado de base (503)
**Como** corrector u orquestador de contenedores **Quiero** `GET /health/live` (200 sin tocar la base) y `GET /health/ready` (`SELECT 1`, 200 o **503** si la base no contesta) **Para** distinguir si el proceso está vivo y si está listo para atender peticiones.
**Criterios de aceptación**: `live` responde `200`; `ready` ejecuta `SELECT 1` y responde `503 Service Unavailable` sin traza interna si PostgreSQL no responde.
**Reglas relacionadas**: RN-15.

### US-002 — Configuración tipada con `pydantic-settings` y `lifespan`
**Como** desarrollador **Quiero** gestionar la configuración con `Settings` (`pydantic-settings>=2.0`), armar `DATABASE_URL` con `@computed_field` a partir de `POSTGRES_*` y exigir `JWT_SECRET` y `POSTGRES_PASSWORD` sin valores por defecto **Para** que la aplicación falle al arrancar si falta un secreto y cree motor, sesiones y hash ficticio en `lifespan`.
**Criterios de aceptación**: sin `.env` o sin secretos la app no arranca; `lifespan` guarda motor (con pool configurado), fábrica de sesiones (`expire_on_commit=False`) y hash ficticio en `app.state`, y ejecuta `dispose()` al apagar.
**Reglas relacionadas**: RN-08, RN-15.

---

## Épica 2: Catálogo, Borrado Lógico y Control de Stock (Ej. 2, Ej. 3, Ej. 6, Ej. 7)

### US-010 — Catálogo público paginado con envoltorio y escritura restringida a `ADMIN`
**Como** visitante **Quiero** consultar libros, editoriales, géneros y libros por editorial/género/autor sin iniciar sesión, y **como** `ADMIN` **Quiero** crear y editar entidades del catálogo con contratos `extra="forbid"` y paginación `{items, total, page, size, pages}` **Para** proteger las escrituras manteniendo público el catálogo.
**Criterios de aceptación**: lecturas en grupo abierto; escrituras requieren rol `ADMIN` en grupo protegido; `page > pages` devuelve `422` («La página X no existe: hay Y»); `total == 0` devuelve `pages: 1`.
**Reglas relacionadas**: RN-01, RN-04, RN-15.

### US-012 — Alta de libro con `stock_inicial` y movimiento inicial
**Como** `ADMIN` **Quiero** crear un libro en `POST /libros` indicando `stock_inicial` y `autores` **Para** que el libro nazca con su stock y su primer registro `"Stock inicial"` en `movimiento_stock` (si `stock_inicial > 0`) a través del punto único de escritura de stock en un solo UoW.
**Criterios de aceptación**: `201` con detalle completo; `PATCH /libros/{id}` permite editar título y precio pero rechaza `stock` con `422` (`extra="forbid"`).
**Reglas relacionadas**: RN-01, RN-11, RN-15.

### US-014 — Reposición, consulta de movimientos y baja lógica de libros
**Como** `ADMIN` **Quiero** reponer stock (`POST /libros/{id}/reponer`), listar movimientos (`GET /libros/{id}/movimientos`) y dar de baja lógica un libro (`DELETE /libros/{id}` → `204`) **Para** mantener la trazabilidad de stock (`stock == SUM(cantidad)`) y retirar libros descatalogados sin romper ventas históricas ni bloquear su ISBN.
**Criterios de aceptación**:
- `POST /libros/{id}/reponer` suma al stock y crea `MovimientoStock` positivo en un UoW; si el libro está dado de baja responde `409` (RN-13).
- `DELETE /libros/{id}` marca `borrado_en` y devuelve `204`; el libro desaparece de `GET /libros` y `GET /libros/{id}` (`404`); cargar un nuevo libro con el mismo ISBN devuelve `201`, y un segundo vigente con ese ISBN devuelve `409` (`C-13`).
- Cualquier `UPDATE` o `DELETE` sobre `movimiento_stock` en PostgreSQL es rechazado por el disparador de la migración 004 (`C-14`).
**Reglas relacionadas**: RN-01, RN-11, RN-12, RN-13.

---

## Épica 3: Clientes sobre UoW y Acceso Web Opcional (Ej. 2, Ej. 5, Ej. 6)

### US-020 — Gestión de clientes y perfiles por personal (`VENDEDOR`, `ADMIN`)
**Como** `VENDEDOR` o `ADMIN` **Quiero** dar de alta clientes de mostrador (`usuario_id = None`), consultar/editar su ficha con perfil (`Cliente.perfil` y `Cliente.usuario` como objetos) y listar sus ventas **Para** atender clientes presenciales y web.
**Criterios de aceptación**: rutas protegidas para `VENDEDOR` y `ADMIN`; operaciones sobre `ClientesUnitOfWork`; email o segundo perfil repetido → `409`.
**Reglas relacionadas**: RN-01, RN-04, RN-15.

---

## Épica 4: Ventas con Descuento Atómico de Stock y Autorización de Dueño (Ej. 5, Ej. 6, Ej. 8)

### US-030 — Registro de venta con descuento de stock y movimientos en un solo UoW
**Como** `VENDEDOR` o `ADMIN` **Quiero** registrar una venta en `POST /ventas` con `{cliente_id, renglones: [{libro_id, cantidad}]}` **Para** que en una única transacción se creen la venta y sus renglones con precios copiados, se descuente el stock de cada libro por el punto único de escritura y se registre un `MovimientoStock` negativo por renglón.
**Criterios de aceptación**:
- Si todos los libros están vigentes y tienen stock suficiente → `201` con detalle completo y se agenda el aviso en `BackgroundTasks` (`asyncio.sleep(0.5)` + log visible en consola normal de `uvicorn`, `C-10`).
- Si algún libro no alcanza (`C-11`), no existe o está dado de baja (`C-12`), o el cliente no existe → `409` y **se revierte toda la transacción** (no queda venta, ni renglones, ni descuentos, ni movimientos; `stock == SUM(cantidad)` se mantiene intacto).
**Reglas relacionadas**: RN-09, RN-10, RN-11, RN-13, RN-15.

### US-031 — Consulta de ventas, detalle autorizado (personal o dueño) y `/mis-ventas`
**Como** `VENDEDOR`/`ADMIN` **Quiero** listar todas las ventas (`GET /ventas`) y ver cualquier detalle (`GET /ventas/{id}`), y **como** `CLIENTE` autenticado **Quiero** listar mis compras (`GET /mis-ventas`) y ver el detalle de mi propia venta (`GET /ventas/{id}`) sin poder ver ventas ajenas (`403`) **Para** garantizar la privacidad de cada cliente y consultas sin N+1.
**Criterios de aceptación**:
- `GET /ventas/{id}` no lleva `requiere_rol` en la ruta: el servicio verifica si el usuario tiene rol `ADMIN`/`VENDEDOR` o es dueño de la venta (`venta.cliente.usuario_id == usuario.id`); si no, responde `403` (`C-06`).
- El detalle de una venta se resuelve con una cantidad fija de consultas (precarga en repositorio) y sigue mostrando el título y datos de libros que hayan sido dados de baja después de la venta (`C-13`, `C-15`).
**Reglas relacionadas**: RN-04, RN-13, RN-14.

---

## Épica 6: Autenticación, Registro y Seguridad de Contraseñas (Ej. 4, Ej. 7)

### US-050 — Auto-registro de cliente en un solo Unit of Work
**Como** visitante **Quiero** registrarme en `POST /auth/registro` con `{nombre, email, password}` **Para** que el sistema cree mi `Usuario`, mi `AsignacionRol(CLIENTE)` y mi ficha `Cliente` vinculada en una sola transacción.
**Criterios de aceptación**: `201` si el correo es nuevo; si el correo ya existe en `usuario` o en `cliente` (ej. un cliente de mostrador previo), responde `409` con mensaje propio, no se apropia de la ficha existente y no deja ninguna fila suelta (`C-02`). Contraseña `> 72` bytes UTF-8 o campo extra (`rol`) → `422`.
**Reglas relacionadas**: RN-01, RN-02, RN-15.

### US-051 — Login con límite de intentos, hash ficticio, cookie `HttpOnly` y sesión propia de auditoría
**Como** usuario **Quiero** iniciar sesión en `POST /auth/login` recibiendo el JWT exclusivamente en una cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`, `Secure` configurable) **Para** autenticarme sin exponer el token al JavaScript ni revelar qué correos existen.
**Criterios de aceptación**:
1. Primero cuenta fallos en `intento_acceso` (mismo `email` e `ip` en los últimos 60 segundos desde el último éxito): si hay 5 fallos, el 6to responde `429` con encabezado `Retry-After` en pocos milisegundos sin ejecutar `bcrypt` (`C-05`).
2. Verifica contraseña con `bcrypt` en `asyncio.to_thread` bajo `asyncio.Semaphore`: contra el hash del usuario o contra el hash ficticio de `app.state` si el correo no existe, devolviendo `401` con el mismo cuerpo y tiempo similar (`C-04`).
3. Anota el intento (exitoso o fallido) en `intento_acceso` usando **una sesión y transacción propias** que confirman siempre, documentadas con el comentario obligatorio de 3 puntos.
4. En éxito, devuelve `200` con `{mensaje, debe_cambiar_password, expira_en_segundos}` sin el token en el cuerpo y fija la cookie (`C-03`).
**Reglas relacionadas**: RN-07, RN-08.

### US-052 — Perfil de sesión (`/auth/yo`), cierre de sesión (`/auth/logout`) y cambio de contraseña
**Como** usuario autenticado **Quiero** consultar `GET /auth/yo`, cerrar sesión en `POST /auth/logout` y cambiar mi contraseña en `POST /auth/cambiar-password` **Para** gestionar mi sesión y desbloquear mi cuenta cuando tengo cambio obligatorio pendiente.
**Criterios de aceptación**: `/auth/yo` muestra los roles vigentes en BD y los roles informativos del token (`C-07`); `/auth/cambiar-password` calcula el nuevo hash fuera de la transacción y en un solo UoW actualiza `password_hash`, pone `debe_cambiar_password=False` y registra `evento_seguridad`, manteniendo válida la cookie actual (`C-09`).
**Reglas relacionadas**: RN-04, RN-06, RN-16.

---

## Épica 7: Autorización, Personal, Vigencia de Roles y Eventos (Ej. 5, Ej. 6, Ej. 7)

### US-060 — Alta de personal y gestión de roles con vigencia y autoprotección
**Como** `ADMIN` **Quiero** dar de alta personal con clave provisoria (`POST /usuarios`), consultar roles (`GET /usuarios/{id}/roles`), asignar roles con vencimiento opcional (`POST /usuarios/{id}/roles`) y revocarlos sin borrar la fila (`DELETE /usuarios/{id}/roles/{rol}`) **Para** administrar los permisos del equipo con trazabilidad completa en `evento_seguridad`.
**Criterios de aceptación**:
- `POST /usuarios` crea el usuario con `debe_cambiar_password=True`, su asignación de rol y un `evento_seguridad` en un solo UoW (`RN-16`).
- `POST /usuarios/{id}/roles`: valida que `vence_en` (si se envía) tenga zona horaria y sea futuro (`422` si no, `C-07`); si tenía ese rol vencido, cierra la fila anterior y abre una nueva; si ya tiene asignación abierta de ese rol → `409` (`RN-03`); registra `evento_seguridad`.
- `DELETE /usuarios/{id}/roles/{rol}`: escribe `revocada_en` sin borrar la fila y registra `evento_seguridad`; en la petición siguiente la sesión abierta del usuario afectado recibe `403` (`C-07`); si un `ADMIN` intenta revocar su propio `ADMIN` o dejar al sistema sin administradores vigentes → `409` (`RN-05`, `C-08`).
- `GET /eventos` devuelve el historial paginado para `ADMIN`.
**Reglas relacionadas**: RN-03, RN-04, RN-05, RN-06, RN-16.

---

## Épica 8: Seed, Casos de Prueba (`C-01` a `C-16`), Contenedor y Despliegue en VPS (Ej. 9, Ej. 10)

### US-070 — Seed canónico y suite de pruebas del Parcial (`C-01` a `C-16`)
**Como** corrector **Quiero** correr `python seed.py`, los archivos `test/*.http` (`C-01` a `C-16`) y `test/solo_agregado.sql` (`C-14`), y revisar `parcial/evidencia/` (`C-14` y `C-15`) **Para** comprobar de forma reproducible todos los requisitos del parcial.
**Criterios de aceptación**: `seed.py` deja exactamente los 5 usuarios, el catálogo del TP, los 3 clientes, la Venta 1 (`69000.00`), los 7 movimientos (`stock == SUM(cantidad)`) y el evento `SISTEMA`.
**Reglas relacionadas**: RN-01 a RN-16.

### US-071 — Imagen Docker (`python:3.12-alpine`) y Despliegue en VPS del TP 1-4 (`D-01` a `D-08`)
**Como** equipo **Quiero** empaquetar el TP de los capítulos 1 a 4 en la carpeta `despliegue/` con un `Dockerfile` sobre `python:3.12-alpine` (<100 MB), usuario sin privilegios (`USER`), sin secretos en la imagen, `alembic upgrade head` al iniciar y `HEALTHCHECK` contra `http://127.0.0.1:8000/health/ready`, y ponerlo en línea en el VPS con `docker run` **Para** cumplir los ejercicios 9 y 10 y documentar `DEPLOY.md` y `despliegue/evidencia/` (`D-01` a `D-08`).
**Criterios de aceptación**: `D-01` a `D-08` verificados y guardados en `despliegue/evidencia/`; `DEPLOY.md` documenta URL pública, fecha/hora, comandos `docker build` y `docker run`, cambios mínimos al TP (si los hubo) y procedimiento de actualización sin pérdida de datos.
**Reglas relacionadas**: Ej. 9 y Ej. 10.
