from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from src.core.config import settings
from src.core.database import Base, engine, SessionLocal
from src.core.security import get_password_hash
from src.models import (
    User, Company, Client, Product, Document, DocumentItem, Despatch, DespatchItem,
    Bank, BankAccount, CompanySeries, WebhookLog,
    Employee, Vehicle
)

def _sync_schema_columns():
    """Garantiza la existencia de columnas nuevas y de borrado lógico en todas las tablas."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    columns_spec = {
        "clients": [
            ("is_active", "TINYINT(1) NOT NULL DEFAULT 1"),
            ("deleted_at", "DATETIME NULL"),
            ("ubigeo", "VARCHAR(6) NULL"),
            ("department", "VARCHAR(50) NULL"),
            ("province", "VARCHAR(50) NULL"),
            ("district", "VARCHAR(50) NULL"),
            ("contact_name", "VARCHAR(100) NULL"),
            ("condition_sunat", "VARCHAR(50) DEFAULT 'HABIDO' NULL"),
            ("state_sunat", "VARCHAR(50) DEFAULT 'ACTIVO' NULL"),
            ("credit_days_default", "INT NOT NULL DEFAULT 0"),
        ],
        "products": [
            ("is_active", "TINYINT(1) NOT NULL DEFAULT 1"),
            ("deleted_at", "DATETIME NULL"),
            ("barcode", "VARCHAR(50) NULL"),
            ("sunat_code", "VARCHAR(50) NULL"),
            ("category_name", "VARCHAR(100) NOT NULL DEFAULT 'General'"),
            ("currency", "VARCHAR(3) NOT NULL DEFAULT 'PEN'"),
            ("cost_price", "DECIMAL(14, 4) NOT NULL DEFAULT 0.00"),
            ("has_detraction", "TINYINT(1) NOT NULL DEFAULT 0"),
            ("detraction_code", "VARCHAR(10) NULL"),
            ("detraction_percent", "DECIMAL(5, 2) NULL"),
            ("is_service", "TINYINT(1) NOT NULL DEFAULT 0"),
            ("stock", "DECIMAL(14, 2) NOT NULL DEFAULT 0.00"),
            ("stock_min", "DECIMAL(14, 2) NOT NULL DEFAULT 0.00"),
            ("notes", "VARCHAR(255) NULL"),
        ],
        "companies": [
            ("is_active", "TINYINT(1) NOT NULL DEFAULT 1"),
            ("deleted_at", "DATETIME NULL"),
            ("bn_account", "VARCHAR(50) NULL"),
            ("detraction_percent_default", "DECIMAL(5, 2) DEFAULT 10.00 NULL"),
            ("phone", "VARCHAR(50) NULL"),
            ("email", "VARCHAR(100) NULL"),
            ("website", "VARCHAR(100) NULL"),
            ("logo_url", "TEXT NULL"),
            ("updated_at", "DATETIME NULL"),
        ],
        "users": [
            ("is_active", "TINYINT(1) NOT NULL DEFAULT 1"),
            ("deleted_at", "DATETIME NULL"),
            ("email", "VARCHAR(100) NULL"),
            ("phone", "VARCHAR(50) NULL"),
            ("role", "VARCHAR(50) NOT NULL DEFAULT 'ADMIN'"),
            ("default_company_id", "INT NULL"),
            ("assigned_series", "VARCHAR(10) NULL"),
            ("permissions", "TEXT NULL"),
        ],
        "documents": [
            ("is_active", "TINYINT(1) NOT NULL DEFAULT 1"),
            ("deleted_at", "DATETIME NULL"),
            ("seller_name", "VARCHAR(100) NULL"),
            ("employee_id", "INT NULL"),
        ],
        "despatches": [("is_active", "TINYINT(1) NOT NULL DEFAULT 1"), ("deleted_at", "DATETIME NULL")],
        "banks": [("is_active", "TINYINT(1) NOT NULL DEFAULT 1")],
        "bank_accounts": [("is_active", "TINYINT(1) NOT NULL DEFAULT 1"), ("deleted_at", "DATETIME NULL")],
        "company_series": [("is_active", "TINYINT(1) NOT NULL DEFAULT 1"), ("deleted_at", "DATETIME NULL")],
    }
    with engine.connect() as conn:
        for tbl, cols in columns_spec.items():
            if tbl in tables:
                existing_cols = {c["name"] for c in inspector.get_columns(tbl)}
                for col_name, col_type in cols:
                    if col_name not in existing_cols:
                        try:
                            conn.execute(text(f"ALTER TABLE `{tbl}` ADD COLUMN `{col_name}` {col_type}"))
                            conn.commit()
                        except Exception:
                            pass

def init_db():
    # 1. Crear todas las tablas que no existan
    Base.metadata.create_all(bind=engine)
    # 2. Sincronizar columnas adicionales
    _sync_schema_columns()

    db: Session = SessionLocal()
    try:
        # 3. Sembrar usuario inicial si no existe
        init_username = settings.ADMIN_INITIAL_USERNAME or "admin"
        admin = db.query(User).filter(User.username == init_username).first()
        if not admin and settings.ADMIN_INITIAL_PASSWORD:
            admin = User(
                username=init_username,
                password_hash=get_password_hash(settings.ADMIN_INITIAL_PASSWORD),
                full_name="Administrador Cupper & Hannia",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

        # 4. Sembrar catálogo maestro de bancos peruanos
        initial_banks = [
            ("BCP", "Banco de Crédito del Perú", "BCP"),
            ("BBVA", "BBVA Banco Continental", "BBVA"),
            ("INTERBANK", "Interbank", "Interbank"),
            ("SCOTIABANK", "Scotiabank Perú", "Scotiabank"),
            ("BN", "Banco de la Nación", "Banco de la Nación"),
            ("BANBIF", "BanBif", "BanBif"),
            ("PICHINCHA", "Banco Pichincha", "Pichincha"),
            ("GNB", "Banco GNB Perú", "GNB"),
        ]
        existing_bank_codes = {b[0] for b in db.query(Bank.code).all()}
        for b_code, b_name, b_short in initial_banks:
            if b_code not in existing_bank_codes:
                db.add(Bank(code=b_code, name=b_name, short_name=b_short, is_active=True))
                existing_bank_codes.add(b_code)
        db.commit()

        # 5. Sembrar empresa matriz: Corporación de Servicios Cupper & Hannia E.I.R.L
        company_ruc = settings.DEFAULT_COMPANY_RUC or "20612955990"
        cupper = db.query(Company).filter(Company.ruc == company_ruc).first()
        if not cupper:
            cupper = Company(
                facturador_company_id=settings.FACTOS_COMPANY_ID or None,
                ruc=company_ruc,
                business_name=settings.DEFAULT_COMPANY_NAME or "CORPORACION DE SERVICIOS CUPPER & HANNIA E.I.R.L.",
                trademark_name="CUPPER & HANNIA",
                address="CAL. SECT 2 F 01 NRO. 23 A.H. LOS REYES CALLAO VENTANILLA",
                ubigeo="070106",
                department="CALLAO",
                province="CALLAO",
                district="VENTANILLA",
                establishment_code="0000",
                sol_user="MODDATOS",
                bn_account="00-068-123456",
                detraction_percent_default=Decimal("10.00"),
                phone="01-555-1234",
                email="administracion@cupperhannia.com",
                is_matrix=True,
                is_active=True,
            )
            db.add(cupper)
            db.commit()
            db.refresh(cupper)
        else:
            if not cupper.bn_account:
                cupper.bn_account = "00-068-123456"
                cupper.detraction_percent_default = Decimal("10.00")
                db.commit()

        # 6. Sembrar cuentas bancarias para empresas activas
        all_companies = db.query(Company).filter(Company.is_active == True).all()
        bn_bank = db.query(Bank).filter(Bank.code == "BN").first()
        bcp_bank = db.query(Bank).filter(Bank.code == "BCP").first()
        bbva_bank = db.query(Bank).filter(Bank.code == "BBVA").first()

        for comp in all_companies:
            if db.query(BankAccount).filter(BankAccount.company_id == comp.id).count() == 0:
                accounts_to_add = []
                if bn_bank:
                    accounts_to_add.append(
                        BankAccount(
                            company_id=comp.id,
                            bank_id=bn_bank.id,
                            account_type="detraccion",
                            currency="PEN",
                            account_number=comp.bn_account or "00-068-123456",
                            cci_number="018-068-000068123456-78",
                            alias="Cuenta Detracciones BN (Carbón y Minería)",
                            show_in_pdf=True,
                            is_default=True,
                        )
                    )
                if bcp_bank:
                    accounts_to_add.append(
                        BankAccount(
                            company_id=comp.id,
                            bank_id=bcp_bank.id,
                            account_type="corriente",
                            currency="PEN",
                            account_number="191-2345678-0-12",
                            cci_number="002-191-002345678012-54",
                            alias="Cuenta Corriente Operaciones Soles BCP",
                            show_in_pdf=True,
                            is_default=False,
                        )
                    )
                if bbva_bank:
                    accounts_to_add.append(
                        BankAccount(
                            company_id=comp.id,
                            bank_id=bbva_bank.id,
                            account_type="corriente",
                            currency="USD",
                            account_number="0011-0123-0100123456",
                            cci_number="011-123-000100123456-91",
                            alias="Cuenta Corriente Dólares BBVA",
                            show_in_pdf=True,
                            is_default=False,
                        )
                    )
                db.add_all(accounts_to_add)
                db.commit()

        # 7. Sembrar series oficiales por defecto para cada empresa
        default_series_specs = [
            ("01", "F001", "Serie Principal Facturas Electrónicas"),
            ("03", "B001", "Serie Principal Boletas de Venta"),
            ("07", "FC01", "Serie Notas de Crédito para Facturas"),
            ("07", "BC01", "Serie Notas de Crédito para Boletas"),
            ("08", "FD01", "Serie Notas de Débito para Facturas"),
            ("08", "BD01", "Serie Notas de Débito para Boletas"),
            ("09", "T001", "Serie Guías de Remisión Remitente"),
        ]
        existing_series = {(s[0], s[1], s[2]) for s in db.query(CompanySeries.company_id, CompanySeries.document_type, CompanySeries.series).all()}
        for comp in all_companies:
            for doc_type, ser, desc in default_series_specs:
                if (comp.id, doc_type, ser) not in existing_series:
                    max_corr = db.query(Document.correlative).filter(
                        Document.company_id == comp.id,
                        Document.type_code == doc_type,
                        Document.series == ser,
                    ).order_by(Document.correlative.desc()).first()
                    curr = max_corr[0] if max_corr else 0

                    db.add(CompanySeries(
                        company_id=comp.id,
                        document_type=doc_type,
                        series=ser,
                        correlative_current=curr,
                        description=desc,
                        is_active=True,
                    ))
                    existing_series.add((comp.id, doc_type, ser))
        db.commit()

        # 8. Sembrar productos y servicios típicos de carbón y pequeña minería si no hay
        if db.query(Product).filter(Product.company_id == cupper.id).count() == 0:
            products = [
                Product(
                    company_id=cupper.id,
                    internal_code="CARB-ANT-01",
                    description="Carbón Antracita en Grano Seleccionado (TNE)",
                    unit_code="TNE",
                    unit_value=Decimal("550.0000"),
                    unit_price=Decimal("649.0000"),
                    igv_type="10",
                ),
                Product(
                    company_id=cupper.id,
                    internal_code="CARB-FIN-02",
                    description="Carbón Fino Térmico Industrial (TNE)",
                    unit_code="TNE",
                    unit_value=Decimal("380.0000"),
                    unit_price=Decimal("448.4000"),
                    igv_type="10",
                ),
                Product(
                    company_id=cupper.id,
                    internal_code="SERV-MOL-01",
                    description="Servicio de Molienda y Tamizado de Mineral de Carbón",
                    unit_code="ZZ",
                    unit_value=Decimal("800.0000"),
                    unit_price=Decimal("944.0000"),
                    igv_type="10",
                ),
                Product(
                    company_id=cupper.id,
                    internal_code="SERV-FLET-01",
                    description="Servicio de Flete Terrestre Tolva Minera",
                    unit_code="ZZ",
                    unit_value=Decimal("1200.0000"),
                    unit_price=Decimal("1416.0000"),
                    igv_type="10",
                ),
            ]
            db.add_all(products)
            db.commit()

        # 9. Sembrar clientes frecuentes de la industria si no hay
        if db.query(Client).filter(Client.company_id == cupper.id).count() == 0:
            clients = [
                Client(
                    company_id=cupper.id,
                    doc_type="6",
                    doc_number="20100070970",
                    name="SIDERPERU - EMPRESA SIDERURGICA DEL PERU S.A.A.",
                    address="AV. SANTIAGO ANTUNEZ DE MAYOLO S/N Z.I. CHIMBOTE",
                    email="adquisiciones@siderperu.com.pe",
                    phone="043-483000",
                ),
                Client(
                    company_id=cupper.id,
                    doc_type="6",
                    doc_number="20100138019",
                    name="CORPORACION ACEROS AREQUIPA S.A.",
                    address="CAR. PANAMERICANA SUR KM. 240 PISCO",
                    email="compras.materia@acerosarequipa.pe",
                    phone="056-532200",
                ),
                Client(
                    company_id=cupper.id,
                    doc_type="6",
                    doc_number="20504794637",
                    name="CEMENTOS PACASMAYO S.A.A.",
                    address="CAL. LA COLONIA NRO. 180 URB. EL VIVERO LIMA",
                    email="facturacion.proveedores@cpacasmayo.com.pe",
                    phone="01-3176000",
                ),
            ]
            db.add_all(clients)
            db.commit()

        # 10. Sembrar trabajadores / vendedores / choferes
        for comp in all_companies:
            if comp and db.query(Employee).filter(Employee.company_id == comp.id).count() == 0:
                employees = [
                    Employee(
                        company_id=comp.id,
                        document_type="1",
                        document_number="45892144",
                        first_name="Carlos",
                        last_name="Mendoza Vega",
                        job_title="Vendedor Principal",
                        email="carlos.ventas@empresa.com",
                        phone="987654321",
                        commission_rate=Decimal("2.50"),
                    ),
                    Employee(
                        company_id=comp.id,
                        document_type="1",
                        document_number="41258963",
                        first_name="Jorge Luis",
                        last_name="Ramírez Soto",
                        job_title="Conductor / Chofer",
                        email="jorge.transporte@empresa.com",
                        phone="951234567",
                        license_number="Q41258963",
                        commission_rate=Decimal("0.00"),
                    ),
                ]
                db.add_all(employees)
                db.commit()

        # 11. Sembrar flota vehicular para Guías de Remisión (GRE)
        for comp in all_companies:
            if comp and db.query(Vehicle).filter(Vehicle.company_id == comp.id).count() == 0:
                vehicles = [
                    Vehicle(
                        company_id=comp.id,
                        plate_number="T3B-892",
                        secondary_plate="BC4-110",
                        brand="Volvo",
                        model="FH540 Tolva",
                        mtc_authorization="MTC-154879-PE",
                    ),
                    Vehicle(
                        company_id=comp.id,
                        plate_number="F4D-721",
                        secondary_plate=None,
                        brand="Scania",
                        model="G460 Furgón",
                        mtc_authorization="MTC-202411-PE",
                    ),
                ]
                db.add_all(vehicles)
                db.commit()

    finally:
        db.close()
