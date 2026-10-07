from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from src.core.database import Base

class CompanySeries(Base):
    __tablename__ = "company_series"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Tipo de documento SUNAT: 01 (Factura), 03 (Boleta), 07 (Nota de Crédito), 08 (Nota de Débito), 09 (GRE Remitente), 31 (GRE Transportista)
    document_type = Column(String(2), nullable=False, index=True)
    series = Column(String(4), nullable=False, index=True) # F001, B001, FC01, BC01, FD01, BD01, T001
    correlative_current = Column(Integer, default=0, nullable=False)
    description = Column(String(100), nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="series")

    __table_args__ = (
        UniqueConstraint("company_id", "document_type", "series", name="uq_company_doc_series"),
    )
