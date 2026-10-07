from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class VehicleBase(BaseModel):
    company_id: int
    plate_number: str = Field(..., max_length=10, description="Placa principal")
    secondary_plate: Optional[str] = Field(None, max_length=10, description="Placa secundaria / carreta")
    brand: Optional[str] = None
    model: Optional[str] = None
    mtc_authorization: Optional[str] = Field(None, description="Certificado de habilitación MTC")

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    plate_number: Optional[str] = None
    secondary_plate: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    mtc_authorization: Optional[str] = None

class VehicleOut(VehicleBase):
    id: int
    is_active: bool
    deleted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
