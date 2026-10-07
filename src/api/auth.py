from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.security import verify_password, get_password_hash, create_access_token
from src.core.deps import get_current_user
from src.models.user import User
from src.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserUpdate, UserOut

router = APIRouter(prefix="/auth", tags=["Autenticación y Usuarios"])

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta de usuario está desactivada",
        )
    
    access_token = create_access_token(user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/users", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(User).order_by(User.id.asc()).all()

@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(User).filter(User.username == payload.username.strip()).first()
    if existing:
        if not existing.is_active:
            existing.password_hash = get_password_hash(payload.password)
            existing.full_name = payload.full_name.strip() if payload.full_name else existing.full_name
            existing.email = payload.email.strip() if payload.email else existing.email
            existing.phone = payload.phone.strip() if payload.phone else existing.phone
            existing.role = payload.role or existing.role
            existing.default_company_id = payload.default_company_id or existing.default_company_id
            existing.assigned_series = payload.assigned_series or existing.assigned_series
            existing.is_active = True
            existing.deleted_at = None
            db.commit()
            db.refresh(existing)
            return existing
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya se encuentra registrado",
        )
    
    new_user = User(
        username=payload.username.strip(),
        password_hash=get_password_hash(payload.password),
        full_name=payload.full_name.strip() if payload.full_name else payload.username.strip(),
        email=payload.email.strip() if payload.email else None,
        phone=payload.phone.strip() if payload.phone else None,
        role=payload.role or "ADMIN",
        default_company_id=payload.default_company_id,
        assigned_series=payload.assigned_series,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.email is not None:
        user.email = payload.email.strip()
    if payload.phone is not None:
        user.phone = payload.phone.strip()
    if payload.role is not None:
        user.role = payload.role
    if payload.default_company_id is not None:
        user.default_company_id = payload.default_company_id
    if payload.assigned_series is not None:
        user.assigned_series = payload.assigned_series
    if payload.password:
        user.password_hash = get_password_hash(payload.password)

    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminación LÓGICA (Soft Delete) de cuenta de usuario."""
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propia cuenta en sesión activa",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user.username == "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar la cuenta principal de administrador del sistema",
        )

    if not user.is_active:
        return {"message": "El usuario ya se encuentra inactivo", "id": user_id, "is_active": False}

    user.is_active = False
    user.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Usuario desactivado lógicamente con éxito", "id": user_id, "is_active": False}
