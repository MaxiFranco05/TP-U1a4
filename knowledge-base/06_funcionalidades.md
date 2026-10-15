# Funcionalidades

## Épica 1: Base, conexión y salud

### US-001 — Healthchecks
**Como** corrector **Quiero** `GET /health/live` (sin base) y `GET /health/ready` (`SELECT 1`) **Para** verificar que la app levanta y que hay conexión a la base.
**Criterios de aceptación**: live responde `{"estado": "vivo"}` 200 sin tocar la base; ready falla si la base no responde.
**Reglas relacionadas**: ninguna.

### US-002 — Configuración por entorno
**Como** alumno **Quiero** leer `DATABASE_URL` desde `.env` (con `env.example` sin secretos) **Para** no versionar credenciales.
**Criterios de aceptación**: sin `.env` la app no conecta; `env.example` documenta la forma del valor.
**Reglas relacionadas**: ninguna.

## Épica 2: Catálogo

### US-010 — CRUD de editoriales y géneros
**Como** librería **Quiero** altas, listados paginados, detalle y PATCH de editoriales y géneros **Para** mantener el catálogo.
**Criterios de aceptación**: 201/404/409/422 según corresponda; `GET /editoriales/{id}/libros` y `GET /generos/{id}/libros`.
**Reglas relacionadas**: RN-10.

### US-011 — CRUD de autores
**Como** librería **Quiero** altas, detalle, PATCH y `GET /autores/{id}/libros` con rol y orden **Para** gestionar autorías.
**Criterios de aceptación**: el listado por autor expone `rol` y `orden` de cada autoría.
**Reglas relacionadas**: RN-10.

### US-012 — Alta de libro con autores
**Como** librería **Quiero** dar de alta un libro con `editorial_id`, `genero_id` y `autores: [{autor_id, rol, orden}]` **Para** catalogar con sus autorías en una sola operación.
**Criterios de aceptación**: 201 con el detalle completo; editorial/autor inexistente → 409 sin `if` previo (la base rechaza la FK); validaciones → 422.
**Reglas relacionadas**: RN-01, RN-03.

### US-013 — Consulta de libros
**Como** librería **Quiero** listar (paginado, filtro por título y `genero_id`) y ver el detalle con editorial, género y autores **Para** buscar y fichar libros.
**Criterios de aceptación**: filtro case-insensitive con parámetro ligado (C-08: `' OR '1'='1` → 200 lista vacía); detalle con número fijo de consultas.
**Reglas relacionadas**: RN-10, RN-11.

## Épica 3: Clientes

### US-020 — CRUD de clientes y perfil
**Como** librería **Quiero** alta, detalle (con perfil), PATCH y `POST /clientes/{id}/perfil` **Para** registrar clientes.
**Criterios de aceptación**: email repetido → 409 (C-02); segundo perfil → 409 (C-03); `Cliente.perfil` es objeto, no lista.
**Reglas relacionadas**: RN-02, RN-09, RN-10.

### US-021 — Ventas por cliente
**Como** librería **Quiero** `GET /clientes/{id}/ventas` **Para** ver el historial de compras.
**Criterios de aceptación**: 200 con la lista; cliente inexistente → 404.
**Reglas relacionadas**: ninguna.

## Épica 4: Ventas

### US-030 — Alta de venta con renglones
**Como** librería **Quiero** `POST /ventas/` con `{cliente_id, renglones: [{libro_id, cantidad}]}` **Para** registrar la venta con precios copiados y total calculado.
**Criterios de aceptación**: 201 con cliente y renglones (precio copiado, subtotal, total); libro/cliente inexistente → 409 (C-05); venta vacía o libro repetido → 422 (RN-05); precio/total/fecha no viajan en el DTO; al registrar se agenda el aviso con `BackgroundTasks`.
**Reglas relacionadas**: RN-04, RN-05, RN-06, RN-07, RN-08.

### US-031 — Consulta de ventas
**Como** librería **Quiero** listar (paginado) y ver el detalle con cliente y renglones **Para** auditar ventas.
**Criterios de aceptación**: detalle con número fijo de consultas; no existe PATCH de ventas.
**Reglas relacionadas**: RN-08, RN-10.

## Épica 5: Entrega y evidencia

### US-040 — Migraciones y seed reproducibles
**Como** corrector **Quiero** `alembic upgrade head` en base vacía + script de seed **Para** partir de un estado conocido.
**Criterios de aceptación**: dos migraciones (segunda agrega `genero`); `downgrade -1` + `upgrade head` funciona; cada migración autogenerada fue leída (y comentada si se corrigió).
**Reglas relacionadas**: ninguna.

### US-041 — Tests `.http` y evidencia C-07
**Como** corrector **Quiero** `test/*.http` con C-01 a C-08 comentados y evidencia de consultas fijas **Para** verificar comportamiento y ausencia de N+1.
**Criterios de aceptación**: C-01 422 sin ejecutar handler; C-04 409; C-06 201 con precios y total; C-07 misma cantidad de queries con 1 o N autores/renglones.
**Reglas relacionadas**: RN-01, RN-05, RN-09, RN-10, RN-11.
