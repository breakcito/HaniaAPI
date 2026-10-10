"""Pruebas de integración de Autenticación, Usuarios y Permisos."""

import pytest
from fastapi.testclient import TestClient

def test_login_success(client: TestClient):
    """Verifica el inicio de sesión exitoso con credenciales correctas."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client: TestClient):
    """Verifica el rechazo de inicio de sesión con clave incorrecta."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "clave_totalmente_incorrecta_999"})
    assert resp.status_code == 401

def test_get_current_user_profile(client: TestClient, auth_headers: dict):
    """Verifica la obtención del perfil autenticado /auth/me."""
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert "role" in data

def test_users_crud_and_roles(client: TestClient, auth_headers: dict, test_company):
    """Verifica el flujo completo de listar, crear y actualizar usuarios con roles y series asignadas."""
    resp_list = client.get("/api/auth/users", headers=auth_headers)
    assert resp_list.status_code == 200
    assert isinstance(resp_list.json(), list)

    import time
    unique_user = f"vendedor_{int(time.time())}"
    user_payload = {
        "username": unique_user,
        "password": "Password123!",
        "full_name": "Juan Perez Vendedor",
        "role": "VENDEDOR"
    }
    resp_create = client.post("/api/auth/users", headers=auth_headers, json=user_payload)
    if resp_create.status_code == 400:
        resp_list = client.get("/api/auth/users", headers=auth_headers)
        created_user = next(u for u in resp_list.json() if u["username"] == unique_user)
        user_id = created_user["id"]
    else:
        assert resp_create.status_code == 201
        created_user = resp_create.json()
        user_id = created_user["id"]
        assert created_user["role"] == "VENDEDOR"

    update_payload = {
        "role": "CONTADOR"
    }
    resp_update = client.put(f"/api/auth/users/{user_id}", headers=auth_headers, json=update_payload)
    assert resp_update.status_code == 200
    updated_user = resp_update.json()
    assert updated_user["role"] == "CONTADOR"
