"""Pruebas unitarias de modelos de datos y reglas de negocio."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from src.models.company import Company
from src.models.product import Product
from src.models.client import Client
from src.models.employee import Employee
from src.models.vehicle import Vehicle
from src.models.bank import Bank, BankAccount
from src.models.series import CompanySeries
from src.models.document import Document, DocumentItem

def test_company_model_structure(db_session: Session, test_company: Company):
    """Verifica que el modelo de Empresa posea los atributos fiscales y maestros requeridos."""
    assert test_company.ruc is not None
    assert len(test_company.ruc) == 11
    assert hasattr(test_company, "detraction_percent_default")
    assert hasattr(test_company, "facturador_company_id")
    assert hasattr(test_company, "is_matrix")

def test_product_model_detraction_and_stock(db_session: Session, test_company: Company):
    """Verifica la persistencia de productos compartidos con reglas de detracción y servicio."""
    prod = Product(
        description="Carbón Especial Prueba Unitaria",
        unit_code="TNE",
        unit_value=Decimal("381.3559"),
        unit_price=Decimal("450.00"),
        is_service=False,
        has_detraction=True,
        detraction_code="027",
        detraction_percent=Decimal("10.00"),
        is_active=True,
    )
    db_session.add(prod)
    db_session.commit()
    db_session.refresh(prod)

    assert prod.id is not None
    assert prod.has_detraction is True
    assert prod.detraction_code == "027"
    assert prod.detraction_percent == Decimal("10.00")
    assert prod.is_service is False

    # Cleanup
    db_session.delete(prod)
    db_session.commit()

def test_employee_seller_driver_flags(db_session: Session, test_company: Company):
    """Verifica los atributos de chofer y datos personales en trabajadores corporativos."""
    emp = Employee(
        document_type="1",
        document_number="78901234",
        first_name="Carlos",
        last_name="Mendoza Soto",
        license_number="Q78901234",
        is_active=True,
    )
    db_session.add(emp)
    db_session.commit()
    db_session.refresh(emp)

    assert emp.id is not None
    assert emp.license_number == "Q78901234"
    assert emp.first_name == "Carlos"

    # Cleanup
    db_session.delete(emp)
    db_session.commit()

def test_vehicle_model_attributes(db_session: Session, test_company: Company):
    """Verifica el modelo de flota vehicular compartida con semirremolque y autorización MTC."""
    veh = Vehicle(
        plate_number="T5X-888",
        secondary_plate="R7Y-111",
        brand="VOLVO",
        model="FH 540",
        mtc_authorization="MTC-2026-9999",
        is_active=True,
    )
    db_session.add(veh)
    db_session.commit()
    db_session.refresh(veh)

    assert veh.id is not None
    assert veh.plate_number == "T5X-888"
    assert veh.secondary_plate == "R7Y-111"
    assert veh.mtc_authorization == "MTC-2026-9999"

    # Cleanup
    db_session.delete(veh)
    db_session.commit()

def test_client_model_ubigeo_and_credit(db_session: Session, test_company: Company):
    """Verifica que el cliente corporativo almacene ubigeo, contacto y días de crédito predeterminados."""
    cli = Client(
        doc_type="6",
        doc_number="20999888777",
        name="CLIENTE DE PRUEBAS UNITARIAS SAC",
        address="Av. Industrial 450",
        ubigeo="150101",
        department="LIMA",
        province="LIMA",
        district="LIMA",
        contact_name="Ing. Roberto Gomez",
        credit_days_default=30,
        is_active=True,
    )
    db_session.add(cli)
    db_session.commit()
    db_session.refresh(cli)

    assert cli.id is not None
    assert cli.ubigeo == "150101"
    assert cli.credit_days_default == 30
    assert cli.contact_name == "Ing. Roberto Gomez"

    # Cleanup
    db_session.delete(cli)
    db_session.commit()

def test_document_immutability_concept(db_session: Session, test_company: Company):
    """Verifica que un comprobante emitido mantenga sus valores fiscales y no sea modificado."""
    doc = Document(
        company_id=test_company.id,
        is_test_mode=True,
        type_code="01",
        series="F001",
        correlative=999901,
        issue_date=datetime.now(timezone.utc).date(),
        currency="PEN",
        client_doc_type="6",
        client_doc_number="20123456789",
        client_name="EMPRESA PRUEBA INMUTABILIDAD SAC",
        total_taxable=Decimal("1000.00"),
        total_igv=Decimal("180.00"),
        total=Decimal("1180.00"),
        status="accepted",
        is_active=True,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    assert doc.id is not None
    assert doc.status == "accepted"
    assert doc.total == Decimal("1180.00")

    # Si se anula, cambia el estado a 'voided' con motivo, pero los totales e items originales no se borran
    doc.status = "voided"
    doc.void_reason = "Error en digitación de RUC"
    doc.voided_at = datetime.now(timezone.utc)
    db_session.commit()
    db_session.refresh(doc)

    assert doc.status == "voided"
    assert doc.total == Decimal("1180.00")  # Los valores históricos no se pierden
    assert doc.void_reason == "Error en digitación de RUC"

    # Cleanup
    db_session.delete(doc)
    db_session.commit()
