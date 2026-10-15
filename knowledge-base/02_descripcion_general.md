# Descripción General

## Stack tecnológico

| Capa | Tecnología | Versión mínima |
|---|---|---|
| Lenguaje | Python | 3.12 |
| Framework web | FastAPI (todo `async def`) | 0.111 |
| Modelos y contratos | SQLModel | 0.0.24 |
| ORM / motor | SQLAlchemy 2.0 asincrónico | 2.0 |
| Driver PG | asyncpg | 0.30 |
| Base de datos | PostgreSQL | 16 |
| Migraciones | Alembic (plantilla asincrónica) | 1.13 |
| Configuración | python-dotenv (`.env` no versionado) | 1.0 |
| Servidor ASGI | uvicorn (vía `fastapi[standard]`) | — |
| Base de dev | PostgreSQL 16 en Docker local | 16 |

## Arquitectura general

Monolito modular por dominio funcional: cada módulo (`editoriales`, `generos`, `autores`, `libros`, `clientes`, `ventas`, `health`) tiene `models.py`, `schemas.py`, `service.py` y `router.py`. El router recibe y delega, el service concentra la lógica (recibe la sesión como parámetro), los schemas separan contratos de tablas.

```
Cliente HTTP (.http) → Router (recibe, declara respuesta) → Service (lógica + sesión)
→ SQLAlchemy async → PostgreSQL 16
```

Decisiones de alto nivel: motor y fábrica de sesiones creados en el `lifespan` y guardados en `app.state` (se cierra el motor al apagar); una sesión por petición vía `Depends(get_session)` con `expire_on_commit=False`; `DATABASE_URL` desde el entorno; esquema creado **exclusivamente** con Alembic (sin `create_all`); dinero siempre con `Decimal`, nunca `float`.

## Integraciones externas

Ninguna. Única dependencia de infraestructura: PostgreSQL 16. El aviso de comprobante al registrar una venta se simula con `BackgroundTasks` + `await asyncio.sleep(0.5)` y un log (no es una integración real).

## API REST

Recursos y operaciones principales (ver consigna para la tabla completa):

- `GET /health/live` (sin base) y `GET /health/ready` (`SELECT 1`).
- CRUD paginado de `editoriales`, `generos`, `autores`, `libros`, `clientes` (POST 201, GET, PATCH parcial con `exclude_unset`).
- `POST /libros/` con `autores: [{autor_id, rol, orden}]`; `GET /libros/` con `limit/offset/titulo/genero_id`; `GET /libros/{id}` con editorial, género y autores.
- `POST /clientes/{id}/perfil`, `GET /clientes/{id}/ventas`.
- `POST /ventas/` con `{cliente_id, renglones: [{libro_id, cantidad}]}` (precios y total calculados por el servidor); `GET /ventas/`, `GET /ventas/{id}` con cliente y renglones.
- Códigos: 201 al crear, 404 si no existe, 409 si la base rechaza, 422 si el contrato no se cumple.
