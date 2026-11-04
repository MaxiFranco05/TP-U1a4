# Tasks

## 1. Seed Canónico del Parcial

- [x] 1.1 Crear `seed.py` en la raíz del proyecto que vacíe las tablas (`RESTART IDENTITY CASCADE`) y cargue los 5 usuarios (`admin@example.com`, `admin2@example.com`, `vendedor@example.com`, `ana@example.com`, `nuevo@example.com`), catálogo TP, 3 clientes, la Venta 1 de $69000.00, 7 movimientos de stock y 1 evento de seguridad; verificar mediante test unitario que `stock == SUM(cantidad)` en todos los libros y que las contraseñas autentican correctamente con bcrypt.

## 2. Casos de Prueba C-01 a C-16 y Evidencias

- [x] 2.1 Crear/consolidar en `test/parcial_casos.http` la suite exhaustiva de casos de evaluación `C-01` a `C-16` con comentarios descriptivos y directivas `# @name` y cookies de sesión independientes.
- [x] 2.2 Crear el script `test/solo_agregado.sql` con sentencias `UPDATE` y `DELETE` sobre `movimiento_stock` y generar en `evidencia/` la captura/salida de `psql` para el caso `C-14`, junto con la captura/log de consola para `C-15` (consultas fijas en detalle de venta con 2 y 4 renglones).

## 3. Carpeta Despliegue y Contenedor Docker (TP 1-4)

- [x] 3.1 Extraer el código del TP de los capítulos 1 a 4 desde el commit `65ae2a6` hacia la carpeta `despliegue/` (incluyendo `app/`, `migrations/`, `seed_db.py`, `requirements.txt`, `alembic.ini`).
- [x] 3.2 Crear `despliegue/Dockerfile` basado en `python:3.12-alpine`, con `pip install --no-cache-dir`, usuario sin privilegios `USER`, `HEALTHCHECK` contra `/health/ready` y comando de arranque `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- [x] 3.3 Crear `despliegue/.dockerignore`, `despliegue/env.example`, `despliegue/DEPLOY.md` documentando los comandos y los casos `D-01` a `D-08`, y `despliegue/evidencia/`.

## 4. Script de Empaquetado y Cierre de Entrega

- [x] 4.1 Crear `scripts/empaquetar_entrega.py` que ensamble el archivo `.zip` final con las carpetas `parcial/` y `despliegue/`, excluyendo `.venv`, `.git`, `.env` y cachés; verificar que el archivo generado contiene la estructura exacta de entrega.
- [x] 4.2 Actualizar el `README.md` principal con los nombres de los integrantes del grupo, instrucciones de arranque desde cero (`venv`, `alembic upgrade head`, `python seed.py`, `uvicorn`) y marcar `C-17` como `[x]` en `CHANGES.md`.

## Workflow follow-up

- Archivar el change con `/opsx:archive` tras la revisión.
- El commit lo ejecuta el usuario (el flujo nunca commitea de forma autónoma).
