from decimal import Decimal
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from src.core.config import settings
from src.core.database import Base, engine, SessionLocal
from src.core.security import get_password_hash
from src.models import User, Company, Client, Product, Document, DocumentItem, Despatch, DespatchItem

def _sync_soft_delete_columns():
    """Garantiza la existencia de columnas de borrado lógico (is_active, deleted_at) en todas las tablas."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    columns_spec = {
        "clients": [("is_active", "TINYINT(1) NOT NULL DEFAULT 1"), ("deleted_at", "DATETIME NULL")],
        "products": [("is_active", "TINYINT(1) NOT NULL DEFAULT 1"), ("deleted_at", "DATETIME NULL")],
        "companies": [("is_active", "TINYINT(1) NOT NULL DEFAULT 1"), ("deleted_at", "DATETIME NULL")],
        "users": [("is_active", "TINYINT(1) NOT NULL DEFAULT 1"), ("deleted_at", "DATETIME NULL")],
        "documents": [("is_active", "TINYINT(1) NOT NULL DEFAULT 1"), ("deleted_at", "DATETIME NULL")],
        "despatches": [("is_active", "TINYINT(1) NOT NULL DEFAULT 1"), ("deleted_at", "DATETIME NULL")],
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
                        except Exception as e:
                            pass

def init_db():
    # 1. Crear todas las tablas si no existen
    Base.metadata.create_all(bind=engine)
    # 2. Sincronizar columnas de borrado lógico
    _sync_soft_delete_columns()

    db: Session = SessionLocal()
    try:
        # 2. Sembrar usuario inicial si no existe
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

        # 3. Sembrar empresa matriz: Corporación de Servicios Cupper & Hannia E.I.R.L
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
                is_matrix=True,
                is_active=True,
            )
            db.add(cupper)
            db.commit()
            db.refresh(cupper)

        # 4. Sembrar productos y servicios típicos de carbón y pequeña minería
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

        # 5. Sembrar clientes frecuentes de la industria
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

        # 6. Sembrar historial realista de operaciones mensuales para indicadores iniciales del Dashboard
        # "Apenas se ingrese deben verse graficos con indicadores por mes en base a todas las operaciones realizadas"
        if db.query(Document).filter(Document.company_id == cupper.id).count() == 0:
            sample_docs = [
                # Mes anterior - Mayo 2026
                (date(2026, 5, 12), "F001", 101, "01", Decimal("33000.00"), Decimal("5940.00"), Decimal("38940.00"), "20100070970", "SIDERPERU S.A.A.", "60 TNE Carbón Antracita", "accepted", "0", "La Factura F001-00000101 ha sido aceptada"),
                (date(2026, 5, 20), "F001", 102, "01", Decimal("22800.00"), Decimal("4104.00"), Decimal("26904.00"), "20100138019", "ACEROS AREQUIPA S.A.", "60 TNE Carbón Fino Térmico", "accepted", "0", "La Factura F001-00000102 ha sido aceptada"),
                (date(2026, 5, 28), "B001", 54, "03", Decimal("1500.00"), Decimal("270.00"), Decimal("1770.00"), "10458923145", "CARLOS MENDOZA FLORES", "3 sacos carbón térmico para fragua", "accepted", "0", "La Boleta B001-00000054 ha sido aceptada"),
                # Junio 2026
                (date(2026, 6, 8), "F001", 103, "01", Decimal("49500.00"), Decimal("8910.00"), Decimal("58410.00"), "20504794637", "CEMENTOS PACASMAYO S.A.A.", "90 TNE Carbón Antracita", "accepted", "0", "La Factura F001-00000103 ha sido aceptada"),
                (date(2026, 6, 17), "F001", 104, "01", Decimal("18000.00"), Decimal("3240.00"), Decimal("21240.00"), "20100070970", "SIDERPERU S.A.A.", "Servicio molienda y tamizado", "accepted", "0", "La Factura F001-00000104 ha sido aceptada"),
                (date(2026, 6, 25), "FC01", 12, "07", Decimal("3300.00"), Decimal("594.00"), Decimal("3894.00"), "20504794637", "CEMENTOS PACASMAYO S.A.A.", "Ajuste por humedad 6 TNE", "accepted", "0", "La Nota de Crédito FC01-00000012 ha sido aceptada"),
                # Julio 2026
                (date(2026, 7, 5), "F001", 105, "01", Decimal("66000.00"), Decimal("11880.00"), Decimal("77880.00"), "20100138019", "ACEROS AREQUIPA S.A.", "120 TNE Carbón Antracita", "accepted", "0", "La Factura F001-00000105 ha sido aceptada"),
                (date(2026, 7, 19), "F001", 106, "01", Decimal("38000.00"), Decimal("6840.00"), Decimal("44840.00"), "20504794637", "CEMENTOS PACASMAYO S.A.A.", "100 TNE Carbón Fino Térmico", "accepted", "0", "La Factura F001-00000106 ha sido aceptada"),
                # Agosto 2026
                (date(2026, 8, 10), "F001", 107, "01", Decimal("55000.00"), Decimal("9900.00"), Decimal("64900.00"), "20100070970", "SIDERPERU S.A.A.", "100 TNE Carbón Antracita Tolva", "accepted", "0", "La Factura F001-00000107 ha sido aceptada"),
                (date(2026, 8, 22), "F001", 108, "01", Decimal("30000.00"), Decimal("5400.00"), Decimal("35400.00"), "20100138019", "ACEROS AREQUIPA S.A.", "Servicio transporte tolvas mineras", "accepted", "0", "La Factura F001-00000108 ha sido aceptada"),
                # Septiembre 2026
                (date(2026, 9, 6), "F001", 109, "01", Decimal("71500.00"), Decimal("12870.00"), Decimal("84370.00"), "20504794637", "CEMENTOS PACASMAYO S.A.A.", "130 TNE Carbón Antracita Minería", "accepted", "0", "La Factura F001-00000109 ha sido aceptada"),
                (date(2026, 9, 18), "F001", 110, "01", Decimal("45600.00"), Decimal("8208.00"), Decimal("53808.00"), "20100070970", "SIDERPERU S.A.A.", "120 TNE Carbón Fino", "accepted", "0", "La Factura F001-00000110 ha sido aceptada"),
                # Octubre 2026 (Mes Actual)
                (date(2026, 10, 2), "F001", 111, "01", Decimal("82500.00"), Decimal("14850.00"), Decimal("97350.00"), "20100138019", "ACEROS AREQUIPA S.A.", "150 TNE Carbón Antracita Industrial", "accepted", "0", "La Factura F001-00000111 ha sido aceptada"),
                (date(2026, 10, 5), "F001", 112, "01", Decimal("28500.00"), Decimal("5130.00"), Decimal("33630.00"), "20504794637", "CEMENTOS PACASMAYO S.A.A.", "75 TNE Carbón Térmico", "accepted", "0", "La Factura F001-00000112 ha sido aceptada"),
            ]

            for issue_d, s, c, tc, tax, igv, tot, doc_num, cname, item_desc, st, sun_code, sun_desc in sample_docs:
                detraction_data = {
                    "payment_method_code": "001",
                    "bank_account": settings.DEFAULT_BN_ACCOUNT or "00-068-123456",
                    "service_code": "023",
                    "percent": 10.0,
                    "amount": float(tot * Decimal("0.10")),
                } if tc == "01" and tot > Decimal("700.00") else None

                doc_pdf = f"{settings.API_FACTURADOR_URL}/api/v1/documents/demo-{s}-{c}/pdf" if settings.API_FACTURADOR_URL else None
                doc_xml = f"{settings.API_FACTURADOR_URL}/api/v1/documents/demo-{s}-{c}/xml" if settings.API_FACTURADOR_URL else None
                doc_cdr = f"{settings.API_FACTURADOR_URL}/api/v1/documents/demo-{s}-{c}/cdr" if settings.API_FACTURADOR_URL else None

                doc = Document(
                    company_id=cupper.id,
                    is_test_mode=False,
                    type_code=tc,
                    operation_type="0101",
                    series=s,
                    correlative=c,
                    issue_date=issue_d,
                    issue_time="10:30:00",
                    currency="PEN",
                    payment_method="credito" if tc == "01" else "contado",
                    installments=[{"due_date": (issue_d + timedelta(days=30)).strftime("%Y-%m-%d"), "amount": float(tot)}] if tc == "01" else None,
                    detraction=detraction_data,
                    client_doc_type="6",
                    client_doc_number=doc_num,
                    client_name=cname,
                    client_address="Dirección fiscal del cliente",
                    total_taxable=tax,
                    total_igv=igv,
                    total=tot,
                    status=st,
                    sunat_code=sun_code,
                    sunat_description=sun_desc,
                    pdf_url=doc_pdf,
                    xml_url=doc_xml,
                    cdr_url=doc_cdr,
                )
                db.add(doc)
                db.flush()

                item = DocumentItem(
                    document_id=doc.id,
                    description=item_desc,
                    unit_code="TNE",
                    quantity=Decimal("1.0000"),
                    unit_value=tax,
                    unit_price=tot,
                    igv_type="10",
                    igv_amount=igv,
                    total=tot,
                )
                db.add(item)
            
            db.commit()

        # 7. Sembrar Guías de Remisión (GRE)
        if db.query(Despatch).filter(Despatch.company_id == cupper.id).count() == 0:
            gre = Despatch(
                company_id=cupper.id,
                is_test_mode=False,
                type_code="09",
                series="T001",
                correlative=51,
                issue_date=date(2026, 10, 4),
                transfer_date=date(2026, 10, 4),
                transport_mode="01", # Público
                transfer_reason="01", # Venta
                total_weight=Decimal("30.0000"),
                weight_unit="TNE",
                packages_count=1,
                recipient={
                    "doc_type": "6",
                    "doc_number": "20100138019",
                    "name": "CORPORACION ACEROS AREQUIPA S.A.",
                    "address": "CAR. PANAMERICANA SUR KM. 240 PISCO",
                },
                origin={
                    "ubigeo": "070106",
                    "address": "CANTERA CUPPER - CALLAO VENTANILLA",
                },
                destination={
                    "ubigeo": "110505",
                    "address": "PLANTA PISCO - ACEROS AREQUIPA",
                },
                carrier={
                    "doc_type": "6",
                    "doc_number": "20489123841",
                    "name": "TRANSPORTES PESADOS DEL NORTE S.A.C.",
                    "mtc": "MTC-98213-L",
                },
                status="accepted",
                sunat_code="0",
                sunat_description="La Guía de Remisión T001-00000051 ha sido aceptada",
                pdf_url=f"{settings.API_FACTURADOR_URL}/api/v1/despatches/demo-t001-51/pdf" if settings.API_FACTURADOR_URL else None,
            )
            db.add(gre)
            db.flush()

            gre_item = DespatchItem(
                despatch_id=gre.id,
                description="Carbón Antracita en Granel 30 TNE",
                unit_code="TNE",
                quantity=Decimal("30.0000"),
            )
            db.add(gre_item)
            db.commit()

    finally:
        db.close()
