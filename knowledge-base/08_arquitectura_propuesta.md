# Arquitectura Propuesta

## Capas y Responsabilidades (`Router → Service → UoW → Repository → Model`)

En el Parcial (Capítulos 1 a 6), todos los módulos de dominio adoptan la arquitectura en 5 capas con responsabilidades estrictamente separadas:

| Capa | Archivo | Qué hace y qué NO hace |
|---|---|---|
| **Router** | `app/modules/<módulo>/router.py` | Declara rutas HTTP, códigos y `response_model`; recibe contratos validados y dependencias (`usuario_actual`, `requiere_rol`, y el `UnitOfWork` del módulo construido por dependencia); llama al servicio pasándole el UoW **sin abrirlo**; traduce excepciones de dominio/`IntegrityError` a respuestas HTTP (`404`, `409`, `422`). **Nunca** ejecuta consultas ni lógica de negocio. |
| **Service** | `app/modules/<módulo>/service.py` | Contiene las reglas de negocio. Calcula hashes `bcrypt` **antes** de abrir la transacción; recibe el `UnitOfWork` como parámetro y lo abre con `async with uow:`; coordina llamadas a uno o varios repositorios del UoW. **Nunca** recibe la `AsyncSession` directamente ni construye el `UnitOfWork` por su cuenta. |
| **Unit of Work** | `app/core/unit_of_work.py` y `app/modules/<módulo>/unit_of_work.py` | Gestor de contexto asincrónico (`__aenter__` / `__aexit__`). Recibe la `AsyncSession` de la petición, instancia los repositorios que el módulo necesita pasándoles esa misma sesión; al salir del bloque sin excepción ejecuta `await self.session.commit()`, si sale con excepción ejecuta `await self.session.rollback()`. **Nunca cierra la sesión** (porque no la creó: la cierra `get_session`). |
| **Repository** | `app/core/repository.py` y `app/modules/<módulo>/repository.py` | `BaseRepository[T]` recibe `session` y `model_cls` en su constructor y ofrece `get_by_id`, `get_all`, `count`, `add`, `update`, `delete`. `SoftDeleteRepository[T]` hereda de `BaseRepository[T]`, filtra `borrado_en IS NULL` y agrega `get_by_id_including_deleted` y `soft_delete`. `add` y `update` ejecutan `await self.session.flush()`, **nunca `commit()`**. Toda precarga (`joinedload`, `selectinload`) se declara **adentro del método del repositorio** que la necesita. |
| **Model & Schemas** | `models.py` y `schemas.py` | `models.py` define tablas SQLModel, `CHECK`, `UNIQUE`, índices parciales (`postgresql_where`) y relaciones bidireccionales. `schemas.py` define contratos de entrada (`extra="forbid"`, límite de 72 bytes UTF-8 en contraseñas, `PATCH` con `exclude_unset=True`) y contratos de salida (que **nunca** incluyen `password_hash`). |

---

## Patrones Aplicados

