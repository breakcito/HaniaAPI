"""Configuración global y fixtures para pytest."""

import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.core.database import SessionLocal, get_db
from src.core.security import create_access_token, get_password_hash
from src.models.user import User
from src.models.company import Company

@pytest.fixture(scope="session")
def db_session() -> Generator[Session, None, None]:
    """Provee una sesión de base de datos para pruebas."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """Cliente HTTP de prueba para invocar la API."""
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="session")
def admin_user(db_session: Session) -> User:
    """Obtiene o crea un usuario administrador para pruebas."""
    user = db_session.query(User).filter(User.username == "admin").first()
    if not user:
        user = User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            full_name="Administrador Principal",
            role="ADMIN",
            is_active=True,
        )
        db_session.add(user)
    else:
        user.password_hash = get_password_hash("admin123")
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(scope="session")
def auth_headers(admin_user: User) -> dict:
    """Cabeceras de autenticación JWT para el usuario administrador."""
    token = create_access_token(admin_user.id)
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

@pytest.fixture(scope="session")
def test_company(db_session: Session) -> Company:
    """Obtiene la empresa matriz o activa principal para pruebas."""
    company = db_session.query(Company).filter(Company.is_active == True).first()
    assert company is not None, "Debe existir al menos una empresa activa en la BD para ejecutar las pruebas"
    return company
