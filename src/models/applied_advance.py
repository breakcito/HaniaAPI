from src.core.datetime_peru import now_peru
from sqlalchemy import Column, Integer, String, Boolean, Numeric, Date, DateTime
from src.core.database import Base

class AppliedAdvance(Base):
    __tablename__ = "applied_advances"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # IDs referenciales sin relaciones de foreign key físicas según directriz de desarrollo
    document_id = Column(Integer, nullable=False, index=True)
    advance_document_id = Column(Integer, nullable=True, index=True)
    advance_type_code = Column(String(2), default="01", nullable=False)
    advance_series = Column(String(10), nullable=False)
    advance_correlative = Column(String(20), nullable=False)
    advance_issue_date = Column(Date, nullable=True)
    amount = Column(Numeric(14, 2), default=0.00, nullable=False)
    description = Column(String(255), nullable=True)
    is_reversed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=now_peru, nullable=False)
