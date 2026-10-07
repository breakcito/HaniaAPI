import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.orm import Session
from src.core.database import SessionLocal
from src.models.company import Company
from src.services.facturador.sync import auto_sync_test_company

@pytest.mark.asyncio
async def test_auto_sync_test_company_creates_and_links():
    db: Session = SessionLocal()
    try:
        mock_factos_company = {
            "id": "mock-test-uuid-9999",
            "user_id": 2,
            "ruc": "20000000001",
            "business_name": "EMPRESA DE PRUEBA SUNAT S.A.C.",
            "trademark_name": "FACTOS BETA TEST",
            "address": "AV. LOS TESTERS 123 - URB. INDUSTRIAL",
            "ubigeo": "150101",
            "department": "LIMA",
            "province": "LIMA",
            "district": "LIMA",
            "establishment_code": "0000",
            "sol_user": "MODDATOS",
            "is_production": False,
            "is_active": True,
        }
        
        with patch("src.services.facturador.sync.facturador_gateway.list_companies", new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {"status": "success", "data": [mock_factos_company]}
            
            synced_company = await auto_sync_test_company(db)
            assert synced_company is not None
            assert synced_company.ruc == "20000000001"
            assert synced_company.is_production is False
            assert synced_company.facturador_company_id == "mock-test-uuid-9999"
            
            # Repetir la sincronización para verificar idempotencia
            synced_again = await auto_sync_test_company(db)
            assert synced_again.id == synced_company.id
            assert synced_again.facturador_company_id == "mock-test-uuid-9999"
    finally:
        # Restaurar el estado original si es necesario
        db.close()
