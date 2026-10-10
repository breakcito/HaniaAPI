from typing import List, Optional, Dict, Any
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
from src.models.client import Client
from src.models.document import Document, DocumentItem
from src.models.series import CompanySeries
from src.schemas.document import DocumentCreate, DocumentOut, DocumentVoidRequest
from src.services.factos_client import factos_client
from src.services.facturador.company_link import resolve_factos_company_id, FactosLinkError
from src.services.facturador.responses import map_status, file_urls, raise_factos_error

router = APIRouter(prefix="/documents", tags=["Comprobantes Electrónicos"])

@router.get("", response_model=List[DocumentOut])
def list_documents(
    company_id: Optional[int] = Query(None),
    is_test_mode: Optional[bool] = Query(None),
    type_code: Optional[str] = Query(None),
    series: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="Fecha inicio YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Fecha fin YYYY-MM-DD"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    include_inactive: bool = Query(False, description="Incluir comprobantes eliminados lógicamente"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Document)
    if not include_inactive:
        q = q.filter(Document.is_active == True)
    if company_id is not None:
        q = q.filter(Document.company_id == company_id)
    if is_test_mode is not None:
        q = q.filter(Document.is_test_mode == is_test_mode)
    if type_code:
        q = q.filter(Document.type_code == type_code)
    if series:
        q = q.filter(Document.series == series.upper())
    if status:
        q = q.filter(Document.status == status)
    if start_date:
        try:
            d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            q = q.filter(Document.issue_date >= d_start)
        except ValueError:
            pass
    if end_date:
        try:
            d_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            q = q.filter(Document.issue_date <= d_end)
        except ValueError:
            pass
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            (Document.client_name.ilike(pattern)) |
            (Document.client_doc_number.ilike(pattern)) |
            (Document.series.ilike(pattern))
        )

    return q.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()

@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    return doc

