# Parcial: Librería con Acceso, Transacciones y Despliegue en el VPS

> **Tecnicatura Universitaria en Programación — Universidad Tecnológica Nacional (UTN)**  
> **Materia**: Programación III  
> **Unidad**: 1 a 6 — Del Objeto a la Transacción  
> **Grupo**: LocalHost  
> **Integrantes**:
> - Máximo Franco
> - Andrés Donoso
> - Octavio Roco

---

## 📖 Descripción General del Proyecto

Este proyecto amplía el Trabajo Práctico de los capítulos 1 a 4 y cubre integralmente hasta el capítulo 6 de la materia:
1. **Arquitectura en 5 capas**: `Router → Service → Unit of Work → Repository → Model`.
2. **Identidad, Roles y Autenticación**:
   - Contraseñas hasheadas con `bcrypt` fuera del bucle de eventos (`asyncio.to_thread`) y bajo semáforo concurrente (`asyncio.Semaphore`).
   - Sesión basada en cookie `HttpOnly` `access_token` firmada con PyJWT (HS256).
   - Autorización consultando la tabla `asignacion_rol` en la base de datos en cada petición con soporte de vigencia temporal (`desde`, `vence_en`, `revocada_en`).
   - Dos grupos de rutas: grupo **abierto** (rutas públicas y `/auth`) y grupo **protegido** (aplica verificación de rol y control del cambio obligatorio de contraseña `debe_cambiar_password`).
3. **Persistencia y Transaccionalidad**:
   - `BaseRepository[T]` y `SoftDeleteRepository[T]` (borrado lógico con `borrado_en` e índices únicos parciales `WHERE borrado_en IS NULL`).
   - `UnitOfWork` asincrónico por módulo que abre transacciones explícitas, confirma al salir del bloque y revierte ante cualquier excepción.
   - Punto único de escritura de stock (`libro.stock == SUM(movimiento_stock.cantidad)`).
   - Tabla `movimiento_stock` de **sólo-agregado** protegida en PostgreSQL mediante un disparador (`TRIGGER`) instalado por la **Migración 004** escrita a mano.
   - Prevención exhaustiva de N+1 mediante precarga anticipada (`joinedload` y `selectinload`).
4. **Despliegue del TP 1-4 en VPS (`despliegue/`)**:
   - Contenedor Docker basado en `python:3.12-alpine` (< 100 MB), usuario sin privilegios `USER appuser`, sin secretos en la imagen, `HEALTHCHECK` activo contra `/health/ready`, y arranque con migraciones automáticas (`alembic upgrade head`).

---

## 🚀 Puesta en Marcha desde Cero

### Requisitos Previos
- **Python 3.12** instalado en el sistema (`py -3.12 --version` o `python3.12 --version`).
- **PostgreSQL 16** en ejecución (local o en contenedor Docker).

### 1. Clonar el Repositorio y Crear el Entorno Virtual
```powershell
# En Windows PowerShell:
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# En Linux / macOS:
python3.12 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar Dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configurar el Archivo de Entorno (`.env`)
Copiar la plantilla `env.example` a `.env` (este archivo no se versiona):
```bash
cp env.example .env     # En Linux / macOS
Copy-Item env.example .env  # En PowerShell
```

Generar una clave de firma criptográfica para JWT y configurarla en `.env`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Ajustar las variables en `.env` según la configuración local de PostgreSQL:
```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=tu_password_local
POSTGRES_DB=libreria
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

JWT_SECRET=clave_generada_con_secrets_token_hex_32
JWT_EXPIRATION_SECONDS=1800
BCRYPT_ROUNDS=12
COOKIE_SECURE=false

DB_POOL_SIZE=5
SQL_ECHO=false
```

### 4. Aplicar Migraciones de la Base de Datos (Alembic)
Aplica las 4 migraciones (001 a 004), creando las 14 tablas e instalando la función y disparador de sólo-agregado:
```bash
alembic upgrade head
```

### 5. Poblar el Estado Canónico Inicial (`seed.py`)
Ejecutar el script canónico idempotente:
```bash
python seed.py
```
El script vacía todas las tablas con `RESTART IDENTITY CASCADE` y carga el estado de referencia:
- **5 usuarios**:
  - `admin@example.com` (`ADMIN`, contraseña: `Admin123!`)
  - `admin2@example.com` (`ADMIN`, contraseña: `Admin123!`)
  - `vendedor@example.com` (`VENDEDOR`, contraseña: `Vendedor123!`)
  - `ana@example.com` (`CLIENTE`, contraseña: `Cliente123!`)
  - `nuevo@example.com` (`VENDEDOR`, contraseña: `Nuevo123!`, con `debe_cambiar_password=True`)
- **Catálogo**: 3 editoriales, 3 géneros, 6 autores y 5 libros con stock exacto:
  - *Rayuela* (stock: 10, precio: $25000.00)
  - *Antología de la literatura fantástica* (stock: 5, precio: $30000.00)
  - *Ficciones* (stock: 8, precio: $22000.00)
  - *Respiración artificial* (stock: 3, precio: $18000.00)
  - *Bestiario* (stock: 1, precio: $15000.00)
- **3 clientes**: Lucía Fernández (con PerfilCliente), Tomás Ríos (sin usuario), Ana Paz (con usuario_id de Ana).
- **1 venta**: Venta #1 de Lucía Fernández registrada por `vendedor@example.com` ($69000.00, 1 Rayuela + 2 Ficciones).
- **7 movimientos de stock**: 5 de "Stock inicial" + 2 salidas por la Venta #1 (invariante `stock == SUM(cantidad)` verificada).
- **1 evento de seguridad**: `actor="SISTEMA"`, `accion="Carga de los datos iniciales"`.

### 6. Iniciar el Servidor ASGI (`uvicorn`)
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
La documentación interactiva OpenAPI (Swagger) queda disponible en `http://127.0.0.1:8000/docs`.

