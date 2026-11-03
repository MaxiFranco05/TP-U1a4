# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **Librería (TP Capítulos 1 a 4 + Parcial Capítulos 1 a 6: Acceso, Transacciones y Despliegue en el VPS)**.
> Cada change es atómico: un integrante/agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

> **Política de commits (restricción vigente del usuario)**: al final de cada change hay un
> `Commit sugerido`. Es solo una sugerencia explícita de cuándo commitear y con qué mensaje.
> El flujo **nunca commitea de forma autónoma**: el agente propone el commit y el usuario lo ejecuta.

---

## Cómo usar este documento

1. Identificar el change a implementar (verificar que sus dependencias están completadas `[x]`).
2. Leer los docs de la knowledge-base indicados en "Leer antes".
3. Ejecutar `/opsx:propose <nombre-del-change>`.
4. Al terminar el change, archivarlo con `/opsx:archive <nombre-del-change>`.
5. Marcar el checkbox `[x]` en este archivo.

---

## Árbol de dependencias

```
ETAPA 1 — TP Capítulos 1 a 4 (100% Completada [x])
C-01 foundation-setup [x]
  └── C-02 core-models-migracion-001 [x]
        ├── C-03 generos-migracion-002 [x]
        │     └── C-04 catalogo-crud [x] ───────┐
        ├── C-05 clientes-perfil [x] ───────────┼── C-06 ventas-alta-riesgo [x]
                                                │     └── C-07 lecturas-sin-nplusuno [x]
                                                │           └── C-08 seed-entrega-evidencia [x]
                                                │
ETAPA 2 — Parcial Capítulos 1 a 6 (C-09 a C-17) ▼
C-08 [x]
  └── C-09 parcial-config-y-lifespan                        [Bloque 1: Maxi]
        ├── C-10 modelos-acceso-stock-y-migraciones-003-004 [Bloque 1: Maxi]
        └── C-11 core-repositories-uow-y-paginacion         [Bloque 1: Maxi]
              │
              ├── C-12 security-bcrypt-jwt-y-dependencies [x]   [Bloque 2: Andrés]
              │     └── C-13 auth-registro-login-y-cambio-password [Bloque 2: Andrés]
              │           ├── C-14 usuarios-roles-vigencia-y-eventos [Bloque 2: Andrés]
              │           │
              │           └── C-15 catalogo-uow-borrado-logico-y-stock [Bloque 3: Octavio]
              │                 └── C-16 clientes-y-ventas-uow-stock-y-autorizacion [Bloque 3: Octavio]
              │                       └── C-17 seed-casos-prueba-y-despliegue-docker [Bloque 3: Octavio]
```

### Paralelismo por fase (Etapa 1 TP + Etapa 2 Parcial)

> Cada "gate" es un punto de sincronización. Los changes dentro de un grupo pueden ejecutarse en paralelo.

```
── ETAPA 1: TP Capítulos 1 a 4 (COMPLETADA) ──────────────────────────
GATE 0..6: C-01 ✓ → C-02 ✓ → (C-03 + C-05) ✓ → C-04 ✓ → C-06 ✓ → C-07 ✓ → C-08 ✓

── ETAPA 2: Parcial Capítulos 1 a 6 (NUEVA) ──────────────────────────
GATE 7: C-08 ✓
  → C-09 parcial-config-y-lifespan                          [Maxi]
  → (En paralelo opcional: adelanto de Dockerfile/DEPLOY en `despliegue/` de C-17 sobre TP C-08)

GATE 8: C-09 ✓
  → C-10 modelos-acceso-stock-y-migraciones-003-004         [Maxi]
  → C-11 core-repositories-uow-y-paginacion                 [Maxi]

GATE 9: C-10 + C-11 ✓
  → C-12 security-bcrypt-jwt-y-dependencies                 [Andrés]

GATE 10: C-12 ✓
  → C-13 auth-registro-login-y-cambio-password              [Andrés]
  → C-15 catalogo-uow-borrado-logico-y-stock                [Octavio — puede iniciar en paralelo con C-13]

GATE 11: C-13 ✓ (+ C-15 ✓)
  → C-14 usuarios-roles-vigencia-y-eventos                  [Andrés]
  → C-16 clientes-y-ventas-uow-stock-y-autorizacion         [Octavio]

GATE 12: C-14 + C-16 ✓
  → C-17 seed-casos-prueba-y-despliegue-docker              [Octavio]
```

### Camino crítico completo (15 changes secuenciales mínimos)

```
[TP: C-01 → C-02 → C-03 → C-04 → C-06 → C-07 → C-08]
  → C-09 → C-10 → C-11 → C-12 → C-13 → C-15 → C-16 → C-17
```

---

## División Equitativa del Parcial entre los 3 Integrantes (`C-09` a `C-17`)

Los **9 changes del Parcial (`C-09` a `C-17`)** se dividen en **3 bloques continuos de 3 changes por integrante**, balanceando exactamente la complejidad técnica y los puntos de evaluación de la consigna (~33–34 puntos sobre 100 cada uno):

| Integrante | Bloque / Rol en el Parcial | Changes asignados | Ejercicios de la consigna que resuelve | Peso equivalente |
|---|---|---|---|---|
| **Maxi** | **Bloque 1 — Cimientos, Modelos/Migraciones y Arquitectura UoW** | `C-09`, `C-10`, `C-11` (3 changes) | Ej. 1 (Config/Lifespan 6%), Ej. 2 (Modelos + Migraciones 003 y 004 trigger 10%), Ej. 3 base (`paginacion.py` 4%), Ej. 6 base (`BaseRepository`, `SoftDeleteRepository`, `UnitOfWork` 8%), Ej. 7 base (trigger sólo-agregado 5%) | **~33 %** (33 pts) |
| **Andrés** | **Bloque 2 — Seguridad, Autenticación, Autorización y Personal** | `C-12`, `C-13`, `C-14` (3 changes) | Ej. 4 (Autenticación `bcrypt` + `to_thread` + semáforo + límite 429 + hash ficticio + cookie 14%), Ej. 5 (Autorización 401/403 + vigencia en BD + autoprotección + bloqueo clave 12%), Ej. 6/7 en `usuarios` (UoW registro RN-02, `intento_acceso` sesión propia con comentario, `evento_seguridad` RN-16 7%) | **~33 %** (33 pts) |
| **Octavio** | **Bloque 3 — Dominio en UoW (Catálogo/Stock/Ventas), Seed y Despliegue VPS** | `C-15`, `C-16`, `C-17` (3 changes) | Ej. 3/6/8 aplicados a Catálogo, Clientes y Ventas (punto único de stock RN-11, baja lógica RN-13, venta atómica RN-10, dueño RN-14, sin N+1 16%), Ej. 9 (Imagen Docker `python:3.12-alpine` 11%) y Ej. 10 (Despliegue en VPS + `seed.py` + `C-01..C-16` y `D-01..D-08` 7%) | **~34 %** (34 pts) |

