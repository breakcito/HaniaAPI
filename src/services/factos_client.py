import httpx
import logging
from typing import Optional, Dict, Any
from src.core.config import settings

logger = logging.getLogger("factos_client")

class FactosClient:
    def __init__(self):
        self.base_url = settings.API_FACTURADOR_URL
        self._cached_token: Optional[str] = None

    async def get_token(self, force_refresh: bool = False) -> str:
        if self._cached_token and not force_refresh:
            return self._cached_token

        login_url = f"{self.base_url}/api/v1/auth/login"
        payload = {
            "email": settings.FACTOS_USER_EMAIL,
            "password": settings.FACTOS_USER_PASSWORD,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                response = await client.post(
                    login_url,
                    json=payload,
                    headers={"Accept": "application/json", "Content-Type": "application/json"}
                )
                if response.status_code == 200:
                    data = response.json()
                    self._cached_token = data.get("token")
                    return self._cached_token
                else:
                    logger.error(f"Error authenticating with Factos API: {response.status_code} - {response.text}")
                    raise Exception(f"No se pudo autenticar con el facturador: {response.text}")
            except Exception as e:
                logger.exception("Connection error with Factos API login")
                raise Exception(f"Error de conexión con Factos API: {str(e)}")

    async def request(self, method: str, path: str, json_data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        token = await self.get_token()
        url = f"{self.base_url}/api/v1/{path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(method, url, json=json_data, params=params, headers=headers)
                
                # Si el token expiró (401), reintentar una vez obteniendo token nuevo
                if response.status_code == 401:
                    logger.info("Factos token expired, refreshing token...")
                    token = await self.get_token(force_refresh=True)
                    headers["Authorization"] = f"Bearer {token}"
                    response = await client.request(method, url, json=json_data, params=params, headers=headers)

                data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"text": response.text}
                
                if response.status_code in (200, 201, 202):
                    return data
                else:
                    logger.warning(f"Factos API error [{response.status_code}] on {method} {path}: {response.text}")
                    return {
                        "error": True,
                        "status_code": response.status_code,
                        "message": data.get("message", "Error al procesar en Factos API"),
                        "errors": data.get("errors", None),
                    }
            except Exception as e:
                logger.exception(f"Factos request failure on {method} {url}")
                return {
                    "error": True,
                    "status_code": 500,
                    "message": f"Error de comunicación con el facturador: {str(e)}"
                }

    # Métodos auxiliares de conveniencia
    async def get_ruc_data(self, ruc: str) -> Dict[str, Any]:
        return await self.request("GET", f"services/ruc/{ruc}")

    async def get_dni_data(self, dni: str) -> Dict[str, Any]:
        return await self.request("GET", f"services/dni/{dni}")

    async def get_exchange_rate(self) -> Dict[str, Any]:
        return await self.request("GET", "services/exchange-rate")

    async def list_companies(self) -> Dict[str, Any]:
        return await self.request("GET", "companies")

    async def send_document(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("POST", "documents", json_data=payload)

    async def get_document(self, document_id: str) -> Dict[str, Any]:
        return await self.request("GET", f"documents/{document_id}")

    async def void_document(self, document_id: str, reason: str) -> Dict[str, Any]:
        return await self.request("POST", f"documents/{document_id}/void", json_data={"reason": reason})

    async def send_despatch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request("POST", "despatches", json_data=payload)

    async def get_despatch(self, despatch_id: str) -> Dict[str, Any]:
        return await self.request("GET", f"despatches/{despatch_id}")

    async def void_despatch(self, despatch_id: str, reason: str) -> Dict[str, Any]:
        return await self.request("POST", f"despatches/{despatch_id}/void", json_data={"reason": reason})

factos_client = FactosClient()
