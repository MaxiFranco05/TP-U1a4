# Design

## Context

El proyecto ya tiene la foundation (C-01) y módulos de catálogo (C-02, C-03, C-04) implementados siguiendo la arquitectura modular: `app/modules/<módulo>/{models,schemas,service,router}.py`. La base de datos PostgreSQL 16 está corriendo en localhost:5433 con migraciones aplicadas. El patrón de service con sesión como parámetro y DTOs separados (Create/Update/Read) está establecido. Errores de integridad se traducen a mensajes propios + 409/422 (RN-12). Paginación con `limit`/`offset` validados en `Query` (RN-10). Eager loading con `joinedload`/`selectinload` obligatorio.

## Goals / Non-Goals

**Goals:**
- Crear módulo `clientes` con modelos `Cliente` y `PerfilCliente` (uno a uno)
- Implementar service con lógica de CRUD y traducción de `IntegrityError`
- Exponer 6 endpoints REST según spec
- Generar migración Alembic para tablas `cliente` y `perfil_cliente` con constraints UNIQUE, FK e índices
- Registrar router en `app/main.py`

**Non-Goals:**
- Autenticación/autorización (fuera de alcance del TP)
- PATCH de perfil (solo POST para crear; actualización no requerida en US-020)
- Tests unitarios automatizados (solo evidencia `.http`)

## Decisions

### Modelo de datos: `Cliente` y `PerfilCliente` como tablas separadas

**Rationale:** El modelo de datos (KB-04) define `cliente` y `perfil_cliente` como tablas distintas con relación 1:0..1. `perfil_cliente.cliente_id` tiene UNIQUE para garantizar RN-09. Esto permite eager loading con `joinedload(Cliente.perfil)` y evita columnas nulas en `cliente`.

**Alternativa considerada:** Tabla única con columnas `telefono`, `direccion` en `cliente` (nullable). Rechazada: viola el modelo obligatorio y no permite constraint UNIQUE a nivel de base para RN-09.

### DTOs: Separados por operación

**Rationale:** Consistente con módulos existentes (`editoriales`, `generos`, `autores`, `libros`).
- `ClienteCreate`: `nombre`, `email` (sin `id`)
- `ClienteUpdate`: `nombre?`, `email?` (todos opcional, `exclude_unset`)
- `ClienteRead`: `id`, `nombre`, `email`, `perfil?: PerfilClienteRead`
- `PerfilClienteCreate`: `telefono`, `direccion`
- `PerfilClienteRead`: `id`, `cliente_id`, `telefono`, `direccion`

### Service: Sesión como parámetro, traducción centralizada

**Rationale:** Patrón establecido. El service recibe `session: AsyncSession` y expone métodos async. Un helper privado `_handle_integrity_error(exc: IntegrityError) -> Never` inspecciona `exc.orig` (asyncpg) y mapea:
- `unique_violation` en `cliente.email` → 409 "Email ya registrado"
- `unique_violation` en `perfil_cliente.cliente_id` → 409 "El cliente ya tiene un perfil"
- `foreign_key_violation` en `perfil_cliente.cliente_id` → 404 "Cliente no encontrado" (o 409 consistente con C-05)

### Router: Endpoints y validación de paginación

**Rationale:** FastAPI `Query` con `ge=1, le=100` para `limit` y `ge=0` para `offset` (RN-10). `GET /clientes/{id}/ventas` reutiliza lógica de `ventas` service si existe, o consulta directa con `selectinload(Venta.renglones).selectinload(RenglonVenta.libro)`.

### Migración Alembic

**Rationale:** Una sola revisión que crea ambas tablas en orden: `cliente` primero, luego `perfil_cliente` con FK a `cliente.id`. Índices explícitos en FK (PG no los crea automático). Constraints: `UNIQUE(email)`, `UNIQUE(cliente_id)`, `CHECK` no necesarios aquí.

### Eager loading

**Rationale:** `GET /clientes/{id}` → `joinedload(Cliente.perfil)` (to-one). `GET /clientes/` → sin relaciones (solo campos de cliente). `GET /clientes/{id}/ventas` → `selectinload(Venta.renglones).selectinload(RenglonVenta.libro)`.

## Risks / Trade-offs

- [Risk] `IntegrityError` mapping depende de nombres de constraint en PG → Mitigación: nombrar constraints explícitamente en migración (`uq_cliente_email`, `uq_perfil_cliente_cliente_id`, `fk_perfil_cliente_cliente_id`) y mapear por nombre de constraint en lugar de mensaje de error.
- [Risk] `GET /clientes/{id}/ventas` acopla módulo `clientes` a `ventas` → Mitigación: importar models de `ventas` solo en router; service de clientes no conoce ventas. Alternativa: mover endpoint a módulo `ventas` como `GET /ventas/?cliente_id=...` pero US-021 especifica ruta bajo `/clientes/`.
- [Trade-off] No PATCH de perfil → Simplifica implementación; US-020 solo pide POST. Si se requiere luego, se añade endpoint y DTO `PerfilClienteUpdate`.

## Migration Plan

1. Generar migración: `alembic revision --autogenerate -m "add cliente and perfil_cliente tables"`
2. Revisar SQL generado: verificar constraints, índices, orden de tablas
3. Aplicar: `alembic upgrade head`
4. Verificar: `alembic downgrade -1` + `upgrade head` funciona
5. Seed: script o comando que cree cliente con perfil y venta de ejemplo