### Plan de ejecución por pasos (Parcial `C-09` a `C-17`)

```
Paso │ Maxi (Bloque 1: Base y Datos)        │ Andrés (Bloque 2: Auth y Roles)     │ Octavio (Bloque 3: Dominio y VPS)
─────┼──────────────────────────────────────┼─────────────────────────────────────┼─────────────────────────────────────────
  1  │ C-09 parcial-config-y-lifespan       │ —                                   │ (Preparación carpeta `despliegue/` TP)
  2  │ C-10 modelos-acceso-stock-y-mig-03-04│ —                                   │ —
  3  │ C-11 core-repositories-uow-y-paginac.│ —                                   │ —
  4  │ —                                    │ C-12 security-bcrypt-jwt-y-deps     │ —
  5  │ —                                    │ C-13 auth-registro-login-y-password │ C-15 catalogo-uow-borrado-logico-y-stock
  6  │ —                                    │ C-14 usuarios-roles-vigencia-eventos│ C-16 clientes-y-ventas-uow-stock-y-auth
  7  │ —                                    │ —                                   │ C-17 seed-casos-prueba-y-despliegue-vps
```

---

## FASE 0 — Cimientos y modelo core (TP Capítulos 1 a 4 — Completada)

> C-01 y C-02 son estrictamente secuenciales. Al cerrar la fase se sugiere el segundo commit del proyecto.

### [C-01] `foundation-setup`
- **Estado**: `[x]` completado
- **Scope**: Scaffolding completo + infraestructura base (sin modelos de dominio)
  - Estructura: `app/main.py` (app, `lifespan` crea motor async + fábrica de sesiones en `app.state`, cierra motor al apagar), `app/core/config.py` (`DATABASE_URL` desde entorno), `app/core/database.py` (motor SQLAlchemy 2.0 async + asyncpg, `get_session` con `Depends()`, `expire_on_commit=False`), esqueleto `app/modules/health/` y carpetas de los 7 módulos
  - `GET /health/live` → `{"estado": "vivo"}` 200 sin tocar la base; `GET /health/ready` → `SELECT 1`, falla si la base no responde (RN-12: sin traza interna)
  - `requirements.txt` (FastAPI>=0.111, SQLModel>=0.0.24, SQLAlchemy 2.0 async, asyncpg>=0.30, Alembic>=1.13, python-dotenv, `fastapi[standard]`/uvicorn), `.env` (no versionado) + `env.example` (`DATABASE_URL`, `SQL_ECHO`), `compose.yaml` PG16 para dev (PA-04: comodidad local, documentar que no es parte de la entrega)
  - Alembic inicializado con plantilla asincrónica en `migrations/` (sin versiones aún); `alembic.ini` sin contraseñas
  - Resuelve PA-01 (proveer Python 3.12 en paralelo a 3.14 antes de crear el venv) y deja asentada PA-02 (VPS/Easypanel solo deploy opcional post-entrega, fuera de la corrección)
  - Tests: live responde sin base; ready OK con base y error sin base
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-01: foundation + healthchecks"`
- **Dependencias**: ninguna
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/01_vision_y_objetivos.md` (alcance v1.0 y bloqueantes de corrección)
  - `knowledge-base/02_descripcion_general.md` §Stack
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios
  - `knowledge-base/10_preguntas_abiertas.md` §PA-01, PA-02, PA-04

---

### [C-02] `core-models-migracion-001`
- **Estado**: `[x]` completado
- **Scope**: Modelos del dominio (todo menos `genero`, que llega en C-03) + primera migración
  - Modelos: `Editorial`, `Autor`, `Libro` (**sin** `genero_id` todavía), `LibroAutor` (objeto de asociación: PK (`libro_id`, `autor_id`), `rol` en (autor, coautor, traductor, ilustrador), `orden >= 1`, navegación `libro.autorias[i].autor`), `Cliente`, `PerfilCliente`, `Venta`, `RenglonVenta`
  - Dinero siempre `Decimal` (NUMERIC 10,2 / 12,2); CHECK `precio > 0`, `stock >= 0`, `cantidad > 0`, `precio_unitario > 0`, `total >= 0`; UNIQUE `isbn`, `email`, `editorial.nombre`, `perfil_cliente.cliente_id`; `Cliente.perfil` devuelve objeto (no lista)
  - Toda FK con índice explícito + `Relationship(back_populates=...)` en ambos extremos
  - Migración 001 autogenerada (`alembic revision --autogenerate`) **leída** (comentario en el archivo si se corrigió un diff espurio); `upgrade head` en base vacía verificado
  - Tests: constraints en base (ISBN/email duplicado rechazan, CHECK precio/stock rechazan)
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-02: modelos core + migracion 001 (sin genero)"`
- **Dependencias**: C-01
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Entidades (editorial, autor, libro, libro_autor, cliente, perfil_cliente, venta, renglon_venta)
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Catálogo (RN-01, RN-03) y §Dominio: Clientes (RN-02, RN-09)
  - `knowledge-base/07_flujos_principales.md` §Flujo 5: Migración del esquema
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-03, DD-04, DD-06

---

## FASE 1 — Catálogo (TP Capítulos 1 a 4 — Completada)

> C-03 desbloquea C-04. C-05 (FASE 2) corre en paralelo con C-03 desde GATE 2.

### [C-03] `generos-migracion-002`
- **Estado**: `[x]` completado
- **Scope**: Entidad `genero` + segunda migración (cierra US-040)
  - Modelo `Genero` (`nombre` UNIQUE) + `Libro.genero_id` nullable (FK con índice, agregación opcional)
  - Endpoints: CRUD paginado de géneros (201/404/409/422, PATCH `exclude_unset`) + `GET /generos/{id}/libros` paginado (RN-10: `limit` 1–100/def. 20, `offset >= 0` → 422 si se viola)
  - Migración 002 autogenerada (agrega `genero` + `libro.genero_id`); verificada `downgrade -1` + `upgrade head` en base vacía; archivo leído y comentado si se corrigió
  - Tests: CRUD género, `downgrade/upgade` redondo, listado por género pagina
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-03: generos + migracion 002"`
- **Dependencias**: C-02
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §genero y §libro (`genero_id` nullable)
  - `knowledge-base/06_funcionalidades.md` §US-010 y §US-040
  - `knowledge-base/05_reglas_de_negocio.md` §RN-10
  - `knowledge-base/07_flujos_principales.md` §Flujo 5: Migración del esquema

---

