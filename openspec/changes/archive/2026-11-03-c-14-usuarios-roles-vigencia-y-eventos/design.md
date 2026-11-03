# Design

## Context

Este diseño define la arquitectura e implementación para la administración de personal, gestión de roles con vigencia temporal, autoprotección de administradores y bitácora de auditoría de seguridad del módulo `app/modules/usuarios/`.
Se integra sobre la infraestructura de UoW y dependencias construida en C-11, C-12 y C-13 (`UsuariosUnitOfWork`, `requiere_rol("ADMIN")`, `verificar_password_cambiada` y `app/core/paginacion.py`).
Ver `proposal.md` para la motivación y `specs/user-management/spec.md` para los requerimientos funcionales observables.

## Goals / Non-Goals

**Goals:**
- Implementar `POST /usuarios` para alta de personal con contraseña provisoria, `debe_cambiar_password=True`, rol inicial y registro en `evento_seguridad` dentro de un único UoW (RN-06, RN-16).
- Implementar `GET /usuarios/{id}/roles` para consulta de roles activos e históricos del usuario (`404` si no existe).
- Implementar `POST /usuarios/{id}/roles` con validación estricta de `vence_en` con zona horaria en el futuro (`422` si falla, C-07), cierre automático de asignaciones vencidas preexistentes (`revocada_en = now()`), control de duplicados activos (RN-03, `409`) y bitácora en `evento_seguridad` (RN-16).
- Implementar `DELETE /usuarios/{id}/roles/{rol}` con revocación lógica (`revocada_en = now()`), regla de autoprotección administrativa (RN-05, C-08) y bitácora en `evento_seguridad` (RN-16).
- Implementar `GET /eventos` con envoltorio de paginación `{items, total, page, size, pages}` ordenado por `cuando` descendente (RN-16, C-16).
- Montar todas las rutas en `protected_group` con `requiere_rol("ADMIN")`.

**Non-Goals:**
- Gestión del catálogo y movimientos de stock (corresponde a C-15).
- Gestión de ventas y clientes (corresponde a C-16).

## Decisions

### Decisión 1: Validación estricta de `vence_en` en `RolAsignarRequest`
- **Decisión**: Se implementa un `@field_validator("vence_en")` en Pydantic:
  ```python
  @field_validator("vence_en")
  @classmethod
  def validate_vence_en(cls, v: datetime | None) -> datetime | None:
      if v is not None:
          if v.tzinfo is None:
              raise ValueError("La fecha de vencimiento debe incluir zona horaria")
          if v <= datetime.now(timezone.utc):
              raise ValueError("La fecha de vencimiento debe ser en el futuro")
      return v
  ```
- **Razón**: El caso de prueba C-07 del Parcial exige explícitamente responder `422 Unprocessable Entity` cuando la fecha no tenga zona horaria (`tzinfo is None`) o pertenezca al pasado.

### Decisión 2: Reemplazo automático de rol vencido en `asignar_rol`
- **Decisión**: Antes de insertar una nueva asignación de rol:
  1. El servicio consulta si existe una asignación previa abierta (`revocada_en IS NULL`) para ese `(usuario_id, rol)`.
  2. Si existe y su `vence_en` es nulo o futuro (`vence_en > now()`): el rol sigue vigente $\to$ lanza `HTTPException(409, detail="El usuario ya tiene ese rol asignado")` (RN-03).
  3. Si existe pero su fecha ya expiró (`vence_en <= now()`): se cierra la asignación anterior marcando `asignacion.revocada_en = datetime.now(timezone.utc)` y llamando a `await uow.asignaciones_rol.update(asignacion)`.
  4. Se crea la nueva `AsignacionRol` con `desde = now()` en la misma transacción del UoW.
- **Razón**: Mantiene la invariante del índice único parcial `(usuario_id, rol) WHERE revocada_en IS NULL`, permitiendo renovar roles expirados sin violar la restricción de unicidad y preservando el historial.

### Decisión 3: Autoprotección del Administrador (RN-05, C-08)
- **Decisión**: En `DELETE /usuarios/{id}/roles/{rol}`:
  1. Si `rol.upper() == "ADMIN"` y `usuario_id == admin_actor.id`:
     `raise HTTPException(status_code=409, detail="Un administrador no puede revocarse su propio rol ADMIN")`
  2. Si `rol.upper() == "ADMIN"`:
     Se consulta en la base de datos la cantidad de administradores vigentes distintos:
     `admins_vigentes = await uow.asignaciones_rol.contar_admins_vigentes()`
     Si `admins_vigentes <= 1`:
       `raise HTTPException(status_code=409, detail="No se puede revocar el rol: el sistema debe conservar al menos un administrador vigente")`
- **Razón**: Cumple estrictamente la regla de negocio RN-05 y los escenarios de prueba C-08, impidiendo que el sistema quede sin administradores activos.

### Decisión 4: Organización de routers y montaje en `app/main.py`
- **Decisión**: En `app/modules/usuarios/router.py` se definen:
  - `usuarios_router = APIRouter(prefix="/usuarios", tags=["Usuarios y Roles"], dependencies=[Depends(requiere_rol("ADMIN"))])`
  - `eventos_router = APIRouter(prefix="/eventos", tags=["Auditoría de Seguridad"], dependencies=[Depends(requiere_rol("ADMIN"))])`
  Ambos se incluyen en `protected_group` en `app/main.py`.
- **Razón**: `protected_group` ya aplica el filtro transversal de `verificar_password_cambiada`, y `requiere_rol("ADMIN")` garantiza que sólo administradores con credenciales al día y rol activo en BD puedan operar estas rutas.

### Decisión 5: Consulta paginada en `GET /eventos`
- **Decisión**: Utiliza los componentes de `app/core/paginacion.py` (`PaginationParams`, `paginate`, `PaginatedResponse`) sobre `EventoSeguridadRepository.listar_eventos_paginado`.
- **Razón**: Cumple con el envoltorio `{items, total, page, size, pages}` respondiendo `422` con `«La página {page} no existe: hay {pages}»` cuando `page > pages` (C-16).

## Risks / Trade-offs

- **[Riesgo] Violación de unicidad al reasignar roles**:
  - *Mitigación*: Se cierra la fila vencida previa marcando `revocada_en` dentro de la misma transacción antes de insertar la nueva asignación.
- **[Riesgo] Exposición de hashes en endpoints administrativos**:
  - *Mitigación*: `UsuarioReadResponse` excluye explícitamente `password_hash` y todos los DTOs de entrada declaran `extra="forbid"`.
