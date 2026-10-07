from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    document_type = Column(String(2), default="1", nullable=False) # 1=DNI, 4=CE
    document_number = Column(String(15), nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    # Cargo / Rol Opcional
    job_title = Column(String(50), nullable=True, default=None)
    email = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Para choferes de Guías de Remisión (GRE)
    license_number = Column(String(20), nullable=True) # Licencia de conducir MTC (ej. Q12345678)
    
    # Comisión comercial opcional
    commission_rate = Column(Numeric(5, 2), default=0.00, nullable=True)
    
    # Vinculación con cuenta de acceso de usuario (si tiene credenciales en el sistema)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="employees")
    user = relationship("User", foreign_keys=[user_id])

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_seller(self) -> bool:
        title = (self.job_title or "").lower()
        return "vendedor" in title or (self.commission_rate or 0) > 0

    @property
    def is_driver(self) -> bool:
        title = (self.job_title or "").lower()
        return bool(self.license_number) or "chofer" in title or "conductor" in title
