from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    plate_number = Column(String(10), nullable=False, index=True) # Ej. "ABC-123" o "ABC123"
    secondary_plate = Column(String(10), nullable=True) # Placa de semirremolque o remolque
    brand = Column(String(50), nullable=True) # Ej. "Volvo", "Scania", "Toyota"
    model = Column(String(50), nullable=True)
    mtc_authorization = Column(String(50), nullable=True) # Certificado de habilitación vehicular del MTC
    
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="vehicles")
