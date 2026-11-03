# Tasks

## 1. Contratos DTO y Validación Estricta (Strict TDD)

- [x] 1.1 Escribir pruebas unitarias (RED) para los contratos DTO en `test/test_user_management.py` e implementar en `app/modules/usuarios/schemas.py` los esquemas `UsuarioCreateRequest` (con contraseña provisoria $\le 72$ bytes UTF-8), `UsuarioReadResponse`, `RolAsignarRequest` (con validación de `vence_en` con zona horaria en el futuro $\to$ 422 si falla, C-07), `RolAsignacionResponse` y `EventoSeguridadResponse`, asegurando `extra="forbid"` y exclusión de `password_hash` (GREEN).

## 2. Repositorios de Roles y Eventos de Seguridad

- [x] 2.1 Escribir pruebas unitarias (RED) para consultas de persistencia e implementar en `app/modules/usuarios/repository.py`: en `AsignacionRolRepository`, métodos `get_asignacion_activa_por_rol(usuario_id, rol)`, `get_asignaciones_usuario(usuario_id)` y `contar_admins_vigentes()`; en `EventoSeguridadRepository`, método `listar_eventos_paginado(offset, limit)` (GREEN).

## 3. Servicio de Administración de Personal, Roles y Autoprotección

- [x] 3.1 Escribir pruebas unitarias (RED) para `crear_personal` e implementar en `app/modules/usuarios/service.py`: calcular hash provisorio fuera del UoW, crear `Usuario` con `debe_cambiar_password=True`, `AsignacionRol` inicial con `otorgada_por=admin.id` y registro en `evento_seguridad` en un solo UoW traduciendo email repetido a 409 (RN-06, RN-16) (GREEN).
- [x] 3.2 Escribir pruebas unitarias (RED) para `listar_roles` y `asignar_rol` e implementar en `app/modules/usuarios/service.py`: validar existencia de usuario (404), revocar automáticamente asignaciones abiertas vencidas (`vence_en <= now()`), rechazar asignaciones activas duplicadas (RN-03, 409, C-07) y registrar en `evento_seguridad` en la misma transacción (GREEN).
- [x] 3.3 Escribir pruebas unitarias (RED) para `revocar_rol` y `listar_eventos` e implementar en `app/modules/usuarios/service.py`: autoprotección de admin (rechazar auto-revocación de ADMIN y último admin con 409, RN-05, C-08), revocación lógica (`revocada_en = now()`), registro en `evento_seguridad` (RN-16) y consulta paginada de eventos con envoltorio estándar `{items, total, page, size, pages}` (GREEN).

## 4. Routers `/usuarios` y `/eventos` e Integración

- [x] 4.1 Escribir pruebas de integración API (RED) e implementar en `app/modules/usuarios/router.py` los routers `usuarios_router` (`POST /usuarios`, `GET /usuarios/{id}/roles`, `POST /usuarios/{id}/roles`, `DELETE /usuarios/{id}/roles/{rol}`) y `eventos_router` (`GET /eventos`), inyectando dependencias con sesión compartida (GREEN).
- [x] 4.2 Montar `usuarios_router` y `eventos_router` en `protected_group` en `app/main.py` con dependencia `requiere_rol("ADMIN")`; verificar que todas las rutas respondan en OpenAPI y estén protegidas (GREEN).

## 5. Verificación Integral y Casos de Prueba del Parcial

- [x] 5.1 Ejecutar la suite completa en `test/test_user_management.py` validando los casos `C-07` (revocación de rol quita permisos de inmediato en petición subsecuente y `/auth/yo` refleja el cambio; `vence_en` naive o pasado da 422), `C-08` (autoprotección de admin: auto-revocación y último admin dan 409) y `C-16` (paginación de eventos da 422 si `page > pages`); verificar 100% de tests en verde y sin regresiones en la suite combinada.
