"""Pruebas de integración para Maestros Operativos: Productos, Clientes, Trabajadores, Vehículos y Catálogos SUNAT."""

import pytest
from fastapi.testclient import TestClient

def test_sunat_catalogs_api_endpoint(client: TestClient, auth_headers: dict):
    """Verifica el endpoint centralizado de catálogos normativos SUNAT."""
    resp = client.get("/api/catalogs/sunat", headers=auth_headers)
    assert resp.status_code == 200
    cats = resp.json()
    assert "document_types" in cats
    assert "detraction_services" in cats
    assert "identity_document_types" in cats

def test_products_crud_and_search(client: TestClient, auth_headers: dict, test_company):
    """Verifica creación, búsqueda, categorización y actualización de productos."""
    # 1. Crear producto con detracción
    prod_payload = {
        "company_id": test_company.id,
        "internal_code": "PROD-TEST-INTEG-01",
        "description": "Carbón Antracita para Exportación",
        "category_name": "Carbones & Minerales",
        "unit_code": "TNE",
        "unit_value": 322.0339,
        "unit_price": 380.0,
        "cost_price": 260.0,
        "is_service": False,
        "has_detraction": True,
        "detraction_code": "027",
        "detraction_percent": 10.0,
        "stock": 500.0,
        "stock_min": 50.0
    }
    resp_create = client.post("/api/products", headers=auth_headers, json=prod_payload)
    if resp_create.status_code == 400 and "código ya existe" in resp_create.text:
        # Si ya existe, buscarlo
        prods = client.get(f"/api/products?company_id={test_company.id}&search=PROD-TEST-INTEG-01", headers=auth_headers).json()
        product_id = prods[0]["id"]
    else:
        assert resp_create.status_code == 201
        created = resp_create.json()
        product_id = created["id"]
        assert created["has_detraction"] is True
        assert created["detraction_code"] == "027"

    # 2. Búsqueda por texto y categoría
    resp_search = client.get(
        f"/api/products?company_id={test_company.id}&search=Antracita&category_name=Carbones & Minerales",
        headers=auth_headers
    )
    assert resp_search.status_code == 200
    results = resp_search.json()
    assert len(results) >= 1
    assert any(p["id"] == product_id for p in results)

    # 3. Actualizar producto
    resp_update = client.put(
        f"/api/products/{product_id}",
        headers=auth_headers,
        json={"unit_price": 395.0}
    )
    assert resp_update.status_code == 200
    updated = resp_update.json()
    assert float(updated["unit_price"]) == 395.0

def test_clients_crud_and_search(client: TestClient, auth_headers: dict, test_company):
    """Verifica registro y actualización de clientes con ubigeo y días de crédito."""
    client_payload = {
        "company_id": test_company.id,
        "doc_type": "6",
        "doc_number": "20555666777",
        "name": "INDUSTRIAS METALICAS DEL SUR SAC",
        "address": "Av. Los Ingenieros 890",
        "ubigeo": "150101",
        "department": "LIMA",
        "province": "LIMA",
        "district": "LIMA",
        "contact_name": "Ing. Miguel Falcon",
        "credit_days_default": 45,
        "is_active": True
    }
    resp_create = client.post("/api/clients", headers=auth_headers, json=client_payload)
    if resp_create.status_code == 400 and "ya está registrado" in resp_create.text:
        clients = client.get(f"/api/clients?company_id={test_company.id}&search=20555666777", headers=auth_headers).json()
        client_id = clients[0]["id"]
    else:
        assert resp_create.status_code == 201
        client_id = resp_create.json()["id"]

    # Actualizar días de crédito
    resp_update = client.put(
        f"/api/clients/{client_id}",
        headers=auth_headers,
        json={"credit_days_default": 60, "contact_name": "Lic. Miguel Falcon Rios"}
    )
    assert resp_update.status_code == 200
    updated = resp_update.json()
    assert updated["credit_days_default"] == 60

def test_employees_crud_and_filters(client: TestClient, auth_headers: dict, test_company):
    """Verifica registro de trabajadores con soporte para choferes y vendedores."""
    emp_payload = {
        "company_id": test_company.id,
        "document_type": "1",
        "document_number": "44332211",
        "first_name": "Javier",
        "last_name": "Rojas Paredes",
        "job_title": "Conductor de Carga Pesada",
        "license_number": "Q44332211",
        "commission_rate": 0.0,
    }
    resp_create = client.post("/api/employees", headers=auth_headers, json=emp_payload)
    if resp_create.status_code == 400 and "ya está registrado" in resp_create.text:
        emps = client.get(f"/api/employees?company_id={test_company.id}&job_title=Conductor de Carga Pesada", headers=auth_headers).json()
        emp_id = emps[0]["id"]
    else:
        assert resp_create.status_code == 201
        emp_id = resp_create.json()["id"]

    # Listar filtrando por cargo
    resp_drivers = client.get(f"/api/employees?company_id={test_company.id}&job_title=Conductor de Carga Pesada", headers=auth_headers)
    assert resp_drivers.status_code == 200
    drivers = resp_drivers.json()
    assert any(e["id"] == emp_id for e in drivers)

def test_vehicles_crud(client: TestClient, auth_headers: dict, test_company):
    """Verifica registro y actualización de vehículos de transporte."""
    veh_payload = {
        "company_id": test_company.id,
        "plate_number": "Z9Z-777",
        "secondary_plate_number": "Y8Y-666",
        "brand": "SCANIA",
        "model": "R500",
        "mtc_authorization_number": "MTC-TEST-777",
        "is_active": True
    }
    resp_create = client.post("/api/vehicles", headers=auth_headers, json=veh_payload)
    if resp_create.status_code == 400 and "ya está registrada" in resp_create.text:
        vehs = client.get(f"/api/vehicles?company_id={test_company.id}", headers=auth_headers).json()
        veh_id = next(v["id"] for v in vehs if v["plate_number"] == "Z9Z-777")
    else:
        assert resp_create.status_code == 201
        veh_id = resp_create.json()["id"]

    # Actualizar modelo
    resp_update = client.put(f"/api/vehicles/{veh_id}", headers=auth_headers, json={"model": "R500 Highline V8"})
    assert resp_update.status_code == 200
    assert resp_update.json()["model"] == "R500 Highline V8"
