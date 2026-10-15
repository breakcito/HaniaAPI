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
from src.models.product import Product
from src.models.bank import BankAccount
from src.models.document import Document, DocumentItem
from src.models.applied_advance import AppliedAdvance
from src.models.series import CompanySeries
from src.schemas.document import DocumentCreate, DocumentOut, DocumentVoidRequest
from src.services.factos_client import factos_client
from src.services.facturador.company_link import resolve_factos_company_id, FactosLinkError
from src.services.facturador.responses import map_status, file_urls, raise_factos_error

router = APIRouter(prefix="/documents", tags=["Comprobantes Electrónicos"])

DEFAULT_INVOICE_OBSERVATION = (
    "DOLARES:BANCO BBVA 0011-0249-0100223354 CCI:011-249-000100223354-00 "
    "/CONTRATO <digitar aqui>/ REF.TMHB<digitar aqui> TN/REF tms <DIGITAR AQUi>"
)

@router.get("", response_model=List[DocumentOut])
def list_documents(
    company_id: Optional[int] = Query(None),
    is_test_mode: Optional[bool] = Query(None),
    type_code: Optional[str] = Query(None),
    series: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_advance: Optional[bool] = Query(None),
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
    if is_advance is not None:
        q = q.filter(Document.is_advance == is_advance)
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

@router.get("/advances/available")
def list_available_advances(
    company_id: int = Query(...),
    client_doc_number: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista anticipos disponibles con saldo para un cliente en específico."""
    advances = db.query(Document).filter(
        Document.company_id == company_id,
        Document.client_doc_number == client_doc_number.strip(),
        Document.is_advance == True,
        Document.advance_balance > 0,
        Document.is_active == True,
    ).order_by(Document.issue_date.asc()).all()

    result = []
    for adv in advances:
        applied_total = float(adv.advance_total - adv.advance_balance)
        result.append({
            "id": adv.id,
            "facturador_document_id": adv.facturador_document_id,
            "document_number": adv.document_number,
            "series": adv.series,
            "correlative": adv.correlative,
            "type_code": adv.type_code,
            "issue_date": str(adv.issue_date),
            "currency": adv.currency,
            "original_amount": float(adv.advance_total),
            "applied_amount": applied_total,
            "balance": float(adv.advance_balance),
            "description": f"Anticipo {adv.document_number} ({adv.issue_date})"
        })

    return result

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

        # Auto-guardar producto no registrado en el catálogo
        item_desc = it.description.strip()
        existing_prod = db.query(Product).filter(
            Product.description == item_desc,
            Product.is_active == True,
        ).first()
        if not existing_prod:
            new_prod = Product(
                description=item_desc,
                unit_code=it.unit_code or "TNE",
                unit_value=it.unit_value,
                unit_price=it.unit_price,
                currency=payload.currency,
                igv_type=it.igv_type or "10",
                is_active=True,
            )
            db.add(new_prod)

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

    # 4. Autocompletar observaciones en Factura si no fueron especificadas
    observations = payload.observations
    if payload.type_code == "01" and (not observations or not observations.strip()):
        observations = DEFAULT_INVOICE_OBSERVATION

    # 5. Obtener cuentas bancarias de la empresa emisora para pie_pagina
    bank_accounts = db.query(BankAccount).filter(
        BankAccount.company_id == company.id,
        BankAccount.is_active == True,
        BankAccount.deleted_at.is_(None)
    ).all()
    cuentas_bancarias_list = [
        {
            "banco": ba.bank.name if ba.bank else "Banco",
            "numero_cuenta": ba.account_number,
            "cci": ba.cci or "",
            "moneda": ba.currency,
        }
        for ba in bank_accounts
    ]
    pie_pagina_data = payload.pie_pagina or {}
    if cuentas_bancarias_list and "cuentas_bancarias" not in pie_pagina_data:
        pie_pagina_data["cuentas_bancarias"] = cuentas_bancarias_list

    # 6. Manejo de Anticipos
    is_advance = payload.is_advance
    advance_total = total_doc if is_advance else Decimal("0.00")
    advance_balance = total_doc if is_advance else Decimal("0.00")
    has_deductions = bool(payload.applied_advances)

    now_pe = now_peru()
    new_doc = Document(
        company_id=company.id,
        is_test_mode=payload.is_test_mode,
        type_code=payload.type_code,
        operation_type=payload.operation_type,
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
        observations=observations,
        pie_pagina=pie_pagina_data,
        is_advance=is_advance,
        advance_total=advance_total,
        advance_balance=advance_balance,
        has_deductions=has_deductions,
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

    # 7. Registrar deducción de anticipos en Hania
    applied_advances_for_factos = []
    if payload.applied_advances:
        for adv in payload.applied_advances:
            amount = adv.amount
            orig_doc_factos_id = None
            if adv.advance_document_id:
                orig_adv = db.query(Document).filter(Document.id == adv.advance_document_id).first()
                if orig_adv:
                    if orig_adv.advance_balance < amount:
                        raise HTTPException(
                            status_code=400,
                            detail=f"El monto a aplicar ({amount}) supera el saldo disponible del anticipo {orig_adv.document_number} ({orig_adv.advance_balance})"
                        )
                    orig_adv.advance_balance = max(Decimal("0.00"), orig_adv.advance_balance - amount)
                    orig_doc_factos_id = orig_adv.facturador_document_id

            applied_entry = AppliedAdvance(
                document_id=new_doc.id,
                advance_document_id=adv.advance_document_id,
                advance_type_code=adv.type_code,
                advance_series=adv.series.upper(),
                advance_correlative=str(adv.correlative),
                advance_issue_date=adv.issue_date,
                amount=amount,
                description=adv.description or f"Deducción anticipo {adv.series}-{adv.correlative}",
            )
            db.add(applied_entry)

            applied_advances_for_factos.append({
                "advance_document_id": orig_doc_factos_id,
                "type_code": adv.type_code,
                "series": adv.series.upper(),
                "correlative": adv.correlative,
                "amount": float(amount),
                "description": adv.description,
                "issue_date": str(adv.issue_date) if adv.issue_date else None,
            })

    # 8. Reversión de anticipos si es Nota de Crédito por anulación (motivo 01)
    if payload.type_code == "07" and payload.note and payload.note.code == "01":
        aff_series = payload.note.affected_series.upper()
        aff_corr = payload.note.affected_correlative
        affected_doc = db.query(Document).filter(
            Document.company_id == company.id,
            Document.series == aff_series,
            Document.correlative == aff_corr,
        ).first()

        if affected_doc:
            prior_applieds = db.query(AppliedAdvance).filter(
                AppliedAdvance.document_id == affected_doc.id,
                AppliedAdvance.is_reversed == False,
            ).all()
            for pa in prior_applieds:
                if pa.advance_document_id:
                    orig_adv = db.query(Document).filter(Document.id == pa.advance_document_id).first()
                    if orig_adv:
                        orig_adv.advance_balance += pa.amount
                pa.is_reversed = True

    # Actualizar correlativo registrado de la serie
    series_record = db.query(CompanySeries).filter(
        CompanySeries.company_id == company.id,
        CompanySeries.document_type == payload.type_code,
        CompanySeries.series == series,
    ).first()
    if series_record:
        series_record.correlative_current = max(series_record.correlative_current, correlative)

    db.commit()

    # 9. Enviar a Factos API (con enlace inmediato al PDF)
    try:
        factos_company_id = await resolve_factos_company_id(db, company, payload.is_test_mode)
    except FactosLinkError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    factos_payload = {
        "company_id": factos_company_id,
        "external_id": str(new_doc.id),
        "is_test": payload.is_test_mode,
        "type_code": payload.type_code,
        "operation_type": payload.operation_type,
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
        "observations": observations,
        "pie_pagina": pie_pagina_data,
        "is_advance": is_advance,
        "applied_advances": applied_advances_for_factos if applied_advances_for_factos else None,
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
        # Tomar links inmediatos devueltos por Factos
        links = doc_data.get("links", {})
        new_doc.pdf_url = links.get("pdf") or file_urls("documents", str(factos_id))["pdf_url"]
        new_doc.xml_url = links.get("xml") or file_urls("documents", str(factos_id))["xml_url"]
        new_doc.cdr_url = links.get("cdr") or file_urls("documents", str(factos_id))["cdr_url"]

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
        raise HTTPException(status_code=400, detail="El comprobante ya se encuentra anulado")

    # Si es una factura que aplicó anticipos y se anula, revertir el saldo de los anticipos
    prior_advances = db.query(AppliedAdvance).filter(
        AppliedAdvance.document_id == doc.id,
        AppliedAdvance.is_reversed == False,
    ).all()
    for adv in prior_advances:
        if adv.advance_document_id:
            orig_adv = db.query(Document).filter(Document.id == adv.advance_document_id).first()
            if orig_adv:
                orig_adv.advance_balance += adv.amount
        adv.is_reversed = True

    # Invocar anulación en Factos API
    if doc.facturador_document_id:
        result = await factos_client.void_document(doc.facturador_document_id, payload.reason)
        if result.get("error"):
            raise_factos_error(result)

    now_pe = now_peru()
    doc.status = "voided"
    doc.void_reason = payload.reason
    doc.voided_at = now_pe
    db.commit()
    db.refresh(doc)
    return doc
