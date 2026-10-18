# Guía de Desarrollo Local (`README.dev.md`)

> Documento de puesta en marcha para desarrollo local correspondiente al change **C-01 (`foundation-setup`)**.

---

## 1. Decisiones de entorno y alcance asentadas

- **PA-01 (Python 3.12 en paralelo):** El proyecto requiere **Python 3.12** (`3.12.10` instalado en paralelo en el sistema). El entorno virtual `.venv` se crea explícitamente con `py -3.12 -m venv .venv`.
- **Puerto de PostgreSQL 16 (`5433`):** Dado que el puerto `5432` del host se encuentra ocupado por un servicio PostgreSQL local preexistente, el contenedor de PostgreSQL 16 expone el puerto **`5433`** hacia el host (`5433:5432`). Tanto `.env` como `env.example` reflejan `localhost:5433`.
- **PA-04 (`compose.yaml` como comodidad local):** El archivo `compose.yaml` se incluye exclusivamente como comodidad de desarrollo local para levantar PostgreSQL 16 reproduciblemente sin alterar instalaciones del sistema operativo; **no forma parte de los artefactos exigidos por la consigna de entrega**.
- **PA-02 (Deploy en VPS / Easypanel fuera de la entrega):** Cualquier despliegue en VPS con Easypanel queda definido únicamente como ejercicio opcional **post-entrega** y fuera del alcance de corrección del trabajo práctico. La evaluación se realiza íntegramente en local siguiendo los pasos de esta guía.

---

## 2. Orden de arranque desde cero

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
*(En C-01 aún no existen versiones en `migrations/versions/`; la primera revisión se genera en C-02).*

### Paso 6 — Iniciar el servidor ASGI (`uvicorn`)
```powershell
.\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## 3. Verificación de sondas de salud (`/health`)

Con el servidor corriendo en `http://127.0.0.1:8000`:

1. **Sonda de vida (`GET /health/live`):**
   - Responde `200 OK` con `{"estado": "vivo"}` sin consultar la base de datos (incluso si el contenedor `db` está detenido).
2. **Sonda de disponibilidad (`GET /health/ready`):**
   - Con PostgreSQL 16 arriba (`docker compose start`): ejecuta `SELECT 1` y responde `200 OK` con `{"estado": "listo"}`.
   - Con PostgreSQL 16 detenido (`docker compose stop`): responde `503 Service Unavailable` con `{"detail": "Base de datos no disponible"}`, sin filtrar trazas, nombres de tablas/constraints ni cadenas de conexión (RN-12).
