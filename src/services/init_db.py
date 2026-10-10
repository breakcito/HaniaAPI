from sqlalchemy import inspect, text
from src.core.database import Base, engine


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
            ("sunat_code", "VARCHAR(50) NULL"),
            ("currency", "VARCHAR(3) NOT NULL DEFAULT 'PEN'"),
            ("has_detraction", "TINYINT(1) NOT NULL DEFAULT 0"),
            ("detraction_code", "VARCHAR(10) NULL"),
            ("detraction_percent", "DECIMAL(5, 2) NULL"),
            ("is_service", "TINYINT(1) NOT NULL DEFAULT 0"),
        ],
        "companies": [
            ("is_active", "TINYINT(1) NOT NULL DEFAULT 1"),
            ("deleted_at", "DATETIME NULL"),
            ("detraction_percent_default", "DECIMAL(5, 2) DEFAULT 10.00 NULL"),
            ("phone", "VARCHAR(50) NULL"),
            ("email", "VARCHAR(100) NULL"),
            ("logo_url", "TEXT NULL"),
            ("updated_at", "DATETIME NULL"),
        ],
        "users": [
            ("is_active", "TINYINT(1) NOT NULL DEFAULT 1"),
            ("deleted_at", "DATETIME NULL"),
            ("role", "VARCHAR(50) NOT NULL DEFAULT 'ADMIN'"),
            ("permissions", "TEXT NULL"),
        ],
        "documents": [
            ("is_active", "TINYINT(1) NOT NULL DEFAULT 1"),
            ("deleted_at", "DATETIME NULL"),
            ("seller_name", "VARCHAR(100) NULL"),
            ("employee_id", "INT NULL"),
        ],
        "despatches": [
            ("is_active", "TINYINT(1) NOT NULL DEFAULT 1"),
            ("deleted_at", "DATETIME NULL"),
        ],
        "banks": [("is_active", "TINYINT(1) NOT NULL DEFAULT 1")],
        "bank_accounts": [
            ("is_active", "TINYINT(1) NOT NULL DEFAULT 1"),
            ("deleted_at", "DATETIME NULL"),
        ],
        "company_series": [
            ("is_active", "TINYINT(1) NOT NULL DEFAULT 1"),
            ("deleted_at", "DATETIME NULL"),
        ],
    }
    with engine.connect() as conn:
        for tbl, cols in columns_spec.items():
            if tbl in tables:
                existing_cols = {c["name"] for c in inspector.get_columns(tbl)}
                for col_name, col_type in cols:
                    if col_name not in existing_cols:
                        try:
                            conn.execute(
                                text(
                                    f"ALTER TABLE `{tbl}` ADD COLUMN `{col_name}` {col_type}"
                                )
                            )
                            conn.commit()
                        except Exception:
                            pass


def init_db():
    # 1. Crear tablas si no existen
    Base.metadata.create_all(bind=engine)
    # 2. Sincronizar columnas faltantes en tablas existentes
    _sync_schema_columns()
