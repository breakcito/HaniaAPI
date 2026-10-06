from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.company import Company
from src.schemas.company import CompanyCreate, CompanyUpdate, CompanyOut
from src.services.factos_client import factos_client

router = APIRouter(prefix="/companies", tags=["Multiempresa"])

@router.get("", response_model=List[CompanyOut])
def list_companies(
    include_inactive: bool = Query(False, description="Incluir empresas eliminadas lógicamente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Company)
    if not include_inactive:
        q = q.filter(Company.is_active == True)
    return q.order_by(Company.is_matrix.desc(), Company.id.asc()).all()

@router.get("/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return company

@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(Company).filter(Company.ruc == payload.ruc).first()
    if existing:
        if not existing.is_active:
            # Reactivar empresa eliminada lógicamente
            existing.is_active = True
            existing.deleted_at = None
            existing.business_name = payload.business_name or existing.business_name
            db.commit()
            db.refresh(existing)
            return existing
        raise HTTPException(status_code=400, detail="El RUC ya está registrado en el sistema")

    # Intentar obtener datos oficiales si falta información
    if not payload.address or not payload.department:
        ruc_info = await factos_client.get_ruc_data(payload.ruc)
        if not ruc_info.get("error") and ruc_info.get("data"):
            data = ruc_info["data"]
            if not payload.business_name:
                payload.business_name = data.get("razon_social", payload.business_name)
            if not payload.address:
                payload.address = data.get("direccion", payload.address)
            if not payload.department:
                payload.department = data.get("departamento", payload.department)
            if not payload.province:
                payload.province = data.get("provincia", payload.province)
            if not payload.district:
                payload.district = data.get("distrito", payload.district)
            if not payload.ubigeo:
                payload.ubigeo = data.get("ubigeo", payload.ubigeo)

    company = Company(
        ruc=payload.ruc,
        business_name=payload.business_name,
        trademark_name=payload.trademark_name or payload.business_name,
        address=payload.address,
        ubigeo=payload.ubigeo,
        department=payload.department,
        province=payload.province,
        district=payload.district,
        establishment_code=payload.establishment_code,
        sol_user=payload.sol_user or "MODDATOS",
        is_matrix=payload.is_matrix,
        is_active=True,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

@router.put("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: int,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(company, field, val)

    db.commit()
    db.refresh(company)
    return company

@router.delete("/{company_id}", status_code=status.HTTP_200_OK)
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminación LÓGICA (Soft Delete) de empresa filial. Nunca se elimina físicamente de la base de datos."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if company.is_matrix:
        raise HTTPException(status_code=400, detail="No se puede eliminar la empresa matriz principal")

    if not company.is_active:
        return {"message": "La empresa ya se encuentra inactiva", "id": company_id, "is_active": False}

    company.is_active = False
    company.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Empresa eliminada lógicamente con éxito", "id": company_id, "is_active": False}
