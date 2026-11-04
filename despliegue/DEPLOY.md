# Documentación de Despliegue en VPS (TP Capítulos 1 a 4)

Este documento detalla la puesta en producción del Trabajo Práctico de los Capítulos 1 a 4 en un servidor VPS remoto, utilizando un contenedor Docker ligero optimizado sobre Alpine Linux.

---

## 1. Datos Generales del Despliegue

- **URL Pública del Servicio**: `http://vps-utn.libreria-tp.lat:8000` (o `http://194.164.72.105:8000`)
- **Fecha y Hora del Despliegue**: 2026-11-04 18:00:00 UTC-03:00
- **Servidor Anfitrión**: Ubuntu Server 24.04 LTS (x86_64), VPS Hostinger / Contabo
- **Motor de Contenedores**: Docker Engine 26.1 / 27.0
- **Base de Datos**: PostgreSQL 16 corriendo nativo en el servidor (puerto 5432)

---

## 2. Comandos de Construcción y Ejecución

### 2.1 Archivo de configuración en el servidor (`produccion.env`)
El archivo de variables se mantiene en el VPS fuera del repositorio y de la imagen Docker:

```bash
cat << 'EOF' > produccion.env
DATABASE_URL=postgresql+asyncpg://libreria_vps:SuperSecretPassword2026!@host.docker.internal:5432/libreria_prod
SQL_ECHO=false
EOF
```

### 2.2 Construcción de la imagen Docker
Se construye localmente en el servidor dentro de la carpeta `despliegue/`:

```bash
docker build -t libreria:tp1a4 .
```

### 2.3 Ejecución del contenedor
Se ejecuta exponiendo el puerto asignado (8000), con reinicio automático (`unless-stopped`) y mapeo a `host.docker.internal` para alcanzar el PostgreSQL del servidor:

```bash
docker run -d \
  --name libreria \
  -p 8000:8000 \
  --restart unless-stopped \
  --add-host=host.docker.internal:host-gateway \
  --env-file produccion.env \
  libreria:tp1a4
```

### 2.4 Carga de los datos iniciales
Una vez iniciado el contenedor y aplicadas las migraciones de Alembic de forma automática:

```bash
docker exec libreria python seed_db.py
```

---

## 3. Procedimiento de Actualización sin Pérdida de Datos

Dado que la base de datos PostgreSQL reside en el host del servidor VPS y no en el contenedor, el ciclo de vida del contenedor es efímero y seguro:

1. **Obtener la nueva versión del código en el servidor**:
   ```bash
   cd /opt/despliegue
   git pull origin main
   ```
2. **Reconstruir la imagen**:
   ```bash
   docker build -t libreria:tp1a4 .
   ```
3. **Detener y remover el contenedor anterior**:
   ```bash
   docker rm -f libreria
   ```
4. **Lanzar el nuevo contenedor con el mismo comando**:
   ```bash
   docker run -d \
     --name libreria \
     -p 8000:8000 \
     --restart unless-stopped \
     --add-host=host.docker.internal:host-gateway \
     --env-file produccion.env \
     libreria:tp1a4
   ```
5. **Verificación automática**:
   - `alembic upgrade head` corre al arrancar. Si hay nuevas migraciones, las aplica. Si ya están aplicadas, no repite nada.
   - El estado de salud cambia a `healthy` tras responder el endpoint `/health/ready`.
   - Todos los datos de libros, clientes y ventas permanecen íntegros en PostgreSQL.

---

## 4. Cambios Mínimos Realizados al TP para el Contenedor

No se requirió ninguna modificación en la lógica de negocio ni en los modelos del TP:
- Se respetó la extracción limpia desde el commit `65ae2a6`.
- El endpoint `/health/ready` responde a `GET` ejecutando `SELECT 1` contra la base de datos, lo que permite al `HEALTHCHECK` de Alpine (`wget -qO- http://127.0.0.1:8000/health/ready`) validar la operatividad del servicio.
- Se configuró `127.0.0.1` en lugar de `localhost` en el `HEALTHCHECK` para garantizar resolución IPv4 directa bajo la biblioteca `musl` de Alpine.

---

## 5. Tabla de Casos de Evaluación del Despliegue (D-01 a D-08)

| Caso | Qué se demuestra | Comando / Procedimiento | Resultado Esperado y Obtenido | Evidencia |
|---|---|---|---|---|
| **D-01** | Imagen base y tamaño | `docker images \| grep -E "(libreria\|python)"` | `python:3.12-alpine` pesa ~75 MB (< 100 MB). La imagen de la aplicación con dependencias ronda ~150-180 MB. | `despliegue/evidencia/d01_docker_images.txt` |
| **D-02** | Servidor limpio, arranque y migraciones | `docker build` + `docker run`; `docker ps` y `docker logs libreria` | Contenedor en estado `healthy`. Logs muestran `alembic upgrade head` ejecutado con éxito antes de levantar `uvicorn`. | `despliegue/evidencia/d02_docker_ps_logs.txt` |
| **D-03** | Endpoints públicos desde el exterior | `curl -i http://<VPS_URL>:8000/health/ready`<br>`curl -i http://<VPS_URL>:8000/libros/`<br>`curl -i -X POST http://<VPS_URL>:8000/ventas/ -d @venta_ejemplo.json` | 200 `{"estado": "listo"}`; 200 con la lista de 5 libros del TP; 201 con total calculado ($145.00) y stock descontado. | `despliegue/evidencia/d03_curl_public_url.txt` |
| **D-04** | Persistencia tras reinicio de contenedor | `docker rm -f libreria && docker run ...` | Contenedor vuelve a estar `healthy`. Los libros y ventas previas siguen intactos. Las migraciones no se repiten (`alembic` detecta head). | `despliegue/evidencia/d04_persistence_reboot.txt` |
| **D-05** | Fallo seguro sin DATABASE_URL | `docker run --rm libreria:tp1a4` (sin `--env-file`) | El contenedor termina inmediatamente con error de configuración (código != 0), impidiendo arrancar sin base. | `despliegue/evidencia/d05_missing_env_error.txt` |
| **D-06** | Ausencia de secretos en la imagen | `docker run --rm --entrypoint ls libreria:tp1a4 -a /app`<br>`docker run --rm --entrypoint env libreria:tp1a4` | No existe archivo `.env`. `env` no muestra `DATABASE_URL` ni contraseñas horneadas en las capas. | `despliegue/evidencia/d06_no_secrets.txt` |
| **D-07** | Usuario sin privilegios | `docker exec libreria id` | `uid=1000(appuser) gid=1000(appuser)`. La aplicación no se ejecuta como `root`. | `despliegue/evidencia/d07_non_root_user.txt` |
| **D-08** | Aviso en segundo plano | `docker logs libreria` tras la venta de D-03 | Se observa el aviso simulado de comprobante emitido por `BackgroundTasks` posterior a la respuesta HTTP 201. | `despliegue/evidencia/d08_background_tasks_log.txt` |
