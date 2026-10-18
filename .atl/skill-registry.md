# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| how do I do X, find a skill for X, is there a skill that can, extend capabilities | find-skills | C:\Users\Andres\.config\opencode\skills\find-skill\SKILL.md |
| create CHANGES.md, armar CHANGES, armar roadmap, crear mapa de changes, generar plan de implementación, qué changes necesito, índice de changes | roadmap-generator | C:\Users\Andres\.config\opencode\skills\roadmap-generator\SKILL.md |
| crear AGENTS.md, generar CLAUDE.md, armar las reglas del proyecto, instrucciones para los agentes | agent-instruction | C:\Users\Andres\.config\opencode\skills\agent-instruction\SKILL.md |
| crear base de conocimiento, generar KB, armar base de conocimiento, documentar proyecto | kb-creator | C:\Users\Andres\.config\opencode\skills\kb-creator\SKILL.md |
| /active-orchestrator:init, /active-orchestrator:kb, /active-orchestrator:rules, /active-orchestrator:discovery, /active-orchestrator:openspec, /active-orchestrator:devops, /active-orchestrator:find-skill, start new project from scratch | active-orchestrator | C:\Users\Andres\.config\opencode\skills\active-orchestrator\SKILL.md |
| create skill, edit skill, optimize skill, run evals, benchmark skill | skill-creator | C:\Users\Andres\.config\opencode\skills\skill-creator\SKILL.md |
| test-driven development, red-green-refactor, integration tests | tdd | C:\Users\Andres\.agents\skills\tdd\SKILL.md |
| FastAPI APIs, Pydantic models, dependencies, streaming SSE, serving frontend | fastapi | C:\Users\Andres\Documents\Tecnicatura en Programación\2° Año\1° Cuatrimestre\Programación 3\Trabajos Prácticos\TP-U1a4\TP-U1a4\.agents\skills\fastapi\SKILL.md |
| full stack monorepo, pnpm workspaces, React + Hono, Prisma + Redis | fe-fullstack-dev | C:\Users\Andres\.agents\skills\fe-fullstack-dev\SKILL.md |
| persistent memory, mem_save, mem_search, session summary | engram-memory | C:\Users\Andres\.agents\skills\engram-memory\SKILL.md |
| React + TypeScript, Vite + React 19 + Tailwind + antd + Zustand/Jotai | fe-react-dev-stack | C:\Users\Andres\.agents\skills\fe-react-dev-stack\SKILL.md |
| FastAPI project templates, async patterns, dependency injection | fastapi-templates | C:\Users\Andres\Documents\Tecnicatura en Programación\2° Año\1° Cuatrimestre\Programación 3\Trabajos Prácticos\TP-U1a4\TP-U1a4\.agents\skills\fastapi-templates\SKILL.md |
| schema validation, input sanitization, output encoding, type coercion, Zod, Pydantic | loom-data-validation | C:\Users\Andres\.agents\skills\loom-data-validation\SKILL.md |
| Jest, Vitest, Testing Library, unit/integration/e2e tests, mocking, TDD | javascript-testing-patterns | C:\Users\Andres\.agents\skills\javascript-testing-patterns\SKILL.md |
| JWT authentication, stateless API access, token refresh, revocation | jwt-auth | C:\Users\Andres\.agents\skills\jwt-auth\SKILL.md |
| dockerize project, docker-compose.yml, Dockerfile, auto-detect services | docker-init | C:\Users\Andres\.agents\skills\docker-init\SKILL.md |
| archive completed change, finalize change, opsx archive | openspec-archive-change | C:\Users\Andres\.agents\skills\openspec-archive-change\SKILL.md |
| PostgreSQL search, pgvector, BM25, JSONB index, asyncpg, PostgreSQL Docker | mastering-postgresql | C:\Users\Andres\.agents\skills\mastering-postgresql\SKILL.md |
| SQLAlchemy 2.0 ORM, typed mappings, select() queries, async engines, Alembic | python-sqlalchemy | C:\Users\Andres\.agents\skills\python-sqlalchemy\SKILL.md |
| generar AGENTS.md, generar CLAUDE.md, armar reglas del proyecto | agents-md-generator | C:\Users\Andres\.agents\skills\agents-md-generator\SKILL.md |
| REST API design, OpenAPI contracts, resource naming, status codes, pagination | rest-api-guidelines | C:\Users\Andres\.agents\skills\rest-api-guidelines\SKILL.md |
| FastAPI Python development with best practices for APIs and async operations | fastapi-python | C:\Users\Andres\Documents\Tecnicatura en Programación\2° Año\1° Cuatrimestre\Programación 3\Trabajos Prácticos\TP-U1a4\TP-U1a4\.agents\skills\fastapi-python\SKILL.md |
| Postgres best practices (Supabase) — schema, indexes, RLS, vectors, performance | supabase-postgres-best-practices | C:\Users\Andres\Documents\Tecnicatura en Programación\2° Año\1° Cuatrimestre\Programación 3\Trabajos Prácticos\TP-U1a4\TP-U1a4\.agents\skills\supabase-postgres-best-practices\SKILL.md |
| PostgreSQL table design — types, keys, constraints, indexes, partitioning | postgresql-table-design | C:\Users\Andres\Documents\Tecnicatura en Programación\2° Año\1° Cuatrimestre\Programación 3\Trabajos Prácticos\TP-U1a4\TP-U1a4\.agents\skills\postgresql-table-design\SKILL.md |
| PostgreSQL optimization — JSONB, arrays, window functions, FTS, extensions | postgresql-optimization | C:\Users\Andres\Documents\Tecnicatura en Programación\2° Año\1° Cuatrimestre\Programación 3\Trabajos Prácticos\TP-U1a4\TP-U1a4\.agents\skills\postgresql-optimization\SKILL.md |
| SQLAlchemy/Alembic expert review — migrations, indexes, constraints, query patterns | sqlalchemy-alembic-expert-best-practices-code-review | C:\Users\Andres\Documents\Tecnicatura en Programación\2° Año\1° Cuatrimestre\Programación 3\Trabajos Prácticos\TP-U1a4\TP-U1a4\.agents\skills\sqlalchemy-alembic-expert-best-practices-code-review\SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### find-skills
- When user asks "how do I do X" or "find a skill for X", search skills.sh leaderboard first
- Run `npx skills find [query]` for specific searches — verify install count (1K+), source reputation (vercel-labs, anthropics, microsoft), GitHub stars (>100)
- Present options with name, function, install count, source, and install command
- Offer to install with `npx skills add <owner/repo@skill> -g -y`
- If no skills found, acknowledge and offer direct help or `npx skills init` to create custom skill

