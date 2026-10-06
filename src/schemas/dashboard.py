from typing import List, Dict, Any
from decimal import Decimal
from pydantic import BaseModel

class MonthlyPoint(BaseModel):
    month: str # e.g. "2026-05", "May"
    month_name: str # e.g. "Mayo 2026"
    total_sales_pen: Decimal
    total_sales_usd: Decimal
    total_operations: int
    total_despatches: int
    total_detraction_pen: Decimal

class StatusBreakdown(BaseModel):
    status: str # "accepted", "pending", "rejected", "voided"
    label: str # "Aceptado por SUNAT", etc.
    count: int
    color: str

class TypeBreakdown(BaseModel):
    type_code: str
    label: str # "Facturas", "Boletas", "Notas de Crédito", "Guías de Remisión"
    count: int
    total_amount_pen: Decimal

class DashboardStatsResponse(BaseModel):
    # KPIs generales del mes actual
    current_month_name: str
    month_sales_pen: Decimal
    month_sales_usd: Decimal
    month_operations_count: int
    month_despatches_count: int
    month_detraction_pen: Decimal
    
    # Serie temporal mensual para gráficos
    monthly_trend: List[MonthlyPoint]
    
    # Distribución por estado SUNAT
    status_distribution: List[StatusBreakdown]
    
    # Distribución por tipo de comprobante
    type_distribution: List[TypeBreakdown]
    
    # Resumen de operaciones recientes
    recent_operations: List[Dict[str, Any]]
