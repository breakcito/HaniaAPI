"""Pruebas unitarias de servicios desacoplados: FacturadorClient, Catálogos SUNAT y Reportería Excel."""

import pytest
from io import BytesIO
import openpyxl
from src.services.facturador.client import FacturadorClient, facturador_gateway
from src.services.facturador.catalogs import (
    DOCUMENT_TYPES,
    IDENTITY_DOCUMENT_TYPES,
    IGV_TYPES,
    CREDIT_NOTE_REASONS,
    DEBIT_NOTE_REASONS,
    OPERATION_TYPES,
    DESPATCH_REASONS,
    DETRACTION_SERVICES,
    UNITS_OF_MEASURE,
    get_all_sunat_catalogs,
)
from types import SimpleNamespace
from src.services.facturador.excel_reports import (
    generate_sales_report_excel,
    generate_despatches_report_excel,
)

def test_facturador_client_headers_and_config():
    """Verifica que el cliente desacoplado configure correctamente headers y API Key."""
    client = FacturadorClient(
        base_url="https://api.ejemplo.test",
        api_key="test_api_key_12345"
    )
    assert client.base_url == "https://api.ejemplo.test"
    headers = client._get_headers()
    assert headers["X-API-KEY"] == "test_api_key_12345"
    assert headers["Authorization"] == "Bearer test_api_key_12345"
    assert headers["Accept"] == "application/json"

def test_sunat_catalogs_completeness():
    """Verifica que los catálogos oficiales de SUNAT contengan las definiciones normativas requeridas."""
    doc_codes = [d["code"] for d in DOCUMENT_TYPES]
    assert "01" in doc_codes
    assert "03" in doc_codes
    assert "07" in doc_codes
    assert "08" in doc_codes
    assert "09" in doc_codes

    id_codes = [d["code"] for d in IDENTITY_DOCUMENT_TYPES]
    assert "1" in id_codes
    assert "6" in id_codes

    nc_codes = [nc["code"] for nc in CREDIT_NOTE_REASONS]
    assert "01" in nc_codes
    assert "06" in nc_codes

    det_codes = [ds["code"] for ds in DETRACTION_SERVICES]
    assert "027" in det_codes
    assert "025" in det_codes

    all_cats = get_all_sunat_catalogs()
    assert "document_types" in all_cats
    assert "detraction_services" in all_cats
    assert "despatch_reasons" in all_cats

def test_generate_sales_excel_report_structure():
    """Verifica la generación binaria de reporte Excel de ventas con formato RVIE."""
    mock_documents = [
        SimpleNamespace(
            issue_date="2026-10-01",
            due_date="2026-10-31",
            type_code="01",
            series="F001",
            correlative=105,
            client_doc_type="6",
            client_doc_number="20444555666",
            client_name="ACEROS AREQUIPA SA",
            currency="PEN",
            total_taxable=10000.00,
            total_igv=1800.00,
            total=11800.00,
            payment_method="Crédito",
            detraction={"amount": 1180.00},
            status="accepted",
            pdf_url="https://api-factos.test/pdf/105",
        ),
        SimpleNamespace(
            issue_date="2026-10-02",
            due_date=None,
            type_code="03",
            series="B001",
            correlative=42,
            client_doc_type="1",
            client_doc_number="45678912",
            client_name="JUAN PEREZ",
            currency="PEN",
            total_taxable=200.00,
            total_igv=36.00,
            total=236.00,
            payment_method="Contado",
            detraction=None,
            status="accepted",
            pdf_url=None,
        )
    ]

    excel_bytes = generate_sales_report_excel(
        company_name="MINERA CARBONES DEL PERU SAC",
        company_ruc="20601234567",
        documents=mock_documents
    )
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 2000

    wb = openpyxl.load_workbook(BytesIO(excel_bytes))
    sheet = wb.active
    assert "MINERA CARBONES DEL PERU SAC" in sheet["A1"].value
    assert "20601234567" in sheet["A2"].value

def test_generate_despatches_excel_report_structure():
    """Verifica la generación binaria de reporte Excel de Guías de Remisión."""
    mock_despatches = [
        SimpleNamespace(
            series="T001",
            correlative=55,
            type_code="09",
            issue_date="2026-10-05",
            transfer_date="2026-10-06",
            recipient={
                "doc_number": "20444555666",
                "name": "CORPORACION LINDLEY",
            },
            origin={"address": "Calle A 123"},
            destination={"address": "Av. B 456"},
            total_weight=28.5,
            weight_unit="TNE",
            transport_mode="02",
            status="accepted",
        )
    ]

    excel_bytes = generate_despatches_report_excel(
        company_name="MINERA CARBONES DEL PERU SAC",
        company_ruc="20601234567",
        despatches=mock_despatches
    )
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 2000

    wb = openpyxl.load_workbook(BytesIO(excel_bytes))
    sheet = wb.active
    assert "MINERA CARBONES DEL PERU SAC" in sheet["A1"].value
