from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import jwt
import bcrypt
from src.core.config import settings

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_access_token(subject: str | Any, expires_delta: Optional[timedelta] = None) -> str:
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
    }
    if expires_delta is not None:
        to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False},
        )
        return payload.get("sub")
    except Exception:
        return None
