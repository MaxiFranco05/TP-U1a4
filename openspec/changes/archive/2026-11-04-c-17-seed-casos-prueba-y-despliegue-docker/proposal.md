# Proposal

## Why

El desarrollo de las funcionalidades de acceso, catálogo, transacciones y roles del Parcial Capítulos 1 a 6 (`C-09` a `C-16`) está completo y verificado al 100%. Para finalizar el proyecto y cumplir la totalidad de los requisitos de evaluación de la cátedra (Ejercicios 9 y 10: 18% de la nota final), es imperativo:
1. Proveer un script `seed.py` canónico y reproducible con el estado de datos exacto exigido por la consigna para sustentar las pruebas de corrección (`C-01` a `C-16`).
2. Generar la suite de pruebas `.http` comentada, scripts SQL de evidencia para restricciones de sólo-agregado y capturas/logs de consultas fijas.
3. Construir la carpeta obligatoria `despliegue/` conteniendo el TP de los capítulos 1 a 4 (extraído del commit `65ae2a6`) con su Dockerfile optimizado (`python:3.12-alpine`), documentación de despliegue en el VPS (`DEPLOY.md`), y el script de empaquetado final para la entrega en `.zip`.

## What Changes

- **Parte A: Entregables del Parcial (`parcial/` / raíz del proyecto)**:
  - Creación de `seed.py` canónico en la raíz: resetea tablas y carga el estado inicial exacto de la consigna (5 usuarios con roles vigentes y contraseñas hasheadas con bcrypt, 3 editoriales, 3 géneros, 6 autores, 5 libros con stock 10, 5, 8, 3 y 1, 3 clientes, 1 venta de $69000.00, 7 movimientos de stock consistentes y 1 evento de seguridad del sistema).
  - Creación y actualización de la suite `test/parcial_casos.http` (o modular en `test/*.http`) cubriendo exhaustivamente los casos `C-01` a `C-16`.
  - Creación del script `test/solo_agregado.sql` para evidenciar el caso `C-14` (trigger de sólo-agregado que impide UPDATE/DELETE en `movimiento_stock`).
  - Generación de la carpeta `evidencia/` con la salida de `psql` para `C-14` y log de consola para `C-15` (consultas fijas en detalle de ventas con 2 y 4 renglones).
  - Actualización del `README.md` con nombres de los integrantes del equipo y guía de instalación y ejecución desde cero.

- **Parte B: Entregables de Despliegue en VPS (`despliegue/`)**:
  - Extracción limpia del código del TP 1-4 desde el commit canónico `65ae2a6aae7e637a81f7ebc1f7ef3547585f7faf` hacia la carpeta `despliegue/`.
  - Creación de `despliegue/Dockerfile`: basado en `python:3.12-alpine`, sin secretos, instalación con `--no-cache-dir`, usuario sin privilegios `USER`, `HEALTHCHECK` activo contra `/health/ready`, arranque con `alembic upgrade head && uvicorn`.
  - Configuración de `despliegue/.dockerignore` y `despliegue/env.example`.
  - Creación de `despliegue/DEPLOY.md` documentando comandos `docker build`/`docker run`, URL pública, procedimientos de actualización y casos `D-01` a `D-08`.
  - Creación de `scripts/empaquetar_entrega.py` para generar el archivo `.zip` final con ambas carpetas (`parcial/` y `despliegue/`) excluyendo `.venv`, `.git` y cachés.

## Capabilities

### New Capabilities
- `canonical-seed-and-evidence`: Script `seed.py` canónico, suite `.http` demostrando casos `C-01` a `C-16`, script `solo_agregado.sql` y carpeta `evidencia/`.
- `vps-docker-deployment`: Contenedor Docker basado en `python:3.12-alpine` para el TP 1-4, `DEPLOY.md`, evidencias `D-01` a `D-08` y script de empaquetado `.zip`.

### Modified Capabilities
<!-- Ninguna capability existente modifica sus contratos de requerimiento; se complementan con seed, empaquetado y contenedor -->

## Impact

- **Código y Raíz**: `seed.py`, `test/*.http`, `test/solo_agregado.sql`, `evidencia/`, `README.md`, `scripts/empaquetar_entrega.py`.
- **Nueva Carpeta**: `despliegue/` conteniendo `app/`, `migrations/`, `Dockerfile`, `.dockerignore`, `DEPLOY.md`, `requirements.txt`, etc.
- **Riesgo**: Bajo a Medio. No modifica la lógica interna de negocio ni modelos ya aprobados en C-09..C-16.
