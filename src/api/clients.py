from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.client import Client
from src.schemas.client import ClientCreate, ClientOut

router = APIRouter(prefix="/clients", tags=["Clientes"])

@router.get("", response_model=List[ClientOut])
def list_clients(
    company_id: Optional[int] = Query(None),
    query: Optional[str] = Query(None),
    include_inactive: bool = Query(False, description="Incluir clientes eliminados lógicamente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Client)
    if not include_inactive:
        q = q.filter(Client.is_active == True)
    if company_id:
        q = q.filter(Client.company_id == company_id)
    if query:
        pattern = f"%{query}%"
        q = q.filter((Client.name.ilike(pattern)) | (Client.doc_number.ilike(pattern)))
    return q.order_by(Client.name.asc()).limit(100).all()

@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(Client).filter(
        Client.company_id == payload.company_id,
        Client.doc_number == payload.doc_number,
    ).first()
    if existing:
        # Actualizar datos existentes y reactivar si estaba eliminado lógicamente
        existing.name = payload.name
        existing.address = payload.address or existing.address
        existing.email = payload.email or existing.email
        existing.phone = payload.phone or existing.phone
        existing.is_active = True
        existing.deleted_at = None
        db.commit()
        db.refresh(existing)
        return existing

    new_client = Client(
        company_id=payload.company_id,
        doc_type=payload.doc_type,
        doc_number=payload.doc_number,
        name=payload.name,
        address=payload.address,
        email=payload.email,
        phone=payload.phone,
        is_active=True,
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    return new_client

@router.delete("/{client_id}", status_code=status.HTTP_200_OK)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminación LÓGICA (Soft Delete) de cliente. Nunca se elimina físicamente de la base de datos."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if not client.is_active:
        return {"message": "El cliente ya se encuentra inactivo", "id": client_id, "is_active": False}

    client.is_active = False
    client.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Cliente eliminado lógicamente con éxito", "id": client_id, "is_active": False}
