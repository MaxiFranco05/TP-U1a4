# user-auth Specification

## Purpose
Define el comportamiento observable de los endpoints de autenticación (/auth): auto-registro de clientes, login con protección contra ataques de fuerza bruta y mitigación de enumeración de cuentas, auditoría independiente de intentos de acceso, gestión de cookies de sesión HttpOnly, introspección de identidad y cambio de contraseña con auditoría transaccional.

## Requirements

### Requirement: Auto-registro atomico de cliente
El endpoint POST /auth/registro SHALL permitir el auto-registro público de clientes creando en una única transacción atómica el Usuario, la AsignacionRol con rol CLIENTE y la ficha de Cliente. Si el correo electrónico ya existe en la tabla de usuarios o en la de clientes, el sistema SHALL rechazar la solicitud con 409 Conflict sin apropiarse de datos preexistentes ni dejar filas huérfanas.

#### Scenario: Registro exitoso de nuevo cliente
- **WHEN** un visitante envía POST /auth/registro con nombre, email y contraseña válida
- **THEN** el sistema responde 201 Created y persiste atómicamente el usuario, su rol CLIENTE y su cliente asociado con debe_cambiar_password en False

#### Scenario: Conflicto por correo ya existente en usuario o cliente
- **WHEN** un visitante envía POST /auth/registro con un email que ya pertenece a un usuario o cliente
- **THEN** el sistema responde 409 Conflict con un mensaje propio y no modifica ninguna tabla del sistema

#### Scenario: Rechazo por contraseña mayor a 72 bytes UTF-8 o campos no permitidos
- **WHEN** un visitante envía POST /auth/registro con una contraseña que excede 72 bytes en codificación UTF-8 o campos adicionales no permitidos
- **THEN** el sistema responde 422 Unprocessable Entity sin invocar bcrypt ni acceder a la base de datos

### Requirement: Control de tasa de intentos fallidos en login
El endpoint POST /auth/login SHALL consultar los intentos fallidos acumulados para el par (email, ip) en los últimos 60 segundos posteriores al último intento exitoso. Si la cantidad de intentos fallidos es mayor o igual a 5, el sistema SHALL registrar el intento fallido en intento_acceso y responder inmediatamente con 429 Too Many Requests y el encabezado Retry-After: 60 sin realizar cálculos criptográficos de contraseña con bcrypt.

#### Scenario: Bloqueo tras acumular 5 fallos en 60 segundos
- **WHEN** un cliente realiza 5 intentos fallidos consecutivos de login para el mismo email e IP dentro de 60 segundos
- **THEN** el quinto fallo posterior y los siguientes se registran como intentos fallidos en intento_acceso y responden 429 Too Many Requests con encabezado Retry-After: 60 sin ejecutar verificación bcrypt

#### Scenario: Reinicio de conteo tras login exitoso
- **WHEN** un usuario realiza intentos fallidos pero luego efectúa un login exitoso con credenciales correctas
- **THEN** el sistema reinicia el conteo de fallos de modo que futuros intentos sólo computen errores posteriores a dicho éxito

### Requirement: Autenticacion en tiempo constante contra usuario o dummy
El endpoint POST /auth/login SHALL verificar la contraseña provista utilizando bcrypt. Si el correo no existe en el sistema, SHALL ejecutar la verificación contra el hash ficticio dummy precalculado en el arranque, tardando un tiempo equivalente y respondiendo 401 Unauthorized con idéntico mensaje genérico para mitigar ataques de temporización y enumeración de usuarios.

#### Scenario: Autenticacion exitosa con credenciales validas
- **WHEN** un usuario activo envía POST /auth/login con email y contraseña correctos
- **THEN** el sistema responde 200 OK con mensaje de éxito, estado debe_cambiar_password y tiempo de expiración, sin incluir el token JWT en el cuerpo

#### Scenario: Credenciales invalidas por contraseña incorrecta
- **WHEN** se envía POST /auth/login con email existente pero contraseña incorrecta
- **THEN** el sistema responde 401 Unauthorized con el mensaje Credenciales inválidas

#### Scenario: Credenciales invalidas por usuario inexistente con tiempo constante
- **WHEN** se envía POST /auth/login con un email que no existe en el sistema
- **THEN** el sistema ejecuta verify_password contra dummy_password_hash y responde 401 Unauthorized con el mismo mensaje genérico

