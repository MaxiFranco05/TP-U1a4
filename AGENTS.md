# TP-U1a4 Librería — Instrucciones para Agentes

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
| Configuración | python-dotenv (`.env` no versionado) | 1.0 |
| Servidor ASGI | uvicorn (vía `fastapi[standard]`) | — |
| Base de dev | PostgreSQL 16 en Docker local | 16 |

Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Entender propósito y alcance |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Auth, RBAC, permisos (sin auth: todo público) |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Entidades, ERD, migraciones |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas codificadas (RN-01 a RN-12) |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias de usuario por épica |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos E2E |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones, estructura, env vars |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | ⚠️ Inconsistencias a resolver ANTES de codear |

> ⚠️ Resolver las preguntas de prioridad **Alta** de `10_preguntas_abiertas.md` (PA-01: proveer Python 3.12) antes de arrancar el primer change.

---

## Skills Disponibles

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend Core** | Modelos, migraciones, CRUD | `postgresql-table-design`, `sqlalchemy-alembic-expert-best-practices-code-review`, `fastapi-templates`, `fastapi` |
| **Backend Ventas** | DTOs anidados, RN-04 a RN-07 | `fastapi-python`, `fastapi` |
| **Performance** | N+1, queries, constraints PG | `postgresql-optimization`, `supabase-postgres-best-practices` |
| **Orquestación** | SDD / OPSX / docs | `kb-creator`, `roadmap-generator`, `agents-md-generator`, `discovery-research`, `skill-registry` |

Cargá la skill correspondiente al contexto ANTES de escribir código.

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; no versionado — no está en el repo). Esta tabla solo mapea skill→rol.

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 8 changes en 4 fases.
- **Camino crítico** (7): `C-01 → C-02 → C-03 → C-04 → C-06 → C-07 → C-08`.
- **Primer change**: `C-01` (foundation-setup).

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y los archivos de "Leer antes".

---

## Reglas Duras

> Reglas globales ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD, engram): el proyecto las hereda. Acá viven solo las reglas **específicas de este proyecto** + las universales que el global no cubra.

Son contrato; romperlas es un defecto:

- NUNCA commitear de forma autónoma → sugerir el commit (mensaje + archivos) y que el usuario lo ejecute.
- NUNCA devolver texto interno de la base ni trazas en errores → traducir `IntegrityError` a mensaje propio + 409/422 (RN-12).
- NUNCA verificar existencias con `if` antes de escribir → dejar que la base rechace FK/UNIQUE y responder 409 (DD-04).
- NUNCA usar `float` para dinero → siempre `Decimal` (NUMERIC).
- NUNCA leer relaciones con carga perezosa → `joinedload` (a uno) / `selectinload` (colecciones) declarados en la consulta.
- NUNCA crear el esquema con `create_all` → exclusivamente Alembic; leer cada migración autogenerada antes de aplicarla.
- NUNCA renombrar ni quitar tablas o columnas del modelo → solo agregar (los tests usan los nombres).
- NUNCA ejecutar llamadas bloqueantes en handlers `async` → `async def` + I/O async siempre.
- NUNCA armar SQL concatenando texto → parámetros ligados siempre (RN-11).
- NUNCA subir secretos al repo → `DATABASE_URL` en `.env` (no versionado), `env.example` y `alembic.ini` sin secretos.

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)        → entender el dominio
2. Identificar el change en CHANGES.md           → respetar dependencias
3. /opsx:propose C-NN-nombre                     → proposal + design + specs + tasks
4. Implementar las tasks (cargando skills)       → respetando las reglas duras
5. /opsx:archive C-NN-nombre + marcar [x]        → cerrar el change
```

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
