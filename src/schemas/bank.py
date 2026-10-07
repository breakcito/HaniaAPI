from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class BankOut(BaseModel):
    id: int
    code: str
    name: str
    short_name: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class BankAccountBase(BaseModel):
    bank_id: int
    account_type: str = "corriente" # corriente, ahorros, detraccion
    currency: str = "PEN" # PEN, USD
    account_number: str
    cci_number: Optional[str] = None
    alias: Optional[str] = None
    show_in_pdf: bool = True
    is_default: bool = False


class BankAccountCreate(BankAccountBase):
    company_id: int


class BankAccountUpdate(BaseModel):
    bank_id: Optional[int] = None
    account_type: Optional[str] = None
    currency: Optional[str] = None
    account_number: Optional[str] = None
    cci_number: Optional[str] = None
    alias: Optional[str] = None
    show_in_pdf: Optional[bool] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class BankAccountOut(BankAccountBase):
    id: int
    company_id: int
    is_active: bool
    created_at: datetime
    bank: Optional[BankOut] = None

    model_config = ConfigDict(from_attributes=True)
