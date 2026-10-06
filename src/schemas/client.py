from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ClientBase(BaseModel):
    company_id: int
    doc_type: str = Field(default="6", description="6=RUC, 1=DNI, 4=CE, 7=Pasaporte, 0=Sin Doc")
    doc_number: str = Field(..., max_length=15)
    name: str
    address: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientOut(ClientBase):
    id: int
    is_active: bool = True
    deleted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
