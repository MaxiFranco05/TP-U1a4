# TP-U1a4 y Parcial Cap. 1 a 6 (Librería) — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

---

## Stack Tecnológico

| Capa | Tecnología | Versión mínima |
|---|---|---|
| Lenguaje | Python | 3.12 |
| Framework web | FastAPI (todo `async def`) | 0.111 |
| Modelos y contratos | SQLModel | 0.0.24 |
| ORM / motor | SQLAlchemy 2.0 asincrónico | 2.0 |
| Driver PG | asyncpg | 0.30 |
| Base de datos | PostgreSQL | 16 |
| Migraciones | Alembic (plantilla asincrónica) | 1.13 |
| Configuración | pydantic-settings (`.env` no versionado, sin secretos por defecto) | 2.0 |
| Hash de contraseñas | bcrypt (`asyncio.to_thread` + `asyncio.Semaphore`) | 4.0 |
| Tokens firmados | PyJWT (cookie `HttpOnly` `access_token`) | 2.8 |
| Servidor ASGI | uvicorn (vía `fastapi[standard]`) | — |
| Contenedores y VPS | Docker (`python:3.12-alpine` para despliegue del TP 1-4) | 20.10 |

Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Entender propósito, alcance TP + Parcial y pesos de evaluación (Ej. 1 a Ej. 10) |
| [02_descripcion_general.md](knowledge-base/02_descripcion_general.md) | Stack, arquitectura en 5 capas (`Router → Service → UoW → Repository → Model`) y resumen de la API |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Roles (`ADMIN`, `VENDEDOR`, `CLIENTE`), vigencia en BD, grupos `abierto` y `protegido`, matriz RBAC |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | 14 tablas, ERD, índices únicos parciales (`postgresql_where`), migraciones 001 a 004 y `seed.py` |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas codificadas del Parcial (`RN-01` a `RN-16`), paginación con envoltorio y límite 72 bytes |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias de usuario por épica con criterios de aceptación |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos E2E (sesión compartida, registro UoW, login con sesión propia, stock único, venta atómica, Docker VPS) |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Responsabilidades de cada capa, estructura obligatoria (`parcial/` y `despliegue/`) y variables de entorno |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones de diseño `DD-01` a `DD-14` y supuestos `SU-01` a `SU-03` |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | Definiciones operativas y división equitativa del trabajo entre Maxi, Andrés y Octavio |

---

## Skills Disponibles

| Agente / Bloque | Rol | Skills que carga |
|--------|-----|------------------|
| **Bloque 1 (Maxi) — Cimientos, Modelos/Migraciones y UoW Base** | `Settings`, `lifespan`, modelos de acceso/stock, migraciones 003/004, `BaseRepository`, `SoftDeleteRepository`, `UnitOfWork`, `paginacion` | `postgresql-table-design`, `sqlalchemy-alembic-expert-best-practices-code-review`, `fastapi-templates`, `fastapi` |
| **Bloque 2 (Andrés) — Seguridad, Auth, Roles y Personal** | `bcrypt` (`to_thread` + semáforo), JWT en cookie `HttpOnly`, `get_usuario_actual`, `requiere_rol`, `/auth/*`, `/usuarios/*`, `/eventos` | `fastapi-python`, `fastapi`, `sqlalchemy-alembic-expert-best-practices-code-review` |
| **Bloque 3 (Octavio) — Dominio sobre UoW, Stock, Ventas y Despliegue VPS** | Catálogo con baja lógica, punto único de stock, ventas atómicas en UoW, sin N+1, `seed.py`, casos `C-01..C-16` y Docker/VPS (`D-01..D-08`) | `fastapi-python`, `fastapi`, `postgresql-optimization`, `supabase-postgres-best-practices` |
| **Orquestación** | SDD / OPSX / docs | `kb-creator`, `roadmap-generator`, `agents-md-generator`, `discovery-research`, `skill-registry` |

Cargá la skill correspondiente al contexto ANTES de escribir código.

---

## Roadmap de Changes y Asignación por Integrante

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 17 changes en 8 fases (`Fase 0` a `Fase 3` del TP + `Fase 4` a `Fase 7` del Parcial).
- **Etapa 1 — TP Capítulos 1 a 4 (`C-01` a `C-08`)**: **100% completada (`[x]`)**.
- **Etapa 2 — Parcial Capítulos 1 a 6 (`C-09` a `C-17`)**: **9 changes divididos en 3 bloques equitativos (~33-34% c/u)**:
  - **Maxi (Bloque 1 — ~33%)**: `C-09` (`parcial-config-y-lifespan`) → `C-10` (`modelos-acceso-stock-y-migraciones-003-004`) → `C-11` (`core-repositories-uow-y-paginacion`).
  - **Andrés (Bloque 2 — ~33%)**: `C-12` (`security-bcrypt-jwt-y-dependencies`) → `C-13` (`auth-registro-login-y-cambio-password`) → `C-14` (`usuarios-roles-vigencia-y-eventos`).
  - **Octavio (Bloque 3 — ~34%)**: `C-15` (`catalogo-uow-borrado-logico-y-stock`) → `C-16` (`clientes-y-ventas-uow-stock-y-autorizacion`) → `C-17` (`seed-casos-prueba-y-despliegue-docker`).

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y los archivos de "Leer antes".

