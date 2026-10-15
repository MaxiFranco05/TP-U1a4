# Preguntas Abiertas

## Inconsistencias detectadas

No se detectaron inconsistencias internas en la consigna: ejercicios, reglas RN-01 a RN-12, endpoints, pesos de evaluación y formato de entrega son coherentes entre sí. Nota: el cliente `psql` 17 instalado localmente no contradice el requisito de servidor PostgreSQL 16 (cliente ≠ servidor).

## Preguntas abiertas (priorizadas)

| Prioridad | Pregunta | Bloquea | Decisor |
|---|---|---|---|
| Alta | PA-01 — ¿Cómo se provee Python 3.12 (instalación en paralelo a 3.14, Python en Docker, u otra vía)? | Creación del venv y `requirements.txt` | Alumno |
| Media | PA-02 — ¿El VPS con Easypanel entra como deploy documentado o queda fuera de la entrega? | Decisiones de `README` y de `.env` de ejemplo | Alumno |
| Media | PA-03 — ¿Contenido exacto del seed (qué editoriales/libros/clientes de ejemplo)? | Reproducibilidad de los `.http` | Alumno |
| Baja | PA-04 — ¿Vale un `compose.yaml` para PG16 en dev aunque la consigna no lo pida? | Comodidad de `docker compose up` | Alumno |
