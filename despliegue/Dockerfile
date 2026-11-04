# ==============================================================================
# Dockerfile para el despliegue del TP de los capítulos 1 a 4 en el VPS
# Imagen base: python:3.12-alpine (< 100 MB, D-01)
# ==============================================================================

FROM python:3.12-alpine

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias antes de copiar el código para optimizar la caché de capas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Crear usuario sin privilegios y configurar permisos (D-07)
RUN adduser -D -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copiar el código del TP y configuración de migraciones
COPY --chown=appuser:appuser . .

# Cambiar al usuario sin privilegios para no correr como root (D-07)
USER appuser

# Exponer el puerto publicado por uvicorn
EXPOSE 8000

# Verificación de salud periódica con wget apuntando a 127.0.0.1 en IPv4 (D-03)
# (En Alpine wget resuelve localhost a ::1 primero; 127.0.0.1 garantiza IPv4 hacia uvicorn)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:8000/health/ready || exit 1

# Al arrancar: aplica migraciones pendientes del TP y luego inicia el servidor ASGI (D-02, D-05)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