### roadmap-generator
- Pre-checks: KB exists with 10 canonicals + `openspec/` dir — if missing, STOP and instruct user
- Read 4 mandatory KB files: 04_modelo_de_datos.md, 06_funcionalidades.md, 07_flujos_principales.md, 08_arquitectura_propuesta.md
- Output CHANGES.md to project root (not inside openspec/) with exact structure: dependency tree ASCII, parallelism gates, critical path, 3-agent plan, phases with C-NN changes
- Use 8 dependency rules: infra first, models before features, auth before protected, referenced entity before referencer, backend before frontend, integrations last, admin last, UI restyle last
- Gates = points where completing one change unlocks multiple independent changes
- Governance levels: BAJO (scaffolding/CRUD), MEDIO (stateful flows), ALTO (notifications/roles), CRITICO (auth/payments/core models)

### agent-instruction
- Pre-checks: KB exists + 02_descripcion_general.md + CHANGES.md (optional, warn if missing)
- Output AGENTS.md + CLAUDE.md at project root (copies, not symlinks)
- Read KB 02 for stack, README for project name, CHANGES for roadmap, .atl/skill-registry.md for skills
- **Hard rules (interactive only)**: 1) Read global ~/.claude/CLAUDE.md — reference don't duplicate; 2) Derive stack-aware rules from KB 02; 3) CONFIRM with user via AskUserQuestion; 4) Write ONLY confirmed rules in NUNCA X → hacer Y format
- Map skills to agent roles in table — DRY: compact rules live ONLY in .atl/skill-registry.md, reference it

