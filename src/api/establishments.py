from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.datetime_peru import now_peru
from src.core.deps import get_current_user
from src.models.user import User
from src.models.establishment import Establishment
from src.schemas.establishment import EstablishmentCreate, EstablishmentOut

router = APIRouter(prefix="/establishments", tags=["Establecimientos y Locales Anexos"])

@router.get("", response_model=List[EstablishmentOut])
def list_establishments(
    entity_type: Optional[str] = Query(None, description="Tipo de entidad: company, client, supplier"),
    entity_id: Optional[int] = Query(None, description="ID de la entidad"),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Establishment)
    if not include_inactive:
        q = q.filter(Establishment.is_active == True)
    if entity_type:
        q = q.filter(Establishment.entity_type == entity_type)
    if entity_id:
        q = q.filter(Establishment.entity_id == entity_id)
    return q.order_by(Establishment.is_primary.desc(), Establishment.code.asc()).all()

@router.get("/{establishment_id}", response_model=EstablishmentOut)
def get_establishment(
    establishment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    est = db.query(Establishment).filter(Establishment.id == establishment_id).first()
    if not est:
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")
    return est

@router.post("", response_model=EstablishmentOut, status_code=status.HTTP_201_CREATED)
def create_establishment(
    payload: EstablishmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.is_primary:
        # Desactivar is_primary previo de la misma entidad
        db.query(Establishment).filter(
            Establishment.entity_type == payload.entity_type,
            Establishment.entity_id == payload.entity_id,
            Establishment.is_primary == True
        ).update({"is_primary": False})

    est = Establishment(
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        code=payload.code.strip() if payload.code else "0000",
        description=payload.description.strip(),
        address=payload.address.strip(),
        ubigeo=payload.ubigeo.strip(),
        department=payload.department.strip() if payload.department else None,
        province=payload.province.strip() if payload.province else None,
        district=payload.district.strip() if payload.district else None,
        is_primary=payload.is_primary,
        is_active=True,
    )
    db.add(est)
    db.commit()
    db.refresh(est)
    return est

@router.delete("/{establishment_id}", status_code=status.HTTP_200_OK)
def delete_establishment(
    establishment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    est = db.query(Establishment).filter(Establishment.id == establishment_id).first()
    if not est:
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")

    est.is_active = False
    est.deleted_at = now_peru()
    db.commit()
    return {"message": "Establecimiento desactivado correctamente", "id": establishment_id}
