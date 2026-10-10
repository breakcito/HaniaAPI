from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.client import Client
from src.schemas.client import ClientCreate, ClientUpdate, ClientOut

router = APIRouter(prefix="/clients", tags=["Clientes"])

@router.get("", response_model=List[ClientOut])
def list_clients(
    query: Optional[str] = Query(None, description="Búsqueda por nombre o número de documento"),
    include_inactive: bool = Query(False, description="Incluir clientes inactivos"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Client)
    if not include_inactive:
        q = q.filter(Client.is_active == True)
    if query:
        pattern = f"%{query}%"
        q = q.filter((Client.name.ilike(pattern)) | (Client.doc_number.ilike(pattern)))
    return q.order_by(Client.name.asc()).limit(100).all()

@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client

@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(Client).filter(
        Client.doc_number == payload.doc_number.strip(),
    ).first()
    if existing:
        existing.name = payload.name.strip()
        existing.address = payload.address.strip() if payload.address else existing.address
        existing.ubigeo = payload.ubigeo or existing.ubigeo
        existing.department = payload.department or existing.department
        existing.province = payload.province or existing.province
        existing.district = payload.district or existing.district
        existing.email = payload.email or existing.email
        existing.phone = payload.phone or existing.phone
        existing.contact_name = payload.contact_name or existing.contact_name
        existing.condition_sunat = payload.condition_sunat or existing.condition_sunat
        existing.state_sunat = payload.state_sunat or existing.state_sunat
        existing.credit_days_default = payload.credit_days_default or existing.credit_days_default
        existing.is_active = True
        existing.deleted_at = None
        db.commit()
        db.refresh(existing)
        return existing

    new_client = Client(
        doc_type=payload.doc_type,
        doc_number=payload.doc_number.strip(),
        name=payload.name.strip(),
        address=payload.address.strip() if payload.address else None,
        ubigeo=payload.ubigeo,
        department=payload.department,
        province=payload.province,
        district=payload.district,
        email=payload.email,
        phone=payload.phone,
        contact_name=payload.contact_name,
        condition_sunat=payload.condition_sunat or "HABIDO",
        state_sunat=payload.state_sunat or "ACTIVO",
        credit_days_default=payload.credit_days_default or 0,
        is_active=True,
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    return new_client

@router.put("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        if isinstance(v, str):
            v = v.strip()
        setattr(client, k, v)

    db.commit()
    db.refresh(client)
    return client

@router.delete("/{client_id}", status_code=status.HTTP_200_OK)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminación LÓGICA (Soft Delete) de cliente."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if not client.is_active:
        return {"message": "El cliente ya se encuentra inactivo", "id": client_id, "is_active": False}

    client.is_active = False
    client.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Cliente eliminado lógicamente con éxito", "id": client_id, "is_active": False}
