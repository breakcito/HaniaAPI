from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.company import Company
from src.models.purchase import PurchaseDocument
from src.schemas.purchase import PurchaseCreate, PurchaseOut
from src.services.factos_client import factos_client
from src.services.facturador.company_link import resolve_factos_company_id

router = APIRouter(prefix="/purchases", tags=["Comprobantes de Compra"])

@router.get("", response_model=List[PurchaseOut])
def list_purchases(
    company_id: Optional[int] = Query(None),
    supplier_doc_number: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(PurchaseDocument).filter(PurchaseDocument.is_active == True)
    if company_id is not None:
        q = q.filter(PurchaseDocument.company_id == company_id)
    if supplier_doc_number:
        q = q.filter(PurchaseDocument.supplier_doc_number == supplier_doc_number.strip())
    if start_date:
        try:
            d_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            q = q.filter(PurchaseDocument.issue_date >= d_start)
        except ValueError:
            pass
    if end_date:
        try:
            d_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            q = q.filter(PurchaseDocument.issue_date <= d_end)
        except ValueError:
            pass
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            (PurchaseDocument.supplier_name.ilike(pattern)) |
            (PurchaseDocument.supplier_doc_number.ilike(pattern)) |
            (PurchaseDocument.series.ilike(pattern)) |
            (PurchaseDocument.goods_description.ilike(pattern))
        )

    return q.order_by(PurchaseDocument.issue_date.desc()).offset(offset).limit(limit).all()

