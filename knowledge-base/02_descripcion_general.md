# Descripción General

## Stack tecnológico

| Capa | Tecnología | Versión mínima | Uso en el proyecto |
|---|---|---|---|
| Lenguaje | Python | 3.12 | Lenguaje base de toda la aplicación |
| Framework web | FastAPI (`async def`) | 0.111 | API HTTP; todos los handlers asincrónicos |
| Modelos y contratos | SQLModel | 0.0.24 | Modelos de tabla y esquemas Pydantic/SQLModel |
| ORM / motor | SQLAlchemy 2.0 asincrónico | 2.0 | Motor async, sesiones y carga anticipada (`joinedload`, `selectinload`) |
| Driver PG | asyncpg | 0.30 | Controlador asincrónico de PostgreSQL |
| Base de datos | PostgreSQL | 16 | Persistencia relacional, índices únicos parciales y disparadores |
| Migraciones | Alembic (plantilla async) | 1.13 | Versionado del esquema (001, 002, 003 autogeneradas + 004 manual) |
| Configuración | pydantic-settings | 2.0 | Lectura tipada del entorno / `.env` sin secretos por defecto |
| Hash de contraseñas | bcrypt | 4.0 | Hash y verificación fuera del event loop (`to_thread` + semáforo) |
| Tokens firmados | PyJWT | 2.8 | Emisión y verificación de JWT en cookie `HttpOnly` |
| Servidor ASGI | uvicorn (`fastapi[standard]`) | — | Servidor de desarrollo y producción en contenedor |
| Contenedores | Docker | 20.10 | Imagen `python:3.12-alpine` y ejecución del TP 1-4 en local y VPS |

---

## Arquitectura general

El sistema es un **monolito modular por dominio funcional** organizado en capas estrictas donde cada capa conoce únicamente la inmediata inferior:

```
Cliente HTTP (.http)
  → Router (recibe request, valida DTO/Query, inyecta dependencias y construye UoW, traduce errores)
    → Service (reglas de negocio, calcula hash fuera de transacción, abre el UoW con `async with`)
      → Unit of Work (agrupa repositorios con la misma sesión, confirma al salir o revierte en excepción)
        → Repository (consultas SQLAlchemy async, precarga declarada, `flush()` sin `commit()`)
          → Model (SQLModel / PostgreSQL 16)
```

### Módulos obligatorios (`app/modules/`)
- `health`: sólo `router.py` (`/health/live` y `/health/ready`).
- `usuarios`: `Usuario`, `AsignacionRol`, `IntentoAcceso`, `EventoSeguridad`; rutas `/auth/*`, `/usuarios/*`, `/eventos`.
- `editoriales`: `Editorial`; CRUD y libros por editorial.
- `generos`: `Genero`; CRUD y libros por género.
- `autores`: `Autor`; CRUD y libros por autor.
- `libros`: `Libro` (con `SoftDeleteRepository`), `LibroAutor`, `MovimientoStock`; CRUD, baja lógica (`204`), reposición y movimientos de stock.
- `clientes`: `Cliente` (con `usuario_id` opcional), `PerfilCliente`; CRUD, perfil e historial de ventas.
- `ventas`: `Venta`, `RenglonVenta`; alta de venta con descuento de stock y movimientos en un solo UoW, consulta general, detalle autorizado y `/mis-ventas`.

### Decisiones estructurales clave
- **Configuración (`app/core/config.py`)**: `Settings(BaseSettings)` lee `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` y arma `DATABASE_URL` con `@computed_field` (`postgresql+asyncpg`). Ni la contraseña de la base ni `JWT_SECRET` tienen valor por defecto en el código: si faltan, la aplicación no arranca.
- **Ciclo de vida (`lifespan` en `app/main.py`)**: crea el motor asincrónico (con el tamaño del pool de `Settings`) y la fábrica de sesiones (`expire_on_commit=False`), calcula **una sola vez** el hash ficticio de login y guarda los tres en `app.state`. Al apagar cierra el motor con `await engine.dispose()`.
- **Una sola sesión por petición**: `get_usuario_actual`, `requiere_rol` y el `UnitOfWork` del módulo reciben la **misma sesión** entregada por `Depends(get_session)`, evitando tomar dos conexiones del pool por petición.
- **Única excepción transaccional**: el registro de cada intento de login en `intento_acceso` usa su **propia sesión y transacción independientes**, que confirman siempre para sobrevivir al rollback de un login fallido (documentado con comentario obligatorio en el código).
- **Dos grupos de rutas en `app/main.py`**: un grupo **abierto** (salud, `/auth/*`, lecturas públicas del catálogo) y un grupo **protegido** que monta una sola vez la dependencia de bloqueo por cambio obligatorio de contraseña (`debe_cambiar_password`).

