"""Cliente HTTP desacoplado para integración con Factos API (Facturador Electrónico SUNAT).

Este cliente puede ser extraído e incorporado directamente en cualquier POS, ERP
o microservicio con solo configurar la URL base y la API Key.
"""

import httpx
import logging
from typing import Optional, Dict, Any, List
from src.core.config import settings

logger = logging.getLogger("facturador_gateway")

class FacturadorClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or settings.API_FACTURADOR_URL).rstrip("/")
        self.api_key = api_key or settings.API_KEY_FACTURADOR

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["X-API-KEY"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        headers = self._get_headers()

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    json=json_data,
                    params=params,
                    headers=headers,
                )

                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    data = response.json()
                else:
                    data = {"text": response.text}

                if response.status_code in (200, 201, 202):
                    return data
                else:
                    logger.warning(
                        f"Facturador API error [{response.status_code}] on {method} {url}: {response.text}"
                    )
                    return {
                        "error": True,
                        "status_code": response.status_code,
                        "message": data.get("message", "Error al procesar en el Facturador"),
                        "errors": data.get("errors", None),
                        "raw": data,
                    }
            except httpx.RequestError as exc:
                logger.exception(f"Error de red o timeout conectando con el facturador: {exc}")
                return {
                    "error": True,
                    "status_code": 503,
                    "message": f"No se pudo conectar con el servicio de facturación: {str(exc)}",
                }
            except Exception as exc:
                logger.exception(f"Error inesperado al invocar el facturador: {exc}")
                return {
                    "error": True,
                    "status_code": 500,
                    "message": f"Error interno en gateway de facturación: {str(exc)}",
                }

    # ==========================================
    # Servicios Auxiliares (RUC, DNI, Tipo Cambio)
    # ==========================================
    async def query_ruc(self, ruc: str) -> Dict[str, Any]:
        """Consulta datos de empresa o persona jurídica en SUNAT mediante el facturador."""
        return await self.request("GET", f"services/ruc/{ruc.strip()}")

    async def query_dni(self, dni: str) -> Dict[str, Any]:
        """Consulta datos de persona natural en RENIEC mediante el facturador."""
        return await self.request("GET", f"services/dni/{dni.strip()}")

    async def query_exchange_rate(self) -> Dict[str, Any]:
        """Consulta el tipo de cambio oficial del día (compra/venta) publicado por SBS/SUNAT."""
        return await self.request("GET", "services/exchange-rate")

    # ==========================================
    # Gestión de Empresas (Tenants) en Facturador
    # ==========================================
    async def list_companies(self) -> Dict[str, Any]:
        """Lista las empresas vinculadas a la cuenta/API Key en el Facturador."""
        return await self.request("GET", "companies")

    async def get_company(self, company_id: str) -> Dict[str, Any]:
        """Obtiene la información detallada de una empresa en el Facturador."""
        return await self.request("GET", f"companies/{company_id}")

    async def create_test_company(self) -> Dict[str, Any]:
        """Crea una empresa de prueba SUNAT en el Facturador si no existe."""
        return await self.request("POST", "companies/test-company")

    async def update_company(self, company_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Actualiza los datos de la empresa emisora en el Facturador (razón social, nombre comercial, dirección, ubigeo, credenciales SOL, webhook, etc.)."""
        return await self.request("PUT", f"companies/{company_id}", json_data=data)

    async def update_company_webhook(self, company_id: str, webhook_url: str, webhook_secret: Optional[str] = None) -> Dict[str, Any]:
        """Configura la URL de recepción de webhooks de la empresa en el Facturador."""
        payload: Dict[str, Any] = {"webhook_url": webhook_url}
        if webhook_secret:
            payload["webhook_secret"] = webhook_secret
        return await self.update_company(company_id, payload)

    # ==========================================
    # Comprobantes de Pago Electrónicos (CPE)
    # ==========================================
    async def send_document(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Emite una Factura (01), Boleta (03), Nota de Crédito (07) o Débito (08)."""
        return await self.request("POST", "documents", json_data=payload)

    async def get_document(self, document_id: str) -> Dict[str, Any]:
        """Consulta el estado de un comprobante y obtiene los enlaces XML, CDR y PDF."""
        return await self.request("GET", f"documents/{document_id}")

    async def void_document(self, document_id: str, reason: str) -> Dict[str, Any]:
        """Solicita la anulación o comunicación de baja de un comprobante ante SUNAT."""
        return await self.request("POST", f"documents/{document_id}/void", json_data={"reason": reason})

    # ==========================================
    # Guías de Remisión Electrónica (GRE)
    # ==========================================
    async def send_despatch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Emite una Guía de Remisión Remitente (09) o Transportista (31)."""
        return await self.request("POST", "despatches", json_data=payload)

    async def get_despatch(self, despatch_id: str) -> Dict[str, Any]:
        """Consulta el estado y enlaces de una Guía de Remisión."""
        return await self.request("GET", f"despatches/{despatch_id}")

    async def void_despatch(self, despatch_id: str, reason: str) -> Dict[str, Any]:
        """Solicita la anulación de una Guía de Remisión."""
        return await self.request("POST", f"despatches/{despatch_id}/void", json_data={"reason": reason})


# Instancia singleton preconfigurada
facturador_gateway = FacturadorClient()
