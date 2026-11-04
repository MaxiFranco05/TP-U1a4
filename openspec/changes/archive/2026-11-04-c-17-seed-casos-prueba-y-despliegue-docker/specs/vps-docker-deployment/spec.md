## ADDED Requirements

### Requirement: Contenedor Docker para Despliegue del TP 1-4
La carpeta `despliegue/` SHALL contener el código del TP 1-4 extraído del commit `65ae2a6`, junto con un `Dockerfile` optimizado en `python:3.12-alpine`, sin secretos, usuario no-root, `HEALTHCHECK` activo y arranque con migraciones.

#### Scenario: Construcción de imagen Docker sin secretos
- **WHEN** se construye la imagen con `docker build -t libreria despliegue/`
- **THEN** la imagen se crea exitosamente, con base Alpine, pesa menos de 100 MB y no contiene credenciales embebidas.

#### Scenario: Verificación de Healthcheck
- **WHEN** el contenedor está en ejecución en el servidor
- **THEN** `docker inspect` reporta estado `healthy` al responder `/health/ready`.

### Requirement: Documentación del Despliegue en VPS
La carpeta `despliegue/` SHALL incluir el archivo `DEPLOY.md` documentando la URL pública en el VPS, comandos completos de ejecución con variables de entorno, procedimiento de actualización sin pérdida de datos y tabla de casos `D-01` a `D-08`.

#### Scenario: Guía de despliegue reproducible
- **WHEN** un operador sigue los pasos de `DEPLOY.md`
- **THEN** puede recrear el despliegue del contenedor en cualquier servidor Linux VPS sin ambigüedades.

### Requirement: Script de Empaquetado de Entrega
El proyecto SHALL incluir `scripts/empaquetar_entrega.py` que empaqueta automáticamente las carpetas `parcial/` (raíz limpia) y `despliegue/` en el archivo comprimido final `.zip`, excluyendo `.venv`, directorios `.git`, archivos `.env` y cachés `__pycache__`.

#### Scenario: Generación del archivo zip de entrega
- **WHEN** se ejecuta `python scripts/empaquetar_entrega.py`
- **THEN** se genera el `.zip` con la estructura canónica requerida por la cátedra sin archivos basura ni secretos.
