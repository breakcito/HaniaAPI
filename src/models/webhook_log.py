from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, JSON, DateTime
from src.core.database import Base

class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True) # document.accepted, document.rejected, document.voided, etc.
    document_id = Column(Integer, nullable=True, index=True)
    despatch_id = Column(Integer, nullable=True, index=True)
    signature = Column(String(100), nullable=True)
    payload = Column(JSON, nullable=False)
    status_processed = Column(String(20), default="processed", nullable=False) # processed, ignored, error
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
