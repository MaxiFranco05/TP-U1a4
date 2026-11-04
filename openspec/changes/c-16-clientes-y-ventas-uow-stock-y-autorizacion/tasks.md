# Tasks

## 1. Clientes sobre Repository y UoW

- [ ] 1.1 Extender `ClienteRepository` (`get_con_perfil` con precarga de `perfil`/`usuario`), crear `PerfilClienteRepository` y `ClientesUnitOfWork`; verificar con tests de repositorio (alta, get con perfil, email duplicado, perfil duplicado) y que ningún repositorio hace `commit()`.
- [ ] 1.2 Reescribir `clientes/service.py` con UoW sin abrir y `async with uow:`; esquemas con `extra="forbid"`; listados con `PaginatedResponse`; verificar `201/404/409/422` (email repetido, segundo perfil, campo desconocido, `page > pages`) y `GET /clientes/{id}/ventas` con `404` para cliente inexistente.
- [ ] 1.3 Reescribir `clientes/router.py` (UoW por `Depends(get_session)`) y montarlo en `main.py` con `requiere_rol("VENDEDOR", "ADMIN")`; verificar `401` sin sesión y `403` con rol `CLIENTE` en cada ruta.

## 2. Venta atómica con descuento de stock

- [ ] 2.1 Hacer reutilizable el punto único de stock de C-15 para `VentasUnitOfWork` sin duplicar su lógica; verificar que los tests de C-15 siguen en verde y que el test AST de "una sola escritura de `.stock`" sigue pasando.
- [ ] 2.2 Crear `VentaRepository` (`get_detalle`, `listar` y `listar_por_usuario` paginados, precarga declarada incluyendo libros dados de baja) y `VentasUnitOfWork`; verificar con tests de repositorio y conteo fijo de consultas con 2 y 4 renglones.
- [ ] 2.3 Reescribir `crear_venta` en `ventas/service.py` (libros con `FOR UPDATE` en orden, precio copiado, total Decimal, descuento por renglón por el punto único con `venta_id` y `usuario_id`); verificar venta válida `201` con movimientos `-cantidad`, stock insuficiente en el 2.º renglón `409` con rollback total, cliente/libro inexistente o dado de baja `409` sin escrituras, y `stock == SUM(cantidad)` en todos los libros.
- [ ] 2.4 Agendar el aviso de comprobante en `BackgroundTasks` solo tras el commit (`asyncio.sleep(0.5)` + log); verificar que una venta confirmada lo registra y una revertida no.
- [ ] 2.5 Reescribir `POST /ventas` en el router con UoW por dependencia y `requiere_rol("VENDEDOR", "ADMIN")`; verificar DTO con `extra="forbid"`, renglones vacíos o repetidos `422`, `401` y `403`.

## 3. Lecturas con autorización de dueño

- [ ] 3.1 Implementar `GET /ventas` paginado con envoltorio (personal) y `GET /ventas/{id}` autorizado en el servicio (personal por roles vigentes en la base o dueño por `cliente.usuario_id`); verificar `200` para dueño y personal, `403` para cliente ajeno, `404` inexistente, y que los roles se leen de la base y no del token.
- [ ] 3.2 Implementar `GET /mis-ventas` paginado y montar `ventas` en `main.py` (rutas sin `requiere_rol` solo en `/ventas/{id}` y `/mis-ventas`); verificar ventas propias solamente, listado vacío sin cliente asociado y `422` con paginación inválida.
- [ ] 3.3 Verificar el detalle sin N+1: misma cantidad de consultas SQL con 2 y 4 renglones y título visible de libros dados de baja después de la venta.

## 4. Tests heredados, limpieza y cierre

- [ ] 4.1 Actualizar los tests y `.http` existentes de clientes y ventas (`c-05-clientes.http`, `c-06-ventas.http`, `c-07-c-08-evidencia.http`) a sesión/rol, envoltorio de paginación y descuento de stock; verificar `pytest` completo en verde (con `POSTGRES_PORT=5432`).
- [ ] 4.2 Verificar por búsqueda en `app/` que `core/pagination.py` ya no se importa y, si es así, eliminarlo; marcar C-16 `[x]` en `CHANGES.md` y sugerir el commit `C-16: clientes y ventas en UoW con descuento atomico de stock, dueño y sin N+1`.

## Workflow follow-up

- Archivar el change con `/opsx:archive` tras la revisión.
- El commit lo ejecuta el usuario (el flujo nunca commitea de forma autónoma).
