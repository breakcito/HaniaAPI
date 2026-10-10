from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.models.company import Company
from src.models.series import CompanySeries
from src.schemas.company import CompanyCreate, CompanyUpdate, CompanyOut
from src.services.facturador.client import facturador_gateway
from src.services.facturador.company_link import try_auto_link, register_company, FactosLinkError
from fastapi import UploadFile, File, Form

router = APIRouter(prefix="/companies", tags=["Multiempresa"])

@router.get("", response_model=List[CompanyOut])
def list_companies(
    include_inactive: bool = Query(False, description="Incluir empresas eliminadas lógicamente"),
    is_production: Optional[bool] = Query(None, description="Filtrar por entorno de producción o pruebas"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Company)
    if not include_inactive:
        q = q.filter(Company.is_active == True)
    if is_production is not None:
        q = q.filter(Company.is_production == is_production)
    return q.order_by(Company.is_matrix.desc(), Company.id.asc()).all()

@router.get("/{company_id}", response_model=CompanyOut)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return company

@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(Company).filter(Company.ruc == payload.ruc).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.deleted_at = None
            existing.business_name = payload.business_name or existing.business_name
            db.commit()
            db.refresh(existing)
            return existing
        raise HTTPException(status_code=400, detail="El RUC ya está registrado en el sistema")

    # Intentar obtener datos oficiales si falta información
    if not payload.address or not payload.department:
        ruc_info = await facturador_gateway.query_ruc(payload.ruc)
        if not ruc_info.get("error") and ruc_info.get("data"):
            data = ruc_info["data"]
            if not payload.business_name:
                payload.business_name = data.get("razon_social", payload.business_name)
            if not payload.address:
                payload.address = data.get("direccion", payload.address)
            if not payload.department:
                payload.department = data.get("departamento", payload.department)
            if not payload.province:
                payload.province = data.get("provincia", payload.province)
            if not payload.district:
                payload.district = data.get("distrito", payload.district)
            if not payload.ubigeo:
                payload.ubigeo = data.get("ubigeo", payload.ubigeo)

    company = Company(
        ruc=payload.ruc,
        business_name=payload.business_name,
        address=payload.address,
        ubigeo=payload.ubigeo,
        department=payload.department,
        province=payload.province,
        district=payload.district,
        establishment_code=payload.establishment_code,
        sol_user=payload.sol_user or "MODDATOS",
        detraction_percent_default=payload.detraction_percent_default,
        phone=payload.phone,
        email=payload.email,
        logo_url=payload.logo_url,
        facturador_company_id=payload.facturador_company_id,
        is_matrix=payload.is_matrix,
        is_production=payload.is_production,
        is_active=True,
    )
    db.add(company)
    db.commit()
    db.refresh(company)

    # Intentar vincular automáticamente con Factos si ya está registrada allá
    try:
        await try_auto_link(db, company)
    except Exception:
        pass

    # Sembrar series iniciales para esta nueva empresa
    default_series_specs = [
        ("01", "F001", "Serie Principal Facturas"),
        ("03", "B001", "Serie Principal Boletas"),
        ("07", "FC01", "Serie Notas de Crédito Facturas"),
        ("07", "BC01", "Serie Notas de Crédito Boletas"),
        ("08", "FD01", "Serie Notas de Débito Facturas"),
        ("08", "BD01", "Serie Notas de Débito Boletas"),
        ("09", "T001", "Serie Guías Remitente"),
    ]
    for doc_type, ser, desc in default_series_specs:
        db.add(CompanySeries(
            company_id=company.id,
            document_type=doc_type,
            series=ser,
            correlative_current=0,
            description=desc,
            is_active=True,
        ))
    db.commit()

    return company

@router.post("/{company_id}/enable-facturador", response_model=CompanyOut)
async def enable_company_in_facturador(
    company_id: int,
    sol_user: str = Form(...),
    sol_pass: str = Form(...),
    certificate_pass: str = Form(...),
    certificate: UploadFile = File(...),
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Habilita la empresa en Factos subiendo su certificado digital y credenciales SOL."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    cert_bytes = await certificate.read()
    if not cert_bytes:
        raise HTTPException(status_code=400, detail="El archivo del certificado digital está vacío")

    res = await register_company(
        db=db,
        company=company,
        sol_user=sol_user.strip(),
        sol_pass=sol_pass.strip(),
        certificate_pass=certificate_pass.strip(),
        certificate=cert_bytes,
        certificate_filename=certificate.filename or "cert.pfx",
        client_id=client_id.strip() if client_id else None,
        client_secret=client_secret.strip() if client_secret else None,
    )
    if res.get("error"):
        raise HTTPException(status_code=422, detail=res.get("message", "Error al registrar empresa en Factos"))

    db.refresh(company)
    return company

@router.put("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: int,
    payload: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(company, field, val)

    company.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(company)

    return company

@router.delete("/{company_id}", status_code=status.HTTP_200_OK)
def delete_company(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if company.is_matrix:
        raise HTTPException(status_code=400, detail="No se puede eliminar la empresa matriz principal")

    if not company.is_active:
        return {"message": "La empresa ya se encuentra inactiva", "id": company_id, "is_active": False}

    company.is_active = False
    company.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Empresa eliminada con éxito", "id": company_id, "is_active": False}
