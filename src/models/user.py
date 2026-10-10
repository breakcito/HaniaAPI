from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from src.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    
    # Roles y Permisos (presets o lista personalizada)
    role = Column(String(50), default="ADMIN", nullable=False)
    permissions = Column(String(1000), nullable=True) # Lista de módulos permitidos (dashboard,invoices,etc.)
    
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)
