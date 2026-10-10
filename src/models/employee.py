from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_type = Column(String(2), default="1", nullable=False) # 1=DNI, 4=CE
    document_number = Column(String(15), nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    email = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Para choferes de Guías de Remisión (GRE)
    license_number = Column(String(20), nullable=True) # Licencia de conducir MTC (ej. Q12345678)
    
    # Vinculación con cuenta de acceso de usuario (si tiene credenciales en el sistema)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    user = relationship("User", foreign_keys=[user_id])

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_seller(self) -> bool:
        return True

    @property
    def is_driver(self) -> bool:
        return bool(self.license_number)