#### Scenario: Usuario deshabilitado o inactivo
- **WHEN** se envía POST /auth/login con credenciales válidas pero el usuario tiene activo en False
- **THEN** el sistema responde 401 Unauthorized con el mensaje genérico de credenciales inválidas

### Requirement: Auditoria de intentos de acceso en sesion y transaccion independientes
Cada invocación a POST /auth/login SHALL registrar una fila en la tabla intento_acceso con (cuando, email, ip, exito). Este registro SHALL ejecutarse mediante una sesión y transacción propias e independientes de la petición que se confirman siempre, preservando la bitácora aún si la autenticación falla o el request se cancela.

#### Scenario: Registro persistido en login fallido
- **WHEN** una petición de login fracasa y produce una respuesta 401 o 429
- **THEN** la tabla intento_acceso contiene la fila registrada con exito en False y los datos del intento

#### Scenario: Registro persistido en login exitoso
- **WHEN** una petición de login es válida y produce una respuesta 200
- **THEN** la tabla intento_acceso contiene la fila registrada con exito en True

### Requirement: Emision y revocacion de sesion via cookie HttpOnly
El endpoint POST /auth/login SHALL emitir el token JWT exclusivamente a través de la cookie access_token con banderas HttpOnly, SameSite=Lax, Max-Age y Secure configurable. El endpoint POST /auth/logout SHALL invalidar la sesión del cliente de forma idempotente eliminando dicha cookie con Max-Age cero, respondiendo 200 OK aun si la cookie original estuviera vencida.

#### Scenario: Cookie HttpOnly configurada en login exitoso
- **WHEN** un usuario inicia sesión satisfactoriamente en POST /auth/login
- **THEN** la respuesta incluye la cabecera Set-Cookie para access_token con HttpOnly, SameSite=Lax y Max-Age correspondiente al vencimiento del token

#### Scenario: Cierre de sesion borra cookie access_token de forma idempotente
- **WHEN** un cliente envía POST /auth/logout con o sin token válido previo
- **THEN** el sistema responde 200 OK y emite cabecera Set-Cookie para access_token con Max-Age cero expirando la cookie

### Requirement: Consulta de perfil de identidad actual
El endpoint GET /auth/yo SHALL permitir a un usuario autenticado obtener sus datos de perfil (id, email, nombre, debe_cambiar_password), la lista de sus roles actualmente vigentes en la base de datos (con revocada_en nulo y sin vencer) y los roles informativos declarados en el token JWT.

#### Scenario: Consulta de identidad por usuario autenticado
- **WHEN** un usuario con sesión activa envía GET /auth/yo
- **THEN** el sistema responde 200 OK con los datos del usuario, roles vigentes en la base y roles del token

#### Scenario: Rechazo por falta de credenciales o cookie vencida
- **WHEN** una petición envía GET /auth/yo sin la cookie access_token o con token expirado
- **THEN** el sistema responde 401 Unauthorized

### Requirement: Cambio de contraseña con registro de auditoria atomico
El endpoint POST /auth/cambiar-password SHALL permitir a un usuario autenticado cambiar su contraseña previa validación de la contraseña actual. La actualización de la contraseña, el reseteo de debe_cambiar_password a False y la inserción del registro correspondiente en evento_seguridad SHALL ejecutarse dentro de la misma transacción atómica de Unit of Work.

#### Scenario: Cambio de contraseña exitoso con auditoria
- **WHEN** un usuario autenticado envía POST /auth/cambiar-password con password_actual correcta y nueva password válida
- **THEN** el sistema actualiza password_hash, establece debe_cambiar_password en False, inserta una fila en evento_seguridad con el actor y la acción, y responde 200 OK

#### Scenario: Rechazo por contraseña actual incorrecta
- **WHEN** un usuario autenticado envía POST /auth/cambiar-password con una password_actual que no coincide
- **THEN** el sistema responde 401 Unauthorized sin modificar la contraseña ni insertar eventos de seguridad

#### Scenario: Rechazo por nueva contraseña mayor a 72 bytes UTF-8
- **WHEN** un usuario envía POST /auth/cambiar-password con una nueva password que excede 72 bytes UTF-8
- **THEN** el sistema responde 422 Unprocessable Entity
