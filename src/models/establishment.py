from src.core.datetime_peru import now_peru
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from src.core.database import Base

class Establishment(Base):
    __tablename__ = "establishments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # Sin FK física
    entity_type = Column(String(20), nullable=False, index=True) # company, client, supplier
    entity_id = Column(Integer, nullable=False, index=True)
    
    code = Column(String(4), default="0000", nullable=False) # 0000 es la principal según SUNAT
    description = Column(String(100), default="Principal", nullable=False)
    address = Column(String(255), nullable=False)
    ubigeo = Column(String(6), nullable=False)
    department = Column(String(50), nullable=True)
    province = Column(String(50), nullable=True)
    district = Column(String(50), nullable=True)
    
    is_primary = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=now_peru, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