### [C-04] `catalogo-crud`
- **Estado**: `[x]` completado
- **Scope**: CRUD de catálogo + alta de libro con autorías + consultas con filtro (US-010 a US-013)
  - CRUD paginado de editoriales (+ `GET /editoriales/{id}/libros`) y autores (+ `GET /autores/{id}/libros` exponiendo `rol` y `orden`); PATCH parcial con `exclude_unset`
  - `POST /libros/` con `{editorial_id, genero_id, autores: [{autor_id, rol, orden}]}` → 201 con detalle completo (editorial, género, autores vía `libro.autorias[i].autor`); editorial/autor inexistente → 409 **sin `if` previo** (la base rechaza la FK); ISBN repetido → 409; cuerpo inválido → 422
  - `GET /libros/` paginado con `titulo` (case-insensitive, parámetro ligado — C-08 `' OR '1'='1` → 200 lista vacía) y `genero_id`; `GET /libros/{id}` con editorial, género y autores
  - Traducción de `IntegrityError` a mensaje propio + 409/422 en services (RN-12: nunca texto interno de la base); DTO `Create`/`Update`/`Read` separados, altas sin `id`
  - Tests `.http`: C-01 (422 sin ejecutar handler), C-04 (409 por FK), paginación 422, filtro inyección → 200 vacía
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-04: CRUD catalogo + alta de libro con autorias"`
- **Dependencias**: C-02, C-03
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-010, US-011, US-012, US-013
  - `knowledge-base/07_flujos_principales.md` §Flujo 2: Alta de libro con autores
  - `knowledge-base/04_modelo_de_datos.md` §libro y §libro_autor
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Catálogo y §Excepciones globales
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-03, DD-04

---

## FASE 2 — Clientes y ventas (TP Capítulos 1 a 4 — Completada)

> C-05 puede arrancar en GATE 2 en paralelo con C-03. C-06 requiere C-04 + C-05 y se recomienda en par (riesgo RN-04..RN-07).

### [C-05] `clientes-perfil`
- **Estado**: `[x]` completado
- **Scope**: CRUD de clientes + perfil único + historial (US-020, US-021)
  - `POST/GET/PATCH /clientes/` paginado; `GET /clientes/{id}` con perfil (objeto, no lista); email repetido → 409 (RN-02)
  - `POST /clientes/{id}/perfil` → segundo perfil 409 (RN-09, C-03 de los casos); cliente inexistente → 404/409 según convención FK
  - `GET /clientes/{id}/ventas` → 200 con historial; cliente inexistente → 404
  - Paginación RN-10 en listados; errores traducidos RN-12
  - Tests `.http`: C-02 (email 409), C-03 (segundo perfil 409), detalle con perfil objeto
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-05: clientes + perfil unico"`
- **Dependencias**: C-02
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-020 y §US-021
  - `knowledge-base/04_modelo_de_datos.md` §cliente y §perfil_cliente
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Clientes (RN-02, RN-09) y §RN-10
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados (DTO, service con sesión)

---

### [C-06] `ventas-alta-riesgo`
- **Estado**: `[x]` completado
- **Scope**: Alta de venta con renglones + aviso en segundo plano (US-030 — riesgo principal)
  - `POST /ventas/` con `{cliente_id, renglones: [{libro_id, cantidad}]}` (DTO anidado, RN-04; precio/total/fecha **no** viajan en el DTO)
  - Validación DTO: ≥ 1 renglón y sin libros repetidos → 422 (RN-05); service lee cada `Libro`, **copia** `precio_unitario` (RN-06), calcula subtotales y `total` Decimal (RN-07); agrega renglones a `venta.renglones` (composición) y persiste en una transacción
  - Cliente/libro inexistente → 409 vía FK (C-05 de los casos, sin `if` previo); **sin PATCH** de ventas (RN-08)
  - `BackgroundTasks`: aviso de comprobante (`asyncio.sleep(0.5)` + log), respuesta 201 **sin esperar** el aviso; handlers 100% `async` sin bloqueos
  - Respuesta 201 con cliente y renglones (precio copiado, subtotal, total)
  - Tests `.http`: C-05 (409), C-06 (201 con precios y total correctos), 422 (vacía/repetidos)
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-06: alta de venta con renglones + background"`
- **Dependencias**: C-04, C-05
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-030
  - `knowledge-base/07_flujos_principales.md` §Flujo 3: Alta de venta con renglones
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Ventas (RN-04 a RN-08)
  - `knowledge-base/04_modelo_de_datos.md` §venta y §renglon_venta
  - `knowledge-base/08_arquitectura_propuesta.md` §Background task y §Dependencia por petición

---

## FASE 3 — Rendimiento y entrega (TP Capítulos 1 a 4 — Completada)

> C-07 deja la evidencia de consultas fijas; C-08 cierra con seed + `.http` + README. Commit final sugerido al terminar C-08.

### [C-07] `lecturas-sin-nplusuno`
- **Estado**: `[x]` completado
- **Scope**: Eager loading declarado + consultas de ventas + evidencia C-07 (US-013 detalle, US-031)
  - Una sola consulta con carga anticipada por tipo: `joinedload` para relaciones a uno (editorial, género, cliente), `selectinload` para colecciones (autorías, renglones); cero lazy loading; número de queries fijo aunque crezcan autores/renglones
  - `GET /ventas/` paginado + `GET /ventas/{id}` con cliente y renglones; `GET /libros/{id}` ya creado en C-04 se endurece aquí con la estrategia de carga
  - `SQL_ECHO` configurable para mostrar consultas en consola (evidencia: misma cantidad de queries con 1 o N autores/renglones)
  - Tests `.http`: C-07 (evidencia documentada en consola/README)
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-07: lecturas sin N+1 + evidencia"`
- **Dependencias**: C-04, C-06
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 4: Detalle sin N+1
  - `knowledge-base/06_funcionalidades.md` §US-013 y §US-031
  - `knowledge-base/08_arquitectura_propuesta.md` §Eager loading declarado y §Variables de entorno (`SQL_ECHO`)
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-05

---

### [C-08] `seed-entrega-evidencia`
- **Estado**: `[x]` completado
- **Scope**: Seed reproducible + suite `.http` + README final (US-040, US-041 — cierre entregable)
  - Script/comando de seed con estado conocido: editoriales, géneros, autores, libros con autorías, un cliente con perfil y una venta de ejemplo (PA-03: fijar contenido exacto para que los `.http` sean reproducibles)
  - `test/*.http` con C-01 a C-08 comentados (casos mínimos de la consigna); `requirements.txt` y `env.example` finales; verificación de punta a punta desde cero: base vacía → `alembic upgrade head` → seed → `.http` en verde; sin credenciales en el repo (bloqueante)
  - `README.md`: pasos desde cero + evidencia C-07 + decisión PA-02 (VPS/Easypanel como deploy opcional de muestra, fuera de la corrección) y nota PA-04 (`compose.yaml` solo dev)
  - Tests: flujo exacto del corrector (SU-03) reproducido en local
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-08: seed + http + README de entrega"`
- **Dependencias**: C-07 (transitivamente C-01 a C-06)
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-040 y §US-041
  - `knowledge-base/01_vision_y_objetivos.md` §Alcance v1.0 y §Métricas de éxito (pesos y bloqueantes)
  - `knowledge-base/02_descripcion_general.md` §API REST (códigos 201/404/409/422)
  - `knowledge-base/10_preguntas_abiertas.md` §PA-02, PA-03, PA-04
  - `knowledge-base/09_decisiones_y_supuestos.md` §SU-02, SU-03

