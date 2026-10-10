from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

class EmployeeBase(BaseModel):
    document_type: str = Field(default="1", description="1=DNI, 4=CE")
    document_number: str = Field(..., max_length=15)
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    license_number: Optional[str] = Field(None, description="Licencia de conducir MTC para transporte")

class EmployeeCreate(EmployeeBase):
    create_system_access: Optional[bool] = False
    username: Optional[str] = None
    password: Optional[str] = None
    system_role: Optional[str] = "PERSONALIZADO"
    permissions: Optional[List[str]] = Field(default=None, description="Lista de módulos accesibles")

class EmployeeUpdate(BaseModel):
    document_type: Optional[str] = None
    document_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    license_number: Optional[str] = None
    
    # Credenciales y permisos de acceso al sistema
    create_system_access: Optional[bool] = None
    username: Optional[str] = None
    password: Optional[str] = None
    system_role: Optional[str] = None
    permissions: Optional[List[str]] = None

class EmployeeOut(EmployeeBase):
    id: int
    full_name: str
    user_id: Optional[int] = None
    has_account: bool = False
    username: Optional[str] = None
    system_role: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: bool
    deleted_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
