from typing import List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.employee import Employee
from src.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeOut

router = APIRouter(prefix="/employees", tags=["Trabajadores y Personal"])

from src.core.security import get_password_hash

def _serialize_employee(emp: Employee, db: Session) -> dict:
    user = db.query(User).filter(User.id == emp.user_id).first() if emp.user_id else None
    perms_list = [p.strip() for p in user.permissions.split(",") if p.strip()] if (user and user.permissions) else None
    return {
        "id": emp.id,
        "document_type": emp.document_type,
        "document_number": emp.document_number,
        "first_name": emp.first_name,
        "last_name": emp.last_name,
        "full_name": emp.full_name,
        "email": emp.email,
        "phone": emp.phone,
        "license_number": emp.license_number,
        "user_id": emp.user_id,
        "has_account": user is not None and user.is_active,
        "username": user.username if user else None,
        "system_role": user.role if user else None,
        "permissions": perms_list,
        "is_active": emp.is_active,
        "deleted_at": emp.deleted_at,
        "created_at": emp.created_at,
    }

@router.get("", response_model=List[EmployeeOut])
def list_employees(
    query: Optional[str] = Query(None, description="Búsqueda por nombre o DNI"),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Employee)
    if not include_inactive:
        q = q.filter(Employee.is_active == True)
    if query:
        pattern = f"%{query}%"
        q = q.filter(
            (Employee.first_name.ilike(pattern))
            | (Employee.last_name.ilike(pattern))
            | (Employee.document_number.ilike(pattern))
        )
    employees = q.order_by(Employee.last_name.asc(), Employee.first_name.asc()).all()
    return [_serialize_employee(emp, db) for emp in employees]

@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    return _serialize_employee(emp, db)

@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    created_user = None
    if payload.create_system_access and payload.username and payload.password:
        existing_user = db.query(User).filter(User.username == payload.username.strip()).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado en el sistema")
        perms_str = ",".join(payload.permissions) if payload.permissions else None
        created_user = User(
            username=payload.username.strip(),
            password_hash=get_password_hash(payload.password),
            full_name=f"{payload.first_name.strip()} {payload.last_name.strip()}",
            role=payload.system_role or "PERSONALIZADO",
            permissions=perms_str,
            is_active=True,
        )
        db.add(created_user)
        db.flush()

    emp = Employee(
        document_type=payload.document_type,
        document_number=payload.document_number.strip(),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        email=payload.email.strip() if payload.email else None,
        phone=payload.phone.strip() if payload.phone else None,
        license_number=payload.license_number.strip() if payload.license_number else None,
        user_id=created_user.id if created_user else None,
        is_active=True,
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return _serialize_employee(emp, db)

@router.put("/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")

    update_data = payload.model_dump(exclude_unset=True)
    
    # Manejo de cuenta de usuario
    username = update_data.pop("username", None)
    password = update_data.pop("password", None)
    system_role = update_data.pop("system_role", None)
    permissions = update_data.pop("permissions", None)
    create_system_access = update_data.pop("create_system_access", None)

    if emp.user_id:
        user = db.query(User).filter(User.id == emp.user_id).first()
        if user:
            if username:
                user.username = username.strip()
            if password:
                user.password_hash = get_password_hash(password)
            if system_role:
                user.role = system_role
            if permissions is not None:
                user.permissions = ",".join(permissions) if permissions else None
            if create_system_access is False:
                user.is_active = False
            elif create_system_access is True:
                user.is_active = True
    elif create_system_access and username and password:
        existing_user = db.query(User).filter(User.username == username.strip()).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado en el sistema")
        perms_str = ",".join(permissions) if permissions else None
        new_user = User(
            username=username.strip(),
            password_hash=get_password_hash(password),
            full_name=f"{emp.first_name} {emp.last_name}",
            role=system_role or "PERSONALIZADO",
            permissions=perms_str,
            is_active=True,
        )
        db.add(new_user)
        db.flush()
        emp.user_id = new_user.id

    for k, v in update_data.items():
        if isinstance(v, str):
            v = v.strip()
        setattr(emp, k, v)

    db.commit()
    db.refresh(emp)
    return _serialize_employee(emp, db)

@router.delete("/{employee_id}", status_code=status.HTTP_200_OK)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")

    if not emp.is_active:
        return {"message": "El trabajador ya se encuentra inactivo", "id": employee_id, "is_active": False}

    emp.is_active = False
    emp.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Trabajador desactivado lógicamente", "id": employee_id, "is_active": False}