---

## FASE 4 — Cimientos del Parcial, Modelos/Migraciones 003-004 y Capa Base UoW (Bloque 1: Maxi)

> Esta fase construye la base arquitectónica y de datos sobre la que se apoyan todos los cambios del Parcial (`C-09`, `C-10`, `C-11`). Responsable: **Maxi**.

### [C-09] `parcial-config-y-lifespan`
- **Responsable**: **Maxi** (Bloque 1 — Change 1/3)
- **Estado**: `[x]` completado
- **Scope**: Configuración tipada con `pydantic-settings`, ciclo de vida con hash ficticio y dos grupos de rutas (Ej. 1 — 6%)
  - `requirements.txt` y `env.example`: agregar `pydantic-settings>=2.0`, `bcrypt>=4.0`, `PyJWT>=2.8`; documentar `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT`, `JWT_SECRET`, `JWT_EXPIRATION_SECONDS`, `BCRYPT_ROUNDS`, `COOKIE_SECURE`, `DB_POOL_SIZE`, `SQL_ECHO` sin secretos reales.
  - `app/core/config.py`: clase `Settings(BaseSettings)` que lee del entorno / `.env` y arma `DATABASE_URL` con `@computed_field` (`postgresql+asyncpg://...`). Ni `POSTGRES_PASSWORD` ni `JWT_SECRET` tienen valor por defecto en el código (si faltan, la aplicación no arranca).
  - `app/core/database.py` y `lifespan` en `app/main.py`: funciones que crean el motor asincrónico (con el tamaño del pool declarado en `Settings`) y la fábrica de sesiones (`expire_on_commit=False`), llamadas desde el `lifespan` y guardadas en `app.state` (nunca al importar el módulo). El `lifespan` calcula además **una sola vez** el hash ficticio del login (`app.state.dummy_password_hash`) y al apagar cierra el motor con `await engine.dispose()`.
  - `app/modules/health/router.py`: dejar sólo `router.py` en `health`; `GET /health/live` devuelve `200` sin tocar la base y `GET /health/ready` ejecuta `SELECT 1` y responde `200` o **`503`** si la base no contesta.
  - `app/main.py`: estructurar los **dos grupos de rutas** (`abierto` y `protegido`) para montar una sola vez el control de cambio obligatorio de contraseña en el grupo protegido.
  - Tests: fallo de arranque si falta `JWT_SECRET` o `POSTGRES_PASSWORD`; `/health/live` 200; `/health/ready` 200 con base y 503 sin base; `dummy_password_hash` presente en `app.state`.
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-09: Settings pydantic-settings, lifespan con hash ficticio y health 503"`
- **Dependencias**: C-08
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/01_vision_y_objetivos.md` §Métricas de éxito (Ej. 1)
  - `knowledge-base/02_descripcion_general.md` §Stack tecnológico y §Decisiones estructurales clave
  - `knowledge-base/07_flujos_principales.md` §Flujo 1: Arranque (`lifespan`), Sesión Compartida y Unit of Work
  - `knowledge-base/08_arquitectura_propuesta.md` §Variables de Entorno

---

### [C-10] `modelos-acceso-stock-y-migraciones-003-004`
- **Responsable**: **Maxi** (Bloque 1 — Change 2/3)
- **Estado**: `[x]` completado
- **Scope**: Nuevos modelos (`usuarios`, `movimiento_stock`), cambios en `cliente` y `libro`, y migraciones Alembic 003 y 004 (Ej. 2 — 10% y Ej. 7 trigger — 5%)
  - `app/modules/usuarios/models.py`:
    - `Usuario` (`usuario`): `id`, `email` (`UNIQUE`), `nombre`, `password_hash`, `activo` (`bool`), `debe_cambiar_password` (`bool`).
    - `AsignacionRol` (`asignacion_rol`): `id`, `usuario_id` (FK a `usuario.id` con índice), `rol` (`CHECK rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')`), `desde` (`timestamptz`), `vence_en` (`timestamptz`, nullable), `revocada_en` (`timestamptz`, nullable), `otorgada_por` (FK a `usuario.id` con índice, nullable). **Índice único parcial** `(usuario_id, rol) WHERE revocada_en IS NULL` (`postgresql_where`, RN-03).
    - `IntentoAcceso` (`intento_acceso`): `id`, `cuando` (`timestamptz`), `email`, `ip`, `exito` (`bool`). Índice compuesto `(email, ip, cuando)`. Sin FK.
    - `EventoSeguridad` (`evento_seguridad`): `id`, `cuando` (`timestamptz`), `actor` (`str`), `accion` (`str`). Sin FK.
  - `app/modules/libros/models.py`:
    - `MovimientoStock` (`movimiento_stock`): `id`, `libro_id` (FK con índice), `venta_id` (FK a `venta.id` con índice, nullable), `usuario_id` (FK a `usuario.id` con índice), `cantidad` (`int`, `CHECK cantidad <> 0`), `motivo` (`str`), `cuando` (`timestamptz`).
    - `Libro` (`libro`): agregar `borrado_en` (`timestamptz`, nullable); reemplazar el `UNIQUE` común de `isbn` por el **índice único parcial** `(isbn) WHERE borrado_en IS NULL` (`postgresql_where`, RN-01, RN-13); mantener `CHECK precio > 0` y `CHECK stock >= 0`.
  - `app/modules/clientes/models.py`:
    - `Cliente` (`cliente`): agregar `usuario_id` (FK a `usuario.id` con índice, nullable, `UNIQUE`); relación `Cliente.usuario` y `Usuario.cliente` bidireccional donde `Cliente.usuario` devuelve un objeto y no una lista (`uselist=False`).
  - **Migración 003**: generada con `alembic revision --autogenerate`, leída antes de aplicarla y con comentario explicativo en el archivo; trae las tablas nuevas y los cambios en `cliente` y `libro`.
  - **Migración 004**: escrita **a mano**, leída y comentada; instala en `upgrade()` la función PL/pgSQL y el disparador (`TRIGGER`) sobre `movimiento_stock` que rechaza cualquier `UPDATE` o `DELETE` (RN-12), y los elimina en `downgrade()`.
  - Verificación completa: `alembic upgrade head` en base vacía → `alembic downgrade base` → `alembic upgrade head`.
  - Tests: índices únicos parciales (`isbn` vigente vs dado de baja, `asignacion_rol` abierta vs revocada), `Cliente.usuario` objeto, y rechazo de `UPDATE`/`DELETE` sobre `movimiento_stock` (`C-14`).
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-10: modelos acceso y stock + migraciones 003 (autogenerate) y 004 (trigger append-only)"`
- **Dependencias**: C-09
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Detalle de Entidades y Restricciones y §Historial de Migraciones Alembic
  - `knowledge-base/05_reglas_de_negocio.md` §RN-01, RN-03, RN-12, RN-13
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-11

