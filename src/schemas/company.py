from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

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

class CompanyCreate(CompanyBase):
    is_matrix: bool = False

class CompanyUpdate(BaseModel):
    business_name: Optional[str] = None
    trademark_name: Optional[str] = None
    address: Optional[str] = None
    ubigeo: Optional[str] = None
    department: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    sol_user: Optional[str] = None
    is_active: Optional[bool] = None

class CompanyOut(CompanyBase):
    id: int
    facturador_company_id: Optional[str] = None
    is_matrix: bool
    is_active: bool
    deleted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
