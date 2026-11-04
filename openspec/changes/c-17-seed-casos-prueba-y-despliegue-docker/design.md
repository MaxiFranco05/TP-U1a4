## Context

El sistema cuenta con la implementación completa de los capítulos 1 a 6 de la materia (modelos, migraciones 001 a 004 con trigger de sólo-agregado, autenticación bcrypt+JWT, roles y vigencia en BD, catálogo con baja lógica, stock por punto único, ventas atómicas en UoW y autorización de dueño). Para la entrega final según el criterio de evaluación de la cátedra:
1. Se requiere un script `seed.py` en la raíz que cargue exactamente el estado inicial de referencia para que los casos `C-01` a `C-16` sean evaluables y repetibles.
2. Se debe generar la suite de archivos `.http` para validar los casos de negocio, el script `test/solo_agregado.sql` para el trigger de auditoría, y las evidencias en `evidencia/`.
3. Se debe generar la carpeta obligatoria `despliegue/` conteniendo el TP de los capítulos 1 a 4 extraído limpiamente del commit canónico `65ae2a6`, con su `Dockerfile` sobre `python:3.12-alpine`, usuario no-root, `HEALTHCHECK`, y documentación `DEPLOY.md`.
4. Se debe proveer un script de empaquetado para generar el archivo final `.zip`.

## Goals / Non-Goals

**Goals:**
- Script `seed.py` canónico en la raíz, idempotente y con cálculo real de hashes bcrypt para los 5 usuarios y los 7 movimientos de stock exactos.
- Archivo `test/parcial_casos.http` y/o archivos `.http` organizados que cubran los casos `C-01` a `C-16` documentados con comentarios claros y directivas de sesión de REST Client.
- Script `test/solo_agregado.sql` y carpeta `evidencia/` con la salida de `psql` para `C-14` y log de consultas fijas para `C-15`.
- Carpeta `despliegue/` conteniendo el TP de capítulos 1 a 4 extraído de `65ae2a6`, `Dockerfile` conforme a `D-01..D-08`, `.dockerignore`, `env.example`, `DEPLOY.md` y evidencias.
- Script `scripts/empaquetar_entrega.py` que genere el `.zip` final con `parcial/` y `despliegue/`.

**Non-Goals:**
- Modificar el esquema de la base de datos o agregar nuevas migraciones.
- Alterar la lógica de negocio implementada en `app/modules/`.
- Conectar en vivo a un servidor VPS externo durante las pruebas automatizadas (la configuración de `DEPLOY.md` y contenedor se estructura para ser inmediatamente desplegable).

## Decisions

- **Seed canónico (`seed.py`)**:
  - Utilizar `asyncio.run` y la infraestructura de `app/core/database.py` y `app/core/security.py` para generar hashes válidos de contraseñas.
  - Orden de vaciado: `TRUNCATE TABLE movimiento_stock, renglon_venta, venta, asignacion_rol, intento_acceso, evento_seguridad, perfil_cliente, cliente, libro_autor, libro, genero, autor, editorial, usuario RESTART IDENTITY CASCADE`.
  - Inserción de 5 usuarios con fechas de vigencia explícitas y roles en `asignacion_rol`.
  - Inserción del catálogo TP (editoriales, géneros, autores y 5 libros).
  - Inserción de 7 movimientos de stock: 5 de `"Stock inicial"` que cuadren con el stock de los libros y 2 salidas asociadas a la Venta 1 de *Lucía Fernández* registrada por `vendedor@example.com` (`$69000.00`).
  - Inserción de 1 evento de seguridad de `SISTEMA`.
- **Extracción de `despliegue/`**:
  - Utilizar `git archive 65ae2a6 app/ migrations/ seed_db.py requirements.txt alembic.ini env.example` o copia directa del árbol de dicho commit para que `despliegue/` sea 100% independiente de las dependencias y modelos del parcial.
- **Dockerfile del Despliegue (`despliegue/Dockerfile`)**:
  - Imagen base: `python:3.12-alpine`.
  - Dependencias: compilar con `--no-cache-dir`.
  - Seguridad: `adduser -D appuser && USER appuser`.
  - Healthcheck: `HEALTHCHECK --interval=30s --timeout=5s CMD wget -qO- http://127.0.0.1:8000/health/ready || exit 1`.
  - Entrypoint / CMD: script o comando en línea `sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"`.
- **Script de empaquetado (`scripts/empaquetar_entrega.py`)**:
  - Construye un archivo `.zip` que sitúa la raíz actual (sin `despliegue/`, `.venv`, `.git`, `.env`) en una carpeta interna `parcial/` y la carpeta `despliegue/` en `despliegue/`.

## Risks / Trade-offs

- [Riesgo de lentitud al generar hashes bcrypt en el seed]: Utilizar un número de rondas estándar en pruebas (`BCRYPT_ROUNDS=4` en test o `12` en producción) para no demorar la inicialización.
- [Divergencia entre TP y Parcial en despliegue/]: Al extraer el código exactamente desde el commit `65ae2a6`, se garantiza que `despliegue/` no contenga ningún modelo ni ruta de usuarios o roles del parcial.

## Migration Plan

No requiere migraciones de base de datos. Se ejecuta `python seed.py` tras correr `alembic upgrade head`.
