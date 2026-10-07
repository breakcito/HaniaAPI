"""Pruebas de integración de Cuentas Bancarias, Bancos y Series Fiscales."""

import pytest
from fastapi.testclient import TestClient

def test_banks_catalog(client: TestClient, auth_headers: dict):
    """Verifica consulta del catálogo nacional de bancos."""
    resp = client.get("/api/banks", headers=auth_headers)
    assert resp.status_code == 200
    banks = resp.json()
    assert isinstance(banks, list)
    assert len(banks) >= 5
    codes = [b["code"] for b in banks]
    assert "BCP" in codes
    assert "BN" in codes
    assert "BBVA" in codes

def test_bank_accounts_crud(client: TestClient, auth_headers: dict, test_company):
    """Verifica creación, listado y actualización de cuentas bancarias de la empresa."""
    # Obtener banco disponible
    banks_resp = client.get("/api/banks", headers=auth_headers)
    assert banks_resp.status_code == 200
    banks = banks_resp.json()
    bank_id = banks[0]["id"]

    # 1. Crear cuenta bancaria
    account_payload = {
        "company_id": test_company.id,
        "bank_id": bank_id,
        "currency": "PEN",
        "account_type": "corriente",
        "account_number": "191-99887766-0-55",
        "cci_number": "00219100998877660551",
        "alias": "BCP Operaciones Soles Principal",
        "show_in_pdf": True,
        "is_default": False
    }
    resp_create = client.post("/api/bank-accounts", headers=auth_headers, json=account_payload)
    assert resp_create.status_code == 201
    created = resp_create.json()
    account_id = created["id"]
    assert created["bank_id"] == bank_id
    assert created["account_number"] == "191-99887766-0-55"

    # 2. Listar cuentas de la empresa
    resp_list = client.get(f"/api/bank-accounts?company_id={test_company.id}", headers=auth_headers)
    assert resp_list.status_code == 200
    accounts = resp_list.json()
    assert any(a["id"] == account_id for a in accounts)

    # 3. Actualizar alias y estado
    resp_update = client.put(
        f"/api/bank-accounts/{account_id}",
        headers=auth_headers,
        json={"alias": "BCP Soles Cobranzas", "is_active": True}
    )
    assert resp_update.status_code == 200
    assert resp_update.json()["alias"] == "BCP Soles Cobranzas"

def test_series_management_and_correlatives(client: TestClient, auth_headers: dict, test_company):
    """Verifica creación de series y consulta atómica del correlativo en vivo."""
    # 1. Listar series de la empresa
    resp_list = client.get(f"/api/series?company_id={test_company.id}", headers=auth_headers)
    assert resp_list.status_code == 200
    series_list = resp_list.json()
    assert isinstance(series_list, list)

    # 2. Consultar próximo correlativo para F001
    resp_corr = client.get(
        f"/api/series/next-correlative?company_id={test_company.id}&document_type=01&series=F001",
        headers=auth_headers
    )
    assert resp_corr.status_code == 200
    corr_data = resp_corr.json()
    assert "next_correlative" in corr_data
    assert "formatted_number" in corr_data
    assert corr_data["next_correlative"] >= 1
    assert "F001-" in corr_data["formatted_number"]
