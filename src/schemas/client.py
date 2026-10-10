from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ClientBase(BaseModel):
    doc_type: str = Field(default="6", description="6=RUC, 1=DNI, 4=CE, 7=Pasaporte, 0=Sin Doc")
    doc_number: str = Field(..., max_length=15)
    name: str
    address: Optional[str] = None
    ubigeo: Optional[str] = None
    department: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_name: Optional[str] = None
    condition_sunat: Optional[str] = "HABIDO"
    state_sunat: Optional[str] = "ACTIVO"
    credit_days_default: int = 0

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    ubigeo: Optional[str] = None
    department: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_name: Optional[str] = None
    condition_sunat: Optional[str] = None
    state_sunat: Optional[str] = None
    credit_days_default: Optional[int] = None

class ClientOut(ClientBase):
    id: int
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
