from datetime import date, datetime
from typing import Optional, List, Any, Dict
from decimal import Decimal
from pydantic import BaseModel, Field

class DocumentItemSchema(BaseModel):
    internal_code: Optional[str] = None
    description: str
    unit_code: str = "TNE"
    quantity: Decimal = Field(..., gt=0)
    unit_value: Decimal = Field(..., ge=0)
    unit_price: Decimal = Field(..., ge=0)
    igv_type: str = "10"
    igv_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    total: Decimal = Field(..., ge=0)

class InstallmentSchema(BaseModel):
    due_date: str # YYYY-MM-DD
    amount: Decimal = Field(..., gt=0)

class DetractionSchema(BaseModel):
    payment_method_code: str = "001" # 001 = Depósito en cuenta Banco de la Nación
    bank_account: str # Cuenta corriente detracciones BN
    service_code: str = "023" # 023 = Minerales no metálicos / carbón, o 004 = Recursos minerales
    percent: Decimal = Field(default=Decimal("10.00"), ge=0)
    amount: Decimal = Field(..., gt=0)

class NoteDataSchema(BaseModel):
    affected_type: str # 01=Factura, 03=Boleta
    affected_series: str # F001, etc.
    affected_correlative: int
    code: str # Código catálogo SUNAT 09 o 10
    reason: str

class ClientDataSchema(BaseModel):
    doc_type: str # 6=RUC, 1=DNI, 4=CE, 7=Pasaporte, 0=Sin doc
    doc_number: str
    name: str
    address: Optional[str] = None
    email: Optional[str] = None

class DocumentCreate(BaseModel):
    company_id: int
    is_test_mode: bool = False
    
    # 01=Factura, 03=Boleta, 07=Nota Crédito, 08=Nota Débito
    type_code: str = "01"
    operation_type: str = "0101" # 0101 = Venta interna
    series: str = Field(..., min_length=4, max_length=4)
    correlative: Optional[int] = None # Si es null, auto-generar siguiente correlativo
    
    issue_date: str # YYYY-MM-DD
    issue_time: Optional[str] = "12:00:00"
    due_date: Optional[str] = None
    currency: str = "PEN" # PEN, USD
    
    payment_method: str = "contado" # contado, credito
    installments: Optional[List[InstallmentSchema]] = None
    
    detraction: Optional[DetractionSchema] = None
    retention: Optional[Dict[str, Any]] = None
    prepayments: Optional[List[Dict[str, Any]]] = None
    related_documents: Optional[List[Dict[str, Any]]] = None
    
    note: Optional[NoteDataSchema] = None # Para notas de crédito / débito
    purchase_order: Optional[str] = None
    plate_number: Optional[str] = None
    
    client: ClientDataSchema
    items: List[DocumentItemSchema]

class DocumentVoidRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=250, description="Motivo de la baja o anulación ante SUNAT")

class DocumentOut(BaseModel):
    id: int
    company_id: int
    is_test_mode: bool
    facturador_document_id: Optional[str] = None
    external_id: Optional[str] = None
    type_code: str
    operation_type: str
    series: str
    correlative: int
    document_number: str
    issue_date: date
    issue_time: str
    due_date: Optional[date] = None
    currency: str
    payment_method: str
    installments: Optional[List[Dict[str, Any]]] = None
    detraction: Optional[Dict[str, Any]] = None
    
    client_doc_type: str
    client_doc_number: str
    client_name: str
    client_address: Optional[str] = None
    client_email: Optional[str] = None
    
    total_taxable: Decimal
    total_unaffected: Decimal
    total_exonerated: Decimal
    total_free: Decimal
    total_exportation: Decimal
    total_igv: Decimal
    total_discount: Decimal
    total: Decimal
    
    status: str
    sunat_code: Optional[str] = None
    sunat_description: Optional[str] = None
    sunat_notes: Optional[List[str]] = None
    
    pdf_url: Optional[str] = None
    xml_url: Optional[str] = None
    cdr_url: Optional[str] = None
    void_reason: Optional[str] = None
    voided_at: Optional[datetime] = None
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
