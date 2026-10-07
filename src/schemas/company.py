from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class CompanyBase(BaseModel):
    ruc: str = Field(..., min_length=11, max_length=11)
    business_name: str
    trademark_name: Optional[str] = None
    address: Optional[str] = None
    ubigeo: Optional[str] = None
    department: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    establishment_code: str = "0000"
    sol_user: Optional[str] = None
    bn_account: Optional[str] = None
    detraction_percent_default: Optional[Decimal] = Decimal("10.00")
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    is_production: bool = True

class CompanyCreate(CompanyBase):
    is_matrix: bool = False
    facturador_company_id: Optional[str] = None

class CompanyUpdate(BaseModel):
    business_name: Optional[str] = None
    trademark_name: Optional[str] = None
    address: Optional[str] = None
    ubigeo: Optional[str] = None
    department: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    sol_user: Optional[str] = None
    bn_account: Optional[str] = None
    detraction_percent_default: Optional[Decimal] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    facturador_company_id: Optional[str] = None
    is_production: Optional[bool] = None
    is_active: Optional[bool] = None

class CompanyOut(CompanyBase):
    id: int
    facturador_company_id: Optional[str] = None
    is_matrix: bool
    is_production: bool
    is_active: bool
    deleted_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