### kb-creator
- Auto-detects mode: Mode A (silent from docs/) if sources exist, Mode B (interactive from scratch) if not
- Output: 10 canonical files in knowledge-base/ (never mix with docs/) + README.md index
- Canonical files: 01_vision, 02_descripcion_general, 03_actores_roles, 04_modelo_datos, 05_reglas_negocio, 06_funcionalidades, 07_flujos_principales, 08_arquitectura, 09_decisiones, 10_preguntas_abiertas
- Mode A: ingest all sources, structure into canonicals, register doubts in 10_preguntas_abiertas.md
- Mode B: strategic partner — analyze context, 3-5 questions, 2-3 approaches, iterate file-by-file with validation
- State integration: writes state.kb with source (ingest/interactive), discovery fields, files list

### active-orchestrator
- Thin orchestrator: owns .active-orchestrator-state.json (version, step, owner only)
- Runs openspec init → Discovery gate (ask user Sí/No) → dispatches phases in order: discovery-research → kb-creator → roadmap-generator → find-skill → skill-registry → agent-instruction
- **Checkpoint protocol**: pre-phase context gate (roadmap-generator asks constraints) + post-phase advance gate (summarize, ask Continuar/Ajustar/Parar)
- Mechanical phases (roadmap, find-skill, skill-registry) run as sub-agents; interactive (kb-creator, agent-instruction) run inline via Skill tool
- Lazy-load: check sub-skill installed via `npx skills list -g | grep <name>` before dispatch; offer install if missing

