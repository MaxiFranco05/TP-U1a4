# Spec Delta

## Purpose

Proporciona el CRUD completo de clientes y su perfil asociado (uno a uno), junto con la consulta del historial de ventas por cliente. Garantiza unicidad de email y perfil único por cliente, con paginación en listados y traducción de errores de base a códigos HTTP semánticos.

## ADDED Requirements

### Requirement: Crear cliente

El sistema DEBE permitir crear un cliente proporcionando nombre y email. El email DEBE ser único; duplicados DEBEN retornar 409 sin exponer detalles de base de datos.

#### Scenario: Crear cliente exitoso
- **WHEN** se envía POST /clientes/ con nombre y email válido no existente
- **THEN** se retorna 201 con el cliente creado incluyendo su id

#### Scenario: Email duplicado
- **WHEN** se envía POST /clientes/ con un email ya registrado
- **THEN** se retorna 409 con mensaje propio sin trazas internas

#### Scenario: Datos inválidos
- **WHEN** se envía POST /clientes/ con email malformado o campos faltantes
- **THEN** se retorna 422

### Requirement: Listar clientes paginado

El sistema DEBE permitir listar clientes con paginación controlada por `limit` (1-100, defecto 20) y `offset` (>=0). Parámetros fuera de rango DEBEN retornar 422.

#### Scenario: Listado con valores por defecto
- **WHEN** se envía GET /clientes/ sin parámetros de paginación
- **THEN** se retorna 200 con hasta 20 clientes y offset 0

#### Scenario: Listado con paginación personalizada
- **WHEN** se envía GET /clientes/?limit=5&offset=10
- **THEN** se retorna 200 con hasta 5 clientes saltando los primeros 10

#### Scenario: Parámetros de paginación inválidos
- **WHEN** se envía GET /clientes/?limit=0 o limit=101 o offset=-1
- **THEN** se retorna 422

### Requirement: Obtener cliente por ID con perfil

El sistema DEBE permitir obtener el detalle de un cliente por su ID, incluyendo su perfil como objeto anidado (no lista). Cliente inexistente DEBE retornar 404.

#### Scenario: Cliente existente con perfil
- **WHEN** se envía GET /clientes/{id} de un cliente con perfil
- **THEN** se retorna 200 con cliente y campo `perfil` como objeto con telefono y direccion

#### Scenario: Cliente existente sin perfil
- **WHEN** se envía GET /clientes/{id} de un cliente sin perfil
- **THEN** se retorna 200 con cliente y campo `perfil` como null

#### Scenario: Cliente inexistente
- **WHEN** se envía GET /clientes/{id} con ID que no existe
- **THEN** se retorna 404

### Requirement: Actualizar cliente parcialmente

El sistema DEBE permitir actualización parcial (PATCH) de nombre y/o email. Email duplicado DEBE retornar 409. Cliente inexistente DEBE retornar 404.

#### Scenario: Actualización exitosa de nombre
- **WHEN** se envía PATCH /clientes/{id} con solo nombre
- **THEN** se retorna 200 con cliente actualizado

#### Scenario: Actualización de email a uno existente
- **WHEN** se envía PATCH /clientes/{id} con email de otro cliente
- **THEN** se retorna 409

#### Scenario: Cliente inexistente
- **WHEN** se envía PATCH /clientes/{id} con ID que no existe
- **THEN** se retorna 404

### Requirement: Crear o actualizar perfil de cliente

El sistema DEBE permitir crear el perfil de un cliente (telefono, direccion) vía POST /clientes/{id}/perfil. Un cliente DEBE tener máximo un perfil; segundo intento DEBE retornar 409. Cliente inexistente DEBE retornar 404.

#### Scenario: Crear perfil exitoso
- **WHEN** se envía POST /clientes/{id}/perfil con telefono y direccion para cliente sin perfil
- **THEN** se retorna 201 con el perfil creado

#### Scenario: Segundo perfil para mismo cliente
- **WHEN** se envía POST /clientes/{id}/perfil para cliente que ya tiene perfil
- **THEN** se retorna 409

#### Scenario: Cliente inexistente
- **WHEN** se envía POST /clientes/{id}/perfil con ID de cliente que no existe
- **THEN** se retorna 404

### Requirement: Consultar ventas por cliente

El sistema DEBE permitir obtener el historial de ventas de un cliente vía GET /clientes/{id}/ventas. Cliente inexistente DEBE retornar 404.

#### Scenario: Cliente con ventas
- **WHEN** se envía GET /clientes/{id}/ventas para cliente con ventas
- **THEN** se retorna 200 con lista de ventas (cada una con id, fecha, total)

#### Scenario: Cliente sin ventas
- **WHEN** se envía GET /clientes/{id}/ventas para cliente sin ventas
- **THEN** se retorna 200 con lista vacía

#### Scenario: Cliente inexistente
- **WHEN** se envía GET /clientes/{id}/ventas con ID que no existe
- **THEN** se retorna 404