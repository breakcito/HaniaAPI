"""Pruebas de integración de Comprobantes Electrónicos y Verificación de Inmutabilidad Fiscal."""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

def test_document_emission_and_strict_immutability(client: TestClient, auth_headers: dict, test_company):
    """Verifica la emisión de comprobante y comprueba la estricta inmutabilidad fiscal del documento."""
    # 1. Emitir Factura en modo prueba
    doc_payload = {
        "company_id": test_company.id,
        "is_test_mode": True,
        "type_code": "01",
        "operation_type": "0101",
        "series": "F001",
        "correlative": None,  # Auto-correlative
        "issue_date": str(datetime.now(timezone.utc).date()),
        "currency": "PEN",
        "payment_method": "Contado",
        "seller_name": "Ana Maria Torres Diaz",
        "client": {
            "doc_type": "6",
            "doc_number": "20100070970",
            "name": "SUPERMERCADOS PERUANOS SOCIEDAD ANONIMA",
            "address": "Calle Morelli 181, San Borja, Lima",
            "email": "facturacion@plazavea.com.pe"
        },
        "items": [
            {
                "internal_code": "ITEM-INM-01",
                "description": "Servicio de Transporte Especializado de Carga",
                "unit_code": "ZZ",
                "quantity": 1.0,
                "unit_value": 1000.0,
                "unit_price": 1180.0,
                "igv_type": "10",
                "igv_amount": 180.0,
                "total": 1180.0
            }
        ]
    }
    resp_create = client.post("/api/documents", headers=auth_headers, json=doc_payload)
    assert resp_create.status_code == 201, f"Error al emitir comprobante: {resp_create.text}"
    created_doc = resp_create.json()
    document_id = created_doc["id"]
    assert created_doc["series"] == "F001"
    assert created_doc["status"] in ("accepted", "pending")
    assert float(created_doc["total"]) == 1180.0
    assert created_doc["seller_name"] == "Ana Maria Torres Diaz"

    # 2. INMUTABILIDAD: Intentar modificar el comprobante mediante PUT
    resp_put = client.put(f"/api/documents/{document_id}", headers=auth_headers, json={"total": 2000.0})
    assert resp_put.status_code == 405
    assert "inmutables" in resp_put.text.lower()

    # 3. INMUTABILIDAD: Intentar modificar el comprobante mediante PATCH
    resp_patch = client.patch(f"/api/documents/{document_id}", headers=auth_headers, json={"status": "rejected"})
    assert resp_patch.status_code == 405
    assert "inmutables" in resp_patch.text.lower()

    # 4. INMUTABILIDAD: Intentar eliminar el comprobante emitido mediante DELETE
    resp_delete = client.delete(f"/api/documents/{document_id}", headers=auth_headers)
    assert resp_delete.status_code == 400
    assert "inmutabilidad" in resp_delete.text.lower() or "inmutables" in resp_delete.text.lower()

    # 5. ANULACIÓN / COMUNICACIÓN DE BAJA: La única vía reglamentaria para dejar sin efecto el comprobante
    void_payload = {
        "reason": "Error en el tipo de operación acordado con el cliente"
    }
    resp_void = client.post(f"/api/documents/{document_id}/void", headers=auth_headers, json=void_payload)
    assert resp_void.status_code == 200
    voided_doc = resp_void.json()
    assert voided_doc["status"] == "voided"
    assert voided_doc["void_reason"] == "Error en el tipo de operación acordado con el cliente"
    assert voided_doc["voided_at"] is not None

    # 6. Intentar anular un comprobante que ya fue anulado -> Debe rechazar con 400
    resp_void_again = client.post(f"/api/documents/{document_id}/void", headers=auth_headers, json=void_payload)
    assert resp_void_again.status_code == 400
    assert "ya fue anulado" in resp_void_again.text.lower()
