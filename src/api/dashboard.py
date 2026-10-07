from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.document import Document
from src.models.despatch import Despatch
from src.schemas.dashboard import DashboardStatsResponse, MonthlyPoint, StatusBreakdown, TypeBreakdown

router = APIRouter(prefix="/dashboard", tags=["Dashboard e Indicadores"])

MONTH_NAMES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Setiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

@router.get("/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(
    company_id: Optional[int] = Query(None),
    is_test_mode: Optional[bool] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc_q = db.query(Document).filter(Document.is_active == True)
    desp_q = db.query(Despatch).filter(Despatch.is_active == True)

    if company_id is not None:
        doc_q = doc_q.filter(Document.company_id == company_id)
        desp_q = desp_q.filter(Despatch.company_id == company_id)

    if is_test_mode is not None:
        doc_q = doc_q.filter(Document.is_test_mode == is_test_mode)
        desp_q = desp_q.filter(Despatch.is_test_mode == is_test_mode)

    if start_date is not None:
        doc_q = doc_q.filter(Document.issue_date >= start_date)
        desp_q = desp_q.filter(Despatch.issue_date >= start_date)

    if end_date is not None:
        doc_q = doc_q.filter(Document.issue_date <= end_date)
        desp_q = desp_q.filter(Despatch.issue_date <= end_date)

    all_docs = doc_q.all()
    all_desps = desp_q.all()

    today = date.today()
    current_year = today.year
    current_month = today.month

    # 1. Meses a graficar (últimos 6 meses)
    monthly_trend: List[MonthlyPoint] = []
    for i in range(5, -1, -1):
        target_date = today.replace(day=1) - timedelta(days=i * 28)
        y = target_date.year
        m = target_date.month
        month_label = f"{MONTH_NAMES_ES[m]} {y}"
        month_code = f"{y}-{str(m).zfill(2)}"

        month_docs = [d for d in all_docs if d.issue_date.year == y and d.issue_date.month == m and d.status != "voided"]
        month_desps = [g for g in all_desps if g.issue_date.year == y and g.issue_date.month == m and g.status != "voided"]

        pen_sales = sum((d.total for d in month_docs if d.currency == "PEN"), Decimal("0.00"))
        usd_sales = sum((d.total for d in month_docs if d.currency == "USD"), Decimal("0.00"))

        detraction_pen = Decimal("0.00")
        for d in month_docs:
            if d.detraction and isinstance(d.detraction, dict):
                amt = d.detraction.get("amount")
                if amt is not None:
                    detraction_pen += Decimal(str(amt))

        monthly_trend.append(
            MonthlyPoint(
                month=month_code,
                month_name=month_label,
                total_sales_pen=pen_sales,
                total_sales_usd=usd_sales,
                total_operations=len(month_docs),
                total_despatches=len(month_desps),
                total_detraction_pen=detraction_pen,
            )
        )

    # 2. KPIs del mes actual
    curr_point = monthly_trend[-1]
    
    # 3. Distribución por Estado SUNAT
    status_counts = {"accepted": 0, "pending": 0, "rejected": 0, "voided": 0}
    for d in all_docs:
        status_counts[d.status] = status_counts.get(d.status, 0) + 1
    for g in all_desps:
        status_counts[g.status] = status_counts.get(g.status, 0) + 1

    status_dist = [
        StatusBreakdown(status="accepted", label="Aceptados por SUNAT", count=status_counts["accepted"], color="#10B981"),
        StatusBreakdown(status="pending", label="Pendientes de Envío", count=status_counts["pending"], color="#F59E0B"),
        StatusBreakdown(status="rejected", label="Rechazados / Error", count=status_counts["rejected"], color="#EF4444"),
        StatusBreakdown(status="voided", label="Anulados / De Baja", count=status_counts["voided"], color="#6B7280"),
    ]

    # 4. Distribución por Tipo de Documento
    type_map = {
        "01": {"label": "Facturas Electrónicas", "count": 0, "amount": Decimal("0.00")},
        "03": {"label": "Boletas de Venta", "count": 0, "amount": Decimal("0.00")},
        "07": {"label": "Notas de Crédito", "count": 0, "amount": Decimal("0.00")},
        "08": {"label": "Notas de Débito", "count": 0, "amount": Decimal("0.00")},
        "09": {"label": "Guías de Remisión", "count": len(all_desps), "amount": Decimal("0.00")},
    }

    for d in all_docs:
        if d.type_code in type_map:
            type_map[d.type_code]["count"] += 1
            if d.status != "voided":
                type_map[d.type_code]["amount"] += d.total

    type_dist = [
        TypeBreakdown(
            type_code=k,
            label=v["label"],
            count=v["count"],
            total_amount_pen=v["amount"],
        )
        for k, v in type_map.items()
    ]

    # 5. Operaciones recientes combinadas
    recent_ops: List[Dict[str, Any]] = []
    sorted_docs = sorted(all_docs, key=lambda x: x.created_at, reverse=True)[:5]
    for d in sorted_docs:
        type_names = {"01": "Factura", "03": "Boleta", "07": "Nota Crédito", "08": "Nota Débito"}
        recent_ops.append({
            "id": d.id,
            "kind": "document",
            "type_label": type_names.get(d.type_code, "Comprobante"),
            "document_number": d.document_number,
            "client_name": d.client_name,
            "total": float(d.total),
            "currency": d.currency,
            "status": d.status,
            "is_test_mode": d.is_test_mode,
            "date": d.issue_date.strftime("%d/%m/%Y"),
        })

    return DashboardStatsResponse(
        current_month_name=curr_point.month_name,
        month_sales_pen=curr_point.total_sales_pen,
        month_sales_usd=curr_point.total_sales_usd,
        month_operations_count=curr_point.total_operations,
        month_despatches_count=curr_point.total_despatches,
        month_detraction_pen=curr_point.total_detraction_pen,
        monthly_trend=monthly_trend,
        status_distribution=status_dist,
        type_distribution=type_dist,
        recent_operations=recent_ops,
    )
