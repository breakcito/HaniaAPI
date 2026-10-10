from datetime import datetime, date
from src.core.datetime_peru import now_peru
from sqlalchemy import Column, Integer, String, Boolean, Numeric, Date, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    is_test_mode = Column(Boolean, default=False, nullable=False, index=True)
    
    facturador_document_id = Column(String(36), nullable=True, index=True) # UUID en Factos API
    external_id = Column(String(100), nullable=True, index=True)
    
    # 01 = Factura, 03 = Boleta, 07 = Nota de Crédito, 08 = Nota de Débito
    type_code = Column(String(2), nullable=False, index=True)
    operation_type = Column(String(4), default="0101", nullable=False)
    establishment_code = Column(String(4), default="0000", nullable=False)
    series = Column(String(4), nullable=False, index=True)
    correlative = Column(Integer, nullable=False, index=True)
    
    issue_date = Column(Date, default=date.today, nullable=False, index=True)
    issue_time = Column(String(8), default="12:00:00", nullable=False)
    due_date = Column(Date, nullable=True)
    currency = Column(String(3), default="PEN", nullable=False) # PEN, USD
    
    # Forma de pago: contado, credito
    payment_method = Column(String(20), default="contado", nullable=False)
    installments = Column(JSON, nullable=True) # [{"due_date": "...", "amount": 100}]
    
    # Detracción (Común en carbón y minería)
    detraction = Column(JSON, nullable=True) # {"payment_method_code": "001", "bank_account": "...", "service_code": "023", "percent": 10, "amount": 150}
    retention = Column(JSON, nullable=True)
    prepayments = Column(JSON, nullable=True)
    related_documents = Column(JSON, nullable=True)
    note_data = Column(JSON, nullable=True) # Para notas de crédito / débito
    
    # Cliente
    client_doc_type = Column(String(2), nullable=False)
    client_doc_number = Column(String(15), nullable=False, index=True)
    client_name = Column(String(255), nullable=False)
    client_address = Column(String(255), nullable=True)
    client_email = Column(String(255), nullable=True)
    
    # Vendedor o Trabajador responsable de la venta
    seller_name = Column(String(100), nullable=True)
    employee_id = Column(Integer, nullable=True, index=True)
    
    # Totales
    total_taxable = Column(Numeric(14, 2), default=0.00, nullable=False)
    total_unaffected = Column(Numeric(14, 2), default=0.00, nullable=False)
    total_exonerated = Column(Numeric(14, 2), default=0.00, nullable=False)
    total_free = Column(Numeric(14, 2), default=0.00, nullable=False)
    total_exportation = Column(Numeric(14, 2), default=0.00, nullable=False)
    total_igv = Column(Numeric(14, 2), default=0.00, nullable=False)
    total_discount = Column(Numeric(14, 2), default=0.00, nullable=False)
    total = Column(Numeric(14, 2), default=0.00, nullable=False)
    
    # Estado SUNAT / Factos: pending, accepted, rejected, voided
    status = Column(String(20), default="pending", nullable=False, index=True)
    sunat_code = Column(String(10), nullable=True)
    sunat_description = Column(Text, nullable=True)
    sunat_notes = Column(JSON, nullable=True)
    
    # Archivos generados
    pdf_url = Column(String(500), nullable=True)
    xml_url = Column(String(500), nullable=True)
    cdr_url = Column(String(500), nullable=True)
    void_xml_url = Column(String(500), nullable=True)
    void_cdr_url = Column(String(500), nullable=True)
    void_reason = Column(String(255), nullable=True)
    voided_at = Column(DateTime, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=now_peru, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="documents")
    items = relationship("DocumentItem", back_populates="document", cascade="all, delete-orphan")

    @property
    def document_number(self) -> str:
        return f"{self.series}-{str(self.correlative).zfill(8)}"

class DocumentItem(Base):
    __tablename__ = "document_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    internal_code = Column(String(50), nullable=True)
    description = Column(String(500), nullable=False)
    unit_code = Column(String(5), default="TNE", nullable=False)
    quantity = Column(Numeric(14, 4), default=1.0000, nullable=False)
    unit_value = Column(Numeric(14, 4), default=0.00, nullable=False)
    unit_price = Column(Numeric(14, 4), default=0.00, nullable=False)
    igv_type = Column(String(5), default="10", nullable=False)
    igv_amount = Column(Numeric(14, 2), default=0.00, nullable=False)
    total = Column(Numeric(14, 2), default=0.00, nullable=False)

    document = relationship("Document", back_populates="items")
