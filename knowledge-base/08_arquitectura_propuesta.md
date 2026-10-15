# Arquitectura Propuesta

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|---|---|---|
| Módulo funcional | `app/modules/<módulo>/{models,schemas,service,router}.py` | Estructura obligatoria; mismo esqueleto en los 7 módulos |
| Service con sesión como parámetro | `service.py` de cada módulo | La lógica vive en el service; el router solo recibe y delega |
| DTO separados de tablas | `schemas.py` (`Create`/`Update`/`Read`) | Contratos estables; altas sin `id`; PATCH con `exclude_unset` |
| Lifespan + `app.state` | `app/main.py` | Motor y sesiones nacen y mueren con la app |
| Dependencia por petición | `get_session` + `Depends()` | Una sesión por request, `expire_on_commit=False` |
| Objeto de asociación | `LibroAutor` (en `libros`), `PerfilCliente` (en `clientes`), `RenglonVenta` (en `ventas`) | Las relaciones con datos propios son entidades |
| Traducción de errores | services | `IntegrityError` → mensaje propio + 409/422 (RN-12) |
| Eager loading declarado | lecturas con relaciones | `joinedload` (a uno) / `selectinload` (colecciones); cero lazy loading |
| Background task | alta de venta | Aviso de comprobante fuera del camino de la respuesta |

## Estructura de directorios

```
TP-U1a4/
├── app/
│   ├── main.py                    # app, lifespan, registro de routers
│   ├── core/
│   │   ├── config.py              # DATABASE_URL desde el entorno
│   │   └── database.py            # motor, fábrica de sesiones, get_session
│   └── modules/
│       ├── health/ models.py schemas.py service.py router.py
│       ├── editoriales/ ... (igual esqueleto)
│       ├── generos/ ...           # LibroAutor vive en libros
│       ├── autores/ ...
│       ├── libros/ ...            # + LibroAutor
│       ├── clientes/ ...          # + PerfilCliente
│       └── ventas/ ...            # + RenglonVenta
├── migrations/                    # Alembic + versiones (mínimo 2)
├── test/                          # .http con C-01..C-08 comentados
├── knowledge-base/                # esta KB (documentación, no se evalúa)
├── discovery/                     # discovery.md (documentación, no se evalúa)
├── .env                           # no versionado | env.example versionado
├── requirements.txt
└── README.md                      # pasos desde cero + evidencia C-07
```

## Seguridad

- Autenticación/autorización: no hay (fuera de alcance del TP).
- Validación de input: DTO + `Query` con límites (RN-10); PATCH parcial.
- SQL: siempre parámetros ligados; prohibida la concatenación de texto (RN-11, C-08).
- Secrets: `DATABASE_URL` en `.env` (no versionado); `env.example` sin secretos; `alembic.ini` sin contraseñas.
- Unicidad y FK: las garantiza la base, no consultas previas con `if`.

## Variables de entorno

| Variable | Descripción | Ejemplo | Sensible |
|---|---|---|---|
| `DATABASE_URL` | URL asyncpg de PostgreSQL 16 | `postgresql+asyncpg://user:pass@localhost:5432/libreria` | Y |
| `SQL_ECHO` | Muestra consultas en consola (evidencia C-07) | `true` | N |
