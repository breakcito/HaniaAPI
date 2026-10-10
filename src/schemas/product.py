from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field

class ProductBase(BaseModel):
    sunat_code: Optional[str] = None
    description: str
    unit_code: str = Field(default="NIU", description="NIU=Unidad, ZZ=Servicio, TNE=Toneladas, KGM=Kilos")
    currency: str = "PEN"
    unit_value: Decimal = Field(default=Decimal("0.00"), description="Valor unitario sin IGV")
    unit_price: Decimal = Field(default=Decimal("0.00"), description="Precio unitario con IGV")
    igv_type: str = Field(default="10", description="10=Gravado - Operación Onerosa")
    
    # Detracción
    has_detraction: bool = False
    detraction_code: Optional[str] = None
    detraction_percent: Optional[Decimal] = None
    
    # Tipo de bien o servicio
    is_service: bool = False

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    sunat_code: Optional[str] = None
    description: Optional[str] = None
    unit_code: Optional[str] = None
    currency: Optional[str] = None
    unit_value: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    igv_type: Optional[str] = None
    has_detraction: Optional[bool] = None
    detraction_code: Optional[str] = None
    detraction_percent: Optional[Decimal] = None
    is_service: Optional[bool] = None

class ProductOut(ProductBase):
    id: int
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
