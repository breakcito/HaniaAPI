from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from src.core.database import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    facturador_company_id = Column(String(36), nullable=True, index=True) # UUID asignado en Factos API
    ruc = Column(String(11), unique=True, index=True, nullable=False)
    business_name = Column(String(255), nullable=False)
    trademark_name = Column(String(255), nullable=True)
    address = Column(String(255), nullable=True)
    ubigeo = Column(String(6), nullable=True)
    department = Column(String(100), nullable=True)
    province = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    establishment_code = Column(String(4), default="0000", nullable=False)
    sol_user = Column(String(50), nullable=True)
    is_matrix = Column(Boolean, default=False, nullable=False) # True para Cupper & Hannia
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    documents = relationship("Document", back_populates="company")
    despatches = relationship("Despatch", back_populates="company")
    clients = relationship("Client", back_populates="company")
    products = relationship("Product", back_populates="company")
