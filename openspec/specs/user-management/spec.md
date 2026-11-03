# user-management Specification

## Purpose

Define el comportamiento observable para la administración de personal, asignación y revocación de roles con vigencia temporal en base de datos, autoprotección del rol de administrador y auditoría paginada de eventos de seguridad.

## Requirements

### Requirement: Alta de personal con clave provisoria y bitacora
El endpoint POST /usuarios SHALL permitir a un usuario con rol ADMIN dar de alta a un nuevo integrante del personal creando el Usuario con debe_cambiar_password en True, su AsignacionRol inicial y registrando la acción en evento_seguridad dentro de una única transacción atómica.

#### Scenario: Alta exitosa de personal por administrador
- **WHEN** un administrador envía POST /usuarios con nombre, email, password provisoria y rol inicial válido
- **THEN** el sistema responde 201 Created y persiste el usuario con debe_cambiar_password en True, su asignación de rol y el evento de seguridad en la misma transacción

#### Scenario: Conflicto por correo electrónico ya registrado
- **WHEN** un administrador envía POST /usuarios con un email preexistente en la base de datos
- **THEN** el sistema responde 409 Conflict con un mensaje propio sin modificar la base de datos

#### Scenario: Rechazo por contraseña mayor a 72 bytes UTF-8 o cuerpo invalido
- **WHEN** un administrador envía POST /usuarios con una contraseña provisoria mayor a 72 bytes UTF-8 o datos inválidos
- **THEN** el sistema responde 422 Unprocessable Entity

### Requirement: Consulta de asignaciones de rol de usuario
El endpoint GET /usuarios/{id}/roles SHALL permitir a un usuario con rol ADMIN consultar todas las asignaciones de rol pertenecientes al usuario indicado, incluyendo asignaciones vigentes, revocadas y vencidas.

#### Scenario: Consulta exitosa de roles de usuario
- **WHEN** un administrador solicita GET /usuarios/{id}/roles para un usuario existente
- **THEN** el sistema responde 200 OK con el listado completo de asignaciones de rol del usuario

#### Scenario: Usuario no encontrado
- **WHEN** un administrador solicita GET /usuarios/{id}/roles para un identificador de usuario inexistente
- **THEN** el sistema responde 404 Not Found

### Requirement: Asignacion de rol con vigencia temporal y reemplazo de roles vencidos
El endpoint POST /usuarios/{id}/roles SHALL permitir a un usuario con rol ADMIN asignar un nuevo rol a un usuario existente con fecha de vencimiento opcional. Si vence_en se proporciona, SHALL validar que posea información de zona horaria y se encuentre en el futuro. Si el usuario posee una asignación de ese rol vencida, el sistema SHALL revocarla y abrir la nueva fila en la misma transacción.

#### Scenario: Asignacion exitosa de rol con vencimiento futuro
- **WHEN** un administrador envía POST /usuarios/{id}/roles con un rol válido y una fecha vence_en con zona horaria en el futuro
- **THEN** el sistema responde 201 Created, persiste la asignación de rol y registra el evento en evento_seguridad

#### Scenario: Rechazo de fecha de vencimiento sin zona horaria o en el pasado
- **WHEN** un administrador envía POST /usuarios/{id}/roles con una fecha vence_en naive (sin tzinfo) o con una fecha anterior al momento actual
- **THEN** el sistema responde 422 Unprocessable Entity

#### Scenario: Conflicto por rol activo vigente preexistente
- **WHEN** un administrador envía POST /usuarios/{id}/roles para un rol que el usuario ya posee actualmente abierto y vigente
- **THEN** el sistema responde 409 Conflict impidiendo asignaciones duplicadas simultáneas

#### Scenario: Reemplazo automatico de rol vencido en el pasado
- **WHEN** un administrador envía POST /usuarios/{id}/roles para un rol cuya asignación previa está abierta pero ya venció
- **THEN** el sistema revoca la asignación anterior estableciendo revocada_en y crea la nueva fila en la misma transacción respondiendo 201 Created

### Requirement: Revocacion de rol con autoproteccion administrativa
El endpoint DELETE /usuarios/{id}/roles/{rol} SHALL permitir a un usuario con rol ADMIN revocar una asignación de rol activa estableciendo revocada_en al momento actual sin eliminar físicamente la fila. El sistema SHALL impedir que un administrador se revoque su propio rol ADMIN y que el sistema quede sin administradores vigentes, respondiendo en ambos casos 409 Conflict.

#### Scenario: Revocacion exitosa de rol
- **WHEN** un administrador envía DELETE /usuarios/{id}/roles/{rol} para revocar un rol válido de otro usuario
- **THEN** el sistema responde 200 OK, actualiza revocada_en en la asignación activa sin borrarla y registra el evento en evento_seguridad

#### Scenario: Autoproteccion por intento de auto-revocacion de ADMIN
- **WHEN** un administrador envía DELETE /usuarios/{id}/roles/ADMIN especificando su propio identificador de usuario
- **THEN** el sistema rechaza la solicitud con 409 Conflict preservando el rol del administrador

#### Scenario: Autoproteccion por ultimo administrador del sistema
- **WHEN** un administrador intenta revocar el rol ADMIN a otro usuario pero este es el único administrador vigente restante
- **THEN** el sistema rechaza la solicitud con 409 Conflict garantizando que siempre exista al menos un administrador vigente

#### Scenario: Rol o usuario no encontrado para revocacion
- **WHEN** se intenta revocar un rol a un usuario inexistente o el usuario no posee dicho rol activo
- **THEN** el sistema responde 404 Not Found

### Requirement: Consulta paginada de la bitacora de eventos de seguridad
El endpoint GET /eventos SHALL permitir a un usuario con rol ADMIN consultar el listado histórico de eventos de seguridad ordenados cronológicamente descendente, utilizando el envoltorio estándar de paginación con total, page, size y pages.

#### Scenario: Consulta paginada exitosa de eventos
- **WHEN** un administrador solicita GET /eventos con parámetros de paginación válidos
- **THEN** el sistema responde 200 OK con el envoltorio paginado conteniendo items, total, page, size y pages

#### Scenario: Peticion de pagina superior al total de paginas
- **WHEN** un administrador solicita GET /eventos con un número de página mayor a la cantidad total de páginas calculadas
- **THEN** el sistema responde 422 Unprocessable Entity con el mensaje La página {page} no existe: hay {pages}

#### Scenario: Acceso denegado a usuarios sin rol ADMIN
- **WHEN** un usuario autenticado sin rol ADMIN vigente intenta acceder a cualquiera de las rutas de administración de usuarios o eventos
- **THEN** el sistema responde 403 Forbidden