---

## Integraciones externas e infraestructura

- **PostgreSQL 16**: única dependencia de base de datos.
- **Aviso de comprobante simulado**: al confirmar `POST /ventas`, se agenda en `BackgroundTasks` una corrutina con `await asyncio.sleep(0.5)` que escribe un mensaje visible en la consola normal de `uvicorn`.
- **Contenedor Docker y VPS (entrega en carpeta `despliegue/`)**: el TP de los capítulos 1 a 4 (sin los cambios del parcial) se empaqueta en una imagen basada en `python:3.12-alpine` y se despliega con `docker run` en el VPS de la cátedra contra el PostgreSQL provisto en el servidor.

---

## Resumen de la API REST (Parcial Capítulos 1 a 6)

### Grupo Abierto (no exige rol ni bloquea por cambio de contraseña pendiente)
- `GET /health/live` → `200` (sin tocar la base).
- `GET /health/ready` → `200` (`SELECT 1`) o `503` si la base no contesta.
- `POST /auth/registro` → `201, 409, 422` (crea `Usuario` + `AsignacionRol(CLIENTE)` + `Cliente` en un UoW).
- `POST /auth/login` → `200, 401, 422, 429` (emite cookie `access_token` `HttpOnly`; body sin token).
- `POST /auth/logout` → `200` (borra cookie).
- `GET /auth/yo` → `200, 401` (autenticado: devuelve usuario, roles vigentes en BD y roles del token).
- `POST /auth/cambiar-password` → `200, 401, 422` (autenticado: actualiza clave + `debe_cambiar_password=False` + `evento_seguridad` en un UoW).
- `GET /libros` (`page, size, titulo, genero_id`) → `200, 422` (solo libros vigentes `borrado_en IS NULL`).
- `GET /libros/{id}` → `200, 404, 422` (solo si está vigente).
- `GET /editoriales`, `GET /generos` (`page, size`) → `200, 422`.
- `GET /editoriales/{id}/libros`, `GET /generos/{id}/libros`, `GET /autores/{id}/libros` → `200, 404`.

### Grupo Protegido (exige sesión `401` y bloquea con `403` si `debe_cambiar_password=True`)
- **Administración de personal y seguridad (`ADMIN`)**:
  - `POST /usuarios` → `201, 409, 422` (alta de personal con clave provisoria `debe_cambiar_password=True` + rol + `evento_seguridad`).
  - `GET /usuarios/{id}/roles` → `200, 404`.
  - `POST /usuarios/{id}/roles` → `201, 404, 409, 422` (con `vence_en` opcional con timezone y futuro + `evento_seguridad`).
  - `DELETE /usuarios/{id}/roles/{rol}` → `200, 404, 409` (marca `revocada_en`, autoprotección RN-05 + `evento_seguridad`).
  - `GET /eventos` (`page, size`) → `200, 422`.
- **Escritura de Catálogo y Stock (`ADMIN`)**:
  - `POST /editoriales`, `POST /generos`, `POST /autores` → `201, 409, 422`.
  - `PATCH /editoriales/{id}`, `PATCH /autores/{id}` → `200, 404, 409, 422`.
  - `POST /libros` (con `autores` y `stock_inicial`) → `201, 409, 422` (deja movimiento `"Stock inicial"`).
  - `PATCH /libros/{id}` (título y precio; `stock` rechazado con `422` por `extra="forbid"`) → `200, 404, 409, 422`.
  - `DELETE /libros/{id}` → `204, 404` (baja lógica `borrado_en`).
  - `POST /libros/{id}/reponer` → `200, 404, 409, 422` (`409` si está dado de baja).
  - `GET /libros/{id}/movimientos` → `200, 404`.
- **Clientes (`VENDEDOR`, `ADMIN`)**:
  - `POST /clientes` → `201, 409, 422`.
  - `GET /clientes/{id}`, `PATCH /clientes/{id}` → `200, 404, 409, 422`.
  - `POST /clientes/{id}/perfil` → `201, 404, 409`.
  - `GET /clientes/{id}/ventas` → `200, 404`.
- **Ventas**:
  - `POST /ventas` (`VENDEDOR`, `ADMIN`) → `201, 409, 422` (crea venta, renglones, descuenta stock y crea movimientos en un UoW; `409` si no alcanza stock o libro dado de baja).
  - `GET /ventas` (`VENDEDOR`, `ADMIN`, `page, size`) → `200, 422`.
  - `GET /ventas/{id}` (autenticado, sin `requiere_rol` en ruta: el servicio permite a `ADMIN`/`VENDEDOR` o al cliente dueño; `403` si es ajena) → `200, 403, 404`.
  - `GET /mis-ventas` (autenticado, `page, size`) → `200, 422`.
