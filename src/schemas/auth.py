from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    username: str = Field(..., description="Nombre de usuario")
    password: str = Field(..., description="Contraseña")

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4)
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str = Field(default="ADMIN", description="ADMIN, FACTURADOR, VENDEDOR, CONTADOR")
    default_company_id: Optional[int] = None
    assigned_series: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    default_company_id: Optional[int] = None
    assigned_series: Optional[str] = None
    password: Optional[str] = None

class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str = "ADMIN"
    default_company_id: Optional[int] = None
    assigned_series: Optional[str] = None
    is_active: bool
    deleted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

TokenResponse.model_rebuild()