@router.post("", response_model=PurchaseOut, status_code=status.HTTP_201_CREATED)
async def create_purchase(
    payload: PurchaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == payload.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    d_issue = datetime.strptime(payload.issue_date, "%Y-%m-%d").date()
    d_due = datetime.strptime(payload.due_date, "%Y-%m-%d").date() if payload.due_date else None

    purchase = PurchaseDocument(
        company_id=company.id,
        supplier_doc_type=payload.supplier_doc_type,
        supplier_doc_number=payload.supplier_doc_number.strip(),
        supplier_name=payload.supplier_name.strip(),
        type_code=payload.type_code,
        series=payload.series.strip().upper(),
        correlative=str(payload.correlative).strip(),
        issue_date=d_issue,
        due_date=d_due,
        currency=payload.currency,
        exchange_rate=payload.exchange_rate,
        taxable_base=payload.taxable_base,
        igv=payload.igv,
        unaffected=payload.unaffected,
        exonerated=payload.exonerated,
        other_taxes=payload.other_taxes,
        total=payload.total,
        goods_description=payload.goods_description,
        items=payload.items,
        observations=payload.observations,
    )
    db.add(purchase)
    db.commit()
    db.refresh(purchase)

    # Replicar / respaldar en Factos API
    try:
        factos_company_id = await resolve_factos_company_id(db, company, False)
        factos_payload = {
            "company_id": factos_company_id,
            "supplier_doc_type": payload.supplier_doc_type,
            "supplier_doc_number": payload.supplier_doc_number.strip(),
            "supplier_name": payload.supplier_name.strip(),
            "type_code": payload.type_code,
            "series": payload.series.strip().upper(),
            "correlative": str(payload.correlative).strip(),
            "issue_date": payload.issue_date,
            "due_date": payload.due_date,
            "currency": payload.currency,
            "exchange_rate": float(payload.exchange_rate) if payload.exchange_rate else None,
            "taxable_base": float(payload.taxable_base),
            "igv": float(payload.igv),
            "unaffected": float(payload.unaffected),
            "exonerated": float(payload.exonerated),
            "other_taxes": float(payload.other_taxes),
            "total": float(payload.total),
            "goods_description": payload.goods_description,
            "items": payload.items,
            "observations": payload.observations,
        }
        await factos_client.request("POST", "purchases", json_data=factos_payload)
    except Exception:
        pass

    return purchase

@router.post("/sync-factos")
async def sync_purchases_from_factos(
    company_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sincroniza y descarga las facturas de compras registradas en Factos API hacia Hania."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    factos_company_id = await resolve_factos_company_id(db, company, False)
    res = await factos_client.request("GET", "purchases", params={"company_id": factos_company_id, "per_page": 100})
    if res.get("error"):
        raise HTTPException(status_code=400, detail="Error consultando compras en Factos")

    purchases_data = res.get("data", {}).get("data", [])
    synced_count = 0
    for p in purchases_data:
        series = str(p.get("series", "")).upper()
        corr = str(p.get("correlative", ""))
        supp_doc = str(p.get("supplier_doc_number", "")).strip()

        exists = db.query(PurchaseDocument).filter(
            PurchaseDocument.company_id == company.id,
            PurchaseDocument.supplier_doc_number == supp_doc,
            PurchaseDocument.series == series,
            PurchaseDocument.correlative == corr,
        ).first()

        if not exists:
            d_issue = datetime.strptime(p.get("issue_date")[:10], "%Y-%m-%d").date()
            new_p = PurchaseDocument(
                company_id=company.id,
                supplier_doc_type=p.get("supplier_doc_type", "6"),
                supplier_doc_number=supp_doc,
                supplier_name=p.get("supplier_name", ""),
                type_code=p.get("type_code", "01"),
                series=series,
                correlative=corr,
                issue_date=d_issue,
                currency=p.get("currency", "PEN"),
                exchange_rate=Decimal(str(p.get("exchange_rate", 1.0))) if p.get("exchange_rate") else None,
                taxable_base=Decimal(str(p.get("taxable_base", 0.0))),
                igv=Decimal(str(p.get("igv", 0.0))),
                unaffected=Decimal(str(p.get("unaffected", 0.0))),
                exonerated=Decimal(str(p.get("exonerated", 0.0))),
                other_taxes=Decimal(str(p.get("other_taxes", 0.0))),
                total=Decimal(str(p.get("total", 0.0))),
                goods_description=p.get("goods_description"),
                items=p.get("items"),
                observations=p.get("observations"),
            )
            db.add(new_p)
            synced_count += 1

    db.commit()
    return {"status": "success", "synced_count": synced_count}

@router.get("/export-txt")
def export_purchases_txt(
    company_id: int = Query(...),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera archivo estructurado TXT de compras apto para contabilidad y validación tributaria SUNAT/SIRE."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    q = db.query(PurchaseDocument).filter(
        PurchaseDocument.company_id == company_id,
        PurchaseDocument.is_active == True,
    )
    if start_date:
        try:
            q = q.filter(PurchaseDocument.issue_date >= datetime.strptime(start_date, "%Y-%m-%d").date())
        except ValueError:
            pass
    if end_date:
        try:
            q = q.filter(PurchaseDocument.issue_date <= datetime.strptime(end_date, "%Y-%m-%d").date())
        except ValueError:
            pass

    purchases = q.order_by(PurchaseDocument.issue_date.asc(), PurchaseDocument.id.asc()).all()

    # Formato delimitado por barras (|) estándar para libros de compras
    lines = []
    for idx, p in enumerate(purchases, start=1):
        corr_padded = str(p.correlative).zfill(8) if p.correlative.isdigit() else p.correlative
        f_issue = p.issue_date.strftime("%d/%m/%Y")
        f_due = p.due_date.strftime("%d/%m/%Y") if p.due_date else ""
        tc = f"{p.exchange_rate:.3f}" if p.exchange_rate else "1.000"
        
        # Estructura: Periodo|Cuo|FechaEmision|FechaVenc|TipoComprobante|Serie|Numero|DocTipo|DocNumero|RazonSocial|BaseGravada|IGV|Inafecto|Exonerado|OtrosTributos|Total|Moneda|TipoCambio|Descripcion
        line = (
            f"{p.issue_date.strftime('%Y%m')}|M{str(idx).zfill(6)}|{f_issue}|{f_due}|"
            f"{p.type_code}|{p.series}|{corr_padded}|{p.supplier_doc_type}|"
            f"{p.supplier_doc_number}|{p.supplier_name}|{p.taxable_base:.2f}|{p.igv:.2f}|"
            f"{p.unaffected:.2f}|{p.exonerated:.2f}|{p.other_taxes:.2f}|{p.total:.2f}|"
            f"{p.currency}|{tc}|{p.goods_description or ''}|"
        )
        lines.append(line)

    content = "\r\n".join(lines)
    filename = f"LE{company.ruc}{datetime.today().strftime('%Y%m')}080100001111.txt"

    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
