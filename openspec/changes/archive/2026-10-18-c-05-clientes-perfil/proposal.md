# Proposal

## Why

Implementar el CRUD completo de clientes y sus perfiles (US-020) y la consulta de ventas por cliente (US-021). Esto completa la Épica 3 (Clientes) y habilita la Épica 4 (Ventas) que requiere `cliente_id` existente. Las reglas RN-02 (email único) y RN-09 (máximo un perfil) son restricciones de base que deben traducirse a 409 sin exponer detalles internos (RN-12).

## What Changes

- Nuevo módulo `app/modules/clientes/` con models, schemas, service, router
- Endpoints:
  - `POST /clientes/` — Alta de cliente (DTO sin `id`)
  - `GET /clientes/` — Listado paginado (RN-10)
  - `GET /clientes/{id}` — Detalle con perfil anidado (objeto, no lista)
  - `PATCH /clientes/{id}` — Actualización parcial
  - `POST /clientes/{id}/perfil` — Crear/actualizar perfil (único por cliente, RN-09)
  - `GET /clientes/{id}/ventas` — Historial de ventas (US-021)
- Migración Alembic para tablas `cliente` y `perfil_cliente` con FK, UNIQUE, índices
- Tests `.http` para evidencia de comportamiento y ausencia de N+1

## Capabilities

### New Capabilities

- `clientes`: CRUD de clientes, gestión de perfil uno-a-uno, y consulta de ventas por cliente. Cubre US-020 y US-021.

### Modified Capabilities

None.

## Impact

- **Código nuevo**: `app/modules/clientes/{models,schemas,service,router}.py`
- **Migración**: Nueva revisión Alembic para `cliente` y `perfil_cliente`
- **App principal**: Registro del router en `app/main.py`
- **Tests**: Archivos `.http` en `test/` para C-05
- **Dependencias**: Requiere C-01 (foundation) y C-02 (migrations base) ya completados