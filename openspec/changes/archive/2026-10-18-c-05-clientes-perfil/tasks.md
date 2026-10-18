# Tasks

## 1. Scaffold del módulo clientes

- [x] 1.1 Crear estructura `app/modules/clientes/{models.py,schemas.py,service.py,router.py,__init__.py}` y verificar que los archivos existen
- [x] 1.2 Agregar import del router en `app/main.py` y verificar que la app arranca sin errores

## 2. Modelos SQLModel (models.py)

- [x] 2.1 Definir clase `Cliente` con campos `id`, `nombre`, `email` y relationship `perfil` (joinedload, back_populates) y `ventas` (selectinload)
- [x] 2.2 Definir clase `PerfilCliente` con campos `id`, `cliente_id` (FK, UNIQUE), `telefono`, `direccion` y relationship `cliente` (back_populates)
- [x] 2.3 Verificar que `sqlmodel` genera metadata correcta ejecutando `python -c "from app.modules.clientes.models import Cliente, PerfilCliente; print('OK')"`

## 3. Migración Alembic

- [x] 3.1 Ejecutar `alembic revision --autogenerate -m "add cliente and perfil_cliente tables"` y revisar SQL generado
- [x] 3.2 Verificar constraints: `UNIQUE(email)` en cliente, `UNIQUE(cliente_id)` y `FK(cliente_id)` en perfil_cliente, índices en FK
- [x] 3.3 Aplicar migración: `alembic upgrade head` y verificar tablas creadas en PG
- [x] 3.4 Probar rollback: `alembic downgrade -1` y `alembic upgrade head` funcionan

## 4. DTOs / Schemas (schemas.py)

- [x] 4.1 Definir `ClienteCreate`, `ClienteUpdate`, `ClienteRead`, `PerfilClienteCreate`, `PerfilClienteRead` con validaciones (email, campos requeridos)
- [x] 4.2 Verificar que `ClienteRead` incluye `perfil: PerfilClienteRead | None` (objeto, no lista)

## 5. Service (service.py)

- [x] 5.1 Implementar `crear_cliente(session, data: ClienteCreate) -> ClienteRead` con traducción de `IntegrityError` (email único → 409)
- [x] 5.2 Implementar `listar_clientes(session, limit, offset) -> list[ClienteListItem]` con paginación
- [x] 5.3 Implementar `obtener_cliente(session, cliente_id) -> ClienteRead` con `joinedload(Cliente.perfil)`
- [x] 5.4 Implementar `actualizar_cliente(session, cliente_id, data: ClienteUpdate) -> ClienteRead` con PATCH parcial y traducción 409/404
- [x] 5.5 Implementar `crear_perfil(session, cliente_id, data: PerfilClienteCreate) -> PerfilClienteRead` con traducción 409 (perfil único) y 404 (cliente no existe)
- [x] 5.6 Implementar `obtener_ventas_cliente(session, cliente_id) -> list[VentaRead]` usando models de ventas
- [x] 5.7 Verificar que service no hace consultas N+1 (revisar queries con SQL_ECHO=true)

## 6. Router (router.py)

- [x] 6.1 Definir 6 endpoints: POST/GET/PATCH /clientes/, GET /clientes/{id}, POST /clientes/{id}/perfil, GET /clientes/{id}/ventas
- [x] 6.2 Validar paginación con `Query(ge=1, le=100)` para limit y `Query(ge=0)` para offset
- [x] 6.3 Usar `Depends(get_session)` y delegar todo al service
- [x] 6.4 Verificar códigos de respuesta: 201, 200, 404, 409, 422 según spec

## 7. Tests de evidencia (.http)

- [x] 7.1 Crear `test/c-05-clientes.http` con requests comentados C-05 para cada endpoint
- [x] 7.2 Incluir casos: creación exitosa, email duplicado (409), paginación, cliente con/sin perfil, perfil duplicado (409), ventas por cliente
- [x] 7.3 Ejecutar requests y verificar respuestas esperadas y ausencia de N+1 en consola (SQL_ECHO)

## 8. Seed de datos

- [x] 8.1 Agregar cliente con perfil y venta de ejemplo al script de seed para que `.http` corran reproduciblemente