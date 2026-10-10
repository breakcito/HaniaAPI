from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.core.database import Base

class Bank(Base):
    __tablename__ = "banks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(20), unique=True, index=True, nullable=False) # BCP, BBVA, INTERBANK, SCOTIABANK, BN, BANBIF, PICHINCHA
    name = Column(String(100), nullable=False)
    is_national = Column(Boolean, default=False, nullable=False) # True para Banco de la Nación
    is_active = Column(Boolean, default=True, nullable=False)

    accounts = relationship("BankAccount", back_populates="bank")


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    bank_id = Column(Integer, ForeignKey("banks.id"), nullable=False, index=True)
    
    # Tipo de cuenta: corriente, ahorros, detraccion
    account_type = Column(String(20), default="corriente", nullable=False)
    currency = Column(String(3), default="PEN", nullable=False) # PEN, USD
    
    account_number = Column(String(50), nullable=False)
    cci_number = Column(String(50), nullable=True)
    alias = Column(String(100), nullable=True)
    
    is_detraction = Column(Boolean, default=False, nullable=False) # Si es cuenta de detracción BN
    show_in_pdf = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="bank_accounts")
    bank = relationship("Bank", back_populates="accounts")
