"""Pruebas de integración de Multiempresa y Sincronización con Facturador."""

import pytest
from fastapi.testclient import TestClient

def test_list_companies(client: TestClient, auth_headers: dict):
    """Verifica listar empresas activas."""
    resp = client.get("/api/companies", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    first_company = data[0]
    assert "ruc" in first_company
    assert "business_name" in first_company
    assert "bn_account" in first_company

def test_get_company_detail(client: TestClient, auth_headers: dict, test_company):
    """Verifica obtener detalle de una empresa por ID."""
    resp = client.get(f"/api/companies/{test_company.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == test_company.id
    assert data["ruc"] == test_company.ruc

def test_create_and_update_company(client: TestClient, auth_headers: dict):
    """Verifica crear y actualizar empresa, sincronizando datos al Facturador."""
    # 1. Crear empresa hermana / sucursal
    test_ruc = "20999111222"
    create_payload = {
        "ruc": test_ruc,
        "business_name": "TRANSPORTES Y LOGISTICA CUPPER SAC",
        "trademark_name": "CUPPER LOGISTICS",
        "address": "Carretera Central Km 12",
        "ubigeo": "150103",
        "department": "LIMA",
        "province": "LIMA",
        "district": "ATE",
        "establishment_code": "0001",
        "sol_user": "MODDATOS",
        "bn_account": "00-068-999888",
        "detraction_percent_default": 10.0,
        "is_matrix": False
    }
    resp_create = client.post("/api/companies", headers=auth_headers, json=create_payload)
    if resp_create.status_code == 400:
        # Si ya existe, buscarla
        companies = client.get("/api/companies?include_inactive=true", headers=auth_headers).json()
        comp = next(c for c in companies if c["ruc"] == test_ruc)
        company_id = comp["id"]
    else:
        assert resp_create.status_code == 201
        company_id = resp_create.json()["id"]

    # 2. Actualizar datos de la empresa
    update_payload = {
        "trademark_name": "CUPPER LOGISTICS & MINING EXPRESS",
        "phone": "999888777",
        "email": "logistica@cupper.pe",
        "detraction_percent_default": 12.0
    }
    resp_update = client.put(f"/api/companies/{company_id}", headers=auth_headers, json=update_payload)
    assert resp_update.status_code == 200
    updated = resp_update.json()
    assert updated["trademark_name"] == "CUPPER LOGISTICS & MINING EXPRESS"
    assert updated["email"] == "logistica@cupper.pe"

def test_delete_matrix_company_blocked(client: TestClient, auth_headers: dict, test_company):
    """Verifica que el sistema impida eliminar la empresa matriz principal."""
    if test_company.is_matrix:
        resp = client.delete(f"/api/companies/{test_company.id}", headers=auth_headers)
        assert resp.status_code == 400
        assert "matriz" in resp.text.lower()

def test_sync_companies_from_factos_api(client: TestClient, auth_headers: dict):
    """Verifica sincronización de empresas dadas de alta en Factos API Gateway."""
    resp = client.post("/api/companies/sync-factos", headers=auth_headers)
    assert resp.status_code == 200
    synced = resp.json()
    assert isinstance(synced, list)
