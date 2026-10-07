from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.company import Company
from src.models.series import CompanySeries
from src.models.document import Document
from src.schemas.series import (
    CompanySeriesCreate,
    CompanySeriesUpdate,
    CompanySeriesOut,
    NextCorrelativeOut,
)

router = APIRouter(prefix="/series", tags=["Series y Correlativos"])

@router.get("", response_model=List[CompanySeriesOut])
def list_series(
    company_id: int = Query(..., description="ID de la empresa emisora"),
    document_type: Optional[str] = Query(None, description="01, 03, 07, 08, 09, 31"),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista las series de comprobantes configuradas para una empresa."""
    q = db.query(CompanySeries).filter(CompanySeries.company_id == company_id)
    if not include_inactive:
        q = q.filter(CompanySeries.is_active == True)
    if document_type:
        q = q.filter(CompanySeries.document_type == document_type)

    return q.order_by(CompanySeries.document_type.asc(), CompanySeries.series.asc()).all()


@router.get("/next-correlative", response_model=NextCorrelativeOut)
def get_next_correlative(
    company_id: int = Query(..., description="ID de la empresa emisora"),
    document_type: str = Query(..., description="Tipo de documento (01, 03, 07, 08, 09)"),
    series: str = Query(..., description="Código de serie (F001, B001, etc.)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calcula y devuelve el siguiente número correlativo disponible para emitir."""
    clean_series = series.strip().upper()
    
    # 1. Buscar en la tabla de series
    series_record = db.query(CompanySeries).filter(
        CompanySeries.company_id == company_id,
        CompanySeries.document_type == document_type,
        CompanySeries.series == clean_series,
    ).first()

    # 2. Verificar el número máximo en la tabla de comprobantes reales
    max_doc_corr = db.query(func.max(Document.correlative)).filter(
        Document.company_id == company_id,
        Document.type_code == document_type,
        Document.series == clean_series,
    ).scalar() or 0

    base_corr = series_record.correlative_current if series_record else 0
    next_corr = max(base_corr, max_doc_corr) + 1

    return NextCorrelativeOut(
        document_type=document_type,
        series=clean_series,
        next_correlative=next_corr,
        formatted_number=f"{clean_series}-{str(next_corr).zfill(8)}",
    )


@router.post("", response_model=CompanySeriesOut, status_code=status.HTTP_201_CREATED)
def create_series(
    payload: CompanySeriesCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea una nueva serie personalizada para la empresa (e.g. F002, B002)."""
    company = db.query(Company).filter(Company.id == payload.company_id, Company.is_active == True).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    clean_series = payload.series.strip().upper()

    existing = db.query(CompanySeries).filter(
        CompanySeries.company_id == payload.company_id,
        CompanySeries.document_type == payload.document_type,
        CompanySeries.series == clean_series,
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"La serie {clean_series} para tipo de comprobante {payload.document_type} ya existe en esta empresa."
        )

    new_series = CompanySeries(
        company_id=payload.company_id,
        document_type=payload.document_type,
        series=clean_series,
        correlative_current=payload.correlative_current or 0,
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(new_series)
    db.commit()
    db.refresh(new_series)
    return new_series


@router.put("/{series_id}", response_model=CompanySeriesOut)
def update_series(
    series_id: int,
    payload: CompanySeriesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza la descripción, estado o correlativo base de una serie."""
    series_record = db.query(CompanySeries).filter(CompanySeries.id == series_id).first()
    if not series_record:
        raise HTTPException(status_code=404, detail="Serie no encontrada")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(series_record, key, value)

    series_record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(series_record)
    return series_record
