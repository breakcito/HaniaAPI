from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.core.deps import get_current_user
from src.core.config import settings
from src.models.user import User
from src.models.company import Company
from src.models.series import CompanySeries
from src.models.bank import Bank, BankAccount
from src.schemas.company import CompanyCreate, CompanyUpdate, CompanyOut
from src.services.facturador.client import facturador_gateway

from src.services.facturador.sync import auto_sync_test_company

router = APIRouter(prefix="/companies", tags=["Multiempresa"])

@router.get("", response_model=List[CompanyOut])
async def list_companies(
    include_inactive: bool = Query(False, description="Incluir empresas eliminadas lógicamente"),
    is_production: Optional[bool] = Query(None, description="Filtrar por entorno de producción o pruebas"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verificación proactiva: Si no existe empresa de prueba en Hania, sincronizarla con Factos API
    if is_production is not True:
        has_test_company = db.query(Company).filter(Company.is_production == False, Company.is_active == True).first()
        if not has_test_company:
            try:
                await auto_sync_test_company(db)
            except Exception:
                pass

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
        trademark_name=payload.trademark_name or payload.business_name,
        address=payload.address,
        ubigeo=payload.ubigeo,
        department=payload.department,
        province=payload.province,
        district=payload.district,
        establishment_code=payload.establishment_code,
        sol_user=payload.sol_user or "MODDATOS",
        bn_account=payload.bn_account,
        detraction_percent_default=payload.detraction_percent_default,
        phone=payload.phone,
        email=payload.email,
        website=payload.website,
        logo_url=payload.logo_url,
        facturador_company_id=payload.facturador_company_id,
        is_matrix=payload.is_matrix,
        is_production=payload.is_production,
        is_active=True,
    )
    db.add(company)
    db.commit()
    db.refresh(company)

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

@router.put("/{company_id}", response_model=CompanyOut)
async def update_company(
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

    # Si la empresa está vinculada al Facturador, sincronizar automáticamente los cambios
    factos_id = company.facturador_company_id or (settings.FACTOS_COMPANY_ID if company.is_matrix else None)
    if factos_id:
        factos_payload = {}
        if company.business_name:
            factos_payload["business_name"] = company.business_name
        if company.trademark_name:
            factos_payload["trademark_name"] = company.trademark_name
        if company.address:
            factos_payload["address"] = company.address
        if company.ubigeo:
            factos_payload["ubigeo"] = company.ubigeo
        if company.department:
            factos_payload["department"] = company.department
        if company.province:
            factos_payload["province"] = company.province
        if company.district:
            factos_payload["district"] = company.district
        if company.establishment_code:
            factos_payload["establishment_code"] = company.establishment_code
        if company.sol_user:
            factos_payload["sol_user"] = company.sol_user

        if factos_payload:
            try:
                res = await facturador_gateway.update_company(str(factos_id), factos_payload)
                if not res.get("error"):
                    company.facturador_company_id = str(factos_id)
                    db.commit()
            except Exception:
                pass  # Sincronización secundaria no bloquea actualización local

    return company

@router.post("/{company_id}/sync-to-factos")
async def sync_company_to_factos(
    company_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Envía y actualiza los datos actuales de la empresa en Hania hacia el Facturador Factos API."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    factos_id = company.facturador_company_id or (settings.FACTOS_COMPANY_ID if company.is_matrix else None)
    if not factos_id:
        res_list = await facturador_gateway.list_companies()
        if not res_list.get("error"):
            for fc in res_list.get("data", []):
                if fc.get("ruc") == company.ruc:
                    factos_id = str(fc.get("id"))
                    company.facturador_company_id = factos_id
                    db.commit()
                    break

    if not factos_id:
        raise HTTPException(
            status_code=400,
            detail="La empresa no está vinculada a un ID del facturador. Sincronice primero desde Factos."
        )

    factos_payload = {
        "business_name": company.business_name,
        "trademark_name": company.trademark_name or company.business_name,
        "address": company.address,
        "ubigeo": company.ubigeo,
        "department": company.department,
        "province": company.province,
        "district": company.district,
        "establishment_code": company.establishment_code or "0000",
        "sol_user": company.sol_user or "MODDATOS",
    }
    factos_payload = {k: v for k, v in factos_payload.items() if v is not None}

    res = await facturador_gateway.update_company(str(factos_id), factos_payload)
    if res.get("error"):
        raise HTTPException(
            status_code=502,
            detail=f"Error al actualizar la empresa en Factos API: {res.get('message')}"
        )

    return {
        "status": "success",
        "message": "Datos de la empresa sincronizados y actualizados correctamente en el Facturador Factos API.",
        "factos_company_id": factos_id,
        "factos_response": res.get("data")
    }

@router.post("/sync-factos", response_model=List[CompanyOut])
async def sync_companies_from_factos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sincroniza e importa las empresas configuradas en el Facturador Electrónico Factos API."""
    res = await facturador_gateway.list_companies()
    if res.get("error"):
        raise HTTPException(
            status_code=502,
            detail=f"Error comunicando con Factos API: {res.get('message', 'Fallo de conexión')}"
        )

    factos_companies = res.get("data", [])
    synced_companies = []

    for fc in factos_companies:
        ruc = fc.get("ruc")
        if not ruc:
            continue

        comp = db.query(Company).filter(Company.ruc == ruc).first()
        if comp:
            comp.facturador_company_id = str(fc.get("id"))
            if not comp.business_name:
                comp.business_name = fc.get("business_name")
            if not comp.trademark_name:
                comp.trademark_name = fc.get("trademark_name")
            if not comp.address:
                comp.address = fc.get("address")
            if not comp.ubigeo:
                comp.ubigeo = fc.get("ubigeo")
            db.commit()
            db.refresh(comp)
            synced_companies.append(comp)
        else:
            new_comp = Company(
                facturador_company_id=str(fc.get("id")),
                ruc=ruc,
                business_name=fc.get("business_name") or f"Empresa RUC {ruc}",
                trademark_name=fc.get("trademark_name") or fc.get("business_name"),
                address=fc.get("address"),
                ubigeo=fc.get("ubigeo"),
                department=fc.get("department"),
                province=fc.get("province"),
                district=fc.get("district"),
                establishment_code=fc.get("establishment_code") or "0000",
                sol_user=fc.get("sol_user") or "MODDATOS",
                bn_account="00-068-123456",
                is_matrix=False,
                is_active=True,
            )
            db.add(new_comp)
            db.commit()
            db.refresh(new_comp)

            # Sembrar series
            default_series = [
                ("01", "F001", "Serie Principal Facturas"),
                ("03", "B001", "Serie Principal Boletas"),
                ("07", "FC01", "Serie Notas de Crédito Facturas"),
                ("07", "BC01", "Serie Notas de Crédito Boletas"),
                ("08", "FD01", "Serie Notas de Débito Facturas"),
                ("08", "BD01", "Serie Notas de Débito Boletas"),
                ("09", "T001", "Serie Guías Remitente"),
            ]
            for dt, s, d in default_series:
                db.add(CompanySeries(
                    company_id=new_comp.id,
                    document_type=dt,
                    series=s,
                    correlative_current=0,
                    description=d,
                    is_active=True,
                ))
            db.commit()
            synced_companies.append(new_comp)

    return synced_companies

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
    return {"message": "Empresa eliminada lógicamente con éxito", "id": company_id, "is_active": False}
