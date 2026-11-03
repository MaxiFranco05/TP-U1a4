# Visión y Objetivos

## Propósito del sistema

API asincrónica para la gestión integral de una librería de barrio (catálogo con borrado lógico, control de stock de sólo-agregado, clientes, ventas transaccionales y control de acceso con usuarios, roles con vigencia y auditoría de seguridad), desarrollada como trabajo práctico integrador (Unidades 1 a 4, completado) y **Parcial Integrador (Unidades 1 a 6)** de Programación III.

El proyecto demuestra el dominio de:
1. Reorganización de una API asincrónica en capas estrictas: **`Router → Service → UoW → Repository → Model`**.
2. Evolución de un esquema versionado con **Alembic** (migraciones autogeneradas y migración escrita a mano para disparadores PostgreSQL).
3. **Autenticación** con contraseñas en `bcrypt` (fuera del event loop y bajo semáforo), límite de intentos y token JWT en cookie `HttpOnly`, sin revelar qué cuentas existen.
4. **Autorización** consultando roles vigentes en la base en cada petición, distinguiendo siempre entre `401` y `403`.
5. **Transacciones atómicas con Unit of Work** para agrupar escrituras de negocio (auto-registro, venta con descuento de stock y movimientos, auditoría de eventos).
6. **Integridad en la base de datos**: unicidad parcial entre registros vigentes (`WHERE borrado_en IS NULL`, `WHERE revocada_en IS NULL`), claves foráneas, `CHECK` y tabla de sólo-agregado (`movimiento_stock`).
7. **Contenedorización y despliegue en VPS**: empaquetado del TP (capítulos 1 a 4) en una imagen Docker (`python:3.12-alpine`, sin root, sin secretos) puesta en línea en el VPS de la cátedra.

---

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|---|---|---|
| **Equipo de alumnos (Maxi, Andrés, Octavio)** | Entregar el Parcial (`parcial/` + `despliegue/`) cumpliendo el 100% de la consigna | Dividir el desarrollo en 3 bloques equitativos (~33-34% c/u) con trazabilidad OpenSpec |
| **Docente / Corrector** | Verificar con `seed.py`, casos `C-01` a `C-16` y `D-01` a `D-08` que el sistema cumple cada ejercicio | Correr `alembic upgrade head` / `downgrade base` / `upgrade head` en base vacía y auditar el despliegue en el VPS |
| **Administrador (`ADMIN`)** | Mantener el catálogo, reponer/dar de baja libros y administrar al personal y sus roles con vigencia | Auditar movimientos de stock y eventos de seguridad (`GET /eventos`) |
| **Vendedor (`VENDEDOR`)** | Atender clientes en el mostrador y registrar ventas descontando stock atómicamente | Consultar fichas de clientes, perfiles e historial de ventas |
| **Cliente (`CLIENTE`)** | Registrarse por la web y consultar sus propias compras (`GET /mis-ventas`, `GET /ventas/{id}`) | Navegar el catálogo público sin iniciar sesión |

---

## Evolución del Alcance

### Etapa 1 — TP Capítulos 1 a 4 (`C-01` a `C-08`) — `[x] Completado`
- Módulos `health`, `editoriales`, `generos`, `autores`, `libros`, `clientes`, `ventas`.
- Modelo inicial de 9 tablas con UNIQUE, CHECK, FK con índices y navegación bidireccional.
- Migraciones Alembic `001` (inicial sin `genero`) y `002` (agrega `genero`).
- Contratos separados, altas con relaciones (`LibroAutor`, `RenglonVenta`), lecturas sin N+1 y aviso con `BackgroundTasks`.

