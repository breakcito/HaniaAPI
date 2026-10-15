from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class EstablishmentCreate(BaseModel):
    entity_type: str = "company" # company, client, supplier
    entity_id: int
    code: str = "0000"
    description: str = "Principal"
    address: str
    ubigeo: str = Field(..., min_length=6, max_length=6)
    department: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    is_primary: bool = False

class EstablishmentOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    code: str
    description: str
    address: str
    ubigeo: str
    department: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    is_primary: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
