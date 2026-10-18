"""Test script to verify C-05 endpoints work correctly."""

import asyncio
import httpx


async def test_endpoints() -> None:
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        print("=== Testing C-05 Clientes Endpoints ===\n")
        
        # 1. Create cliente - success (201)
        print("1. POST /clientes/ - Create cliente (success)")
        response = await client.post("/clientes/", json={"nombre": "Test Cliente", "email": "test_new@example.com"})
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        cliente_id = response.json()["id"]
        print()
        
        # 2. Create cliente - duplicate email (409)
        print("2. POST /clientes/ - Duplicate email (409)")
        response = await client.post("/clientes/", json={"nombre": "Test Cliente 2", "email": "test_new@example.com"})
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print()
        
        # 3. List clientes - default pagination (200)
        print("3. GET /clientes/ - Default pagination")
        response = await client.get("/clientes/")
        print(f"   Status: {response.status_code}")
        print(f"   Count: {len(response.json())}")
        print()
        
        # 4. List clientes - custom pagination (200)
        print("4. GET /clientes/?limit=2&offset=0 - Custom pagination")
        response = await client.get("/clientes/", params={"limit": 2, "offset": 0})
        print(f"   Status: {response.status_code}")
        print(f"   Count: {len(response.json())}")
        print()
        
        # 5. List clientes - invalid limit (422)
        print("5. GET /clientes/?limit=101 - Invalid limit (422)")
        response = await client.get("/clientes/", params={"limit": 101})
        print(f"   Status: {response.status_code}")
        print()
        
        # 6. Get cliente by id - with perfil (200)
        print(f"6. GET /clientes/{cliente_id} - With perfil")
        response = await client.get(f"/clientes/{cliente_id}")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print()
        
        # 7. Get cliente by id - not found (404)
        print("7. GET /clientes/999 - Not found (404)")
        response = await client.get("/clientes/999")
        print(f"   Status: {response.status_code}")
        print()
        
        # 8. Update cliente - nombre only (200)
        print("8. PATCH /clientes/{id} - Update nombre")
        response = await client.patch(f"/clientes/{cliente_id}", json={"nombre": "Updated Name"})
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print()
        
        # 9. Create perfil for cliente - success (201)
        print("9. POST /clientes/{id}/perfil - Create perfil (success)")
        response = await client.post(f"/clientes/{cliente_id}/perfil", json={
            "telefono": "+54 11 9999-9999",
            "direccion": "Test Address 123"
        })
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print()
        
        # 10. Create perfil for cliente - duplicate (409)
        print("10. POST /clientes/{id}/perfil - Duplicate perfil (409)")
        response = await client.post(f"/clientes/{cliente_id}/perfil", json={
            "telefono": "+54 11 8888-8888",
            "direccion": "Another Address"
        })
        print(f"   Status: {response.status_code}")
        print()
        
        # 11. Create perfil for non-existent cliente (404)
        print("11. POST /clientes/999/perfil - Cliente not found (404)")
        response = await client.post("/clientes/999/perfil", json={
            "telefono": "+54 11 1234-5678",
            "direccion": "Test"
        })
        print(f"   Status: {response.status_code}")
        print()
        
        # 12. Get ventas by cliente - success (200)
        print("12. GET /clientes/4/ventas - With ventas (cliente from seed)")
        response = await client.get("/clientes/4/ventas")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print()
        
        # 13. Get ventas by cliente - empty (200)
        print("13. GET /clientes/5/ventas - Empty list (cliente sin ventas)")
        response = await client.get("/clientes/5/ventas")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print()
        
        # 14. Get ventas by cliente - not found (404)
        print("14. GET /clientes/999/ventas - Not found (404)")
        response = await client.get("/clientes/999/ventas")
        print(f"   Status: {response.status_code}")
        print()
        
        print("=== All tests completed ===")


if __name__ == "__main__":
    asyncio.run(test_endpoints())