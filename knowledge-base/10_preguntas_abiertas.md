# Preguntas Abiertas y Definiciones del Equipo

## Inconsistencias detectadas

No se detectaron inconsistencias internas en la consigna del **Parcial (Capítulos 1 a 6)**: el modelo de dominio (14 tablas), las reglas de negocio (`RN-01` a `RN-16`), la tabla de endpoints de referencia (grupos abierto y protegido), los datos iniciales de `seed.py`, los casos de prueba (`C-01` a `C-16` y `D-01` a `D-08`), los pesos de evaluación (100 puntos en 10 ejercicios) y el formato de entrega (`parcial/` y `despliegue/`) son totalmente coherentes entre sí.

---

## Estado de Preguntas Abiertas

### Etapa TP Capítulos 1 a 4 (`PA-01` a `PA-04`) — `Resueltas`

| ID | Pregunta original | Resolución |
|---|---|---|
| **PA-01** | ¿Cómo se provee Python 3.12? | **Resuelta en `C-01`**: entorno virtual con Python 3.12 configurado y verificado. |
| **PA-02** | ¿El VPS entra en la entrega? | **Actualizada por el Parcial**: en el Parcial (Ej. 9 y Ej. 10, 18% de la nota), el despliegue del TP de los capítulos 1 a 4 en el VPS dentro de un contenedor Docker pasa a ser **obligatorio** dentro de la carpeta `despliegue/`. |
| **PA-03** | ¿Contenido exacto del seed? | **Fijado por la consigna del Parcial**: `seed.py` en la raíz tiene tabla oficial obligatoria (5 usuarios, 3 editoriales, 3 géneros, 6 autores, 5 libros con stocks 10/5/8/3/1, 3 clientes, Venta 1 por `69000.00`, 7 movimientos de stock y 1 evento `SISTEMA`). |
| **PA-04** | ¿`compose.yaml` para PG16 en dev? | **Resuelta**: se usa sólo para levantar PostgreSQL 16 en desarrollo local; en `despliegue/` **no se usa Docker Compose**, sino `Dockerfile` + `docker run` contra el PostgreSQL del VPS. |

---

### Etapa Parcial Capítulos 1 a 6 (`PA-05` a `PA-07`) — `Definiciones Operativas`

| Prioridad | ID y Definición | Impacta en | Responsable |
|---|---|---|---|
| **Resuelta** | **PA-05 — División equitativa de los 9 changes del Parcial (`C-09` a `C-17`) entre los 3 integrantes**:<br>• **Maxi**: `C-09`, `C-10`, `C-11` (Config/Lifespan, Modelos/Migraciones 003-004, Core Repositories/UoW/Paginación — ~33 pts).<br>• **Andrés**: `C-12`, `C-13`, `C-14` (Security bcrypt/JWT/Dependencies, Auth Registro/Login/Cambio clave, Usuarios/Roles/Vigencia/Eventos — ~33 pts).<br>• **Octavio**: `C-15`, `C-16`, `C-17` (Catálogo/Stock/Baja lógica sobre UoW, Clientes/Ventas/Autorización sobre UoW, Seed/Tests `C-01..C-16`/Docker y Despliegue VPS `D-01..D-08` — ~34 pts). | `CHANGES.md` (Fases 4 a 7) | Equipo (Maxi, Andrés, Octavio) |
| **Media** | **PA-06 — Datos de conexión y puerto asignado en el VPS de la cátedra**:<br>Confirmar la URL pública, el puerto asignado al grupo (`-p <puerto>:8000`) y la dirección del PostgreSQL en el servidor (`host.docker.internal` con `--add-host=host.docker.internal:host-gateway` o dirección provista) al ejecutar el despliegue de `C-17`. | `despliegue/DEPLOY.md` y `despliegue/evidencia/` (`D-02` a `D-08`) | Octavio / Equipo en `C-17` |
| **Baja** | **PA-07 — Empaquetado final `.zip` (`Parcial_Cap1a6_<NombreDelGrupo>.zip`)**:<br>Al cerrar `C-17`, armar la estructura de entrega con las dos carpetas (`parcial/` y `despliegue/`) verificando que no incluyan `.venv`, `__pycache__` ni `.env`, y que el historial `.git` (si se incluye) no tenga ningún secreto. | Entrega final en campus | Equipo al cerrar `C-17` |
