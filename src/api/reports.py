from typing import Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.company import Company
from src.models.document import Document
from src.models.despatch import Despatch
from src.services.facturador.excel_reports import (
    generate_sales_report_excel,
    generate_despatches_report_excel,
)

router = APIRouter(prefix="/reports", tags=["Reportes Contables y de Negocio"])

@router.get("/sales-excel")
def download_sales_excel(
    company_id: int = Query(..., description="ID de la empresa"),
    start_date: Optional[date] = Query(None, description="Fecha inicio YYYY-MM-DD"),
    end_date: Optional[date] = Query(None, description="Fecha fin YYYY-MM-DD"),
    type_code: Optional[str] = Query(None, description="01, 03, 07, 08"),
    status: Optional[str] = Query(None, description="accepted, voided, rejected, etc."),
    include_test: bool = Query(True, description="Incluir o excluir operaciones de prueba"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Descarga el Registro Oficial de Ventas e Ingresos en formato Excel (.xlsx) estructurado."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    q = db.query(Document).filter(
        Document.company_id == company_id,
        Document.is_active == True,
    )

    if not include_test:
        q = q.filter(Document.is_test_mode == False)
    if start_date:
        q = q.filter(Document.issue_date >= start_date)
    if end_date:
        q = q.filter(Document.issue_date <= end_date)
    if type_code:
        q = q.filter(Document.type_code == type_code)
    if status:
        q = q.filter(Document.status == status)

    docs = q.order_by(Document.issue_date.asc(), Document.correlative.asc()).all()

    excel_bytes = generate_sales_report_excel(
        company_name=company.trademark_name or company.business_name,
        company_ruc=company.ruc,
        documents=docs,
    )

    filename = f"Registro_Ventas_{company.ruc}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get("/despatches-excel")
def download_despatches_excel(
    company_id: int = Query(..., description="ID de la empresa"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    include_test: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Descarga el Reporte Logístico de Guías de Remisión Electrónica en formato Excel (.xlsx)."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    q = db.query(Despatch).filter(
        Despatch.company_id == company_id,
        Despatch.is_active == True,
    )

    if not include_test:
        q = q.filter(Despatch.is_test_mode == False)
    if start_date:
        q = q.filter(Despatch.issue_date >= start_date)
    if end_date:
        q = q.filter(Despatch.issue_date <= end_date)

    despatches = q.order_by(Despatch.issue_date.asc(), Despatch.correlative.asc()).all()

    excel_bytes = generate_despatches_report_excel(
        company_name=company.trademark_name or company.business_name,
        company_ruc=company.ruc,
        despatches=despatches,
    )

    filename = f"Guias_Remision_{company.ruc}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )
