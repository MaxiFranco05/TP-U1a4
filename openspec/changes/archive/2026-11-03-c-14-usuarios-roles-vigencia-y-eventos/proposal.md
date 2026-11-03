# Proposal

## Why

El sistema requiere mecanismos formales para la administración de personal y control de acceso RBAC por parte de los administradores (`ADMIN`). Este change implementa el alta de usuarios de personal con contraseñas provisorias y cambio obligatorio de clave (RN-06), la asignación y revocación de roles con vigencia temporal e historial inmutable en base de datos (RN-03, RN-04), la regla crítica de autoprotección administrativa para garantizar que un administrador no pueda revocar su propio rol ni dejar al sistema sin administradores vigentes (RN-05, C-08), y la consulta paginada de la bitácora de eventos de seguridad (RN-16, C-16).

## What Changes

- **Esquemas DTO (`app/modules/usuarios/schemas.py`)**:
  - `UsuarioCreateRequest`: creación de personal con `nombre`, `email`, `password` ($\le 72$ bytes UTF-8) y `rol` (`'ADMIN'`, `'VENDEDOR'`, `'CLIENTE'`) con `extra="forbid"`.
  - `UsuarioReadResponse`: datos de usuario sin exponer `password_hash`.
  - `RolAsignarRequest`: asignación de rol con `rol` y `vence_en` opcional con validación estricta de zona horaria obligatoria y fecha en el futuro ($\to$ `422` si no tiene timezone o ya venció, C-07), con `extra="forbid"`.
  - `RolAsignacionResponse`: detalle de la asignación (`id`, `usuario_id`, `rol`, `desde`, `vence_en`, `revocada_en`, `otorgada_por`).
  - `EventoSeguridadResponse`: evento de auditoría con `id`, `cuando`, `actor` y `accion`.
- **Repositorios y Unit of Work (`app/modules/usuarios/repository.py`, `app/modules/usuarios/unit_of_work.py`)**:
  - `AsignacionRolRepository`: métodos para obtener la asignación activa de un rol específico, contar administradores vigentes en el sistema y listar todas las asignaciones de un usuario (activas e históricas).
  - `EventoSeguridadRepository`: método para listar eventos paginados ordenados por `cuando` descendente.
- **Servicio (`app/modules/usuarios/service.py`)**:
  - `crear_personal`: calcula `hash_password` fuera del UoW; dentro de `async with uow:` crea `Usuario(debe_cambiar_password=True)`, `AsignacionRol` inicial con `otorgada_por=admin.id` y registra en `evento_seguridad` en la misma transacción (RN-06, RN-16). Correo duplicado $\to$ `409 Conflict`.
  - `listar_roles`: valida existencia del usuario (`404` si no existe) y devuelve sus asignaciones.
  - `asignar_rol`: valida existencia (`404`); si existe una asignación abierta pero vencida en el pasado (`vence_en <= now()`), la cierra (`revocada_en = now()`) y abre la nueva; si ya posee una asignación abierta vigente rechaza con `409 Conflict` (RN-03, C-07); registra en `evento_seguridad` en el mismo UoW (RN-16).
  - `revocar_rol`: valida existencia (`404`); autoprotección (RN-05): rechaza con `409 Conflict` si el admin intenta revocarse su propio rol `ADMIN` o si el sistema quedaría sin administradores vigentes (C-08); marca `revocada_en = now()` en la asignación activa sin borrar la fila; registra en `evento_seguridad` en el mismo UoW (RN-16).
  - `listar_eventos`: consulta paginada sobre `evento_seguridad` utilizando el envoltorio `{items, total, page, size, pages}` de `app/core/paginacion.py` (`422` si `page > pages`, C-16).
- **Rutas y Control de Acceso (`app/modules/usuarios/router.py`, `app/main.py`)**:
  - `usuarios_router` (`/usuarios`) y `eventos_router` (`/eventos`) montados en `protected_group` con dependencia `requiere_rol("ADMIN")`.

## Capabilities

### New Capabilities
- `user-management`: Administración de personal, asignación de roles con vigencia temporal, revocación con autoprotección administrativa y bitácora paginada de eventos de seguridad.

### Modified Capabilities
<!-- Ninguna capacidad existente cambia sus requerimientos -->

## Impact

- **Código Afectado**:
  - `app/modules/usuarios/`: ampliación de `schemas.py`, `repository.py`, `service.py` y `router.py`.
  - `app/main.py`: montaje de `usuarios_router` y `eventos_router` en `protected_group`.
  - `test/test_user_management.py`: suite exhaustiva de pruebas unitarias y de integración.
- **Riesgo y Gobernanza**: Nivel CRÍTICO / ALTO (administración de usuarios, control RBAC y autoprotección de roles). Casos evaluados: `C-07`, `C-08`, `C-16`.
