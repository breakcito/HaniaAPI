from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric
from sqlalchemy.orm import relationship
from src.core.database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    facturador_company_id = Column(String(36), nullable=True, index=True) # UUID asignado en Factos API
    ruc = Column(String(11), unique=True, index=True, nullable=False)
    business_name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=True)
    ubigeo = Column(String(6), nullable=True)
    department = Column(String(100), nullable=True)
    province = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    establishment_code = Column(String(4), default="0000", nullable=False)
    sol_user = Column(String(50), nullable=True)
    
    # Cuentas maestras y contacto
    detraction_percent_default = Column(Numeric(5, 2), default=Decimal("10.00"), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    logo_url = Column(Text, nullable=True)

    is_matrix = Column(Boolean, default=False, nullable=False) # True para Cupper & Hannia
    is_production = Column(Boolean, default=True, nullable=False, index=True) # False para Empresa de Prueba
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    documents = relationship("Document", back_populates="company")
    despatches = relationship("Despatch", back_populates="company")
    bank_accounts = relationship("BankAccount", back_populates="company", cascade="all, delete-orphan")
    series = relationship("CompanySeries", back_populates="company", cascade="all, delete-orphan")
