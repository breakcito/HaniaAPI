from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field

class DespatchItemSchema(BaseModel):
    internal_code: Optional[str] = None
    description: str
    unit_code: str = "TNE"
    quantity: Decimal = Field(..., gt=0)

class DespatchCreate(BaseModel):
    company_id: int
    is_test_mode: bool = False
    
    type_code: str = "09" # 09=Remitente, 31=Transportista
    series: str = Field(..., min_length=4, max_length=4)
    correlative: Optional[int] = None
    
    issue_date: str # YYYY-MM-DD
    issue_time: Optional[str] = "12:00:00"
    transfer_date: str # YYYY-MM-DD
    delivery_date: Optional[str] = None
    
    transport_mode: str = "01" # 01=Público, 02=Privado
    transfer_reason: str = "01" # 01=Venta, 04=Traslado entre establecimientos, 13=Otros
    transfer_description: Optional[str] = None
    
    total_weight: Decimal = Field(..., gt=0)
    weight_unit: str = "TNE" # TNE o KGM
    packages_count: int = Field(default=1, ge=1)
    
    # Destinatario
    recipient: Dict[str, Any] # {doc_type, doc_number, name, address, email}
    
    # Puntos de partida y llegada
    origin: Dict[str, Any] # {ubigeo, address}
    destination: Dict[str, Any] # {ubigeo, address}
    
    # Transporte público
    carrier: Optional[Dict[str, Any]] = None # {doc_type, doc_number, name, mtc}
    
    # Transporte privado
    driver: Optional[Dict[str, Any]] = None # {doc_type, doc_number, name, license}
    vehicle: Optional[Dict[str, Any]] = None # {plate_number, secondary_plate, mtc}
    
    items: List[DespatchItemSchema]

class DespatchVoidRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=250, description="Motivo de la anulación de la GRE")

class DespatchOut(BaseModel):
    id: int
    company_id: int
    is_test_mode: bool
    facturador_despatch_id: Optional[str] = None
    external_id: Optional[str] = None
    type_code: str
    series: str
    correlative: int
    despatch_number: str
    issue_date: date
    issue_time: str
    transfer_date: date
    delivery_date: Optional[date] = None
    transport_mode: str
    transfer_reason: str
    transfer_description: Optional[str] = None
    total_weight: Decimal
    weight_unit: str
    packages_count: int
    recipient: Dict[str, Any]
    origin: Dict[str, Any]
    destination: Dict[str, Any]
    carrier: Optional[Dict[str, Any]] = None
    driver: Optional[Dict[str, Any]] = None
    vehicle: Optional[Dict[str, Any]] = None
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