---

### [C-11] `core-repositories-uow-y-paginacion`
- **Responsable**: **Maxi** (Bloque 1 — Change 3/3)
- **Estado**: `[x]` completado
- **Scope**: Clases base `BaseRepository[T]`, `SoftDeleteRepository[T]`, `UnitOfWork` y envoltorio de paginación (Ej. 3 paginación y Ej. 6 base)
  - `app/core/repository.py`:
    - `BaseRepository[T]`: recibe en su constructor `session: AsyncSession` y `model_cls: type[T]`. Ofrece `get_by_id`, `get_all`, `count`, `add`, `update` y `delete`. `add` y `update` ejecutan `await self.session.flush()`, **nunca `commit()`**.
    - `SoftDeleteRepository[T](BaseRepository[T])`: filtra por defecto los registros con `borrado_en IS NULL` en `get_by_id`, `get_all` y `count`, y agrega `get_by_id_including_deleted` y `soft_delete` (marca `borrado_en = now()` + `flush()`), que no existen en `BaseRepository`.
  - `app/core/unit_of_work.py`:
    - `UnitOfWork` base como gestor de contexto asincrónico (`__aenter__` / `__aexit__`): confirma (`await self.session.commit()`) al salir normalmente del bloque, revierte (`await self.session.rollback()`) si se sale con excepción y **nunca cierra la sesión** (porque la creó `get_session`).
  - `app/core/paginacion.py`:
    - Parámetros de consulta `page: int = Query(1, ge=1)` y `size: int = Query(20, ge=1, le=100)`.
    - Esquema genérico / envoltorio `{items, total, page, size, pages}` y función de cálculo de páginas: con `total == 0` hay `1` página vacía (`pages = 1`); pedir `page > pages` responde **`422`** con el mensaje `«La página {page} no existe: hay {pages}»`.
  - Tests unitarios/integración de `BaseRepository`, `SoftDeleteRepository`, `UnitOfWork` (commit en éxito, rollback en excepción, sesión sigue abierta) y `paginacion.py` (`total=0` → `pages=1`, `page > pages` → `422`).
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-11: BaseRepository, SoftDeleteRepository, UnitOfWork base y paginacion"`
- **Dependencias**: C-09, C-10
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Capas y Responsabilidades (`Repository`, `Unit of Work`, `paginacion.py`)
  - `knowledge-base/05_reglas_de_negocio.md` §Reglas Transversales Adicionales (Paginación con envoltorio)
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-07, DD-08

---

## FASE 5 — Identidad, Autenticación, Autorización y Administración de Personal (Bloque 2: Andrés)

> Esta fase implementa toda la seguridad del sistema (`bcrypt`, JWT en cookie `HttpOnly`, dependencias con sesión compartida, registro/login/cambio de clave y gestión de roles con vigencia y autoprotección). Responsable: **Andrés**.

### [C-12] `security-bcrypt-jwt-y-dependencies`
- **Responsable**: **Andrés** (Bloque 2 — Change 1/3)
- **Estado**: `[x]` completado
- **Scope**: Criptografía `bcrypt` fuera del bucle con semáforo, JWT y dependencias de autenticación/autorización con sesión compartida (Ej. 4 base y Ej. 5 base)
  - `app/core/security.py`:
    - Hash y verificación de contraseñas con `bcrypt` usando el costo `settings.BCRYPT_ROUNDS`, ejecutados siempre fuera del bucle de eventos con `asyncio.to_thread` y protegidos bajo un `asyncio.Semaphore` global.
    - Función validadora reutilizable para contratos Pydantic/SQLModel que verifica `len(v.encode("utf-8")) <= 72` (son bytes UTF-8, no caracteres: una `«ñ»` ocupa 2 bytes) → lanza `ValueError` para que FastAPI responda `422` y nunca `500`.
    - Emisión y verificación de tokens JWT (`PyJWT`) firmados con `settings.JWT_SECRET`, incluyendo `sub` (id del usuario), `exp` y `roles` vigentes al emitirlo.
  - `app/core/dependencies.py`:
    - `get_usuario_actual`: lee el token **exclusivamente** de `request.cookies.get("access_token")` (ignora `Authorization: Bearer`). Recibe `session: AsyncSession = Depends(get_session)` (la misma sesión que usará el Unit of Work de la petición). Responde `401` si no hay cookie, si el token es inválido o venció, o si el usuario no existe o tiene `activo == False` (`C-03`, `C-06`).
    - Dependencia de control de cambio obligatorio de contraseña para montar una sola vez en el **grupo protegido** de `app/main.py`: si `usuario_actual.debe_cambiar_password` es `True`, responde `403` (`RN-06`, `C-09`).
    - `requiere_rol(*roles_permitidos)`: recibe la misma sesión de la petición y consulta en `asignacion_rol` los roles vigentes del usuario en la base (`revocada_en IS NULL` y `(vence_en IS NULL OR vence_en > now())`, `RN-04`). Si no posee ninguno de los roles requeridos, responde `403` (`C-06`, `C-07`).
  - Tests: validación 72 bytes UTF-8 (`422`), `get_usuario_actual` (`401` sin cookie o con Bearer), `requiere_rol` (`403` en BD aunque el token diga que tenía el rol), bloqueo `403` por `debe_cambiar_password` en grupo protegido.
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-12: security (bcrypt to_thread + semaforo, JWT) y dependencies con sesion compartida"`
- **Dependencias**: C-09, C-10, C-11
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §Modelo de Roles y Vigencia en Base de Datos y §Dos Grupos de Rutas
  - `knowledge-base/05_reglas_de_negocio.md` §RN-04, RN-06 y §Límite de 72 bytes en contraseñas
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones Aplicados (`bcrypt`, Sesión unificada)
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-08, DD-10, DD-12

---