---

## 🧪 Pruebas Automatizadas y Casos de Evaluación

### Suite Completa de Tests (Strict TDD)
Ejecutar la suite automatizada con pytest:
```bash
pytest
```
La suite cuenta con 167 tests automatizados en verde que cubren contratos, ciclo de vida, modelos, repositorios, UoW, auth con bcrypt/JWT, roles y vigencia, stock, ventas, trigger de sólo-agregado y empaquetador.

### Casos de Evaluación C-01 a C-16 (`test/parcial_casos.http`)
La carpeta `test/` incluye `parcial_casos.http` documentando los 16 casos mínimos de evaluación exigidos por la consigna:
- **C-01**: Parámetro de ruta no entero con sesión iniciada → `422 Unprocessable Entity`.
- **C-02**: Registro con email duplicado de usuario o de cliente existente → `201` y `409 Conflict`.
- **C-03**: Cookie `access_token` en el login (`HttpOnly`, `SameSite=Lax`); rechazo de `Authorization: Bearer` → `401`.
- **C-04**: Contraseña incorrecta y correo inexistente (tiempo y mensaje uniforme) → `401 Unauthorized`.
- **C-05**: Seis intentos fallidos seguidos → Rate Limit con `429 Too Many Requests` y `Retry-After`.
- **C-06**: 401 contra 403, y lo propio (el cliente ve su venta con 200 y la ajena con 403).
- **C-07**: Revocar un rol con sesión abierta (403 inmediato en la siguiente petición); vencimientos inválidos (422).
- **C-08**: Autoprotección: el administrador no puede revocarse su propio rol ADMIN (409).
- **C-09**: Cambio obligatorio de contraseña: ruta `/auth/cambiar-password` permitida, grupo protegido habilitado tras el cambio con la misma sesión.
- **C-10**: Venta válida con dos renglones: descuento atómico de stock, movimientos registrados y aviso en background.
- **C-11**: Venta con stock insuficiente: rollback total (409), ningún stock alterado, invariante intacta.
- **C-12**: Venta con cliente/libro inexistente o libro dado de baja → `409 Conflict`.
- **C-13**: Reponer stock (200), baja lógica (204), alta reutilizando el mismo ISBN (201) y segundo libro activo repetido (409).
- **C-14**: Intentos de `UPDATE` y `DELETE` sobre `movimiento_stock` en `psql` rechazados por el trigger.
- **C-15**: Detalle de venta con 2 y 4 renglones ejecutando la misma cantidad fija de consultas SQL (2 queries).
- **C-16**: Búsqueda segura con parámetros ligados, paginación con filtros (`page > pages → 422`), PATCH parcial y rechazo de `stock` en PATCH (`422`).

### Script SQL de Sólo-Agregado y Evidencias
- `test/solo_agregado.sql`: Script con sentencias UPDATE y DELETE para demostrar la restricción RN-12.
- `evidencia/c14_solo_agregado.txt`: Captura de salida de `psql` mostrando el rechazo por el trigger.
- `evidencia/c15_sin_nplusone.txt`: Registro de queries ejecutadas para ventas de 2 y 4 renglones demostrando ausencia de N+1.

---

## 🐳 Despliegue en VPS del TP 1-4 (`despliegue/`)

La carpeta `despliegue/` contiene el código original del Trabajo Práctico de los Capítulos 1 a 4 (extraído limpiamente del commit `65ae2a6`), junto con:
- `Dockerfile`: basado en `python:3.12-alpine`, usuario sin privilegios `appuser`, `HEALTHCHECK` activo contra `/health/ready` y arranque con `alembic upgrade head && uvicorn`.
- `.dockerignore`: excluye `.env`, `.venv`, `.git` y `__pycache__`.
- `env.example`: plantilla de configuración del contenedor.
- `DEPLOY.md`: documentación completa del despliegue en VPS, comandos `docker build`/`docker run`, URL pública, procedimientos de actualización y tabla de casos `D-01` a `D-08`.
- `evidencia/`: archivos de captura de los casos `D-01` a `D-08`.

---

## 📦 Empaquetado para la Entrega Final

Para generar el archivo comprimido `.zip` conforme al formato de entrega de la cátedra:
```bash
python scripts/empaquetar_entrega.py LocalHost
```
Este comando ensambla automáticamente `Parcial_Cap1a6_LocalHost.zip` con las dos carpetas independientes:
- `parcial/`: Raíz del proyecto del Parcial completa (código fuente, `migrations/`, `test/`, `evidencia/`, `seed.py`, `README.md`, `requirements.txt`, etc.).
- `despliegue/`: Proyecto TP 1-4 dockerizado con `Dockerfile`, `DEPLOY.md` y evidencias.

Excluyendo estrictamente: `.venv`, `.git`, `.env` y directorios `__pycache__`.
