from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field

class PurchaseItemSchema(BaseModel):
    internal_code: Optional[str] = None
    description: str
    unit_code: str = "NIU"
    quantity: Decimal = Field(default=Decimal("1.0"), gt=0)
    unit_value: Decimal = Field(default=Decimal("0.0"), ge=0)
    unit_price: Decimal = Field(default=Decimal("0.0"), ge=0)
    total: Decimal = Field(default=Decimal("0.0"), ge=0)

class PurchaseCreate(BaseModel):
    company_id: int
    supplier_doc_type: str = "6" # 6=RUC
    supplier_doc_number: str = Field(..., min_length=8, max_length=15)
    supplier_name: str
    type_code: str = "01" # 01=Factura, 03=Boleta
    series: str
    correlative: str
    issue_date: str # YYYY-MM-DD
    due_date: Optional[str] = None
    currency: str = "PEN"
    exchange_rate: Optional[Decimal] = None
    taxable_base: Decimal = Field(default=Decimal("0.00"), ge=0)
    igv: Decimal = Field(default=Decimal("0.00"), ge=0)
    unaffected: Decimal = Field(default=Decimal("0.00"), ge=0)
    exonerated: Decimal = Field(default=Decimal("0.00"), ge=0)
    other_taxes: Decimal = Field(default=Decimal("0.00"), ge=0)
    total: Decimal = Field(..., ge=0)
    goods_description: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    observations: Optional[str] = None

class PurchaseOut(BaseModel):
    id: int
    company_id: int
    supplier_doc_type: str
    supplier_doc_number: str
    supplier_name: str
    type_code: str
    series: str
    correlative: str
    document_number: str
    issue_date: date
    due_date: Optional[date] = None
    currency: str
    exchange_rate: Optional[Decimal] = None
    taxable_base: Decimal
    igv: Decimal
    unaffected: Decimal
    exonerated: Decimal
    other_taxes: Decimal
    total: Decimal
    goods_description: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    observations: Optional[str] = None
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True