### [C-13] `auth-registro-login-y-cambio-password`
- **Responsable**: **Andrés** (Bloque 2 — Change 2/3)
- **Estado**: `[x]` completado
- **Scope**: Repositorios/UoW de `usuarios` y endpoints de `/auth` (`registro`, `login`, `logout`, `yo`, `cambiar-password`) (Ej. 4, Ej. 6 RN-02/RN-16 y Ej. 7 `intento_acceso`)
  - `app/modules/usuarios/repository.py` y `app/modules/usuarios/unit_of_work.py`:
    - Repositorios para `Usuario`, `AsignacionRol`, `IntentoAcceso` y `EventoSeguridad`; `UsuariosUnitOfWork` que compone también `ClienteRepository` para el auto-registro con la misma sesión.
  - `app/modules/usuarios/schemas.py`: contratos de entrada con `extra="forbid"` y límite de 72 bytes UTF-8 en todas las contraseñas; ningún contrato de salida incluye `password_hash`.
  - `POST /auth/registro` (grupo abierto, `201, 409, 422`):
    - Calcula el hash `bcrypt` **antes** de abrir el UoW; dentro de `async with uow:` crea `Usuario`, `AsignacionRol(rol="CLIENTE")` y `Cliente(usuario_id=usuario.id)` (RN-02). Si el correo ya existe en `usuario` o en `cliente`, revierte todo y responde `409` con mensaje propio sin apropiarse de la ficha existente ni dejar filas sueltas (`C-02`).
  - `POST /auth/login` (grupo abierto, `200, 401, 422, 429`):
    - Orden estricto:
      1. Consulta en `intento_acceso` los fallos (`exito=False`) con el mismo `email` e `ip` en los últimos 60 segundos desde el último intento exitoso: si son >= 5, responde **`429`** con encabezado `Retry-After` sin calcular ningún hash (`RN-07`, `C-05`).
      2. Verifica la contraseña con `bcrypt` contra el hash del usuario o contra `app.state.dummy_password_hash` si el correo no existe, tardando lo mismo y devolviendo el mismo mensaje en `401` (`RN-08`, `C-04`).
      3. Registra el intento (exitoso o fallido) en `intento_acceso` abriendo **una sesión y una transacción propias** que se confirman siempre, incluyendo el **comentario obligatorio** que declara: qué hace distinto, por qué no puede compartir la transacción de la petición y cuál es su costo —deja filas aunque la petición falle— (Ej. 7).
      4. Emite el JWT únicamente en la cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Max-Age`, `Secure` según config) y devuelve `{mensaje, debe_cambiar_password, expira_en_segundos}` sin token en el cuerpo (`C-03`).
  - `POST /auth/logout` (borra la cookie `access_token`, `200`).
  - `GET /auth/yo` (grupo abierto, autenticado, `200, 401`): devuelve los datos del usuario, sus roles vigentes en la base y los roles informativos que dice el token (`C-07`).
  - `POST /auth/cambiar-password` (grupo abierto, autenticado, `200, 401, 422`): verifica contraseña actual, calcula el nuevo hash **antes** de abrir el UoW, y en un solo UoW actualiza `password_hash`, pone `debe_cambiar_password=False` y agrega una fila en `evento_seguridad` (RN-16). La misma cookie sigue sirviendo en rutas protegidas sin volver a iniciar sesión (`C-09`).
  - Tests: `C-02`, `C-03`, `C-04`, `C-05` y `C-09`.
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-13: endpoints /auth (registro UoW, login rate-limit + sesion propia, yo, cambiar-password)"`
- **Dependencias**: C-11, C-12
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 2 (Auto-registro) y §Flujo 3 (Login y `intento_acceso`)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-01, RN-02, RN-06, RN-07, RN-08, RN-15, RN-16
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-09, DD-10

---

### [C-14] `usuarios-roles-vigencia-y-eventos`
- **Responsable**: **Andrés** (Bloque 2 — Change 3/3)
- **Estado**: `[ ]` pendiente
- **Scope**: Administración de personal (`POST /usuarios`), asignación y revocación de roles con vigencia y autoprotección, y listado de eventos de seguridad (Ej. 5, Ej. 6 RN-16)
  - Todas las rutas de este change se montan en el **grupo protegido** y exigen `requiere_rol("ADMIN")`:
  - `POST /usuarios` (`201, 409, 422`):
    - Alta de personal con contraseña provisoria: calcula el hash fuera de la transacción y en un solo UoW crea el `Usuario` con `debe_cambiar_password=True`, su `AsignacionRol` inicial y el registro en `evento_seguridad` (RN-06, RN-16). Correo repetido → `409`.
  - `GET /usuarios/{id}/roles` (`200, 404`): devuelve las asignaciones de rol del usuario (`404` si el usuario no existe).
  - `POST /usuarios/{id}/roles` (`201, 404, 409, 422`):
    - Asigna un rol con `vence_en` opcional. Si `vence_en` se envía, el contrato valida que tenga zona horaria (`tzinfo` no nulo) y que sea en el futuro → si no tiene zona o ya pasó, responde **`422`** (`C-07`).
    - Si el usuario tenía una asignación abierta de ese rol pero ya vencida (`vence_en <= now()`), cierra esa fila anterior (`revocada_en = now()`) y abre una fila nueva en el mismo UoW.
    - Si ya tiene una asignación vigente de ese rol, el índice único parcial rechaza y se responde **`409`** (RN-03).
    - Registra la acción en `evento_seguridad` en el mismo UoW (RN-16).
  - `DELETE /usuarios/{id}/roles/{rol}` (`200, 404, 409`):
    - Cumple la **autoprotección (RN-05)**: un administrador no puede revocarse su propio rol `ADMIN`, y el sistema nunca puede quedar sin administradores vigentes → ambos casos responden **`409`** (`C-08`).
    - Escribe `revocada_en = now()` en la asignación vigente **sin borrar la fila** y registra la acción en `evento_seguridad` en el mismo UoW (RN-16, `C-07`).
  - `GET /eventos` (`200, 422`): listado paginado de `evento_seguridad` con el envoltorio `{items, total, page, size, pages}`.
  - Tests: `C-07` (revocar rol con sesión abierta → siguiente petición da `403`, `/auth/yo` muestra la diferencia, fila revocada sigue en tabla; vencimiento sin zona o pasado da `422`) y `C-08` (autoprotección `409`).
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-14: administracion de usuarios, roles con vigencia, autoproteccion y eventos"`
- **Dependencias**: C-12, C-13
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §Modelo de Roles y Vigencia en Base de Datos y §Matriz RBAC
  - `knowledge-base/05_reglas_de_negocio.md` §RN-03, RN-04, RN-05, RN-16 y §Validación de vencimiento de rol
  - `knowledge-base/07_flujos_principales.md` §Flujo 4: Autorización por Petición y Gestión de Roles

---

## FASE 6 — Catálogo, Stock, Clientes y Ventas sobre Unit of Work (Bloque 3: Octavio — Parte 1)

> Esta fase migra todos los módulos del dominio (`editoriales`, `generos`, `autores`, `libros`, `clientes`, `ventas`) a `Repository` + `UnitOfWork`, incorpora el punto único de escritura de stock, el borrado lógico de libros y el descuento atómico de stock en las ventas. Responsable: **Octavio**.

