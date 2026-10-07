from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field

class EmployeeBase(BaseModel):
    company_id: int
    document_type: str = Field(default="1", description="1=DNI, 4=CE")
    document_number: str = Field(..., max_length=15)
    first_name: str
    last_name: str
    job_title: str = Field(default="Vendedor", description="Vendedor, Chofer/Conductor, Cajero, Administrador")
    email: Optional[str] = None
    phone: Optional[str] = None
    license_number: Optional[str] = Field(None, description="Licencia de conducir MTC para choferes")
    commission_rate: Decimal = Field(default=Decimal("0.00"), description="Porcentaje de comisión")

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    license_number: Optional[str] = None
    commission_rate: Optional[Decimal] = None

class EmployeeOut(EmployeeBase):
    id: int
    full_name: str
    is_active: bool
    deleted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
