import logging
from datetime import datetime
from src.core.datetime_peru import now_peru
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.models.document import Document
from src.models.despatch import Despatch
from src.models.webhook_log import WebhookLog

logger = logging.getLogger("webhook_receiver")
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/factos", status_code=status.HTTP_200_OK)
async def receive_factos_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_factos_event: Optional[str] = Header(None, alias="X-Factos-Event"),
    x_factos_signature: Optional[str] = Header(None, alias="X-Factos-Signature"),
):
    """Receptor oficial de eventos asíncronos emitidos por Factos API (facturador electrónico).

    Actualiza en tiempo real el estado ante SUNAT de Facturas, Boletas, Notas y Guías,
    almacenando los enlaces definitivos de descarga XML, CDR y PDF.
    """
    try:
        payload = await request.json()
    except Exception as exc:
        logger.error(f"Error parseando cuerpo del webhook de Factos: {exc}")
        raise HTTPException(status_code=400, detail="Formato JSON no válido")

    event = x_factos_event or payload.get("event", "unknown")
    data = payload.get("data", {})
    factos_id = str(data.get("id")) if data.get("id") else None
    series = data.get("series")
    correlative = data.get("correlative")
    doc_type = data.get("document_type")
    doc_status = data.get("status", "pending")
    sunat_info = data.get("sunat", {}) or {}
    links = data.get("links", {}) or {}

    document_id = None
    despatch_id = None
    process_message = "Procesado"

    # 1. Tratar eventos de Guías de Remisión
    if event.startswith("despatch."):
        despatch = None
        if factos_id:
            despatch = db.query(Despatch).filter(Despatch.facturador_despatch_id == factos_id).first()
        if not despatch and series and correlative:
            despatch = db.query(Despatch).filter(
                Despatch.series == series.upper(),
                Despatch.correlative == int(correlative),
            ).first()

        if despatch:
            despatch_id = despatch.id
            if factos_id and not despatch.facturador_despatch_id:
                despatch.facturador_despatch_id = factos_id

            if event == "despatch.accepted":
                despatch.status = "accepted"
                despatch.sunat_code = sunat_info.get("code", "0")
                despatch.sunat_description = sunat_info.get("description", "Guía aceptada por SUNAT")
                if links.get("pdf"):
                    despatch.pdf_url = links["pdf"]
                if links.get("xml"):
                    despatch.xml_url = links["xml"]
                if links.get("cdr"):
                    despatch.cdr_url = links["cdr"]
            elif event == "despatch.rejected":
                despatch.status = "rejected"
                despatch.sunat_code = sunat_info.get("code", "99")
                despatch.sunat_description = sunat_info.get("description", "Guía rechazada por SUNAT")
            elif event == "despatch.voided":
                despatch.status = "voided"

            process_message = f"Guía ID {despatch.id} actualizada a {despatch.status}"
        else:
            process_message = f"Guía {series}-{correlative} no encontrada localmente"

    # 2. Tratar eventos de Comprobantes de Pago (01, 03, 07, 08)
    else:
        document = None
        if factos_id:
            document = db.query(Document).filter(Document.facturador_document_id == factos_id).first()
        if not document and series and correlative:
            document = db.query(Document).filter(
                Document.series == series.upper(),
                Document.correlative == int(correlative),
            ).first()

        if document:
            document_id = document.id
            if factos_id and not document.facturador_document_id:
                document.facturador_document_id = factos_id

            if event == "document.accepted":
                document.status = "accepted"
                document.sunat_code = sunat_info.get("code", "0")
                document.sunat_description = sunat_info.get("description", "Comprobante aceptado por SUNAT")
                if links.get("pdf"):
                    document.pdf_url = links["pdf"]
                if links.get("xml"):
                    document.xml_url = links["xml"]
                if links.get("cdr"):
                    document.cdr_url = links["cdr"]
            elif event == "document.rejected":
                document.status = "rejected"
                document.sunat_code = sunat_info.get("code", "99")
                document.sunat_description = sunat_info.get("description", "Comprobante rechazado por SUNAT")
            elif event == "document.voided":
                document.status = "voided"
                document.voided_at = now_peru()
                if links.get("xml"):
                    document.void_xml_url = links["xml"]
                if links.get("cdr"):
                    document.void_cdr_url = links["cdr"]

            process_message = f"Comprobante ID {document.id} actualizado a {document.status}"
        else:
            process_message = f"Comprobante {series}-{correlative} no encontrado localmente"

    # 3. Guardar log de auditoría
    webhook_log = WebhookLog(
        event_type=event,
        document_id=document_id,
        despatch_id=despatch_id,
        signature=x_factos_signature,
        payload=payload,
        status_processed="processed",
        message=process_message,
        created_at=now_peru(),
    )
    db.add(webhook_log)
    db.commit()

    logger.info(f"Factos Webhook recibido con éxito: [{event}] -> {process_message}")
    return {
        "status": "success",
        "message": process_message,
        "event": event,
    }
