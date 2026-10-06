from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    internal_code = Column(String(50), nullable=True)
    description = Column(String(255), nullable=False)
    unit_code = Column(String(5), default="TNE", nullable=False) # TNE=Toneladas, NIU=Unidad, KGM=Kilos, etc.
    unit_value = Column(Numeric(14, 4), default=0.00, nullable=False) # Valor unitario (sin IGV)
    unit_price = Column(Numeric(14, 4), default=0.00, nullable=False) # Precio unitario (con IGV)
    igv_type = Column(String(5), default="10", nullable=False) # 10=Gravado Ope Onerosa
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="products")
