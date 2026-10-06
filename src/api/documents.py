from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
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
from src.schemas.document import DocumentCreate, DocumentOut, DocumentVoidRequest
from src.services.factos_client import factos_client

router = APIRouter(prefix="/documents", tags=["Comprobantes Electrónicos"])

@router.get("", response_model=List[DocumentOut])
def list_documents(
    company_id: Optional[int] = Query(None),
    is_test_mode: Optional[bool] = Query(None),
    type_code: Optional[str] = Query(None),
    series: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
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
        max_corr = db.query(func.max(Document.correlative)).filter(
            Document.company_id == company.id,
            Document.type_code == payload.type_code,
            Document.series == series,
        ).scalar()
        correlative = (max_corr or 0) + 1

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

    # 3. Guardar/actualizar cliente en la libreta si no existía
    existing_client = db.query(Client).filter(
        Client.company_id == company.id,
        Client.doc_number == payload.client.doc_number.strip(),
    ).first()
    if not existing_client:
        new_client = Client(
            company_id=company.id,
            doc_type=payload.client.doc_type,
            doc_number=payload.client.doc_number.strip(),
            name=payload.client.name.strip(),
            address=payload.client.address,
            email=payload.client.email,
        )
        db.add(new_client)

    # 4. Crear el registro en base de datos local
    now_utc = datetime.now(timezone.utc)
    new_doc = Document(
        company_id=company.id,
        is_test_mode=payload.is_test_mode,
        type_code=payload.type_code,
        operation_type=payload.operation_type,
        series=series,
        correlative=correlative,
        issue_date=payload.issue_date,
        issue_time=payload.issue_time or "12:00:00",
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
        total_taxable=total_taxable,
        total_igv=total_igv,
        total=total_doc,
        status="pending",
        created_at=now_utc,
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

    # 5. Enviar a Factos API (o procesar en modo prueba)
    if payload.is_test_mode:
        # Modo de Prueba: Simulación exitosa y segura para el usuario
        new_doc.status = "accepted"
        new_doc.sunat_code = "0"
        new_doc.sunat_description = f"[MODO PRUEBA] El comprobante {series}-{str(correlative).zfill(8)} fue procesado satisfactoriamente sin impacto fiscal."
        if settings.API_FACTURADOR_URL:
            new_doc.pdf_url = f"{settings.API_FACTURADOR_URL}/api/v1/documents/simulated-{series}-{correlative}/pdf"
            new_doc.xml_url = f"{settings.API_FACTURADOR_URL}/api/v1/documents/simulated-{series}-{correlative}/xml"
            new_doc.cdr_url = f"{settings.API_FACTURADOR_URL}/api/v1/documents/simulated-{series}-{correlative}/cdr"
    else:
        # Modo Real: Enviar a Factos API
        factos_company_id = company.facturador_company_id or settings.FACTOS_COMPANY_ID
        factos_payload = {
            "company_id": factos_company_id,
            "type_code": payload.type_code,
            "operation_type": payload.operation_type,
            "series": series,
            "correlative": correlative,
            "issue_date": str(payload.issue_date),
            "issue_time": payload.issue_time or "12:00:00",
            "due_date": str(payload.due_date) if payload.due_date else None,
            "currency": payload.currency,
            "payment_method": payload.payment_method,
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
            ]
        }

        result = await factos_client.send_document(factos_payload)
        if result.get("error"):
            new_doc.status = "rejected"
            new_doc.sunat_description = result.get("message", "Error al procesar con Factos API")
        else:
            doc_data = result.get("data", {})
            factos_id = doc_data.get("id")
            new_doc.facturador_document_id = str(factos_id) if factos_id else None
            new_doc.status = doc_data.get("status", "accepted")
            new_doc.sunat_code = "0"
            new_doc.sunat_description = "Comprobante emitido y enviado a SUNAT correctamente."
            if factos_id and settings.API_FACTURADOR_URL:
                new_doc.pdf_url = f"{settings.API_FACTURADOR_URL}/api/v1/documents/{factos_id}/pdf"
                new_doc.xml_url = f"{settings.API_FACTURADOR_URL}/api/v1/documents/{factos_id}/xml"
                new_doc.cdr_url = f"{settings.API_FACTURADOR_URL}/api/v1/documents/{factos_id}/cdr"

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

    now_utc = datetime.now(timezone.utc)
    doc.void_reason = payload.reason
    doc.voided_at = now_utc
    doc.status = "voided"

    if not doc.is_test_mode and doc.facturador_document_id:
        # Enviar baja a Factos API
        await factos_client.void_document(doc.facturador_document_id, payload.reason)

    doc.sunat_description = f"Comprobante anulado / dado de baja. Motivo: {payload.reason}"

    db.commit()
    db.refresh(doc)
    return doc

@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Eliminación LÓGICA (Soft Delete) de comprobante. Nunca se elimina físicamente de la base de datos."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")

    if not doc.is_active:
        return {"message": "El comprobante ya fue eliminado lógicamente", "id": document_id, "is_active": False}

    doc.is_active = False
    doc.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Comprobante archivado/eliminado lógicamente con éxito", "id": document_id, "is_active": False}
