import logging
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from src.models.company import Company
from src.models.series import CompanySeries
from src.models.bank import Bank, BankAccount
from src.services.facturador.client import facturador_gateway

logger = logging.getLogger("hania_sync")

async def auto_sync_test_company(db: Session) -> Optional[Company]:
    """
    Verifica que la empresa de prueba generada automáticamente por el Facturador
    (Factos API) esté registrada y sincronizada en la base de datos de Hania.
    
    Si no existe en Hania, consulta el Facturador, obtiene sus datos oficiales y la inserta
    junto con sus series y cuentas bancarias para que ambos sistemas queden perfectamente
    interconectados de forma automática.
    """
    try:
        # 1. Consultar empresas registradas en Factos API para la cuenta actual
        res = await facturador_gateway.list_companies()
        factos_companies = res.get("data", []) if isinstance(res, dict) else []
        
        # 2. Localizar la empresa de prueba en el Facturador
        test_factos = None
        for c in factos_companies:
            if c.get("is_production") is False or str(c.get("ruc")) == "20000000001":
                test_factos = c
                break
                
        # Si no existe en el Facturador todavía, solicitar su creación vía API
        if not test_factos:
            logger.info("Empresa de prueba no encontrada en Facturador. Creando empresa de prueba...")
            create_res = await facturador_gateway.create_test_company()
            if isinstance(create_res, dict) and "data" in create_res:
                test_factos = create_res["data"]
            else:
                test_factos = create_res
                
        if not test_factos or not test_factos.get("id"):
            logger.warning("No se pudo obtener la empresa de prueba desde el Facturador.")
            return None
            
        factos_id = str(test_factos["id"])
        factos_ruc = str(test_factos.get("ruc") or "20000000001")
        
        # 3. Verificar si ya existe en la BD de Hania
        existing = db.query(Company).filter(
            (Company.facturador_company_id == factos_id) |
            ((Company.ruc == factos_ruc) & (Company.is_production == False))
        ).first()
        
        if existing:
            # Asegurar sincronización de ID y entorno
            updated = False
            if existing.facturador_company_id != factos_id:
                existing.facturador_company_id = factos_id
                updated = True
            if existing.is_production is not False:
                existing.is_production = False
                updated = True
            if not existing.is_active:
                existing.is_active = True
                updated = True
            if updated:
                db.commit()
                db.refresh(existing)
            logger.info(f"Empresa de prueba sincronizada en Hania: ID {existing.id} (RUC: {existing.ruc})")
            return existing
            
        # 4. No existe en Hania: Insertarla tomando los datos del Facturador
        logger.info(f"Insertando empresa de prueba de Factos en Hania BD (Factos ID: {factos_id}, RUC: {factos_ruc})...")
        new_company = Company(
            facturador_company_id=factos_id,
            ruc=factos_ruc,
            business_name=test_factos.get("business_name") or "EMPRESA DE PRUEBA SUNAT S.A.C.",
            trademark_name=test_factos.get("trademark_name") or "FACTOS BETA TEST",
            address=test_factos.get("address") or "AV. LOS TESTERS 123 - URB. INDUSTRIAL",
            ubigeo=test_factos.get("ubigeo") or "150101",
            department=test_factos.get("department") or "LIMA",
            province=test_factos.get("province") or "LIMA",
            district=test_factos.get("district") or "LIMA",
            establishment_code=test_factos.get("establishment_code") or "0000",
            sol_user=test_factos.get("sol_user") or "MODDATOS",
            bn_account="00-068-123456",
            detraction_percent_default=Decimal("10.00"),
            phone="01-555-1234",
            email=test_factos.get("mail_from_address") or "contabilidad@empresa-prueba.pe",
            is_matrix=False,
            is_production=False,
            is_active=True,
        )
        db.add(new_company)
        db.commit()
        db.refresh(new_company)
        
        # 5. Sembrar series oficiales para comprobantes de prueba
        default_series_specs = [
            ("01", "F001", "Serie Principal Facturas Electrónicas (Prueba)"),
            ("03", "B001", "Serie Principal Boletas de Venta (Prueba)"),
            ("07", "FC01", "Serie Notas de Crédito Facturas (Prueba)"),
            ("07", "BC01", "Serie Notas de Crédito Boletas (Prueba)"),
            ("08", "FD01", "Serie Notas de Débito Facturas (Prueba)"),
            ("08", "BD01", "Serie Notas de Débito Boletas (Prueba)"),
            ("09", "T001", "Serie Guías de Remisión Remitente (Prueba)"),
        ]
        for doc_type, ser, desc in default_series_specs:
            db.add(CompanySeries(
                company_id=new_company.id,
                document_type=doc_type,
                series=ser,
                correlative_current=0,
                description=desc,
                is_active=True,
            ))
            
        # 6. Sembrar cuentas bancarias iniciales de prueba
        bn_bank = db.query(Bank).filter(Bank.code == "BN").first()
        if bn_bank:
            db.add(BankAccount(
                company_id=new_company.id,
                bank_id=bn_bank.id,
                account_type="detraccion",
                currency="PEN",
                account_number="00-068-123456",
                cci_number="018-068-000068123456-78",
                alias="Cuenta Detracciones BN (Pruebas)",
                is_detraction=True,
                is_default=True,
            ))
        bcp_bank = db.query(Bank).filter(Bank.code == "BCP").first()
        if bcp_bank:
            db.add(BankAccount(
                company_id=new_company.id,
                bank_id=bcp_bank.id,
                account_type="corriente",
                currency="PEN",
                account_number="191-2345678-0-12",
                cci_number="002-191-002345678012-54",
                alias="Cuenta Corriente Soles BCP (Pruebas)",
                is_detraction=False,
                is_default=False,
            ))
            
        db.commit()
        logger.info(f"Empresa de prueba sincronizada y creada exitosamente en Hania: ID {new_company.id}")
        return new_company

    except Exception as e:
        logger.error(f"Error al sincronizar empresa de prueba con Factos API: {e}", exc_info=True)
        return None
