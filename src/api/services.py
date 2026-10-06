from fastapi import APIRouter, Depends, HTTPException
from src.core.deps import get_current_user
from src.models.user import User
from src.services.factos_client import factos_client

router = APIRouter(prefix="/services", tags=["Servicios Auxiliares SUNAT / RENIEC"])

@router.get("/ruc/{number}")
async def lookup_ruc(
    number: str,
    current_user: User = Depends(get_current_user),
):
    number = number.strip()
    if len(number) != 11 or not number.isdigit():
        raise HTTPException(status_code=400, detail="El RUC debe tener exactamente 11 dígitos numéricos")

    result = await factos_client.get_ruc_data(number)
    if result.get("error"):
        raise HTTPException(
            status_code=result.get("status_code", 400),
            detail=result.get("message", "No se pudo consultar el RUC en SUNAT"),
        )
    return result

@router.get("/dni/{number}")
async def lookup_dni(
    number: str,
    current_user: User = Depends(get_current_user),
):
    number = number.strip()
    if len(number) != 8 or not number.isdigit():
        raise HTTPException(status_code=400, detail="El DNI debe tener exactamente 8 dígitos numéricos")

    result = await factos_client.get_dni_data(number)
    if result.get("error"):
        raise HTTPException(
            status_code=result.get("status_code", 400),
            detail=result.get("message", "No se pudo consultar el DNI en RENIEC"),
        )
    return result

@router.get("/exchange-rate")
async def get_exchange_rate(
    current_user: User = Depends(get_current_user),
):
    result = await factos_client.get_exchange_rate()
    if result.get("error"):
        # Fallback de seguridad si el servicio de tipo de cambio externo tiene una pausa
        return {
            "status": "success",
            "data": {
                "moneda": "USD",
                "fecha": "hoy",
                "compra": 3.745,
                "venta": 3.755,
                "origen": "referencial",
            }
        }
    return result
