from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field

class ProductBase(BaseModel):
    company_id: int
    internal_code: Optional[str] = None
    barcode: Optional[str] = None
    sunat_code: Optional[str] = None
    description: str
    category_name: str = "General"
    unit_code: str = Field(default="NIU", description="NIU=Unidad, ZZ=Servicio, TNE=Toneladas, KGM=Kilos")
    currency: str = "PEN"
    unit_value: Decimal = Field(default=Decimal("0.00"), description="Valor unitario sin IGV")
    unit_price: Decimal = Field(default=Decimal("0.00"), description="Precio unitario con IGV")
    cost_price: Decimal = Field(default=Decimal("0.00"), description="Costo referencial de compra")
    igv_type: str = Field(default="10", description="10=Gravado - Operación Onerosa")
    
    # Detracción
    has_detraction: bool = False
    detraction_code: Optional[str] = None
    detraction_percent: Optional[Decimal] = None
    
    # Control de Stock
    is_service: bool = False
    stock: Decimal = Decimal("0.00")
    stock_min: Decimal = Decimal("0.00")
    notes: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    internal_code: Optional[str] = None
    barcode: Optional[str] = None
    sunat_code: Optional[str] = None
    description: Optional[str] = None
    category_name: Optional[str] = None
    unit_code: Optional[str] = None
    currency: Optional[str] = None
    unit_value: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    cost_price: Optional[Decimal] = None
    igv_type: Optional[str] = None
    has_detraction: Optional[bool] = None
    detraction_code: Optional[str] = None
    detraction_percent: Optional[Decimal] = None
    is_service: Optional[bool] = None
    stock: Optional[Decimal] = None
    stock_min: Optional[Decimal] = None
    notes: Optional[str] = None

class ProductOut(ProductBase):
    id: int
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
