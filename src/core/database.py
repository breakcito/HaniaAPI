from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator
from src.core.config import settings

import json
from decimal import Decimal
from datetime import date, datetime

def _json_serializer(obj):
    return json.dumps(
        obj,
        default=lambda o: float(o) if isinstance(o, Decimal) else o.isoformat() if isinstance(o, (date, datetime)) else str(o)
    )

engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    json_serializer=_json_serializer,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