| Patrón | Dónde se aplica | Justificación técnica |
|---|---|---|
| **Configuración tipada sin secretos por defecto** | `app/core/config.py` (`Settings`) | `pydantic-settings>=2.0` arma `DATABASE_URL` con `@computed_field` desde `POSTGRES_*`; si faltan `POSTGRES_PASSWORD` o `JWT_SECRET`, la app no arranca. |
| **Lifespan + `app.state`** | `app/main.py` y `app/core/database.py` | Motor async (con pool configurado), fábrica de sesiones (`expire_on_commit=False`) y hash ficticio de login se crean una vez en `lifespan` y se limpian con `dispose()`. |
| **Sesión unificada por petición** | `app/core/dependencies.py` y UoW | `get_usuario_actual`, `requiere_rol` y el `UnitOfWork` reciben la misma sesión de `Depends(get_session)`, evitando consumir dos conexiones del pool por request. |
| **Sesión independiente para auditoría de login** | `POST /auth/login` (`intento_acceso`) | Única escritura fuera del UoW de la petición: usa su propia sesión y transacción que confirman siempre para que el fallo de login quede registrado aunque la petición falle (lleva comentario obligatorio de 3 puntos). |
| **`bcrypt` fuera del bucle y con semáforo** | `app/core/security.py` | `asyncio.to_thread` evita bloquear el event loop durante los ~300 ms del hash, y `asyncio.Semaphore` limita cuántos hashes corren en paralelo para no saturar la CPU. Se ejecuta siempre **fuera** del bloque `async with uow:`. |
| **Dos grupos de rutas** | `app/main.py` (`abierto` y `protegido`) | Como FastAPI suma dependencias y no las resta, el bloqueo por `debe_cambiar_password=True` (`403`) se monta una sola vez en el grupo protegido. |
| **Punto único de escritura de stock** | Módulo `libros` / `ventas` (RN-11) | Toda modificación de `libro.stock` pasa por una única operación que actualiza `libro.stock` y crea el `MovimientoStock` en el mismo UoW, garantizando `stock == SUM(cantidad)`. |
| **Sólo agregado en base de datos** | Migración `004` (`movimiento_stock`) | Función y `TRIGGER` PostgreSQL instalados por migración manual que rechazan cualquier `UPDATE` o `DELETE` sobre `movimiento_stock` (RN-12). |
| **Envoltorio de paginación uniforme** | `app/core/paginacion.py` | Calcula `{items, total, page, size, pages}` con `pages = max(1, ceil(total / size))` y rechaza `page > pages` con `422` («La página X no existe: hay Y»). |

---

## Estructura Obligatoria de Directorios y Entrega

El repositorio de desarrollo mantiene la estructura obligatoria del proyecto en la raíz, y para la entrega final del `.zip` (`Parcial_Cap1a6_<NombreDelGrupo>.zip`) se empaquetan las dos carpetas exigidas por la cátedra (`parcial/` y `despliegue/`):

```
TP-U1a4/ (raíz del proyecto / carpeta `parcial/` en el .zip de entrega)
├── app/
│   ├── main.py                        # Aplicación, lifespan y los dos grupos de rutas (abierto y protegido)
│   ├── core/
│   │   ├── config.py                  # Settings con pydantic-settings y @computed_field DATABASE_URL
│   │   ├── database.py                # Funciones que crean motor y fábrica de sesiones (llamadas por lifespan), y get_session
│   │   ├── security.py                # Hash con bcrypt (to_thread + Semaphore), validación 72 bytes y JWT (PyJWT)
│   │   ├── dependencies.py            # get_usuario_actual, roles vigentes, control de cambio obligatorio y requiere_rol
│   │   ├── repository.py              # BaseRepository[T] y SoftDeleteRepository[T]
│   │   ├── paginacion.py              # Envoltorio {items, total, page, size, pages} y validación de páginas
│   │   └── unit_of_work.py            # UnitOfWork base: confirma o revierte al salir del bloque sin cerrar sesión
│   └── modules/
│       ├── health/
│       │   └── router.py              # GET /health/live (200) y GET /health/ready (200 o 503)
│       ├── usuarios/
│       │   ├── models.py              # Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad
│       │   ├── schemas.py             # Contratos de auth, usuarios, roles y eventos (extra="forbid", sin password_hash en salida)
│       │   ├── repository.py          # Repositorios de Usuario, AsignacionRol, IntentoAcceso, EventoSeguridad
│       │   ├── unit_of_work.py        # UsuariosUnitOfWork
│       │   ├── service.py             # Lógica de registro, login, cambio de clave, alta personal, roles y autoprotección
│       │   └── router.py              # Routers para /auth (abierto) y /usuarios, /eventos (protegido ADMIN)
│       ├── editoriales/               # models.py, schemas.py, repository.py, unit_of_work.py, service.py, router.py
│       ├── generos/                   # models.py, schemas.py, repository.py, unit_of_work.py, service.py, router.py
│       ├── autores/                   # models.py, schemas.py, repository.py, unit_of_work.py, service.py, router.py
│       ├── libros/                    # models.py (+ LibroAutor, MovimientoStock), schemas.py, repository.py (SoftDeleteRepository), unit_of_work.py, service.py, router.py
│       ├── clientes/                  # models.py (+ PerfilCliente, cliente.usuario_id), schemas.py, repository.py, unit_of_work.py, service.py, router.py
│       └── ventas/                    # models.py (+ RenglonVenta), schemas.py, repository.py, unit_of_work.py, service.py, router.py
├── migrations/                        # Alembic async + 4 versiones (001, 002, 003 autogenerada, 004 manual trigger)
├── test/                              # Archivos .http (C-01 a C-16) y solo_agregado.sql (C-14)
├── evidencia/                         # Capturas/salidas de C-14 (psql trigger) y C-15 (consultas fijas detalle venta 2 vs 4 renglones)
├── seed.py                            # Vacía las tablas y carga los datos iniciales exactos del parcial
├── alembic.ini                        # Sin credenciales
├── env.example                        # Todas las variables requeridas sin secretos reales
├── requirements.txt                   # Dependencias con versiones mínimas del parcial
├── README.md                          # Integrantes y pasos desde cero
│
└── despliegue/                        # Segunda carpeta del .zip: el TP de los capítulos 1 a 4 dockerizado para el VPS
    ├── app/                           # Código del TP de los capítulos 1 a 4 tal como se entregó
    ├── migrations/                    # Migraciones 001 y 002 del TP
    ├── seed.py                        # Seed del TP
    ├── requirements.txt               # Dependencias del TP
    ├── alembic.ini
    ├── env.example                    # Variables del contenedor (DATABASE_URL, SQL_ECHO) sin secretos
    ├── Dockerfile                     # python:3.12-alpine, --no-cache-dir, USER no-root, upgrade head + uvicorn 0.0.0.0, HEALTHCHECK 127.0.0.1
    ├── .dockerignore                  # Excluye .env, .venv, .git, __pycache__
    ├── DEPLOY.md                      # URL pública, fecha/hora, docker build/run, cambios al TP y cómo actualizar
    └── evidencia/                     # Comandos y salidas de los casos D-01 a D-08 en el VPS
```