### [C-15] `catalogo-uow-borrado-logico-y-stock`
- **Responsable**: **Octavio** (Bloque 3 — Change 1/3)
- **Estado**: `[ ]` pendiente
- **Scope**: Refactor de `editoriales`, `generos`, `autores` y `libros` a `Repository` + `UnitOfWork`, paginación con envoltorio, borrado lógico y punto único de stock (Ej. 3, Ej. 6, Ej. 8)
  - En `editoriales`, `generos`, `autores` y `libros`:
    - Crear `repository.py` y `unit_of_work.py` en cada módulo; los routers construyen el UoW por dependencia y lo pasan al servicio sin abrirlo; el servicio lo abre con `async with uow:` y deja de recibir la sesión.
    - Actualizar contratos de entrada con `extra="forbid"` y listados con el envoltorio `{items, total, page, size, pages}` (`page >= 1`, `size` 1..100, `422` si `page > pages`, `total` cuenta con los mismos filtros que la página).
    - Separar rutas de lectura pública en el **grupo abierto** (`GET /libros`, `GET /libros/{id}`, `GET /editoriales`, `GET /generos`, `GET /editoriales/{id}/libros`, `GET /generos/{id}/libros`, `GET /autores/{id}/libros`) y rutas de escritura/administración en el **grupo protegido** con `requiere_rol("ADMIN")`.
  - En `app/modules/libros/`:
    - `LibroRepository` hereda de `SoftDeleteRepository[Libro]`; declara toda precarga (`editorial`, `genero`, `autorias.autor`) adentro de sus métodos.
    - **Punto único de escritura de stock (RN-11)**: función/método único que actualiza `libro.stock` y agrega la fila en `MovimientoStock` dentro del mismo UoW.
    - `POST /libros` (`ADMIN`, `201, 409, 422`): recibe `stock_inicial` (en lugar de `stock`) y `autores`; crea el libro y, a través del punto único de escritura de stock, registra el movimiento `"Stock inicial"` en el mismo UoW.
    - `PATCH /libros/{id}` (`ADMIN`, `200, 404, 409, 422`): permite editar `titulo` y `precio` (`exclude_unset=True`); enviar `stock` da **`422`** gracias a `extra="forbid"` (`RN-11`, `C-16`).
    - `DELETE /libros/{id}` (`ADMIN`, `204, 404`): ejecuta baja lógica (`soft_delete` marca `borrado_en = now()`, RN-13). El libro desaparece del catálogo y su ISBN queda libre para dar de alta un nuevo libro vigente (`201`), mientras que un segundo vigente con ese ISBN da `409` (`C-13`).
    - `POST /libros/{id}/reponer` (`ADMIN`, `200, 404, 409, 422`): suma stock y crea el `MovimientoStock` positivo usando el punto único de escritura de stock; si el libro está dado de baja responde **`409`** (`RN-13`, `C-13`).
    - `GET /libros/{id}/movimientos` (`ADMIN`, `200, 404`): lista los movimientos de stock del libro.
  - Tests: `C-13` (reponer 200 con movimiento, baja 204, desaparece del catálogo, nuevo libro con mismo ISBN 201, segundo vigente 409) y `C-16` (búsqueda `' OR '1'='1` con `total: 0`, paginación con filtro `page=2` da `422`, `PATCH` parcial y `PATCH` con `stock` da `422`).
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-15: catalogo sobre Repository/UoW, borrado logico de libros y punto unico de stock"`
- **Dependencias**: C-11, C-12 (puede avanzar en paralelo con C-13/C-14)
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §RN-01, RN-11, RN-12, RN-13, RN-15 y §Paginación con envoltorio
  - `knowledge-base/07_flujos_principales.md` §Flujo 5: Punto Único de Escritura de Stock y Baja Lógica de Libros
  - `knowledge-base/08_arquitectura_propuesta.md` §Capas y Responsabilidades

---

