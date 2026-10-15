from datetime import date
from src.core.datetime_peru import now_peru
from sqlalchemy import Column, Integer, String, Boolean, Numeric, Date, DateTime, Text, JSON
from src.core.database import Base

class PurchaseDocument(Base):
    __tablename__ = "purchase_documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # Sin FK física
    company_id = Column(Integer, nullable=False, index=True)
    supplier_doc_type = Column(String(2), default="6", nullable=False)
    supplier_doc_number = Column(String(15), nullable=False, index=True)
    supplier_name = Column(String(255), nullable=False)
    
    type_code = Column(String(2), default="01", nullable=False) # 01 Factura, 03 Boleta
    series = Column(String(10), nullable=False)
    correlative = Column(String(20), nullable=False)
    
    issue_date = Column(Date, default=date.today, nullable=False, index=True)
    due_date = Column(Date, nullable=True)
    currency = Column(String(3), default="PEN", nullable=False)
    exchange_rate = Column(Numeric(10, 4), nullable=True)
    
    taxable_base = Column(Numeric(14, 2), default=0.00, nullable=False)
    igv = Column(Numeric(14, 2), default=0.00, nullable=False)
    unaffected = Column(Numeric(14, 2), default=0.00, nullable=False)
    exonerated = Column(Numeric(14, 2), default=0.00, nullable=False)
    other_taxes = Column(Numeric(14, 2), default=0.00, nullable=False)
    total = Column(Numeric(14, 2), default=0.00, nullable=False)
    
    goods_description = Column(Text, nullable=True)
    items = Column(JSON, nullable=True)
    observations = Column(Text, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=now_peru, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    @property
    def document_number(self) -> str:
        return f"{self.series}-{self.correlative}"
