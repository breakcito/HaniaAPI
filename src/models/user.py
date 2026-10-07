from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from src.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Roles y Permisos: ADMIN (Total), FACTURADOR (Emisión), VENDEDOR (POS/Caja), CONTADOR (Reportes)
    role = Column(String(20), default="ADMIN", nullable=False)
    default_company_id = Column(Integer, nullable=True) # Empresa predeterminada asignada
    assigned_series = Column(String(255), nullable=True) # Series fiscales asignadas (ej. F001,B001)
    
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)
