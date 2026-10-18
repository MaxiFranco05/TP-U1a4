import subprocess
import time
import httpx
import sys

# Start server
proc = subprocess.Popen([
    sys.executable, "-m", "uvicorn", "app.main:app", 
    "--port", "8000", "--log-level", "debug"
], cwd=r"C:\Users\Andres\Documents\Tecnicatura en Programación\2° Año\1° Cuatrimestre\Programación 3\Trabajos Prácticos\TP-U1a4\TP-U1a4")

try:
    time.sleep(3)
    
    import uuid
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    
    response = httpx.post("http://localhost:8000/clientes/", json={"nombre": "Test Cliente", "email": unique_email})
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
finally:
    proc.terminate()
    proc.wait()