### [C-16] `clientes-y-ventas-uow-stock-y-autorizacion`
- **Responsable**: **Octavio** (Bloque 3 — Change 2/3)
- **Estado**: `[ ]` pendiente
- **Scope**: Refactor de `clientes` y `ventas` a `Repository` + `UnitOfWork`, venta atómica con descuento de stock y movimientos, autorización de dueño y consultas sin N+1 (Ej. 5 RN-14, Ej. 6 RN-10/RN-11, Ej. 8)
  - En `app/modules/clientes/`:
    - `repository.py` (`ClienteRepository`, `PerfilClienteRepository` con precarga de `perfil` y `usuario` declarada en el repositorio) y `unit_of_work.py` (`ClientesUnitOfWork`).
    - Contratos con `extra="forbid"`; rutas protegidas con `requiere_rol("VENDEDOR", "ADMIN")`: `POST /clientes`, `GET /clientes/{id}`, `PATCH /clientes/{id}`, `POST /clientes/{id}/perfil`, `GET /clientes/{id}/ventas`.
  - En `app/modules/ventas/`:
    - `repository.py` (`VentaRepository` con precarga declarada de `cliente`, `renglones` y `renglones.libro` usando `joinedload`/`selectinload`, incluyendo libros dados de baja para el detalle de ventas históricas) y `unit_of_work.py` (`VentasUnitOfWork` que compone `VentaRepository`, `ClienteRepository`, `LibroRepository` y `MovimientoStockRepository` con la misma sesión).
    - `POST /ventas` (grupo protegido, `requiere_rol("VENDEDOR", "ADMIN")`, `201, 409, 422`):
      - En un solo bloque `async with uow:`: verifica libros vigentes y stock suficiente, copia `precio_unitario` de cada libro, calcula `total` (`Decimal`), crea la `Venta` y sus `RenglonVenta`, y por cada renglón invoca el **punto único de escritura de stock** para descontar `libro.stock` y crear un `MovimientoStock` con `cantidad = -renglon.cantidad`, `venta_id = venta.id` y `usuario_id = usuario_actual.id`.
      - Si el cliente no existe, algún libro no existe o está dado de baja (`borrado_en IS NOT NULL`), o algún libro no alcanza en stock → lanza conflicto **`409`** y el UoW revierte toda la transacción (no queda venta, ni renglones, ni descuentos, ni movimientos; `stock == SUM(cantidad)` en todos los libros, `RN-10`, `RN-13`, `C-11`, `C-12`).
      - Recién tras confirmar la transacción, agenda en `BackgroundTasks` el aviso del comprobante (`await asyncio.sleep(0.5)` + mensaje en el log que se ve en la consola con el arranque normal de `uvicorn`, `C-10`).
    - `GET /ventas` (grupo protegido, `requiere_rol("VENDEDOR", "ADMIN")`, `200, 422`): listado paginado con `{items, total, page, size, pages}`.
    - `GET /ventas/{id}` (grupo protegido, **sin `requiere_rol` en la ruta**, `200, 403, 404`): el servicio comprueba si el usuario tiene rol vigente `ADMIN`/`VENDEDOR` o si es el cliente dueño de la venta (`venta.cliente.usuario_id == usuario_actual.id`); si no es ni personal ni dueño, responde **`403`** (`RN-14`, `C-06`). Resuelve la lectura con número fijo de consultas (sin N+1, `C-15`) y muestra el título de los libros aunque hayan sido dados de baja después de la venta (`C-13`).
    - `GET /mis-ventas` (grupo protegido, autenticado, `200, 422`): devuelve las ventas paginadas del cliente asociado al `usuario_actual` (`RN-14`).
  - Tests: `C-06` (cliente ve su venta 200 y no la ajena 403), `C-10` (venta válida 201 con descuento, movimientos y aviso en consola), `C-11` (venta con stock insuficiente en 2do renglón revierte todo 409), `C-12` (cliente/libro inexistente o dado de baja 409 sin escrituras) y `C-15` (misma cantidad de consultas SQL con 2 y 4 renglones).
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-16: clientes y ventas en UoW con descuento atomico de stock, dueño y sin N+1"`
- **Dependencias**: C-13, C-15
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/07_flujos_principales.md` §Flujo 6 (Registro de Venta en UoW) y §Flujo 7 (Detalle de Venta Autorizado y Sin N+1)
  - `knowledge-base/05_reglas_de_negocio.md` §RN-09, RN-10, RN-11, RN-13, RN-14, RN-15
  - `knowledge-base/03_actores_y_roles.md` §Matriz RBAC (`GET /ventas/{id}` sin `requiere_rol`)

---

## FASE 7 — Seed Canónico, Evidencia (`C-01`..`C-16`) y Despliegue Docker en el VPS (Bloque 3: Octavio — Parte 2)

> Cierra los entregables del Parcial (`seed.py`, `test/*.http`, `test/solo_agregado.sql`, `evidencia/`, `README.md`) y construye la carpeta `despliegue/` con el TP de los capítulos 1 a 4 dockerizado y puesto en línea en el VPS (`D-01` a `D-08`). Responsable: **Octavio**.

### [C-17] `seed-casos-prueba-y-despliegue-docker`
- **Responsable**: **Octavio** (Bloque 3 — Change 3/3)
- **Estado**: `[ ]` pendiente
- **Scope**: `seed.py` del Parcial, suite de pruebas `C-01` a `C-16`, e imagen Docker + despliegue en el VPS en carpeta `despliegue/` (Ej. 9 — 11% y Ej. 10 — 7%)
  - **Parte A — Cierre de `parcial/` (raíz del proyecto)**:
    - `seed.py` en la raíz: vacía las tablas y carga los datos iniciales exactos de la consigna:
      - 5 usuarios: `admin@example.com` (`ADMIN`), `admin2@example.com` (`ADMIN`), `vendedor@example.com` (`VENDEDOR`), `ana@example.com` (`CLIENTE`) y `nuevo@example.com` (`VENDEDOR` con `debe_cambiar_password=True`).
      - Catálogo del TP: 3 editoriales, 3 géneros, 6 autores y los 5 libros con su stock actual (*Rayuela* 10, *Antología de la literatura fantástica* 5, *Ficciones* 8, *Respiración artificial* 3, *Bestiario* 1).
      - 3 clientes: *Lucía Fernández* (con perfil, sin usuario), *Tomás Ríos* (sin usuario) y *Ana Paz* (con `ana@example.com`).
      - Venta 1 de *Lucía*, registrada por `vendedor@example.com`: 1 *Rayuela* + 2 *Ficciones* (`total = 69000.00`).
      - 7 movimientos de stock: 5 de `"Stock inicial"` (*Rayuela* 11, *Antología* 5, *Ficciones* 10, *Respiración* 3, *Bestiario* 1) + 2 salidas de la Venta 1 (`-1` y `-2`), verificando `stock == SUM(cantidad)` en los 5 libros.
      - 1 fila en `evento_seguridad` con `actor="SISTEMA"` y `accion="Carga de los datos iniciales"`.
    - `test/*.http` demostrando los casos `C-01` a `C-16` comentados (usando `# @name` y `# @no-cookie-jar` cuando conviven varias sesiones) y `test/solo_agregado.sql` para `C-14`.
    - Carpeta `evidencia/` con la captura/salida de `psql` de `C-14` y el fragmento de consola de `C-15` (consultas fijas en detalle de venta con 2 y 4 renglones).
    - `README.md` actualizado con los nombres y apellidos de los integrantes y los pasos desde cero (`venv`, `requirements.txt`, `.env` y generación de `JWT_SECRET`, `alembic upgrade head`, `python seed.py`, arranque de `uvicorn`).
  - **Parte B — Carpeta `despliegue/` (Contenedor y Despliegue en el VPS del TP Capítulos 1 a 4)**:
    - Extraer en `despliegue/` el TP de los capítulos 1 a 4 exactamente desde el commit **`65ae2a6aae7e637a81f7ebc1f7ef3547585f7faf`** (`fix(remediation): restore async alembic, fix seed_db, implement patch libro and venta schemas`), que contiene todas las correcciones finales del TP 1–4, sin ninguno de los cambios del parcial; e incluir un script de empaquetado (`scripts/empaquetar_entrega.py`) que arme el `.zip` final con las dos carpetas (`parcial/` y `despliegue/`) sin `.venv`, `__pycache__` ni `.env`.
    - `despliegue/Dockerfile`:
      - Parte de `python:3.12-alpine` (imagen base < 100 MB, `D-01`).
      - Copia e instala `requirements.txt` con `pip install --no-cache-dir` antes de copiar el código.
      - Crea un usuario sin privilegios y lo activa con `USER` (`D-07`).
      - Sin secretos en la imagen (`D-06`).
      - Declara `HEALTHCHECK` contra `http://127.0.0.1:8000/health/ready` (`wget -qO- http://127.0.0.1:8000/health/ready || exit 1`).
      - Al arrancar ejecuta `alembic upgrade head` y levanta `uvicorn app.main:app --host 0.0.0.0 --port 8000` (`D-02`, `D-05`).
    - `despliegue/.dockerignore`: excluye `.env`, `.venv`, `.git` y `__pycache__`.
    - `despliegue/env.example`: documenta la forma de `DATABASE_URL` y `SQL_ECHO=false` sin valores reales.
    - `despliegue/DEPLOY.md`: documenta URL pública en el VPS, fecha y hora del despliegue, comandos `docker build` y `docker run` completos (`--env-file`, `--restart unless-stopped`, `-p <puerto>:8000`), cualquier ajuste mínimo hecho al TP y procedimiento de actualización sin perder datos.
    - `despliegue/evidencia/`: salidas y capturas de los casos `D-01` a `D-08`.
  - Commit sugerido (manual, nunca autónomo): `git commit -m "C-17: seed.py del parcial, casos C-01..C-16 y carpeta despliegue/ con Docker y evidencia D-01..D-08"`
- **Dependencias**: C-14, C-16 (la parte de `despliegue/` sobre el TP 1-4 puede adelantarse desde C-08)
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Datos Iniciales Obligatorios (`seed.py`)
  - `knowledge-base/07_flujos_principales.md` §Flujo 8: Construcción y Despliegue del Contenedor en el VPS
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura Obligatoria de Directorios y Entrega
  - `knowledge-base/01_vision_y_objetivos.md` §Métricas de éxito (Ej. 9 y Ej. 10)