### Etapa 2 — Parcial Capítulos 1 a 6 (`C-09` a `C-17`) — `En curso`
- **Configuración y Ciclo de Vida (Ej. 1)**: `Settings` con `pydantic-settings>=2.0`, `@computed_field` para `DATABASE_URL` (`POSTGRES_*`), sin secretos por defecto; `lifespan` con motor, pool, fábrica de sesiones y hash ficticio en `app.state`; dos grupos de rutas (`abierto` y `protegido`); `/health/ready` devuelve `503` si la base no contesta.
- **Modelo y Migraciones 003 y 004 (Ej. 2)**: Nuevas tablas `usuario`, `asignacion_rol`, `intento_acceso`, `evento_seguridad`, `movimiento_stock`; cambios en `cliente` (`usuario_id` UNIQUE nullable) y `libro` (`borrado_en` + índice único parcial de ISBN vigente); migración `003` autogenerada y migración `004` manual con trigger PostgreSQL de sólo-agregado sobre `movimiento_stock`.
- **Contratos, CRUD y Paginación (Ej. 3)**: `extra="forbid"` en todos los contratos de entrada, nunca exponer `password_hash`, código `204` en baja lógica de libro, envoltorio paginado `{items, total, page, size, pages}` con `422` si `page > pages`.
- **Autenticación y Autorización (Ej. 4 y Ej. 5)**: `bcrypt` con `asyncio.to_thread` y `asyncio.Semaphore`, límite de 72 bytes UTF-8 en contraseñas, JWT en cookie `HttpOnly` (`access_token`), orden estricto de login (límite 5 fallos/60s → `429` con `Retry-After`, verificación constante con hash ficticio, registro en `intento_acceso` con sesión propia), auto-registro en un UoW, vigencia de roles en BD por petición, autoprotección de `ADMIN` y bloqueo por `debe_cambiar_password`.
- **Repositorios, Unit of Work, Stock y Ventas (Ej. 6, Ej. 7 y Ej. 8)**: `BaseRepository[T]`, `SoftDeleteRepository[T]`, `UnitOfWork` por módulo sin cerrar sesión, sesión compartida entre auth y UoW, punto único de escritura de stock, descuento de stock en ventas dentro de un solo UoW, autorización de dueño en `GET /ventas/{id}` y `GET /mis-ventas`, precarga en repositorio sin N+1.
- **Seed, Evidencia y Despliegue en VPS (Ej. 9 y Ej. 10)**: `seed.py` canónico, suite `test/*.http` (`C-01` a `C-16`) + `test/solo_agregado.sql`, y carpeta `despliegue/` con el TP 1-4 dockerizado (`python:3.12-alpine`, no-root, `HEALTHCHECK`, `DEPLOY.md` y evidencias `D-01` a `D-08`).

---

## Fuera de alcance

- **Concurrencia y bloqueo pesimista (Capítulo 7)**: no se evalúa aislamiento ante actualizaciones perdidas concurrentes de stock.
- **Colas de tareas con Redis (Capítulo 8)**: el aviso al registrar una venta sigue usando `BackgroundTasks` en el mismo proceso.
- Frontend web propio, pasarela de pagos real, envío real de correos.

---

## Métricas de éxito (Criterios de Evaluación del Parcial)

| Ejercicio / Criterio | Peso | Qué se evalúa |
|---|---|---|
| **Ej. 1 · Proyecto, configuración y ciclo de vida** | **6 %** | Estructura, `Settings` sin secretos por defecto, motor/fábrica/hash ficticio en `lifespan`, `get_session`, `/health/ready` con `503` |
| **Ej. 2 · Modelos, relaciones y migraciones** | **10 %** | Restricciones, índices únicos parciales (`postgresql_where`), navegación, migraciones 003 (autogenerada) y 004 (a mano), `upgrade`/`downgrade` |
| **Ej. 3 · Contratos y CRUD** | **8 %** | Contratos separados, `extra="forbid"`, códigos (`201`/`204`/`404`/`409`/`422`), ninguna entrada inválida en `500`, PATCH parcial, envoltorio `{items, total, page, size, pages}` |
| **Ej. 4 · Autenticación** | **14 %** | `bcrypt` fuera del bucle (`to_thread`) y con semáforo, límite 72 bytes, orden del login, límite `429` (`Retry-After`), hash ficticio, cookie `HttpOnly` |
| **Ej. 5 · Autorización** | **12 %** | `401` vs `403`, roles vigentes en BD en cada petición, autoprotección `ADMIN`, dos grupos de rutas, cambio obligatorio de contraseña, lo propio (`/mis-ventas`, dueño) |
| **Ej. 6 · Repositorios y Unit of Work** | **16 %** | `BaseRepository[T]` y `SoftDeleteRepository[T]`, `flush` y nunca `commit`, precarga en repositorio, quién crea/abre/confirma/cierra el UoW, operaciones multi-escritura, punto único de stock |
| **Ej. 7 · Integridad: sólo agregado e intento de acceso** | **10 %** | Trigger de sólo-agregado en `movimiento_stock`; `intento_acceso` en su propia sesión/transacción con su comentario obligatorio de 3 puntos; eventos en la misma transacción |
| **Ej. 8 · Lecturas sin N+1 y asincronía** | **6 %** | Consultas fijas en detalle de venta (incluso con libros dados de baja); sin llamadas bloqueantes; aviso en segundo plano visible en consola normal de uvicorn |
| **Ej. 9 · Contenedor: la imagen** | **11 %** | Sobre el TP 1-4 en `despliegue/`: base `python:3.12-alpine` (<100 MB), capas en orden (`--no-cache-dir`), usuario no-root `USER`, sin secretos, `alembic upgrade head` al arrancar, `HEALTHCHECK` |
| **Ej. 10 · Despliegue en el VPS** | **7 %** | TP 1-4 en línea en la URL declarada, `DEPLOY.md` completo, casos `D-01` a `D-08` con su evidencia en `despliegue/evidencia/` |

> **Condiciones bloqueantes de corrección**: un proyecto que no levanta, que no crea su esquema con `alembic upgrade head` sobre una base vacía o que contiene credenciales reales en el repositorio, en la imagen o en el `.zip` no se corrige hasta que se subsane.
