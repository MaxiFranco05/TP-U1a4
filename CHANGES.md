# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **TP-U1a4 (API Librería: FastAPI + PostgreSQL)**.
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

> **Política de commits (restricción vigente del usuario)**: al final de cada change hay un
> `Commit sugerido`. Es solo una sugerencia explícita de cuándo commitear y con qué mensaje.
> El flujo **nunca commitea de forma autónoma**: el agente propone el commit y el usuario lo ejecuta.

---

## Cómo usar este documento

1. Identificar el change a implementar (verificar que sus dependencias están en `openspec/changes/archive/`).
2. Leer los docs de la knowledge-base indicados en "Leer antes".
3. Ejecutar `/opsx:propose <nombre-del-change>`.
4. Al terminar el change, archivarlo con `/opsx:archive <nombre-del-change>`.
5. Marcar el checkbox `[x]` en este archivo.

---

## Árbol de dependencias

```
C-01 foundation-setup
  └── C-02 core-models-migracion-001          ← desbloquea TODO lo demás
        │
        ├── C-03 generos-migracion-002
        │     └── C-04 catalogo-crud ────────┐
        │                                     ├── C-06 ventas-alta-riesgo (riesgo principal RN-04..RN-07)
        ├── C-05 clientes-perfil ────────────┘     │
        │     (paralelo con C-03)                  └── C-07 lecturas-sin-nplusuno
                                                         └── C-08 seed-entrega-evidencia
```

### Paralelismo por fase

> Cada "gate" es un punto de sincronización. Los changes dentro de un grupo pueden ejecutarse en paralelo.

```
GATE 0: ninguna
  → C-01 (solo)

GATE 1: C-01 ✓
  → C-02 (solo — modelos core, cambio CRITICO, un agente)

GATE 2: C-02 ✓                          ← PRIMER FORK (2 paralelos)
  → C-03 generos-migracion-002          [Agente A]
  → C-05 clientes-perfil                [Agente B]

GATE 3: C-03 ✓ (C-05 puede seguir en paralelo)
  → C-04 catalogo-crud                  [Agente A]

GATE 4: C-04 + C-05 ✓
  → C-06 ventas-alta-riesgo             [Agente A + B — riesgo principal, en par]

GATE 5: C-06 ✓ (+ C-04 ✓)
  → C-07 lecturas-sin-nplusuno          [Agente C]

GATE 6: C-07 ✓ (transitivamente todo)
  → C-08 seed-entrega-evidencia         [Agente C]
```

### Camino crítico (7 changes — mínimo irreducible)

```
C-01 → C-02 → C-03 → C-04 → C-06 → C-07 → C-08
```

### Plan óptimo con 3 agentes

```
Paso │ Agente A (Catálogo)            │ Agente B (Clientes/Ventas)       │ Agente C (Infra/Calidad)
─────┼────────────────────────────────┼──────────────────────────────────┼─────────────────────────────
  1  │ C-01 foundation-setup          │ —                                │ —
  2  │ C-02 core-models-migracion-001 │ —                                │ —
  3  │ C-03 generos-migracion-002     │ C-05 clientes-perfil             │ —
  4  │ C-04 catalogo-crud             │ (apoyo C-04 / adelanto diseño C-06) │ —
  5  │ C-06 ventas-alta-riesgo (en par con B) │ C-06 ventas-alta-riesgo (en par con A) │ —
  6  │ —                              │ —                                │ C-07 lecturas-sin-nplusuno
  7  │ —                              │ —                                │ C-08 seed-entrega-evidencia
```

---

## FASE 0 — Cimientos y modelo core

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

## FASE 1 — Catálogo

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
- **Estado**: `[ ]` pendiente
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

## FASE 2 — Clientes y ventas (riesgo principal)

> C-05 puede arrancar en GATE 2 en paralelo con C-03. C-06 requiere C-04 + C-05 y se recomienda en par (riesgo RN-04..RN-07).

### [C-05] `clientes-perfil`
- **Estado**: `[ ]` pendiente
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
- **Estado**: `[ ]` pendiente
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

## FASE 3 — Rendimiento y entrega

> C-07 deja la evidencia de consultas fijas; C-08 cierra con seed + `.http` + README. Commit final sugerido al terminar C-08.

### [C-07] `lecturas-sin-nplusuno`
- **Estado**: `[ ]` pendiente
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
- **Estado**: `[ ]` pendiente
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
