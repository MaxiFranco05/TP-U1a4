import subprocess
import time
import sys
import asyncio
import httpx
from sqlalchemy import text

BASE_URL = "http://127.0.0.1:8000"

async def cleanup_database():
    """Truncate all tables to ensure clean state for tests."""
    from app.core.config import get_settings
    from app.core.database import build_engine
    settings = get_settings()
    engine = build_engine(settings.database_url, settings.sql_echo)
    try:
        async with engine.begin() as conn:
            # Disable foreign key checks temporarily
            await conn.execute(text("SET session_replication_role = 'replica'"))
            # Truncate all tables
            tables = [
                'renglon_venta', 'venta', 'perfil_cliente', 'cliente',
                'libro_autor', 'libro', 'autor', 'editorial', 'genero'
            ]
            for table in tables:
                await conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
            await conn.execute(text("SET session_replication_role = 'origin'"))
    except Exception as e:
        print(f"Cleanup warning: {e}")
    finally:
        await engine.dispose()

async def run_tests():
    print("Cleaning up database...")
    await cleanup_database()
    print("\n=== Testing Editoriales ===")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Create editorial
        r = await client.post("/editoriales/", json={"nombre": "Editorial Planeta", "pais": "España"})
        print(f"POST /editoriales/ (create): {r.status_code} - {r.json()}")
        assert r.status_code == 201
        editorial_id = r.json()["id"]

        # Create duplicate editorial
        r = await client.post("/editoriales/", json={"nombre": "Editorial Planeta", "pais": "Argentina"})
        print(f"POST /editoriales/ (duplicate): {r.status_code} - {r.json()}")
        assert r.status_code == 409

        # List editoriales
        r = await client.get("/editoriales/")
        print(f"GET /editoriales/ (list): {r.status_code} - count: {len(r.json())}")
        assert r.status_code == 200

        # List with custom pagination
        r = await client.get("/editoriales/?limit=5&offset=0")
        print(f"GET /editoriales/?limit=5&offset=0: {r.status_code}")
        assert r.status_code == 200

        # Invalid limit
        r = await client.get("/editoriales/?limit=101")
        print(f"GET /editoriales/?limit=101: {r.status_code}")
        assert r.status_code == 422

        # Invalid offset
        r = await client.get("/editoriales/?offset=-1")
        print(f"GET /editoriales/?offset=-1: {r.status_code}")
        assert r.status_code == 422

        # Get editorial by id
        r = await client.get(f"/editoriales/{editorial_id}")
        print(f"GET /editoriales/{editorial_id}: {r.status_code} - {r.json()}")
        assert r.status_code == 200

        # Get non-existent editorial
        r = await client.get("/editoriales/999")
        print(f"GET /editoriales/999: {r.status_code}")
        assert r.status_code == 404

        # Update editorial
        r = await client.patch(f"/editoriales/{editorial_id}", json={"pais": "España (actualizado)"})
        print(f"PATCH /editoriales/{editorial_id}: {r.status_code} - {r.json()}")
        assert r.status_code == 200

        # Create another editorial for duplicate test
        r = await client.post("/editoriales/", json={"nombre": "Editorial Sudamericana", "pais": "Argentina"})
        print(f"POST /editoriales/ (second): {r.status_code} - {r.json()}")
        assert r.status_code == 201
        editorial_id_2 = r.json()["id"]

        # Update with duplicate name
        r = await client.patch(f"/editoriales/{editorial_id}", json={"nombre": "Editorial Sudamericana"})
        print(f"PATCH /editoriales/{editorial_id} (duplicate): {r.status_code} - {r.json()}")
        assert r.status_code == 409

        # Get libros by editorial
        r = await client.get(f"/editoriales/{editorial_id}/libros")
        print(f"GET /editoriales/{editorial_id}/libros: {r.status_code} - count: {len(r.json())}")
        assert r.status_code == 200

        # Get libros by non-existent editorial
        r = await client.get("/editoriales/999/libros")
        print(f"GET /editoriales/999/libros: {r.status_code}")
        assert r.status_code == 404

    print("[OK] Editoriales tests passed")

    print("\n=== Testing Autores ===")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Create autor
        r = await client.post("/autores/", json={"nombre": "Gabriel García Márquez", "nacionalidad": "Colombiana"})
        print(f"POST /autores/ (create): {r.status_code} - {r.json()}")
        assert r.status_code == 201
        autor_id = r.json()["id"]

        # Get autor by id
        r = await client.get(f"/autores/{autor_id}")
        print(f"GET /autores/{autor_id}: {r.status_code} - {r.json()}")
        assert r.status_code == 200

        # Get non-existent autor
        r = await client.get("/autores/999")
        print(f"GET /autores/999: {r.status_code}")
        assert r.status_code == 404

        # Update autor
        r = await client.patch(f"/autores/{autor_id}", json={"nacionalidad": "Colombiana/Mexicana"})
        print(f"PATCH /autores/{autor_id}: {r.status_code} - {r.json()}")
        assert r.status_code == 200

        # Update non-existent autor
        r = await client.patch("/autores/999", json={"nombre": "Inexistente"})
        print(f"PATCH /autores/999: {r.status_code}")
        assert r.status_code == 404

        # Get libros by autor
        r = await client.get(f"/autores/{autor_id}/libros")
        print(f"GET /autores/{autor_id}/libros: {r.status_code} - count: {len(r.json())}")
        assert r.status_code == 200

        # Get libros by non-existent autor
        r = await client.get("/autores/999/libros")
        print(f"GET /autores/999/libros: {r.status_code}")
        assert r.status_code == 404

    print("[OK] Autores tests passed")

    print("\n=== Testing Libros ===")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Create editorial for libro tests
        r = await client.post("/editoriales/", json={"nombre": "Editorial Test", "pais": "Argentina"})
        print(f"POST /editoriales/ (for libros): {r.status_code}")
        assert r.status_code == 201
        editorial_id = r.json()["id"]

        # Create autor for libro tests
        r = await client.post("/autores/", json={"nombre": "Autor Test", "nacionalidad": "Argentina"})
        print(f"POST /autores/ (for libros): {r.status_code}")
        assert r.status_code == 201
        autor_id = r.json()["id"]

        # Create genero for libro tests
        r = await client.post("/generos/", json={"nombre": "Ficción"})
        print(f"POST /generos/ (for libros): {r.status_code}")
        assert r.status_code == 201
        genero_id = r.json()["id"]

        # Create libro with authors
        r = await client.post("/libros/", json={
            "isbn": "978-987-1234-56-7",
            "titulo": "El Libro de Prueba",
            "precio": "29.99",
            "stock": 10,
            "editorial_id": editorial_id,
            "genero_id": genero_id,
            "autores": [{"autor_id": autor_id, "rol": "autor", "orden": 1}]
        })
        print(f"POST /libros/ (create): {r.status_code} - {r.json()}")
        assert r.status_code == 201
        libro_id = r.json()["id"]

        # Create duplicate ISBN
        r = await client.post("/libros/", json={
            "isbn": "978-987-1234-56-7",
            "titulo": "Otro Libro",
            "precio": "19.99",
            "stock": 5,
            "editorial_id": editorial_id,
            "genero_id": genero_id,
            "autores": [{"autor_id": autor_id, "rol": "autor", "orden": 1}]
        })
        print(f"POST /libros/ (duplicate ISBN): {r.status_code} - {r.json()}")
        assert r.status_code == 409

        # Non-existent editorial_id
        r = await client.post("/libros/", json={
            "isbn": "978-987-1234-56-8",
            "titulo": "Libro Editorial Inexistente",
            "precio": "19.99",
            "stock": 5,
            "editorial_id": 999,
            "genero_id": genero_id,
            "autores": [{"autor_id": autor_id, "rol": "autor", "orden": 1}]
        })
        print(f"POST /libros/ (non-existent editorial): {r.status_code} - {r.json()}")
        assert r.status_code == 409

        # Non-existent autor_id
        r = await client.post("/libros/", json={
            "isbn": "978-987-1234-56-9",
            "titulo": "Libro Autor Inexistente",
            "precio": "19.99",
            "stock": 5,
            "editorial_id": editorial_id,
            "genero_id": genero_id,
            "autores": [{"autor_id": 999, "rol": "autor", "orden": 1}]
        })
        print(f"POST /libros/ (non-existent autor): {r.status_code} - {r.json()}")
        assert r.status_code == 409

        # Invalid precio
        r = await client.post("/libros/", json={
            "isbn": "978-987-1234-57-0",
            "titulo": "Libro Precio Inválido",
            "precio": "-10.00",
            "stock": 5,
            "editorial_id": editorial_id,
            "genero_id": genero_id,
            "autores": [{"autor_id": autor_id, "rol": "autor", "orden": 1}]
        })
        print(f"POST /libros/ (invalid precio): {r.status_code} - {r.json()}")
        assert r.status_code == 422

        # Invalid stock
        r = await client.post("/libros/", json={
            "isbn": "978-987-1234-57-1",
            "titulo": "Libro Stock Inválido",
            "precio": "19.99",
            "stock": -1,
            "editorial_id": editorial_id,
            "genero_id": genero_id,
            "autores": [{"autor_id": autor_id, "rol": "autor", "orden": 1}]
        })
        print(f"POST /libros/ (invalid stock): {r.status_code} - {r.json()}")
        assert r.status_code == 422

        # Invalid rol
        r = await client.post("/libros/", json={
            "isbn": "978-987-1234-57-2",
            "titulo": "Libro Rol Inválido",
            "precio": "19.99",
            "stock": 5,
            "editorial_id": editorial_id,
            "genero_id": genero_id,
            "autores": [{"autor_id": autor_id, "rol": "editor", "orden": 1}]
        })
        print(f"POST /libros/ (invalid rol): {r.status_code} - {r.json()}")
        assert r.status_code == 422

        # Invalid orden
        r = await client.post("/libros/", json={
            "isbn": "978-987-1234-57-3",
            "titulo": "Libro Orden Inválido",
            "precio": "19.99",
            "stock": 5,
            "editorial_id": editorial_id,
            "genero_id": genero_id,
            "autores": [{"autor_id": autor_id, "rol": "autor", "orden": 0}]
        })
        print(f"POST /libros/ (invalid orden): {r.status_code} - {r.json()}")
        assert r.status_code == 422

        # List libros
        r = await client.get("/libros/")
        print(f"GET /libros/ (list): {r.status_code} - count: {len(r.json())}")
        assert r.status_code == 200

        # List with custom pagination
        r = await client.get("/libros/?limit=5&offset=0")
        print(f"GET /libros/?limit=5&offset=0: {r.status_code}")
        assert r.status_code == 200

        # Filter by titulo
        r = await client.get("/libros/?titulo=prueba")
        print(f"GET /libros/?titulo=prueba: {r.status_code} - count: {len(r.json())}")
        assert r.status_code == 200

        # Filter by genero_id
        r = await client.get(f"/libros/?genero_id={genero_id}")
        print(f"GET /libros/?genero_id={genero_id}: {r.status_code} - count: {len(r.json())}")
        assert r.status_code == 200

        # Combined filters
        r = await client.get(f"/libros/?titulo=libro&genero_id={genero_id}&limit=10")
        print(f"GET /libros/?titulo=libro&genero_id={genero_id}&limit=10: {r.status_code} - count: {len(r.json())}")
        assert r.status_code == 200

        # Invalid pagination
        r = await client.get("/libros/?limit=101")
        print(f"GET /libros/?limit=101: {r.status_code}")
        assert r.status_code == 422

        r = await client.get("/libros/?offset=-1")
        print(f"GET /libros/?offset=-1: {r.status_code}")
        assert r.status_code == 422

        # Get libro by id
        r = await client.get(f"/libros/{libro_id}")
        print(f"GET /libros/{libro_id}: {r.status_code} - {r.json()}")
        assert r.status_code == 200

        # Get non-existent libro
        r = await client.get("/libros/999")
        print(f"GET /libros/999: {r.status_code}")
        assert r.status_code == 404

        # SQL injection test
        r = await client.get("/libros/?titulo=' OR '1'='1")
        print(f"GET /libros/?titulo=' OR '1'='1: {r.status_code} - count: {len(r.json())}")
        assert r.status_code == 200
        assert len(r.json()) == 0  # Should return empty list, not error

    print("[OK] Libros tests passed")
    print("\n=== ALL TESTS PASSED ===")

async def main():
    # Start the server
    print("Starting server...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "info"],
        cwd="C:\\Users\\Andres\\Documents\\Tecnicatura en Programación\\2° Año\\1° Cuatrimestre\\Programación 3\\Trabajos Prácticos\\TP-U1a4\\TP-U1a4"
    )
    
    # Wait for server to start
    time.sleep(3)
    
    try:
        await run_tests()
    except Exception as e:
        print(f"\n=== TEST FAILED ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Stop the server
        server_process.terminate()
        server_process.wait(timeout=5)
        print("Server stopped")
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))