---

## Variables de Entorno

### En el proyecto del Parcial (`env.example` de la raíz / `parcial/`)

| Variable | Descripción | Valor por defecto en `Settings` | Ejemplo en `env.example` | Sensible |
|---|---|---|---|---|
| `POSTGRES_USER` | Usuario de PostgreSQL | Sin secreto por defecto | `postgres` | N |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL | **Ninguno (obligatoria)** | `cambiar_en_entorno_local` | **Y** |
| `POSTGRES_DB` | Nombre de la base de datos | Sin secreto por defecto | `libreria` | N |
| `POSTGRES_HOST` | Host del servidor PostgreSQL | `"localhost"` (o requerido) | `localhost` | N |
| `POSTGRES_PORT` | Puerto de PostgreSQL | `5432` | `5432` | N |
| `DATABASE_URL` | Armada en `Settings` con `@computed_field` (`postgresql+asyncpg://...`) | Calculada automáticamente | *(calculada desde `POSTGRES_*`)* | **Y** |
| `JWT_SECRET` | Clave de firma de los tokens JWT | **Ninguno (obligatoria)** | `generar_con_openssl_rand_hex_32` | **Y** |
| `JWT_EXPIRATION_SECONDS` | Duración del JWT y `Max-Age` de la cookie | `1800` | `1800` | N |
| `BCRYPT_ROUNDS` | Costo (rondas) de `bcrypt` | `12` | `12` | N |
| `COOKIE_SECURE` | Atributo `Secure` de la cookie `access_token` | `False` | `false` | N |
| `DB_POOL_SIZE` | Tamaño del pool del motor asincrónico | `5` (o `10`) | `5` | N |
| `SQL_ECHO` | Muestra las consultas SQL en consola (`C-15`) | `False` | `true` | N |

### En el contenedor de Despliegue (`despliegue/env.example`)

| Variable | Descripción | Ejemplo en `despliegue/env.example` | Sensible |
|---|---|---|---|
| `DATABASE_URL` | URL `postgresql+asyncpg` hacia el PostgreSQL del VPS (ej. `host.docker.internal` o host de cátedra) | `postgresql+asyncpg://usuario:password@host.docker.internal:5432/libreria` | **Y** |
| `SQL_ECHO` | Desactivado en producción en el VPS | `false` | N |
