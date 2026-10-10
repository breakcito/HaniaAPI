"""Vinculación entre una empresa de Hania y su empresa emisora en Factos.

Reglas:
- Modo prueba: siempre se emite con la empresa de prueba (SUNAT Beta) de la cuenta Factos
  asociada a la API Key. Factos la crea automáticamente si no existe.
- Modo real: se usa `company.facturador_company_id`. Si está vacío se busca en Factos una
  empresa con el mismo RUC (auto-vinculación). Si no existe, la empresa debe registrarse
  en Factos con sus credenciales SUNAT (ver `register_company`).
"""

from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from src.core.config import settings
from src.models.company import Company
from src.services.facturador.client import facturador_gateway


class FactosLinkError(Exception):
    """La empresa no puede emitir porque no está registrada/vinculada en Factos."""


def _webhook_fields() -> Dict[str, Any]:
    fields: Dict[str, Any] = {}
    if settings.HANIA_WEBHOOK_URL:
        fields["webhook_url"] = settings.HANIA_WEBHOOK_URL
        if settings.WEBHOOK_SECRET:
            fields["webhook_secret"] = settings.WEBHOOK_SECRET
    return fields


async def _ensure_webhook(factos_company: Dict[str, Any]) -> None:
    """Apunta el webhook de la empresa en Factos hacia Hania (si está configurado)."""
    fields = _webhook_fields()
    if fields and factos_company.get("webhook_url") != fields["webhook_url"]:
        await facturador_gateway.update_company(str(factos_company["id"]), fields)


async def get_test_company_id() -> str:
    """Devuelve (creándola si hace falta) la empresa de prueba SUNAT Beta en Factos."""
    res = await facturador_gateway.create_test_company()
    if res.get("error") or not res.get("data"):
        raise FactosLinkError(f"No se pudo obtener la empresa de prueba en Factos: {res.get('message')}")
    await _ensure_webhook(res["data"])
    return str(res["data"]["id"])


async def find_company_by_ruc(ruc: str) -> Optional[Dict[str, Any]]:
    """Busca en Factos una empresa real (producción) con el RUC dado."""
    res = await facturador_gateway.list_companies()
    if res.get("error"):
        raise FactosLinkError(f"No se pudo consultar Factos: {res.get('message')}")
    for item in res.get("data", []):
        if item.get("ruc") == ruc and item.get("is_production"):
            return item
    return None


async def try_auto_link(db: Session, company: Company) -> Optional[str]:
    """Vincula la empresa con Factos por RUC si ya existe allá. No lanza error si no existe."""
    if company.facturador_company_id:
        return company.facturador_company_id
    if not company.is_production:
        company.facturador_company_id = await get_test_company_id()
    else:
        found = await find_company_by_ruc(company.ruc)
        if not found:
            return None
        await _ensure_webhook(found)
        company.facturador_company_id = str(found["id"])
    db.commit()
    return company.facturador_company_id


async def resolve_factos_company_id(db: Session, company: Company, is_test_mode: bool) -> str:
    """Determina con qué empresa de Factos se debe emitir el comprobante/guía."""
    if is_test_mode:
        return await get_test_company_id()

    factos_id = await try_auto_link(db, company)
    if not factos_id:
        raise FactosLinkError(
            f"La empresa {company.business_name} (RUC {company.ruc}) aún no está habilitada para facturar. "
            "Regístrela en el facturador desde Empresas → 'Habilitar facturación' con su usuario SOL y certificado digital."
        )
    return factos_id


async def register_company(
    db: Session,
    company: Company,
    sol_user: str,
    sol_pass: str,
    certificate_pass: str,
    certificate: bytes,
    certificate_filename: str,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> Dict[str, Any]:
    """Registra la empresa en Factos con sus credenciales SUNAT y guarda el vínculo."""
    data = {
        "ruc": company.ruc,
        "business_name": company.business_name,
        "address": company.address,
        "ubigeo": company.ubigeo,
        "department": company.department,
        "province": company.province,
        "district": company.district,
        "establishment_code": company.establishment_code or "0000",
        "sol_user": sol_user,
        "sol_pass": sol_pass,
        "certificate_pass": certificate_pass,
        "client_id": client_id,
        "client_secret": client_secret,
        "is_production": company.is_production,
        **_webhook_fields(),
    }
    res = await facturador_gateway.create_company_with_certificate(data, certificate, certificate_filename)
    if res.get("error"):
        return res

    company.facturador_company_id = str(res["data"]["id"])
    company.sol_user = sol_user
    db.commit()
    return res
