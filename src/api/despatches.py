from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from src.core.datetime_peru import now_peru
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.company import Company
from src.models.despatch import Despatch, DespatchItem
from src.models.series import CompanySeries
from src.schemas.despatch import DespatchCreate, DespatchOut, DespatchVoidRequest, DespatchItemSchema
from src.services.factos_client import factos_client
from src.services.facturador.company_link import resolve_factos_company_id, FactosLinkError
from src.services.facturador.responses import map_status, file_urls, raise_factos_error

router = APIRouter(prefix="/despatches", tags=["Guías de Remisión Electrónica"])

@router.get("", response_model=List[DespatchOut])
def list_despatches(
    company_id: Optional[int] = Query(None),
    is_test_mode: Optional[bool] = Query(None),
    series: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
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
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            (Despatch.series.ilike(pattern)) |
            (Despatch.transfer_reason.ilike(pattern))
        )

    return q.order_by(Despatch.created_at.desc()).offset(offset).limit(limit).all()

@router.get("/{despatch_id}", response_model=DespatchOut)
def get_despatch(
    despatch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    gre = db.query(Despatch).filter(Despatch.id == despatch_id).first()
    if not gre:
        raise HTTPException(status_code=404, detail="Guía de remisión no encontrada")
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

    # 1. Si se indicó corregir una guía anterior, darla de baja automáticamente
    if payload.previous_despatch_id_to_void:
        prev_gre = db.query(Despatch).filter(Despatch.id == payload.previous_despatch_id_to_void).first()
        if prev_gre and prev_gre.status != "voided":
            void_reason = "Baja por reemisión y corrección de datos de guía de remisión"
            if prev_gre.facturador_despatch_id:
                try:
                    await factos_client.void_despatch(prev_gre.facturador_despatch_id, void_reason)
                except Exception:
                    pass
            prev_gre.status = "voided"
            prev_gre.void_reason = void_reason
            prev_gre.voided_at = now_peru()

    series = payload.series.strip().upper()

    # 2. Determinar correlativo
    if payload.correlative is not None and payload.correlative > 0:
        correlative = payload.correlative
    else:
        series_record = db.query(CompanySeries).filter(
            CompanySeries.company_id == company.id,
            CompanySeries.document_type == payload.type_code,
            CompanySeries.series == series,
        ).first()
        max_corr = db.query(func.max(Despatch.correlative)).filter(
            Despatch.company_id == company.id,
            Despatch.type_code == payload.type_code,
            Despatch.series == series,
        ).scalar() or 0
        base_corr = series_record.correlative_current if series_record else 0
        correlative = max(base_corr, max_corr) + 1

    # 3. Observaciones y peso referencial
    observations = payload.observations
    if payload.is_referential_weight:
        if not observations or "REFERENCIAL" not in observations.upper():
            observations = (observations + " - EL PESO ES REFERENCIAL") if observations else "EL PESO ES REFERENCIAL"

    # 4. Certificado vehicular / TUCE
    vehicle_dict = payload.vehicle or {}
    vehicle_cert = payload.vehicle_certificate or vehicle_dict.get("certificate")

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
        vehicle=vehicle_dict,
        vehicle_certificate=vehicle_cert,
        observations=observations,
        is_referential_weight=payload.is_referential_weight,
        related_documents=payload.related_documents,
        status="pending",
        created_at=now_pe,
    )
    db.add(new_gre)
    db.flush()

    despatch_items = list(payload.items)
    if not despatch_items:
        despatch_items = [
            DespatchItemSchema(
                internal_code=None,
                description="Mineral en bruto sin procesar",
                unit_code=payload.weight_unit or "TNE",
                quantity=payload.total_weight or Decimal("1.0"),
            )
        ]

    for it in despatch_items:
        desc = it.description.strip() if it.description else "Mineral en bruto sin procesar"
        gre_item = DespatchItem(
            despatch_id=new_gre.id,
            internal_code=it.internal_code,
            description=desc,
            unit_code=it.unit_code or "TNE",
            quantity=it.quantity,
        )
        db.add(gre_item)

    # Actualizar correlativo de la serie
    series_record = db.query(CompanySeries).filter(
        CompanySeries.company_id == company.id,
        CompanySeries.document_type == payload.type_code,
        CompanySeries.series == series,
    ).first()
    if series_record:
        series_record.correlative_current = max(series_record.correlative_current, correlative)

    db.commit()

    # 5. Enviar a Factos API (con enlace inmediato al PDF)
    try:
        factos_company_id = await resolve_factos_company_id(db, company, payload.is_test_mode)
    except FactosLinkError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    factos_rel_docs = None
    if payload.related_documents:
        factos_rel_docs = []
        for rd in payload.related_documents:
            rd_item = dict(rd)
            if not rd_item.get("number"):
                s = rd_item.get("series", "")
                c = rd_item.get("correlative", "")
                if s and c:
                    rd_item["number"] = f"{s}-{c}"
            if not rd_item.get("type_code") and rd_item.get("document_type"):
                rd_item["type_code"] = rd_item["document_type"]
            factos_rel_docs.append(rd_item)

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
        "delivery_date": str(payload.delivery_date) if payload.delivery_date else None,
        "transport_mode": payload.transport_mode,
        "transfer_reason": payload.transfer_reason,
        "transfer_description": payload.transfer_description,
        "total_weight": float(payload.total_weight),
        "weight_unit": payload.weight_unit,
        "packages_count": payload.packages_count,
        "is_referential_weight": payload.is_referential_weight,
        "vehicle_certificate": vehicle_cert,
        "observations": observations,
        "related_documents": factos_rel_docs,
        "recipient": payload.recipient,
        "origin": payload.origin,
        "destination": payload.destination,
        "carrier": payload.carrier,
        "driver": payload.driver,
        "vehicle": vehicle_dict,
        "items": [
            {
                "internal_code": it.internal_code,
                "description": it.description or "Mineral en bruto sin procesar",
                "unit_code": it.unit_code or "TNE",
                "quantity": float(it.quantity),
            }
            for it in despatch_items
        ],
    }

    result = await factos_client.send_despatch(factos_payload)
    if result.get("error"):
        new_gre.status = "rejected"
        new_gre.sunat_description = result.get("message", "Error al procesar GRE en Factos API")
        db.commit()
        raise_factos_error(result)

    desp_data = result.get("data", {})
    factos_id = desp_data.get("id")
    if factos_id:
        new_gre.facturador_despatch_id = str(factos_id)
        links = desp_data.get("links", {})
        new_gre.pdf_url = links.get("pdf") or file_urls("despatches", str(factos_id))["pdf_url"]
        new_gre.xml_url = links.get("xml") or file_urls("despatches", str(factos_id))["xml_url"]
        new_gre.cdr_url = links.get("cdr") or file_urls("despatches", str(factos_id))["cdr_url"]

    if new_gre.status == "pending":
        factos_status = desp_data.get("status", "pending")
        new_gre.status = map_status(factos_status)
        if new_gre.status == "accepted":
            new_gre.sunat_code = "0"
            new_gre.sunat_description = desp_data.get("sunat_description", "Guía aceptada por SUNAT")
        else:
            new_gre.sunat_code = "0"
            new_gre.sunat_description = "Guía emitida y encolada para procesamiento en Factos."

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
        raise HTTPException(status_code=404, detail="Guía de remisión no encontrada")

    if gre.status == "voided":
        raise HTTPException(status_code=400, detail="La guía ya se encuentra anulada")

    if gre.facturador_despatch_id:
        result = await factos_client.void_despatch(gre.facturador_despatch_id, payload.reason)
        if result.get("error"):
            raise_factos_error(result)

    gre.status = "voided"
    gre.void_reason = payload.reason
    gre.voided_at = now_peru()
    db.commit()
    db.refresh(gre)
    return gre