@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == payload.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa emisora no encontrada")

    series = payload.series.strip().upper()
    
    # 1. Determinar o auto-calcular el siguiente correlativo
    if payload.correlative is not None and payload.correlative > 0:
        correlative = payload.correlative
    else:
        series_record = db.query(CompanySeries).filter(
            CompanySeries.company_id == company.id,
            CompanySeries.document_type == payload.type_code,
            CompanySeries.series == series,
        ).first()
        max_corr = db.query(func.max(Document.correlative)).filter(
            Document.company_id == company.id,
            Document.type_code == payload.type_code,
            Document.series == series,
        ).scalar() or 0
        base_corr = series_record.correlative_current if series_record else 0
        correlative = max(base_corr, max_corr) + 1

    # 2. Calcular totales a partir de los ítems
    total_taxable = Decimal("0.00")
    total_igv = Decimal("0.00")
    total_doc = Decimal("0.00")

    items_to_create = []
    for it in payload.items:
        total_taxable += it.unit_value * it.quantity
        total_igv += it.igv_amount
        total_doc += it.total
        items_to_create.append(it)

    # 3. Guardar/actualizar cliente en la libreta si no existía (directorio corporativo)
    existing_client = db.query(Client).filter(
        Client.doc_number == payload.client.doc_number.strip(),
    ).first()
    if not existing_client:
        new_client = Client(
            doc_type=payload.client.doc_type,
            doc_number=payload.client.doc_number.strip(),
            name=payload.client.name.strip(),
            address=payload.client.address,
            email=payload.client.email,
        )
        db.add(new_client)

    # 4. Crear el registro en base de datos local
    # Determinar tipo de operación SUNAT automáticamente según el contenido
    operation_type = payload.operation_type
    if payload.detraction:
        operation_type = "1001"  # Operación Sujeta a Detracción
    elif payload.retention:
        operation_type = "2001"  # Operación Sujeta a Percepción / Retención
    elif all(it.igv_type == "40" for it in payload.items):
        operation_type = "0200"  # Exportación de bienes/servicios

    now_pe = now_peru()
    new_doc = Document(
        company_id=company.id,
        is_test_mode=payload.is_test_mode,
        type_code=payload.type_code,
        operation_type=operation_type,
        series=series,
        correlative=correlative,
        issue_date=payload.issue_date,
        issue_time=payload.issue_time or now_pe.strftime("%H:%M:%S"),
        due_date=payload.due_date,
        currency=payload.currency,
        payment_method=payload.payment_method,
        installments=[i.model_dump() for i in payload.installments] if payload.installments else None,
        detraction=payload.detraction.model_dump() if payload.detraction else None,
        retention=payload.retention,
        prepayments=payload.prepayments,
        related_documents=payload.related_documents,
        note_data=payload.note.model_dump() if payload.note else None,
        client_doc_type=payload.client.doc_type,
        client_doc_number=payload.client.doc_number.strip(),
        client_name=payload.client.name.strip(),
        client_address=payload.client.address,
        client_email=payload.client.email,
        seller_name=payload.seller_name,
        employee_id=payload.employee_id,
        total_taxable=total_taxable,
        total_igv=total_igv,
        total=total_doc,
        status="pending",
        created_at=now_pe,
    )
    db.add(new_doc)
    db.flush()

    for it in items_to_create:
        doc_item = DocumentItem(
            document_id=new_doc.id,
            internal_code=it.internal_code,
            description=it.description,
            unit_code=it.unit_code,
            quantity=it.quantity,
            unit_value=it.unit_value,
            unit_price=it.unit_price,
            igv_type=it.igv_type,
            igv_amount=it.igv_amount,
            total=it.total,
        )
        db.add(doc_item)

    # Actualizar correlativo registrado de la serie
    if series_record:
        series_record.correlative_current = max(series_record.correlative_current, correlative)

    db.commit()

    # 5. Enviar a Factos API (tanto en prueba como en producción real)
    try:
        factos_company_id = await resolve_factos_company_id(db, company, payload.is_test_mode)
    except FactosLinkError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    factos_payload = {
        "company_id": factos_company_id,
        "external_id": str(new_doc.id),
        "is_test": payload.is_test_mode,
        "type_code": payload.type_code,
        "operation_type": operation_type,
        "series": series,
        "correlative": correlative,
        "issue_date": str(payload.issue_date),
        "issue_time": payload.issue_time or "12:00:00",
        "due_date": str(payload.due_date) if payload.due_date else None,
        "currency": payload.currency,
        "payment_method": payload.payment_method.lower(),
        "installments": [i.model_dump() for i in payload.installments] if payload.installments else None,
        "detraction": payload.detraction.model_dump() if payload.detraction else None,
        "retention": payload.retention,
        "prepayments": payload.prepayments,
        "related_documents": payload.related_documents,
        "note": payload.note.model_dump() if payload.note else None,
        "client": {
            "doc_type": payload.client.doc_type,
            "doc_number": payload.client.doc_number.strip(),
            "name": payload.client.name.strip(),
            "address": payload.client.address,
            "email": payload.client.email,
        },
        "totals": {
            "taxable": float(total_taxable),
            "unaffected": 0.0,
            "exonerated": 0.0,
            "free": 0.0,
            "exportation": 0.0,
            "igv": float(total_igv),
            "icbper": 0.0,
            "discount": 0.0,
            "total": float(total_doc),
        },
        "items": [
            {
                "internal_code": it.internal_code,
                "description": it.description,
                "unit_code": it.unit_code,
                "quantity": float(it.quantity),
                "unit_value": float(it.unit_value),
                "unit_price": float(it.unit_price),
                "igv_type": it.igv_type,
                "igv_amount": float(it.igv_amount),
                "total": float(it.total),
            }
            for it in payload.items
        ],
    }

    result = await factos_client.send_document(factos_payload)
    if result.get("error"):
        new_doc.status = "rejected"
        new_doc.sunat_description = result.get("message", "Error al procesar con Factos API")
        db.commit()
        raise_factos_error(result)

    doc_data = result.get("data", {})
    factos_id = doc_data.get("id")
    if factos_id:
        new_doc.facturador_document_id = str(factos_id)
        urls = file_urls("documents", str(factos_id))
        new_doc.pdf_url = urls["pdf_url"]
        new_doc.xml_url = urls["xml_url"]
        new_doc.cdr_url = urls["cdr_url"]

    # Si el webhook ya actualizó el comprobante sincrónicamente, conservar su estado
    db.refresh(new_doc)
    if new_doc.status == "pending":
        factos_status = doc_data.get("status", "pending")
        new_doc.status = map_status(factos_status)
        if new_doc.status == "accepted":
            new_doc.sunat_code = "0"
            new_doc.sunat_description = doc_data.get("sunat_description", "Aceptado por SUNAT")
        else:
            new_doc.sunat_code = "0"
            new_doc.sunat_description = "Comprobante emitido y encolado para procesamiento en Factos."

    db.commit()
    db.refresh(new_doc)
    return new_doc

@router.post("/{document_id}/void", response_model=DocumentOut)
async def void_document(
    document_id: int,
    payload: DocumentVoidRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")

    if doc.status == "voided":
        raise HTTPException(status_code=400, detail="El comprobante ya fue anulado")

    now_pe = now_peru()
    doc.void_reason = payload.reason
    doc.voided_at = now_pe
    doc.status = "voided"

    if not doc.is_test_mode and doc.facturador_document_id:
        # Enviar baja a Factos API
        await factos_client.void_document(doc.facturador_document_id, payload.reason)

    doc.sunat_description = f"{payload.reason}"

    db.commit()
    db.refresh(doc)
    return doc

@router.put("/{document_id}")
@router.patch("/{document_id}")
def update_document_blocked(
    document_id: int,
    current_user: User = Depends(get_current_user),
):
    """Bloqueo explícito de edición: Los comprobantes de pago electrónicos son inmutables."""
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Los comprobantes electrónicos son inmutables por normativa tributaria. No se permite la edición de un comprobante emitido. Para corregir montos o anular efectos fiscales, emita una Nota de Crédito o una comunicación de baja."
    )

@router.delete("/{document_id}", status_code=status.HTTP_400_BAD_REQUEST)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regla de inmutabilidad: Los comprobantes tributarios emitidos no pueden ser eliminados."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Inmutabilidad fiscal: Los comprobantes de pago electrónicos son inmutables y no pueden eliminarse del registro. Si requiere anular la validez del comprobante ante SUNAT, utilice el endpoint de anulación (/documents/{id}/void) o emita una Nota de Crédito."
    )
