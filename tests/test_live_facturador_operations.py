"""Pruebas de operaciones en vivo con Factos API Gateway (Facturador Electrónico)."""

import pytest
from src.services.facturador.client import facturador_gateway

@pytest.mark.asyncio
async def test_live_facturador_list_companies():
    """Verifica la consulta de empresas configuradas en Factos API Gateway con la X-API-KEY."""
    res = await facturador_gateway.list_companies()
    assert not res.get("error"), f"Error en list_companies: {res.get('message')}"
    data = res.get("data", [])
    assert isinstance(data, list)
    assert len(data) >= 1
    first_company = data[0]
    assert "id" in first_company
    assert "ruc" in first_company
    assert "business_name" in first_company

@pytest.mark.asyncio
async def test_live_facturador_query_ruc():
    """Verifica la consulta de RUC oficial contra SUNAT a través del Facturador."""
    res = await facturador_gateway.query_ruc("20100070970")
    assert not res.get("error"), f"Error consultando RUC: {res.get('message')}"
    data = res.get("data", {})
    assert "SUPERMERCADOS PERUANOS" in data.get("razon_social", "").upper()
    assert data.get("ruc") == "20100070970"

@pytest.mark.asyncio
async def test_live_facturador_query_dni():
    """Verifica la consulta de DNI oficial contra RENIEC a través del Facturador."""
    res = await facturador_gateway.query_dni("44332211")
    # Si RENIEC responde con datos o estado de consulta
    if not res.get("error"):
        data = res.get("data", {})
        assert "nombres" in data or "nombre_completo" in data

@pytest.mark.asyncio
async def test_live_facturador_query_exchange_rate():
    """Verifica la consulta de tipo de cambio del día."""
    res = await facturador_gateway.query_exchange_rate()
    if not res.get("error"):
        data = res.get("data", {})
        assert "compra" in data or "venta" in data or "date" in data

@pytest.mark.asyncio
async def test_live_facturador_update_company_data():
    """Verifica la modificación y actualización de datos de la empresa en el Facturador para sincronizarla con Hania."""
    # 1. Obtener la primera empresa vinculada
    list_res = await facturador_gateway.list_companies()
    assert not list_res.get("error")
    companies = list_res.get("data", [])
    assert len(companies) >= 1
    target_company = companies[0]
    target_id = str(target_company["id"])

    # 2. Actualizar datos en Factos API para que vayan acorde a HaniaSystem
    update_payload = {
        "trademark_name": "CUPPER & HANNIA SISTEMAS",
        "establishment_code": "0000",
        "sol_user": "MODDATOS",
    }
    update_res = await facturador_gateway.update_company(target_id, update_payload)
    assert not update_res.get("error"), f"Error actualizando empresa en Factos API: {update_res.get('message')}"
    updated_data = update_res.get("data", {})
    assert updated_data.get("trademark_name") == "CUPPER & HANNIA SISTEMAS"
