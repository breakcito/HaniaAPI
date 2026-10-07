from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.employee import Employee
from src.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeOut

router = APIRouter(prefix="/employees", tags=["Trabajadores y Personal"])

@router.get("", response_model=List[EmployeeOut])
def list_employees(
    company_id: Optional[int] = Query(None),
    job_title: Optional[str] = Query(None, description="Filtrar por cargo (Vendedor, Chofer, etc.)"),
    query: Optional[str] = Query(None, description="Búsqueda por nombre o DNI"),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Employee)
    if not include_inactive:
        q = q.filter(Employee.is_active == True)
    if company_id:
        q = q.filter(Employee.company_id == company_id)
    if job_title:
        q = q.filter(Employee.job_title == job_title)
    if query:
        pattern = f"%{query}%"
        q = q.filter(
            (Employee.first_name.ilike(pattern))
            | (Employee.last_name.ilike(pattern))
            | (Employee.document_number.ilike(pattern))
        )
    return q.order_by(Employee.last_name.asc(), Employee.first_name.asc()).all()

@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Trabajador no encontrado")
    return emp

@router.post("", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp = Employee(
        company_id=payload.company_id,
        document_type=payload.document_type,
        document_number=payload.document_number.strip(),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        job_title=payload.job_title.strip() if payload.job_title else "Vendedor",
        email=payload.email.strip() if payload.email else None,
        phone=payload.phone.strip() if payload.phone else None,
        license_number=payload.license_number.strip() if payload.license_number else None,
        commission_rate=payload.commission_rate,
        is_active=True,
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp

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
    for k, v in update_data.items():
        if isinstance(v, str):
            v = v.strip()
        setattr(emp, k, v)

    db.commit()
    db.refresh(emp)
    return emp

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
