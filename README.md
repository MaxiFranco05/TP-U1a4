# API de Librería — TP Unidades 1 a 4

> API REST construida con FastAPI + SQLAlchemy 2.0 async + PostgreSQL 16.
> Esta documentación cubre el estado final después de implementar C-01 a C-08.

---

## 📦 Estado actual de la fundación

Todos los changes C-01 a C-08 están `[x]` completados. El proyecto tiene:

- **C-01**: Scaffolding + healthchecks (base + `GET /health/live` y `GET /health/ready`)
- **C-02**: Modelos core + primera migración (constraints UNIQUE/CHECK, `Decimal` para dinero)
- **C-03**: Entidad `genero` + segunda migración (CRUD géneros, relación opcional `libro.genero_id`)
- **C-04**: CRUD catálogo + alta de libro con autorías (filtros case-insensitive, `IntegrityError → 409`)
- **C-05**: CRUD clientes + perfil único (RN-09: un perfil por cliente)
- **C-06**: Alta de venta con renglones + `BackgroundTasks` (RN-04 a RN-08, precios copiados server-side)
- **C-07**: Lecturas sin N+1 (carga anticipada `joinedload`/`selectinload`, queries fijas)
- **C-08**: Seed reproducible + suite `.http` + README final de entrega

---

## 🚀 Orden de arranque desde cero

### Paso 0 — Iniciar Docker Desktop

Asegurarse de que el daemon de Docker esté corriendo antes de levantar la base de datos:

```powershell
docker desktop start
```

### Paso 1 — Crear y activar el entorno virtual con Python 3.12

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

### Paso 2 — Instalar dependencias

```powershell
pip install -r requirements.txt
```

### Paso 3 — Configurar variables de entorno (`.env`)

Copiar `env.example` a `.env` (no versionado) y ajustar las credenciales locales que coincidan con `compose.yaml`:

```powershell
Copy-Item env.example .env
```

Valores de desarrollo local por defecto en `.env`:

```dotenv
DATABASE_URL=postgresql+asyncpg://libreria:libreria_dev_local@localhost:5433/libreria
SQL_ECHO=false
```

> **PA-01 (Python 3.12 en paralelo):** El proyecto requiere **Python 3.12** (`3.12.10` instalado en paralelo en el sistema). El entorno virtual `.venv` se crea explícitamente con `py -3.12 -m venv .venv`. No usar Python 3.14 como venv principal.

> **PA-04 (`compose.yaml` como comodidad local):** El archivo `compose.yaml` se incluye exclusivamente como comodidad de desarrollo local para levantar PostgreSQL 16 reproduciblemente sin alterar instalaciones del sistema operativo; **no forma parte de los artefactos exigidos por la consigna de entrega**.

### Paso 4 — Levantar PostgreSQL 16 en Docker

```powershell
docker compose up -d
docker compose ps
```

Verificar que el contenedor `tp_libreria_pg16` figure en estado `healthy` y acepte conexiones en el puerto `5433`:

```powershell
docker exec tp_libreria_pg16 pg_isready -U libreria -d libreria
```

### Paso 5 — Verificar estado de migraciones (Alembic asincrónico)

```powershell
.\.venv\Scripts\alembic current
```

### Paso 6 — Aplicar seed de datos reproducibles

```powershell
python seed_db.py
```

Debería imprimir algo como:

```
✅ Seed completado exitosamente
   - 3 editoriales
   - 3 géneros
   - 4 autores
   - 5 libros
   - 1 cliente con perfil
   - 1 venta de ejemplo con 2 renglones
```

### Paso 7 — Iniciar el servidor ASGI (`uvicorn`)

