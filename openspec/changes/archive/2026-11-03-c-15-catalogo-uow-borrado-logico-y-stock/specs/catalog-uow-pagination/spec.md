## ADDED Requirements

### Requirement: Catálogo sobre Repository y UnitOfWork
Los módulos `editoriales`, `generos`, `autores` y `libros` SHALL tener `repository.py` y `unit_of_work.py`; el router construye el UoW por dependencia con la sesión de `get_session` y lo pasa al servicio sin abrir, y el servicio lo abre con `async with uow:`. Los repositorios SHALL ejecutar solo `flush()`, nunca `commit()`.

#### Scenario: Alta confirmada por el UoW
- **WHEN** se crea una editorial válida
- **THEN** la respuesta es `201` y el `commit()` lo ejecuta el UoW al salir del bloque `async with`

#### Scenario: Error revierte la transacción
- **WHEN** una operación del servicio lanza una excepción dentro de `async with uow:`
- **THEN** el UoW hace `rollback()` y no queda ninguna escritura

### Requirement: Contratos de entrada estrictos
Todos los esquemas de entrada del catálogo SHALL declarar `extra="forbid"`; un campo no declarado SHALL responder `422`.

#### Scenario: Campo desconocido
- **WHEN** se envía `POST /editoriales` con un campo no declarado
- **THEN** la respuesta es `422`

### Requirement: Listados con envoltorio de paginación
Los listados de catálogo SHALL responder `{items, total, page, size, pages}` con `page >= 1` y `size` entre 1 y 100; `page > pages` SHALL responder `422`, y `total` SHALL contarse con los mismos filtros que la página.

#### Scenario: Filtro y total coherentes
- **WHEN** `GET /libros?titulo=' OR '1'='1` no coincide con ningún libro
- **THEN** la respuesta es `200` con `items: []` y `total: 0`

#### Scenario: Página fuera de rango
- **WHEN** se pide `page=2` con un filtro que produce una sola página
- **THEN** la respuesta es `422`

#### Scenario: Tamaño inválido
- **WHEN** se pide `size=101` o `page=0`
- **THEN** la respuesta es `422`

### Requirement: Grupo abierto y grupo protegido
Las lecturas públicas (`GET /libros`, `GET /libros/{id}`, `GET /editoriales`, `GET /generos`, `GET /autores`, `GET /editoriales/{id}/libros`, `GET /generos/{id}/libros`, `GET /autores/{id}/libros`) SHALL ser accesibles sin sesión. Las escrituras y la administración SHALL exigir `requiere_rol("ADMIN")` evaluado contra `asignacion_rol` vigentes en la base.

#### Scenario: Lectura sin sesión
- **WHEN** un visitante anónimo consulta `GET /libros`
- **THEN** la respuesta es `200`

#### Scenario: Listado de autores sin sesión
- **WHEN** un visitante anónimo consulta `GET /autores`
- **THEN** la respuesta es `200` con el envoltorio de paginación

#### Scenario: Escritura sin sesión
- **WHEN** un visitante anónimo envía `POST /libros`
- **THEN** la respuesta es `401`

#### Scenario: Escritura sin rol ADMIN
- **WHEN** un usuario con rol `CLIENTE` envía `POST /editoriales`
- **THEN** la respuesta es `403`

### Requirement: Precarga declarada en el repositorio
Toda relación leída por el catálogo (`editorial`, `genero`, `autorias.autor`) SHALL cargarse con `joinedload`/`selectinload` dentro del método del repositorio, sin carga perezosa.

#### Scenario: Detalle de libro con número fijo de consultas
- **WHEN** se lee un libro con 1 autor y otro con 3 autores
- **THEN** ambas lecturas ejecutan la misma cantidad de consultas SQL

### Requirement: Errores de integridad traducidos
Las violaciones `UNIQUE`/`FOREIGN KEY` SHALL traducirse a un mensaje propio con `409` o `422`, sin texto interno de la base ni traza, y sin verificación previa por consulta.

#### Scenario: ISBN vigente repetido
- **WHEN** se crea un libro con un ISBN ya vigente
- **THEN** la respuesta es `409` con mensaje propio
