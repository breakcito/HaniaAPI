from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field

class ProductBase(BaseModel):
    company_id: int
    internal_code: Optional[str] = None
    description: str
    unit_code: str = Field(default="TNE", description="TNE=Toneladas, NIU=Unidad, KGM=Kilos")
    unit_value: Decimal = Field(default=Decimal("0.00"), description="Valor unitario sin IGV")
    unit_price: Decimal = Field(default=Decimal("0.00"), description="Precio unitario con IGV")
    igv_type: str = Field(default="10", description="10=Gravado - Operación Onerosa")

class ProductCreate(ProductBase):
    pass

class ProductOut(ProductBase):
    id: int
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