---

## Reglas Duras

> Reglas globales ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD, engram): el proyecto las hereda. Acá viven solo las reglas **específicas de este proyecto** + las universales que el global no cubra.

Son contrato; romperlas es un defecto:

- **NUNCA commitear de forma autónoma** → sugerir el commit (mensaje + archivos) y que el usuario lo ejecute.
- **NUNCA poner secretos ni contraseñas por defecto en el código** → `Settings` (`pydantic-settings`) arma `DATABASE_URL` con `@computed_field` desde `POSTGRES_*`; si faltan `POSTGRES_PASSWORD` o `JWT_SECRET`, la aplicación no arranca. Tampoco subir `.env` ni secretos en `alembic.ini` o en la imagen Docker.
- **NUNCA crear el motor ni la fábrica de sesiones al importar un módulo** → crearlos en el `lifespan` de `app/main.py` junto con el hash ficticio de login, guardarlos en `app.state` y cerrar con `dispose()` al apagar.
- **NUNCA llamar a `commit()` dentro de un repositorio** → `add` y `update` en `BaseRepository` / `SoftDeleteRepository` hacen únicamente `flush()`. Sólo el `UnitOfWork` confirma (`commit()`) o revierte (`rollback()`).
- **NUNCA construir el `UnitOfWork` adentro del servicio ni cerrar la sesión en el `UnitOfWork`** → el router lo construye por dependencia y se lo pasa al servicio sin abrir; el servicio lo abre con `async with uow:`; la sesión la cierra `get_session`.
- **NUNCA usar dos sesiones distintas en una petición autenticada** → `get_usuario_actual`, `requiere_rol` y el `UnitOfWork` reciben la **misma sesión** de `Depends(get_session)`. La **única excepción** en todo el sistema es el registro en `intento_acceso` durante el login, que usa su propia sesión y transacción (con el comentario obligatorio de 3 puntos: qué hace distinto, por qué no comparte transacción y su costo).
- **NUNCA ejecutar `bcrypt` en el bucle de eventos ni dentro de una transacción abierta** → siempre en `asyncio.to_thread` bajo `asyncio.Semaphore`, y calculando el hash **antes** de abrir `async with uow:`. Limitar toda contraseña de entrada a **72 bytes UTF-8** (`422`).
- **NUNCA enviar el JWT en el cuerpo del login ni leerlo de `Authorization: Bearer`** → viaja exclusivamente en la cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`, `Secure` configurable).
- **NUNCA decidir permisos con los roles del token** → `requiere_rol` consulta `asignacion_rol` vigentes en la base en cada petición (RN-04).
- **NUNCA escribir `libro.stock` fuera del punto único de escritura de stock** → sólo cambia mediante movimientos en el alta con `stock_inicial`, la reposición y la venta (RN-11), manteniendo `libro.stock == SUM(movimiento_stock.cantidad)`. Prohibido editar `stock` por `PATCH` (`extra="forbid"` → `422`).
- **NUNCA modificar ni borrar filas de `movimiento_stock` ni de `asignacion_rol`** → `movimiento_stock` está protegido por el disparador de sólo-agregado (Migración 004, RN-12) y revocar un rol sólo escribe `revocada_en`.
- **NUNCA aceptar campos no declarados en contratos de entrada ni exponer `password_hash`** → todos los esquemas de entrada llevan `extra="forbid"` y ninguna respuesta incluye `password_hash`.
- **NUNCA devolver texto interno de la base ni trazas en errores** → traducir `IntegrityError` a mensaje propio + `409`/`422` (RN-15). Ninguna entrada inválida termina en un `500`.
- **NUNCA verificar unicidad con consultas previas antes de insertar cuando la base lo garantiza** → delegar en `UNIQUE`, índice único parcial (`postgresql_where`) y `FOREIGN KEY`, respondiendo `409`.
- **NUNCA usar `float` para dinero ni carga perezosa en relaciones** → dinero siempre con `Decimal` (`NUMERIC`) y toda relación leída se precarga (`joinedload` / `selectinload`) **adentro del método del repositorio**.
- **NUNCA crear el esquema con `create_all` ni renombrar/quitar tablas o columnas obligatorias** → esquema exclusivamente con Alembic (leer y comentar cada migración nueva antes de aplicarla).
- **NUNCA armar SQL concatenando texto** → parámetros ligados siempre.

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)        → entender el dominio y las reglas RN-01..RN-16
2. Identificar el change en CHANGES.md           → respetar dependencias y bloque asignado
3. /opsx:propose C-NN-nombre                     → proposal + design + specs + tasks
4. Implementar las tasks (cargando skills)       → respetando las reglas duras y TDD
5. /opsx:archive C-NN-nombre + marcar [x]        → cerrar el change
```

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
