from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    internal_code = Column(String(50), nullable=True, index=True)
    barcode = Column(String(50), nullable=True, index=True) # Código de barras / SKU para lectores POS
    sunat_code = Column(String(50), nullable=True) # Catálogo 25 SUNAT (UNSPSC)
    
    description = Column(String(255), nullable=False)
    category_name = Column(String(100), default="General", nullable=False, index=True)
    unit_code = Column(String(5), default="NIU", nullable=False) # NIU=Unidad, ZZ=Servicio, TNE=Toneladas, KGM=Kilos, etc.
    
    # Precios y Moneda
    currency = Column(String(3), default="PEN", nullable=False)
    unit_value = Column(Numeric(14, 4), default=0.00, nullable=False) # Valor de venta (sin IGV)
    unit_price = Column(Numeric(14, 4), default=0.00, nullable=False) # Precio de venta (con IGV)
    cost_price = Column(Numeric(14, 4), default=0.00, nullable=False) # Costo de compra referencial
    igv_type = Column(String(5), default="10", nullable=False) # 10=Gravado Ope Onerosa
    
    # Detracción y Régimen Tributario
    has_detraction = Column(Boolean, default=False, nullable=False)
    detraction_code = Column(String(10), nullable=True) # Ej. "019" Transporte, "027" Carbón, "022" Otros
    detraction_percent = Column(Numeric(5, 2), nullable=True) # Ej. 10.00, 4.00, 12.00
    
    # Control de Stock
    is_service = Column(Boolean, default=False, nullable=False) # True=Servicio (sin stock), False=Bien físico
    stock = Column(Numeric(14, 2), default=0.00, nullable=False)
    stock_min = Column(Numeric(14, 2), default=0.00, nullable=False)
    
    notes = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="products")
