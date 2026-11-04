# Tasks

## 1. Repositorios y UoW del catálogo

- [x] 1.1 Crear `repository.py` y `unit_of_work.py` en `editoriales`, `generos` y `autores` (heredando de `BaseRepository`/`UnitOfWork`, solo `flush()`); verificar con tests unitarios de repositorio (alta, get, count con filtros) en verde.
- [x] 1.2 Crear `LibroRepository` (`SoftDeleteRepository[Libro]`, precarga de `editorial`, `genero`, `autorias.autor` declarada adentro), `MovimientoStockRepository` y `LibrosUnitOfWork`; verificar que el detalle de un libro con 1 y con 3 autores ejecuta igual cantidad de consultas SQL.

## 2. Punto único de stock

- [x] 2.1 Implementar el método único `registrar_movimiento_stock` (valida `stock + cantidad >= 0`, actualiza `libro.stock`, agrega `MovimientoStock`); verificar con tests de invariante `stock == SUM(cantidad)` tras alta, reposición y cantidad que dejaría stock negativo (rechazo).
- [x] 2.2 Test de regresión que confirme por búsqueda en `app/` que ningún otro módulo asigna `libro.stock` directamente.

## 3. Servicios, contratos y paginación

- [x] 3.1 Reescribir los servicios de `editoriales`, `generos` y `autores` para recibir el UoW sin abrir y usar `async with uow:`; esquemas con `extra="forbid"` y listados con `PaginatedResponse`; verificar `422` por campo desconocido, `page=0`, `size=101` y `page > pages`, y que `total` respeta los filtros.
- [x] 3.2 Reescribir el servicio de `libros`: `POST` con `stock_inicial` y movimiento `"Stock inicial"`, `PATCH` (solo `titulo`/`precio`, `stock` → `422`), `DELETE` con baja lógica, `POST /{id}/reponer`, `GET /{id}/movimientos`; traducir `IntegrityError` a `409`/`422`. Verificar casos de la consigna: reponer 200 con movimiento, baja 204 y desaparece, ISBN reutilizable 201, segundo vigente 409, reponer libro dado de baja 409, `' OR '1'='1` con `total: 0`, `page=2` con filtro 422.

## 4. Routers y grupos de acceso

- [x] 4.1 Construir el UoW por dependencia en cada router (sesión de `get_session` compartida con `requiere_rol`); separar routers públicos (lecturas abiertas) y protegidos (`requiere_rol("ADMIN")`) y registrarlos en `open_group`/`protected_group` de `app/main.py`; verificar con tests: lecturas abiertas `200` sin sesión, escrituras `401` sin sesión y `403` con rol `CLIENTE`.

## 5. Actualización de tests y documentación

- [x] 5.1 Adaptar `test_generos_and_migration_002.py` y los `.http` de `libros`, `editoriales` y `autores` al envoltorio de paginación, `stock_inicial` y autenticación; verificar que `pytest` de todo el repo queda en verde sin regresiones.
- [x] 5.2 Marcar C-15 `[x]` en `CHANGES.md` al terminar y dejar sugerido el commit `C-15: catalogo sobre Repository/UoW, borrado logico de libros y punto unico de stock`.

## Workflow follow-up

- Archivar el change con `/opsx:archive` tras la revisión.
- El commit lo ejecuta el usuario (el flujo nunca commitea de forma autónoma).
