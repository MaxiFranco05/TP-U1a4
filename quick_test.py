import httpx

response = httpx.post("http://localhost:8000/clientes/", json={"nombre": "Test Cliente", "email": "test_new2@example.com"})
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")