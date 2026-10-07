from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.vehicle import Vehicle
from src.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleOut

router = APIRouter(prefix="/vehicles", tags=["Vehículos y Transporte GRE"])

@router.get("", response_model=List[VehicleOut])
def list_vehicles(
    company_id: Optional[int] = Query(None),
    query: Optional[str] = Query(None, description="Búsqueda por placa o marca"),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Vehicle)
    if not include_inactive:
        q = q.filter(Vehicle.is_active == True)
    if company_id:
        q = q.filter(Vehicle.company_id == company_id)
    if query:
        pattern = f"%{query}%"
        q = q.filter((Vehicle.plate_number.ilike(pattern)) | (Vehicle.brand.ilike(pattern)))
    return q.order_by(Vehicle.plate_number.asc()).all()

@router.get("/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    veh = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not veh:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return veh

@router.post("", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    payload: VehicleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    veh = Vehicle(
        company_id=payload.company_id,
        plate_number=payload.plate_number.strip().upper(),
        secondary_plate=payload.secondary_plate.strip().upper() if payload.secondary_plate else None,
        brand=payload.brand.strip() if payload.brand else None,
        model=payload.model.strip() if payload.model else None,
        mtc_authorization=payload.mtc_authorization.strip() if payload.mtc_authorization else None,
        is_active=True,
    )
    db.add(veh)
    db.commit()
    db.refresh(veh)
    return veh

@router.put("/{vehicle_id}", response_model=VehicleOut)
def update_vehicle(
    vehicle_id: int,
    payload: VehicleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    veh = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not veh:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        if isinstance(v, str):
            v = v.strip().upper() if "plate" in k else v.strip()
        setattr(veh, k, v)

    db.commit()
    db.refresh(veh)
    return veh

@router.delete("/{vehicle_id}", status_code=status.HTTP_200_OK)
def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    veh = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not veh:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")

    if not veh.is_active:
        return {"message": "El vehículo ya se encuentra inactivo", "id": vehicle_id, "is_active": False}

    veh.is_active = False
    veh.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Vehículo desactivado lógicamente", "id": vehicle_id, "is_active": False}
