"""Utilidades para interpretar las respuestas de Factos API."""

from typing import Any, Dict
from fastapi import HTTPException
from src.core.config import settings

# Estados de Factos -> estados de Hania (pending, accepted, rejected, voided)
_STATUS_MAP = {
    "accepted": "accepted",
    "rejected": "rejected",
    "voided": "voided",
}


def map_status(factos_status: str) -> str:
    """Cualquier estado intermedio de Factos (pending, waiting_sunat, failed...) es 'pending' en Hania."""
    return _STATUS_MAP.get(factos_status or "", "pending")


def file_urls(resource: str, factos_id: str) -> Dict[str, str]:
    """Enlaces de descarga en Factos. `resource` = 'documents' | 'despatches'."""
    base = f"{settings.API_FACTURADOR_URL}/api/v1/{resource}/{factos_id}"
    return {"pdf_url": f"{base}/pdf", "xml_url": f"{base}/xml", "cdr_url": f"{base}/cdr"}


def raise_factos_error(result: Dict[str, Any]) -> None:
    """Convierte un error de Factos en un HTTP 422/502 legible para el frontend."""
    message = result.get("message") or "Error al procesar en el facturador"
    errors = result.get("errors") or {}
    details = [msg for msgs in errors.values() for msg in (msgs if isinstance(msgs, list) else [msgs])]
    if details:
        message = " | ".join(details)

    status_code = result.get("status_code", 502)
    raise HTTPException(status_code=422 if status_code in (400, 409, 422) else 502, detail=message)