### skill-creator
- Capture intent: what should skill do, when trigger, output format, test cases needed
- Interview for edge cases, I/O formats, examples, success criteria, dependencies
- Write SKILL.md with frontmatter (name, description — make it "pushy" for triggering), body under 500 lines
- Test loop: spawn with-skill + baseline runs in parallel, draft assertions while running, capture timing, grade, aggregate benchmark, launch viewer
- Iterate until user happy / feedback empty / no progress — generalize from feedback, keep prompt lean, explain why
- Description optimization: 20 eval queries (should/shouldn't trigger), review with user, run optimization loop, apply best_description

### tdd
- Red before green: write failing test first, then minimal code to pass
- One slice at a time: one seam, one test, one implementation per cycle
- Test at pre-agreed seams only — public interfaces, never internals
- Anti-patterns: implementation-coupled (mocks internals), tautological (recomputes expected), horizontal slicing (all tests then all impl)
- Refactoring is separate review stage, not part of red-green loop
- Read GLOSSARY.md for domain vocabulary, respect ADRs in area

### fastapi
- Use `Annotated[..., Depends(...)]` for all parameters and dependencies — create type aliases for reuse
- No `...` (Ellipsis) for required params or model fields
- Prefer return type over response_model; use response_model only when public schema differs
- Router-level prefix, tags, shared dependencies on APIRouter, not in include_router()
- Use `async def` only when fully certain logic is async-compatible; default to `def` (runs in threadpool)
- For SSE: `response_class=EventSourceResponse` + `yield ServerSentEvent(data=...)`
- `app.frontend("/")` or `router.frontend("/")` for serving built frontend assets
- Enable OpenTelemetry via `fastapi[standard]`, `FASTAPI_OTEL_AUTO_CONFIGURE=true`
- Do not use `ORJSONResponse`/`UJSONResponse` (deprecated) — Pydantic serializes on Rust side

### fe-fullstack-dev
- Monorepo: pnpm workspaces with web/ (React+Vite+TS+Tailwind+antd), server/ (Hono+Zod+Prisma+Redis), packages/shared/
- Root package.json scripts: `dev` (parallel), `build`, `lint`, `clean` via `pnpm -r`
- Vite proxy: `/api` → `http://localhost:3000` for dev
- Shared types/validators in `packages/shared` — import via `@project/shared` workspace protocol
- Add deps with `--filter`: `pnpm add antd --filter web`, `pnpm add zod --filter @project/shared -w`
- Prisma: `pnpm --filter server prisma generate/db push/studio/migrate dev`
- API routes: validator in shared → route in server/src/routes → register in index.ts → service in web/src/services → types in shared

### engram-memory
- **ALWAYS ACTIVE** — save proactively after decisions, conventions, bugs, discoveries, user confirmations/rejections
- Call `mem_save` immediately: title (verb+what), type (bugfix|decision|architecture|discovery|pattern|config|preference), scope (project|personal|global), topic_key for upserts
- Content format: What/Why/Where/Learned
- Search: mem_context (recent) → mem_search (FTS) → mem_get_observation (full)
- Proactive search when starting work, user references past, or first message mentions project
- Session close: MUST call mem_session_summary with Goal/Instructions/Discoveries/Accomplished/Next Steps/Relevant Files
- After compaction: immediate mem_session_summary with compacted content, then mem_context

### fe-react-dev-stack
- Stack: pnpm, React 19 + TS strict, Vite, React Router 7, Zustand/Jotai, TanStack Query, ahooks, antd, Tailwind, Ramda optional
- **Strict rules**: NO class components, NO `this`, NO lifecycle methods — function components + hooks only
- Use ahooks semantic hooks: `useMount`/`useUnmount`/`useUpdateEffect` instead of raw useEffect
- Replace useEffect per scenario: data→useRequest, events→useEventListener, debounce→useDebounce, timers→useInterval, storage→useLocalStorage, keys→useKeyPress
- Import order: React → third-party → internal → hooks/stores/services → types
- Naming: pages default export PascalCase, components named export PascalCase, hooks useXxx, stores useXxxStore, services fetchXxx/createXxx, types PascalCase
- Style priority: antd className API → Tailwind utilities → avoid handwritten CSS
- Tailwind config: `preflight: false` to avoid antd conflicts, extend colors with CSS vars

### fastapi-templates
- Project structure: app/{api/v1/endpoints, core, models, schemas, services, repositories, main.py}
- DI: Depends for DB sessions, auth, shared logic, config
- Async patterns: async route handlers, async DB operations, async background tasks, async middleware
- Requirements: fastapi, uvicorn[standard], pydantic-settings, sqlalchemy[asyncio]>=2.0, asyncpg, PyJWT, pwdlib[argon2], python-multipart
- Testing: pytest-asyncio, httpx ASGITransport, aiosqlite for in-memory DB, override get_db dependency
- Use DeclarativeBase, Mapped/mapped_column, select() not Session.query()

### loom-data-validation
- **Parse, don't validate** — return typed value (Result<User>, User | errors) so downstream can't receive unvalidated data
- Validate at boundary once (HTTP handlers, queue consumers, file parsers, pipeline ingestion), then trust typed value inward
- Server-side authoritative; client-side is UX only
- Allowlist > denylist — enumerate permitted (enum, char classes, known hosts)
- Canonicalize before validating: Unicode NFC, lowercase host, resolve paths, decode percent-encoding
- Encoding ≠ validation — encode at sink for sink's context (HTML/attr/JS/URL/CSS/SQL/shell)
- Limits are validation: cap length, array size, object depth, payload bytes (DoS prevention)
- Zod: `.strict()` on request bodies (reject unknown keys), `safeParse` at boundaries, async rules need `.parseAsync`
- Pydantic v2: `ConfigDict(extra="forbid", str_strip_whitespace=True)`, `@field_validator` + `@classmethod`, `EmailStr`
- Never build SQL/HTML/shell by concatenation — parameterized queries, argv arrays, DOM APIs
- XSS: output-encode at every sink, sanitize stored HTML with allowlist (DOMPurify), set CSP
- Mass assignment: `.strict()` / `extra="forbid"` / explicit allowlists — never bind request body to ORM model
- ReDoS: avoid nested quantifiers, anchor patterns, cap input length, use RE2 for untrusted patterns

### javascript-testing-patterns
- Jest: ts-jest preset, node env, 80% coverage threshold, setupFilesAfterEnv
- Vitest: globals, node env, v8 coverage, setupFiles
- AAA pattern: Arrange, Act, Assert — one assertion or logically related per test
- Mock external deps (fetch, modules, DI), keep tests isolated, test edge cases not just happy paths
- Pure functions: test with literals, independent expected values (not recomputed)
- Classes: beforeEach new instance, test behavior not implementation
- Async: mock fetch globally with vi.fn(), mockResolvedValue for success/error
- Module mocking: vi.mock('module', () => ({ default: { method: vi.fn() } }))
- DI for testing: inject interface, mock implementation in beforeEach
- Spy on functions: vi.spyOn(object, 'method'), restore in afterEach
- Integration: supertest + test DB, truncate in beforeEach, tear down in afterAll
- Frontend: Testing Library, semantic queries (getByRole, getByPlaceholderText) > data-testid
- Factories: @faker-js/faker with overrides for test data
- Best practices: descriptive names, TypeScript, 80%+ coverage, test error handling, clean up

### jwt-auth
- Stateless: no server-side session storage, signed tokens (HS256/RS256), claims-based payload
- Prep: choose algorithm, generate secret/keypair, define claims structure, plan storage
- Flow: Generate → Sign → Issue (httpOnly cookie or header) → Validate (middleware) → Refresh → Revocate
- Do: httpOnly cookies, token refresh, validate expiration
- Don't: store sensitive data in payload, weak secrets, skip signature verification
- Anti-patterns: sensitive data in JWT, no expiration, weak keys, no validation

### docker-init
- Scan before generating: read package.json, pyproject.toml, requirements.txt, go.mod, Cargo.toml for deps
- Read existing docker-compose.yml/Dockerfile first — ask before overwriting
- Only official images with pinned tags (alpine/slim variants)
- Every service: healthcheck with interval/timeout/retries/start_period, security_opt no-new-privileges, deploy.resources.limits, restart unless-stopped
- Credentials as `${VAR}` refs to .env, `${VAR:?required}` for passwords
- Data in named volumes, networks only as needed (frontend/backend/db segmentation)
- Kafka: KRaft mode (single node), not Zookeeper
- Dockerfile: multi-stage, slim/alpine base pinned to project version, non-root USER, no secrets, HEALTHCHECK for HTTP apps
- .dockerignore: VCS, .env*, deps, caches, build output, Dockerfile itself
- Prod overlay: no host ports, restart always, tighter limits, bounded logs
- Validate: hadolint, docker build, docker compose config, .env in .gitignore

### openspec-archive-change
- If no change name: run `openspec list --json`, prompt user to select active change
- Check artifact completion via `openspec status --change <name> --json` — warn if incomplete, confirm proceed
- Check tasks.md for incomplete tasks (`- [ ]`) — warn, confirm proceed
- Assess delta spec sync: compare openspec/changes/<name>/specs/ with openspec/specs/<capability>/spec.md
- If delta specs exist: show combined summary, prompt "Sync now"/"Archive without syncing"
- Archive: mkdir -p openspec/changes/archive, mv to YYYY-MM-DD-<name>, fail if target exists
- Output: change name, schema, archive location, sync status, warnings

### mastering-postgresql
- Docker: `pgvector/pgvector:pg17` with pgvector + pg_trgm extensions
- Search decision tree: exact→B-tree, FTS→tsvector+GIN+ts_rank, Google-like→pg_search BM25, typo→pg_trgm, semantic→pgvector, hybrid→tsvector+pgvector
- Vector index: <100K→no index, best recall→HNSW, fast build→IVFFlat, AlloyDB→ScaNN, Azure→pg_diskann, billions→vchordrq, dims>2000→halfvec
- Python lib: sync→psycopg2, async modern→psycopg3, max perf→asyncpg, ORM→SQLAlchemy+asyncpg
- Index by column: scalar→B-tree, JSONB→GIN (jsonb_path_ops for @>), array→GIN, tsvector→GIN/GiST, vector→HNSW/IVFFlat, range/geo→GiST
- HNSW: m=16 default (12-48), ef_construction=64 (64-200), ef_search=40 (set at query time)
- IVFFlat: lists=sqrt(rows) (<1M) or rows/1000 (>1M), probes=sqrt(lists)
- Troubleshoot: ANALYZE for seq scan, increase ef_search for slow vectors, increase probes for poor recall, check language config for FTS, verify operator class

### python-sqlalchemy
- Use SQLAlchemy 2.0 stable: DeclarativeBase, Mapped/mapped_column, select() not Session.query()
- Session: create_engine → sessionmaker → context manager with SessionLocal(), app owns transaction (with session.begin())
- Queries: session.scalars(select(Model).where(...)).all(), session.get(Model, id), session.scalar(select(func.count()).select_from(Model))
- Upsert: postgresql.insert().values(...).on_conflict_do_update(index_elements=[pk], set_={...}).returning(Model) with populate_existing
- Relationships: ForeignKey + relationship(back_populates) on both sides
- JSON: MutableDict.as_mutable(JSON) for dict columns, detect mutations via replacement assignment
- Alembic for migrations — review autogenerated, especially destructive changes and data backfills

### agents-md-generator
- Same as agent-instruction — generates AGENTS.md/CLAUDE.md from KB + roadmap + registry
- Pre-checks: KB exists + 02_descripcion_general.md + CHANGES.md (warn if missing)
- Input: KB 02 (stack), README (name), CHANGES (roadmap), .atl/skill-registry.md (skills source of truth), 10_preguntas_abiertas (alta flags), global CLAUDE.md (to avoid duplication)
- Hard rules: read global, reference don't duplicate; derive stack-aware candidates; CONFIRM with user; write ONLY confirmed in NUNCA X → hacer Y format
- Skills table: map detected skills to agent roles — reference .atl/skill-registry.md for compact rules (DRY)

### rest-api-guidelines
- Default decisions: resource-oriented noun URIs, path major versioning (/v1/users), PATCH for updates, application/merge-patch+json, cursor pagination (pageSize/pageToken/nextPageToken), application/problem+json errors, opaque external IDs, RFC3339 UTC timestamps
- Compatibility: additive fields safe, removals/renames/semantic changes/enum removals = breaking
- Workflow: classify as design/review/draft → start from defaults → read needed refs → state deviations explicitly → keep contract consistent
- Design: simplest resource model, CRUD first, custom actions only when behavior doesn't fit resource
- Review: findings first, identify violated guideline + concrete risk + recommended fix, prioritize breaking/compatibility over style
- Draft: concrete endpoint contracts with method, path, request/response shapes, success/error codes, headers

### fastapi-python
- RORO: receive a Pydantic object, return an object; type-hint every signature; Pydantic models over raw dicts
- Guard clauses with early returns at function entry; happy path last; no else-after-return
- HTTPException with explicit status codes for expected errors; lifespan manager for startup/shutdown; middleware for logging
- snake_case file names (e.g. `routers/user_routes.py`); plain functions over classes for organization
- Async for all DB and external API I/O; never block inside async paths
- Dependency injection via Depends for DB session, config, auth
- Pydantic v2: ConfigDict(extra="forbid", str_strip_whitespace=True), @field_validator + @classmethod
- Structured routes: router → services → models → schemas separation

### supabase-postgres-best-practices
- Load BEFORE any database change — even a one-column migration or single query
- Index every FK plus frequent filters/sorts/joins; diagnose with EXPLAIN (ANALYZE, BUFFERS) and pg_stat_statements
- Bound parameters ALWAYS, never string-concatenated SQL (RN-11: title filter uses bound ILIKE/LOWER parameter)
- Pool connections, set idle timeouts, keep transactions short to avoid exhaustion and deadlocks
- Batch inserts and ON CONFLICT upserts for seeds; validate pagination as limit 1-100/default 20, offset >= 0 (RN-10)
- Detail rules live in references/ by prefix: query-*, conn-*, security-*, schema-*, lock-*, data-*, monitor-*
- RLS policies for multi-tenant; verify with tests; never concatenate user input into SQL

### postgresql-table-design
- PK on every reference table: BIGINT GENERATED ALWAYS AS IDENTITY (never serial); UUID only for distributed/opaque IDs
- Normalize to 3NF first; denormalize only for measured, high-ROI read wins
- NOT NULL everywhere semantically required; DEFAULTs for common values
- Types: TIMESTAMPTZ (never bare timestamp), NUMERIC(p,s) for money (never money), TEXT + CHECK (LENGTH(col) <= n) (never varchar/char), BOOLEAN NOT NULL
- Uniqueness (ISBN, email, one-profile-per-client) via UNIQUE; CHECK (price > 0) / CHECK (stock >= 0) with NOT NULL; explicit ON DELETE/UPDATE on every FK; snake_case unquoted identifiers
- PostgreSQL does NOT auto-index FK columns: create each FK index manually; use UNIQUE NULLS NOT DISTINCT (PG15+) when only one NULL allowed
- Case-insensitive lookups: expression index ON tbl (LOWER(col)), and query must use same expression
- Avoid: timestamp, char/varchar, money, serial — use timestamptz, text+CHECK, numeric, identity

### postgresql-optimization
- Prefer keyset pagination (WHERE id > $last_id) for large datasets; keep project's limit/offset contract but back it with covering indexes
- Composite indexes obey leftmost-prefix; INCLUDE (...) covering indexes for index-only scans; partial indexes for hot subsets; GIN for JSONB/FTS, GiST for ranges/geometry
- Kill N+1 with eager/selectin loading; never per-row queries in loops (Ej.6)
- Diagnose via EXPLAIN (ANALYZE, BUFFERS) plus pg_stat_statements; fix sequential scans on large tables first; drop zero-scan (idx_scan = 0) indexes
- Parameterized queries exclusively; RLS where multi-tenant; regular VACUUM/ANALYZE maintenance
- Cursor-based pagination over OFFSET for large datasets; window functions for analytics

### sqlalchemy-alembic-expert-best-practices-code-review
- Autogenerate (alembic revision --autogenerate) then hand-review every migration; never ship raw autogenerate (project: exactly 2 reviewed autogenerated migrations, Ej.3)
- New indexes use postgresql_concurrently=True inside autocommit blocks; unique constraints as concurrent-index-then-constraint two-step
- New FKs and CHECKs: add NOT VALID first, VALIDATE in a separate step to avoid table locks
- Column type changes via multi-step add/backfill/swap; never a single locking ALTER on live data
- Max 3 columns per non-unique index; no index redundant with a composite leftmost prefix; every query pattern must have a matching index
- Verify query patterns are indexed: SQLAlchemy select() with joinedload/selectinload must have covering indexes

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| AGENTS.md | C:\Users\Andres\Documents\Tecnicatura en Programación\2° Año\1° Cuatrimestre\Programación 3\Trabajos Prácticos\TP-U1a4\TP-U1a4\AGENTS.md | Index — references knowledge-base/*, CHANGES.md, .atl/skill-registry.md |
| CLAUDE.md | C:\Users\Andres\Documents\Tecnicatura en Programación\2° Año\1° Cuatrimestre\Programación 3\Trabajos Prácticos\TP-U1a4\TP-U1a4\CLAUDE.md | Index — references knowledge-base/*, CHANGES.md, .atl/skill-registry.md |

Read the convention files listed above for project-specific patterns and rules. All referenced paths have been extracted — no need to read index files to discover more.