```powershell
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## 📡 Endpoints principales

### Sondas de salud

| Endpoint | Descripción |
|---|---|
| `GET /health/live` | `200 {"estado": "vivo"}` — sin tocar la base |
| `GET /health/ready` | `200 {"estado": "listo"}` — `SELECT 1` contra la base |

> **RN-12: sin traza interna** — los errores de DB se traducen a `"Base de datos no disponible"` sin exponer contraseñas ni nombres de tabla.

### Catálogo (módulo `libros`)

| Endpoint | Descripción |
|---|---|
| `POST /libros/` | Crear libro con autorías (201). ISBN repetido → 409. FK inexistente → 409. DTO inválido → 422. |
| `GET /libros/` | Listado paginado (`limit` 1-100/def.20, `offset` >=0). Filtro `titulo` case-insensitive con parámetro ligado. Filtro `genero_id`. |
| `GET /libros/{id}` | Detalle con **eager loading declarado** (C-07): `joinedload` editorial/género, `selectinload` autorías. Cero lazy loading. |

> **C-07 (Evidencia):** Con `SQL_ECHO=true`, la misma cantidad de queries se ejecuta independientemente de la cantidad de autores o renglones. Ejemplo de salida de consola:

```
INFO sqlalchemy.engine.Engine: SELECT libro.id, ... FROM libro ...
INFO sqlalchemy.engine.Engine: SELECT ... FROM editorial WHERE editorial.id = ...
INFO sqlalchemy.engine.Engine: SELECT ... FROM genero WHERE genero.id = ...
INFO sqlalchemy.engine.Engine: SELECT ... FROM libro_autor WHERE libro_id = ...
INFO sqlalchemy.engine.Engine: SELECT ... FROM autor WHERE autor.id = ...
```

Siempre 6 queries (1 base + 2 one-to-one + 1 colección), aunque el libro tenga 1 o 10 autores.

| Endpoint | Descripción |
|---|---|
| `GET /libros/?titulo=' OR '1'='1` | Inyección SQL segura → 200 con lista vacía (parámetro ligado, no concatena texto) |

### Ventas (módulo `ventas`)

| Endpoint | Descripción |
|---|---|
| `POST /ventas/` | Crear venta con renglones (201). ≥1 renglón y sin libros repetidos. Precio/copy desde libro al renglón (RN-06). Total calculado server-side (RN-07). `BackgroundTasks` aviso de comprobante (no bloquea respuesta). Sin PATCH en ventas (RN-08). |
| `GET /ventas/` | Listado paginado con `cliente` cargado (`joinedlist`). **No carga renglones** para evitar N+1 (US-031). |
| `GET /ventas/{id}` | Detalle con **eager loading fijo**: `joinedload` cliente, `selectinload` renglones + `libro`. Cantidad fija de queries aunque haya N renglones. |

> **C-07 (Evidencia):** Con `SQL_ECHO=true`, verificar que `GET /ventas/1` y `GET /libros/1` ejecutan la misma cantidad de queries que `GET /ventas/` y `GET /libros/` respectivamente, aun con más datos.

| Endpoint | Descripción |
|---|---|
| `GET /ventas/?limit=5&offset=0` | Listado paginado (RN-10). |

### Clientes (módulo `clientes`)

| Endpoint | Descripción |
|---|---|
| `POST /clientes/` | Crear cliente (201). Email único a nivel de base (RN-02, 409). |
| `GET /clientes/` | Listado paginado (RN-10). Sin perfil para evitar N+1. |
| `GET /clientes/{id}` | Cliente con perfil (objeto, no lista). Email repetido → 409 (RN-02). |
| `POST /clientes/{id}/perfil` | Segundo perfil para mismo cliente → 409 (RN-09, C-03 de los casos). |
| `GET /clientes/{id}/ventas` | Historial de ventas del cliente. |

---

## 📊 Evidencia C-07: Lecturas sin N+1

Para generar la evidencia de queries fijas:

1. Poner `SQL_ECHO=true` en el archivo `.env`
2. Levantar el servidor (`uvicorn app.main:app --host 127.0.0.1 --port 8000`)
3. Ejecutar las siguientes peticiones y contar las queries en consola:

### Con 1 libro/autor (datos mínimos semilla):

```bash
GET /libros/1
GET /ventas/1
```

### Con N libros/autores (después de correr `python seed_db.py`):

```bash
GET /libros/1
GET /ventas/1
```

**Expected output (consola):** Siempre la misma cantidad de queries, ej:

```
INFO sqlalchemy.engine.Engine: SELECT libro.id, libro.isbn, ... FROM libro WHERE libro.id = ? (params: (1,))
INFO sqlalchemy.engine.Engine: SELECT editorial.id, editorial.nombre, ... FROM editorial WHERE editorial.id = ? (params: (1,))
INFO sqlalchemy.engine.Engine: SELECT genero.id, genero.nombre, ... FROM genero WHERE genero.id = ? (params: (1,))
INFO sqlalchemy.engine.Engine: SELECT libro_autor.libro_id, ... FROM libro_autor WHERE libro_id = ? (params: (1,))
INFO sqlalchemy.engine.Engine: SELECT autor.id, autor.nombre, ... FROM autor WHERE autor.id IN (...) (params: (1,))
```

La cuenta no crece al agregar más autores/renglones porque todas las relaciones usan `joinedload` (one-to-one) o `selectinload` (colecciones) en una sola query cada una.

---

## 📦 Artefactos de entrega (C-08)

Los siguientes archivos forman el entregable final:

| Archivo | Descripción |
|---|---|
| `seed_db.py` | Script de seed reproducible con estado conocido (editoriales, géneros, autores, libros, cliente+perfil, venta de ejemplo). |
| `test/*.http` | Suite de pruebas `.http` que cubren C-01 a C-08, incluyendo evidencia C-07 (SQL_ECHO). |
| `requirements.txt` | Dependencias finales (igual a la versión actual). |
| `env.example` | Variables de entorno ejemplo (igual a la versión actual con `SQL_ECHO=false`). |
| `README.md` | Esta documentación — pasos desde cero + evidencia C-07 + decisiones PA-02 y PA-04. |

> **PA-02 (VPS/Easypanel fuera de la entrega):** Cualquier despliegue en VPS con Easypanel queda definido únicamente como ejercicio opcional **post-entrega** y fuera del alcance de corrección del trabajo práctico. La evaluación se realiza íntegramente en local siguiendo los pasos de esta guía.

> **PA-04 (`compose.yaml` solo dev):** El archivo `compose.yaml` es una comodidad de desarrollo local para levantar PostgreSQL 16 reproduciblemente. **No subirse al repositorio** como parte de la entrega corporativa; forma parte del entorno de desarrollo del equipo.

---

## 📜 Reglas aplicadas (desde `AGENTS.md` / `CLAUDE.md`)

No commitear de forma autónoma. Usar `Decimal` para dinero. Cargar relaciones con `joinedload`/`selectinload` (nunca lazy loading por defecto). Traducir `IntegrityError` a mensaje propio + 409/422. Nunca crear esquema con `create_all` — exclusivo Alembic. SQL concatenado con texto prohibido — usar parámetros ligados.

---

## 🛠️ Comandos útiles

| Comando | Descripción |
|---|---|
| `alembic upgrade head` | Aplicar todas las migraciones pendientes |
| `alembic downgrade -1` | Deshacer la última migración |
| `python seed_db.py` | Cargar datos reproducibles en la base |
| `SQL_ECHO=true uvicorn app.main:app --host 127.0.0.1 --port 8000` | Ver consultas SQL en consola (C-07 evidencia) |
| `pytest` | Ejecutar test suite |