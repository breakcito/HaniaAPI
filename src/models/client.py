from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    doc_type = Column(String(2), default="6", nullable=False) # 6=RUC, 1=DNI, 4=CE, 7=Pasaporte, 0=Sin Doc
    doc_number = Column(String(15), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=True)
    
    # Ubigeo y Localización para Guías de Remisión y Facturación
    ubigeo = Column(String(6), nullable=True)
    department = Column(String(50), nullable=True)
    province = Column(String(50), nullable=True)
    district = Column(String(50), nullable=True)
    
    # Datos de Contacto y Comerciales
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    contact_name = Column(String(100), nullable=True) # Nombre de contacto comercial
    
    # Estado SUNAT y Condiciones de Pago Habituales
    condition_sunat = Column(String(50), default="HABIDO", nullable=True)
    state_sunat = Column(String(50), default="ACTIVO", nullable=True)
    credit_days_default = Column(Integer, default=0, nullable=False) # 0=Contado, 7, 15, 30 días de crédito
    
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="clients")
