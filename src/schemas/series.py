from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class CompanySeriesBase(BaseModel):
    document_type: str # 01, 03, 07, 08, 09, 31
    series: str # F001, B001, etc.
    correlative_current: int = 0
    description: Optional[str] = None
    is_active: bool = True


class CompanySeriesCreate(CompanySeriesBase):
    company_id: int


class CompanySeriesUpdate(BaseModel):
    correlative_current: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CompanySeriesOut(CompanySeriesBase):
    id: int
    company_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NextCorrelativeOut(BaseModel):
    document_type: str
    series: str
    next_correlative: int
    formatted_number: str
