# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| Working with FastAPI APIs, Pydantic models, dependencies, SSE/streaming, serving frontends | fastapi | C:\Users\maxif\.agents\skills\fastapi\SKILL.md |
| Building new FastAPI applications or setting up backend API projects | fastapi-templates | C:\Users\maxif\.agents\skills\fastapi-templates\SKILL.md |
| FastAPI Python development with best practices for APIs and async operations | fastapi-python | C:\Users\maxif\.agents\skills\fastapi-python\SKILL.md |
| Creating/altering Postgres tables, columns, migrations, indexes, queries, or diagnosing slow queries/locks/connections | supabase-postgres-best-practices | C:\Users\maxif\.agents\skills\supabase-postgres-best-practices\SKILL.md |
| Designing or reviewing a PostgreSQL-specific schema (types, keys, constraints, indexes) | postgresql-table-design | C:\Users\maxif\.agents\skills\postgresql-table-design\SKILL.md |
| PostgreSQL-specific features, advanced types, query optimization, EXPLAIN analysis | postgresql-optimization | C:\Users\maxif\.agents\skills\postgresql-optimization\SKILL.md |
| Writing, reviewing, or refactoring SQLAlchemy models, Alembic migrations, or query patterns | sqlalchemy-alembic-expert-best-practices-code-review | C:\Users\maxif\.agents\skills\sqlalchemy-alembic-expert-best-practices-code-review\SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### fastapi
- `Annotated[..., Path/Query/Header/Depends]` style for all params and dependencies; create type aliases for reusable dependencies
- Return type annotation on every endpoint (validates/filters/serializes via Pydantic); use `response_model` only when the public schema differs from the return type
- Router-level `prefix/tags/dependencies` declared on `APIRouter`, not in `include_router()`
- One HTTP operation per function; never `...` (Ellipsis) defaults; never Pydantic `RootModel`; never `ORJSONResponse`/`UJSONResponse`
- `async def` only when inner calls are truly non-blocking; default to `def` (threadpool) when in doubt; never run blocking code inside `async`
- Prefer SQLModel over raw SQLAlchemy, HTTPX over Requests, lifespan context managers over `on_event`
- Dev server via `fastapi dev`, prod via `fastapi run`; declare entrypoint under `[tool.fastapi]` in pyproject.toml

### fastapi-templates
- Module layout: `app/{api/v1/endpoints, core, models, schemas, services, repositories}/main.py`; keep routes, business logic, and data access in separate layers
- Shared concerns (DB session, auth) via `Depends`, applied at router level
- Async handlers plus async DB operations end to end; background work via BackgroundTasks (no blocking the event loop)
- Tests override the `get_db` dependency and use AsyncClient; assert contract codes 201/404/409/422

### fastapi-python
- RORO: receive a Pydantic object, return an object; type-hint every signature; Pydantic models over raw dicts
- Guard clauses with early returns at function entry; happy path last; no else-after-return
- `HTTPException` with explicit status codes for expected errors; lifespan manager for startup/shutdown; middleware for logging
- `snake_case` file names (e.g. `routers/user_routes.py`); plain functions over classes for organization
- Async for all DB and external API I/O; never block inside async paths

### supabase-postgres-best-practices
- Load before ANY database change, even a one-column migration or a single query
- Index every FK plus frequent filters/sorts/joins; diagnose with `EXPLAIN (ANALYZE, BUFFERS)` and `pg_stat_statements`
- Bound parameters always, never string-concatenated SQL (RN-11 title filter uses a bound `ILIKE`/`LOWER()` parameter)
- Pool connections, set idle timeouts, keep transactions short to avoid exhaustion and deadlocks
- Batch inserts and `ON CONFLICT` upserts for seeds; validate pagination as limit 1-100/default 20, offset >= 0 (RN-10)
- Detail rules live in `references/` by prefix: `query-*`, `conn-*`, `security-*`, `schema-*`, `lock-*`, `data-*`, `monitor-*`

### postgresql-table-design
- PK on every reference table: `BIGINT GENERATED ALWAYS AS IDENTITY` (never `serial`); UUID only for distributed/opaque IDs
- Normalize to 3NF first; denormalize only for measured, high-ROI read wins
- `NOT NULL` everywhere semantically required; `DEFAULT`s for common values
- Types: `TIMESTAMPTZ` (never bare `timestamp`), `NUMERIC(p,s)` for money (never `money`), `TEXT` + `CHECK (LENGTH(col) <= n)` (never `varchar(n)`/`char(n)`), `BOOLEAN NOT NULL`
- Uniqueness (ISBN, email, one-profile-per-client) via `UNIQUE`; `CHECK (price > 0)` / `CHECK (stock >= 0)` combined with `NOT NULL`; explicit `ON DELETE/UPDATE` on every FK; `snake_case` unquoted identifiers
- PostgreSQL does NOT auto-index FK columns: create each FK index manually; use `UNIQUE NULLS NOT DISTINCT` (PG15+) when only one NULL is allowed
- Case-insensitive lookups: expression index `ON tbl (LOWER(col))`, and the query must use the same expression

### postgresql-optimization
- Prefer keyset pagination (`WHERE id > $last_id`) for large datasets; keep the project's limit/offset contract but back it with covering indexes
- Composite indexes obey leftmost-prefix; `INCLUDE (...)` covering indexes for index-only scans; partial indexes for hot subsets; GIN for JSONB/FTS, GiST for ranges/geometry
- Kill N+1 with eager/selectin loading; never per-row queries in loops (Ej.6)
- Diagnose via `EXPLAIN (ANALYZE, BUFFERS)` plus `pg_stat_statements`; fix sequential scans on large tables first; drop zero-scan (`idx_scan = 0`) indexes
- Parameterized queries exclusively; RLS where multi-tenant; regular `VACUUM`/`ANALYZE` maintenance

### sqlalchemy-alembic-expert-best-practices-code-review
- Autogenerate (`alembic revision --autogenerate`) then hand-review every migration; never ship raw autogenerate (project: exactly 2 reviewed autogenerated migrations, Ej.3)
- New indexes use `postgresql_concurrently=True` inside autocommit blocks; unique constraints as concurrent-index-then-constraint two-step
- New FKs and CHECKs: add `NOT VALID` first, `VALIDATE` in a separate step to avoid table locks
- Column type changes via multi-step add/backfill/swap; never a single locking ALTER on live data
- Max 3 columns per non-unique index; no index redundant with a composite leftmost prefix; every query pattern must have a matching index

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| (none yet) | — | Project CLAUDE.md/AGENTS.md do not exist yet (generated in the next phase); no `.cursorrules`, `GEMINI.md`, or `copilot-instructions.md` found |

Read the convention files listed above for project-specific patterns and rules. All referenced paths have been extracted — no need to read index files to discover more.
