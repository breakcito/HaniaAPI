from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from src.core.datetime_peru import now_peru
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.core.config import settings
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.company import Company
from src.models.despatch import Despatch, DespatchItem
from src.schemas.despatch import DespatchCreate, DespatchOut, DespatchVoidRequest
from src.services.factos_client import factos_client
from src.services.facturador.company_link import resolve_factos_company_id, FactosLinkError
from src.services.facturador.responses import map_status, file_urls, raise_factos_error

router = APIRouter(prefix="/despatches", tags=["Guías de Remisión Electrónica (GRE)"])

@router.get("", response_model=List[DespatchOut])
def list_despatches(
    company_id: Optional[int] = Query(None),
    is_test_mode: Optional[bool] = Query(None),
    series: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="Fecha inicio YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Fecha fin YYYY-MM-DD"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    include_inactive: bool = Query(False, description="Incluir guías eliminadas lógicamente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Despatch)
    if not include_inactive:
        q = q.filter(Despatch.is_active == True)
    if company_id is not None:
        q = q.filter(Despatch.company_id == company_id)
    if is_test_mode is not None:
        q = q.filter(Despatch.is_test_mode == is_test_mode)
    if series:
        q = q.filter(Despatch.series == series.upper())
    if status:
        q = q.filter(Despatch.status == status)
    if start_date:
        try:
            d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            q = q.filter(Despatch.issue_date >= d_start)
        except ValueError:
            pass
    if end_date:
        try:
            d_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            q = q.filter(Despatch.issue_date <= d_end)
        except ValueError:
            pass
    if search:
        pattern = f"%{search}%"
        q = q.filter(Despatch.series.ilike(pattern))

    return q.order_by(Despatch.created_at.desc()).offset(offset).limit(limit).all()

@router.get("/{despatch_id}", response_model=DespatchOut)
def get_despatch(
    despatch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    gre = db.query(Despatch).filter(Despatch.id == despatch_id).first()
    if not gre:
        raise HTTPException(status_code=404, detail="Guía de Remisión no encontrada")
    return gre

@router.post("", response_model=DespatchOut, status_code=status.HTTP_201_CREATED)
async def create_despatch(
    payload: DespatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == payload.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa emisora no encontrada")

    series = payload.series.strip().upper()
    if payload.correlative is not None and payload.correlative > 0:
        correlative = payload.correlative
    else:
        max_corr = db.query(func.max(Despatch.correlative)).filter(
            Despatch.company_id == company.id,
            Despatch.series == series,
        ).scalar()
        correlative = (max_corr or 0) + 1

    now_pe = now_peru()
    new_gre = Despatch(
        company_id=company.id,
        is_test_mode=payload.is_test_mode,
        type_code=payload.type_code,
        series=series,
        correlative=correlative,
        issue_date=payload.issue_date,
        issue_time=payload.issue_time or "12:00:00",
        transfer_date=payload.transfer_date,
        delivery_date=payload.delivery_date,
        transport_mode=payload.transport_mode,
        transfer_reason=payload.transfer_reason,
        transfer_description=payload.transfer_description,
        total_weight=payload.total_weight,
        weight_unit=payload.weight_unit,
        packages_count=payload.packages_count,
        recipient=payload.recipient,
        origin=payload.origin,
        destination=payload.destination,
        carrier=payload.carrier,
        driver=payload.driver,
        vehicle=payload.vehicle,
        status="pending",
        created_at=now_pe,
    )
    db.add(new_gre)
    db.flush()

    for it in payload.items:
        gre_item = DespatchItem(
            despatch_id=new_gre.id,
            internal_code=it.internal_code,
            description=it.description,
            unit_code=it.unit_code,
            quantity=it.quantity,
        )
        db.add(gre_item)

    # 5. Enviar a Factos API (tanto en prueba como en producción real)
    try:
        factos_company_id = await resolve_factos_company_id(db, company, payload.is_test_mode)
    except FactosLinkError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    factos_payload = {
        "company_id": factos_company_id,
        "external_id": str(new_gre.id),
        "is_test": payload.is_test_mode,
        "type_code": payload.type_code,
        "series": series,
        "correlative": correlative,
        "issue_date": str(payload.issue_date),
        "issue_time": payload.issue_time or "12:00:00",
        "transfer_date": str(payload.transfer_date),
        "transport_mode": payload.transport_mode,
        "transfer_reason": payload.transfer_reason,
        "transfer_description": payload.transfer_description,
        "total_weight": float(payload.total_weight),
        "weight_unit": payload.weight_unit,
        "packages_count": payload.packages_count,
        "recipient": payload.recipient,
        "origin": payload.origin,
        "destination": payload.destination,
        "carrier": payload.carrier,
        "driver": payload.driver,
        "vehicle": payload.vehicle,
        "items": [
            {
                "internal_code": it.internal_code,
                "description": it.description,
                "unit_code": it.unit_code,
                "quantity": float(it.quantity),
            }
            for it in payload.items
        ],
    }

    result = await factos_client.send_despatch(factos_payload)
    if result.get("error"):
        new_gre.status = "rejected"
        new_gre.sunat_description = result.get("message", "Error al procesar GRE en Factos API")
        db.commit()
        raise_factos_error(result)

    data = result.get("data", {})
    despatch_id = data.get("id")
    if despatch_id:
        new_gre.facturador_despatch_id = str(despatch_id)
        urls = file_urls("despatches", str(despatch_id))
        new_gre.pdf_url = urls["pdf_url"]
        new_gre.xml_url = urls["xml_url"]
        new_gre.cdr_url = urls["cdr_url"]

    new_gre.status = map_status(data.get("status", "pending"))
    new_gre.sunat_code = "0"
    new_gre.sunat_description = "Guía de Remisión Electrónica emitida y encolada para procesamiento en Factos."

    db.commit()
    db.refresh(new_gre)
    return new_gre

@router.post("/{despatch_id}/void", response_model=DespatchOut)
async def void_despatch(
    despatch_id: int,
    payload: DespatchVoidRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    gre = db.query(Despatch).filter(Despatch.id == despatch_id).first()
    if not gre:
        raise HTTPException(status_code=404, detail="Guía de Remisión no encontrada")

    if gre.status == "voided":
        raise HTTPException(status_code=400, detail="La Guía de Remisión ya fue anulada")

    now_pe = now_peru()
    gre.void_reason = payload.reason
    gre.voided_at = now_pe
    gre.status = "voided"

    if not gre.is_test_mode and gre.facturador_despatch_id:
        await factos_client.void_despatch(gre.facturador_despatch_id, payload.reason)

    gre.sunat_description = f"Guía de Remisión anulada. Motivo: {payload.reason}"

    db.commit()
    db.refresh(gre)
    return gre

@router.delete("/{despatch_id}", status_code=status.HTTP_200_OK)
def delete_despatch(
    despatch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminación LÓGICA (Soft Delete) de Guía de Remisión. Nunca se elimina físicamente de la base de datos."""
    gre = db.query(Despatch).filter(Despatch.id == despatch_id).first()
    if not gre:
        raise HTTPException(status_code=404, detail="Guía de Remisión no encontrada")

    if not gre.is_active:
        return {"message": "La Guía ya fue eliminada lógicamente", "id": despatch_id, "is_active": False}

    gre.is_active = False
    gre.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Guía de Remisión archivada/eliminada lógicamente con éxito", "id": despatch_id, "is_active": False}
