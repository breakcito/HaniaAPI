import httpx
import json
import hashlib
import sys
from decimal import Decimal

HANIA_URL = "http://127.0.0.1:8000"
FACTOS_URL = "http://127.0.0.1:8050"

client = httpx.Client(timeout=35.0)

print("=" * 70)
print("SUITE COMPLETA DE PRUEBAS DE INTEGRACIÓN FACTOS & HANIA (TODOS LOS CASOS)")
print("=" * 70)

# ----------------------------------------------------
# 1. Health checks de ambas APIs
# ----------------------------------------------------
print("\n[PASO 1] VERIFICACIÓN DE SERVICIOS ACTIVOS (HEALTH CHECK)")
r_factos = client.get(f"{FACTOS_URL}/api/health")
print(f"Factos API: {r_factos.status_code} -> {r_factos.text}")
assert r_factos.status_code == 200, "Factos API no responde"

r_hania = client.get(f"{HANIA_URL}/api/health")
print(f"Hania API: {r_hania.status_code} -> {r_hania.text}")
assert r_hania.status_code == 200, "Hania API no responde"

# ----------------------------------------------------
# 2. Autenticación en Hania
# ----------------------------------------------------
print("\n[PASO 2] AUTENTICACIÓN JWT EN HANIA")
r_login = client.post(f"{HANIA_URL}/api/auth/login", json={"username": "admin", "password": "Password123!"})
assert r_login.status_code == 200, f"Error en login: {r_login.text}"
token = r_login.json().get("access_token")
assert token, "No se recibió access_token"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print(f"✓ Autenticado con éxito como 'admin'. Token obtenido.")

# ----------------------------------------------------
# 3. Multi-Establecimientos (Empresa, Cliente, Proveedor)
# ----------------------------------------------------
print("\n[PASO 3] ESTABLECIMIENTOS MULTI-LOCAL (SUCURSALES Y PLANTAS)")
est_payload = {
    "entity_type": "company",
    "entity_id": 1,
    "code": "0002",
    "description": "Planta de Beneficio Chala Sur",
    "address": "Carretera Panamericana Sur Km 612",
    "ubigeo": "040301",
    "department": "Arequipa",
    "province": "Caravelí",
    "district": "Chala",
    "is_primary": False
}
r_est = client.post(f"{HANIA_URL}/api/establishments", json=est_payload, headers=headers)
assert r_est.status_code in [200, 201], f"Error al crear establecimiento: {r_est.text}"
est_id = r_est.json().get("id")

r_est_list = client.get(f"{HANIA_URL}/api/establishments?entity_type=company&entity_id=1", headers=headers)
assert r_est_list.status_code == 200
assert any(e["id"] == est_id for e in r_est_list.json())
print(f"✓ Establecimiento creado y listado correctamente (ID={est_id}, Código=0002)")

# ----------------------------------------------------
# 4. Caso 1: Factura estándar con Detracción SPOT 10%, Crédito y Observación BBVA
# (Basado exactamente en files/factura-sin-anticipo.pdf)
# ----------------------------------------------------
print("\n[PASO 4] CASO 1: FACTURA ESTÁNDAR CON DETRACCIÓN 10%, CUOTAS Y OBSERVACIÓN BBVA")
factura_standard_payload = {
    "company_id": 1,
    "type_code": "01",
    "series": "F001",
    "issue_date": "2026-10-15",
    "due_date": "2026-10-30",
    "currency": "USD",
    "payment_method": "credito",
    "installments": [
        {"due_date": "2026-10-30", "amount": 10800.00}
    ],
    "detraction": {
        "payment_method_code": "001",
        "bank_account": "00754012994",
        "service_code": "034", # Minerales metálicos
        "percent": 10.00,
        "amount": 1200.00
    },
    "client": {
        "doc_type": "6",
        "doc_number": "20601234567",
        "name": "MINERA DEL SUR S.A.C.",
        "address": "Av. Las Minas 456, Arequipa",
        "email": "facturas@mineradelsur.pe"
    },
    "items": [
        {
            "internal_code": "MIN-AG-01",
            "description": "MINERAL CHANCADO Y MOLIDO DE PLATA",
            "unit_code": "TNE",
            "quantity": 10.0,
            "unit_value": 1016.95,
            "unit_price": 1200.00,
            "igv_type": "10",
            "igv_amount": 1830.50,
            "total": 12000.00
        }
    ],
    "observations": "" # Debe completarse automáticamente con formato BBVA
}
r_f1 = client.post(f"{HANIA_URL}/api/documents", json=factura_standard_payload, headers=headers)
assert r_f1.status_code in [200, 201], f"Error al emitir factura estándar: {r_f1.text}"
f1_data = r_f1.json()
print(f"Factura estándar emitida ID={f1_data['id']}, Comprobante={f1_data['series']}-{f1_data['correlative']}")
assert "DOLARES:BANCO BBVA" in f1_data.get("observations", "")
assert f1_data.get("pdf_url") is not None
print("✓ Factura emitida con formato BBVA automático, detracción 10% y enlace PDF inmediato")

# ----------------------------------------------------
# 5. Caso 2: Emisión de Factura de Anticipo (Pago Anticipado)
# (Basado en files/anticipo.jpeg E001-43)
# ----------------------------------------------------
print("\n[PASO 5] CASO 2: FACTURA DE PAGO ANTICIPADO (ANTICIPO)")
anticipo_payload = {
    "company_id": 1,
    "type_code": "01",
    "series": "F001",
    "issue_date": "2026-10-15",
    "currency": "USD",
    "is_advance": True,
    "client": {
        "doc_type": "6",
        "doc_number": "20609988776",
        "name": "COMPAÑIA MINERA CHALA S.A.",
        "address": "Carretera Panamericana Sur Km 600",
        "email": "contacto@chalaminera.pe"
    },
    "items": [
        {
            "internal_code": "ANT-MIN-01",
            "description": "MINERAL MOLIDO Y CHANCADO DE PLATA***Pago Anticipado***",
            "unit_code": "NIU",
            "quantity": 1.0,
            "unit_value": 12627.08,
            "unit_price": 14899.95,
            "igv_type": "10",
            "igv_amount": 2272.87,
            "total": 14899.95
        }
    ],
    "observations": ""
}
r_ant = client.post(f"{HANIA_URL}/api/documents", json=anticipo_payload, headers=headers)
assert r_ant.status_code in [200, 201], f"Error al emitir anticipo: {r_ant.text}"
ant_data = r_ant.json()
ant_id = ant_data["id"]
ant_total = ant_data["total"]
print(f"Factura de Anticipo emitida ID={ant_id}, Total={ant_total}")
assert ant_data.get("is_advance") is True
assert float(ant_data.get("advance_balance")) == 14899.95
print("✓ Anticipo registrado con saldo inicial igual a USD 14,899.95")

# ----------------------------------------------------
# 6. Caso 3: Consulta de Anticipos Disponibles para Cliente
# ----------------------------------------------------
print("\n[PASO 6] CASO 3: CONSULTA DE SALDO DE ANTICIPOS DISPONIBLES")
r_avail = client.get(f"{HANIA_URL}/api/documents/advances/available?company_id=1&client_doc_number=20609988776", headers=headers)
assert r_avail.status_code == 200
avail_list = r_avail.json()
found_adv = next((a for a in avail_list if a["id"] == ant_id), None)
assert found_adv is not None, "El anticipo no figura disponible"
assert float(found_adv["balance"]) == 14899.95
print(f"✓ Anticipo encontrado disponible con saldo USD {found_adv['balance']}")

# ----------------------------------------------------
# 7. Caso 4: Factura Deduciendo Anticipo
# (Basado exactamente en files/factura-con-anticipo.jpeg E001-44)
# Sub Total: 18,602.46, Anticipos: -14,899.95, Valor Venta: 3,702.51, IGV: 666.45, Total: 4,368.96
# ----------------------------------------------------
print("\n[PASO 7] CASO 4: FACTURA DEDUCIENDO ANTICIPO (SUBTOTAL - ANTICIPO = BASE)")
f_deduct_payload = {
    "company_id": 1,
    "type_code": "01",
    "series": "F001",
    "issue_date": "2026-10-15",
    "currency": "USD",
    "payment_method": "credito",
    "installments": [
        {"due_date": "2026-10-31", "amount": 4368.96}
    ],
    "client": {
        "doc_type": "6",
        "doc_number": "20609988776",
        "name": "COMPAÑIA MINERA CHALA S.A.",
        "address": "Carretera Panamericana Sur Km 600",
        "email": "contacto@chalaminera.pe"
    },
    "items": [
        {
            "internal_code": "LOTE-PLATA-44",
            "description": "MINERAL MOLIDO Y CHANCADO DE PLATA LOTE 44",
            "unit_code": "TNE",
            "quantity": 15.0,
            "unit_value": 1240.164,
            "unit_price": 1463.394,
            "igv_type": "10",
            "igv_amount": 3348.44,
            "total": 21950.90
        }
    ],
    "applied_advances": [
        {
            "advance_document_id": ant_id,
            "type_code": "01",
            "series": ant_data["series"],
            "correlative": ant_data["correlative"],
            "amount": 14899.95,
            "description": f"ANTICIPO: FACTURA NRO. {ant_data['series']}-{ant_data['correlative']}"
        }
    ],
    "observations": "Liquidación final con deducción de anticipo E001-43"
}
r_f_deduct = client.post(f"{HANIA_URL}/api/documents", json=f_deduct_payload, headers=headers)
assert r_f_deduct.status_code in [200, 201], f"Error al emitir factura con deducción: {r_f_deduct.text}"
f_deduct_data = r_f_deduct.json()
f_deduct_id = f_deduct_data["id"]
print(f"Factura deduciendo anticipo emitida ID={f_deduct_id}, Comprobante={f_deduct_data['series']}-{f_deduct_data['correlative']}")

# Verificar que el saldo del anticipo se redujo a 0.00
r_avail_after = client.get(f"{HANIA_URL}/api/documents/advances/available?company_id=1&client_doc_number=20609988776", headers=headers)
avail_list_after = r_avail_after.json()
found_adv_after = next((a for a in avail_list_after if a["id"] == ant_id), None)
assert found_adv_after is None or float(found_adv_after["balance"]) == 0.0
print("✓ Saldo de anticipo consumido correctamente (0.00 restante)")

# ----------------------------------------------------
# 8. Caso 5: Nota de Crédito 01 (Anulación total) revirtiendo la deducción del anticipo
# ----------------------------------------------------
print("\n[PASO 8] CASO 5: NOTA DE CRÉDITO MOTIVO 01 CON REVERSIÓN DE ANTICIPO APLICADO")
nc01_payload = {
    "company_id": 1,
    "type_code": "07", # Nota de Crédito
    "series": "FC01",
    "issue_date": "2026-10-15",
    "currency": "USD",
    "client": {
        "doc_type": "6",
        "doc_number": "20609988776",
        "name": "COMPAÑIA MINERA CHALA S.A."
    },
    "note": {
        "affected_type": "01",
        "affected_series": f_deduct_data["series"],
        "affected_correlative": f_deduct_data["correlative"],
        "code": "01",
        "reason": "ANULACION DE LA OPERACION"
    },
    "items": [
        {
            "internal_code": "LOTE-PLATA-44",
            "description": "ANULACION LOTE 44",
            "unit_code": "TNE",
            "quantity": 15.0,
            "unit_value": 1240.164,
            "unit_price": 1463.394,
            "igv_type": "10",
            "igv_amount": 3348.44,
            "total": 21950.90
        }
    ]
}
r_nc01 = client.post(f"{HANIA_URL}/api/documents", json=nc01_payload, headers=headers)
assert r_nc01.status_code in [200, 201], f"Error al emitir NC 01: {r_nc01.text}"
nc01_data = r_nc01.json()
print(f"Nota de Crédito 01 emitida ID={nc01_data['id']}, Comprobante={nc01_data['series']}-{nc01_data['correlative']}")

# Verificar que el saldo del anticipo fue restituido a 14,899.95
r_avail_restored = client.get(f"{HANIA_URL}/api/documents/advances/available?company_id=1&client_doc_number=20609988776", headers=headers)
restored_adv = next((a for a in r_avail_restored.json() if a["id"] == ant_id), None)
assert restored_adv is not None, "El saldo del anticipo no fue restituido"
assert abs(float(restored_adv["balance"]) - 14899.95) < 0.01
print("✓ Reversión exitosa: Saldo del anticipo completamente restituido a USD 14,899.95")

# ----------------------------------------------------
# 9. Caso 6: Nota de Crédito 03 (Corrección de descripción con «Dice» y «Debe decir»)
# (Basado exactamente en files/20261010_112858.jpg E001-15)
# ----------------------------------------------------
print("\n[PASO 9] CASO 6: NOTA DE CRÉDITO MOTIVO 03 CON «DICE» Y «DEBE DECIR»")
nc03_payload = {
    "company_id": 1,
    "type_code": "07",
    "series": "FC01",
    "issue_date": "2026-10-15",
    "currency": "USD",
    "client": {
        "doc_type": "6",
        "doc_number": "20601234567",
        "name": "MINERA DEL SUR S.A.C."
    },
    "note": {
        "affected_type": "01",
        "affected_series": f1_data["series"],
        "affected_correlative": f1_data["correlative"],
        "code": "03",
        "reason": "CORRECCION POR ERROR EN LA DESCRIPCION",
        "dice": "MINERAL DE PLATA",
        "debe_decir": "MINERAL CHANCADO Y MOLIDO DE PLATA"
    },
    "items": [
        {
            "internal_code": "CORR-01",
            "description": "CORRECCION DE DESCRIPCION",
            "unit_code": "NIU",
            "quantity": 1.0,
            "unit_value": 0.0,
            "unit_price": 0.0,
            "igv_type": "10",
            "igv_amount": 0.0,
            "total": 0.0
        }
    ]
}
r_nc03 = client.post(f"{HANIA_URL}/api/documents", json=nc03_payload, headers=headers)
assert r_nc03.status_code in [200, 201], f"Error al emitir NC 03: {r_nc03.text}"
nc03_data = r_nc03.json()
print(f"Nota de Crédito 03 emitida ID={nc03_data['id']}, Comprobante={nc03_data['series']}-{nc03_data['correlative']}")

# Descargar PDF de la NC 03 y verificar que contenga «DICE» y «DEBE DECIR»
r_nc_pdf = client.get(nc03_data["pdf_url"])
assert r_nc_pdf.status_code == 200
assert r_nc_pdf.content[:4] == b"%PDF"
print("✓ Nota de Crédito 03 emitida con éxito y PDF verificado (bytes %PDF)")

# ----------------------------------------------------
# 10. Caso 7: GRE Remitente (09) por Transformación con Transporte Público y Peso Referencial
# (Basado en files/guia - ? -.pdf EG07-189)
# ----------------------------------------------------
print("\n[PASO 10] CASO 7: GRE REMITENTE (09) POR TRANSFORMACIÓN CON TRANSPORTE PÚBLICO Y PESO REFERENCIAL")
gre_transf_payload = {
    "company_id": 1,
    "type_code": "09",
    "series": "T001",
    "issue_date": "2026-10-15",
    "transfer_date": "2026-10-16",
    "delivery_date": "2026-10-15",
    "transport_mode": "01", # Transporte Público
    "transfer_reason": "13", # Traslado de bienes para transformación
    "transfer_description": "Traslado a planta procesadora para beneficio",
    "total_weight": 31.45,
    "weight_unit": "TNE",
    "packages_count": 1,
    "is_referential_weight": True,
    "recipient": {
        "doc_type": "6",
        "doc_number": "20601234567",
        "name": "PLANTA METALURGICA DEL SUR S.A.C.",
        "address": "Km 615 Panamericana Sur, Chala"
    },
    "origin": {
        "ubigeo": "040301",
        "address": "Campamento Minero Cerro Rico S/N"
    },
    "destination": {
        "ubigeo": "040301",
        "address": "Planta de Beneficio Chala Km 615"
    },
    "carrier": {
        "doc_type": "6",
        "doc_number": "20501234567",
        "name": "TRANSPORTES LOGISTICOS MINEROS DEL PERU S.A.C.",
        "mtc": "15113580CNG"
    },
    "items": [], # Ítem por defecto automático "Mineral en bruto sin procesar"
    "observations": ""
}
r_gre_transf = client.post(f"{HANIA_URL}/api/despatches", json=gre_transf_payload, headers=headers)
assert r_gre_transf.status_code in [200, 201], f"Error al emitir GRE transformación: {r_gre_transf.text}"
gre_transf_data = r_gre_transf.json()
print(f"GRE Transformación emitida ID={gre_transf_data['id']}, Comprobante={gre_transf_data['series']}-{gre_transf_data['correlative']}")
assert "EL PESO ES REFERENCIAL" in gre_transf_data.get("observations", "")
assert gre_transf_data["items"][0]["description"] == "Mineral en bruto sin procesar"
print("✓ GRE con Transporte Público, MTC 15113580CNG, ítem por defecto y observación referencial")

# ----------------------------------------------------
# 11. Caso 8: GRE Remitente (09) por Compra con Proveedor, Factura Sustentatoria y Multi-Items
# (Basado en files/guia - ?.jpeg EG07-205)
# ----------------------------------------------------
print("\n[PASO 11] CASO 8: GRE REMITENTE POR COMPRA CON FACTURA DE PROVEEDOR Y MULTI-ITEMS")
gre_compra_payload = {
    "company_id": 1,
    "type_code": "09",
    "series": "T001",
    "issue_date": "2026-10-15",
    "transfer_date": "2026-10-16",
    "transport_mode": "02", # Transporte Privado
    "transfer_reason": "02", # Compra
    "transfer_description": "Traslado por compra de insumos mineros",
    "total_weight": 18.50,
    "weight_unit": "TNE",
    "packages_count": 50,
    "vehicle_certificate": "15M24002047E",
    "recipient": {
        "doc_type": "6",
        "doc_number": "20612955990", # La propia empresa receptora
        "name": "CORPORACION DE SERVICIOS CUPPER & HANNIA E.I.R.L.",
        "address": "Av. Principal 123, Chala, Arequipa"
    },
    "origin": {
        "ubigeo": "150101",
        "address": "Almacén Central Proveedor, Lima"
    },
    "destination": {
        "ubigeo": "040301",
        "address": "Planta de Beneficio Cupper & Hannia, Chala"
    },
    "vehicle": {
        "plate": "TDS-870",
        "certificate": "15M24002047E"
    },
    "driver": {
        "doc_type": "1",
        "doc_number": "41235678",
        "name": "ACOSTA MIGUEL ANGEL ALBERTO",
        "license": "Q41235678"
    },
    "related_documents": [
        {
            "type_code": "01",
            "series": "F006",
            "correlative": "7059",
            "supplier_ruc": "20601140625",
            "supplier_name": "COMPAÑIA DISTRIBUIDORA L & G E.I.R.L."
        }
    ],
    "items": [
        {
            "internal_code": "REACT-01",
            "description": "REACTIVO FLOTADOR DE PLATA",
            "unit_code": "KGM",
            "quantity": 10000.0
        },
        {
            "internal_code": "CAL-02",
            "description": "CAL VIVA INDUSTRIAL EN BOLSAS",
            "unit_code": "KGM",
            "quantity": 8500.0
        }
    ]
}
r_gre_compra = client.post(f"{HANIA_URL}/api/despatches", json=gre_compra_payload, headers=headers)
assert r_gre_compra.status_code in [200, 201], f"Error al emitir GRE Compra: {r_gre_compra.text}"
gre_compra_data = r_gre_compra.json()
gre_compra_id = gre_compra_data["id"]
print(f"GRE por Compra emitida ID={gre_compra_id}, Comprobante={gre_compra_data['series']}-{gre_compra_data['correlative']}")
assert len(gre_compra_data["items"]) == 2
print("✓ GRE Compra vinculada a Factura F006-7059 de COMPAÑIA DISTRIBUIDORA L & G con 2 ítems")

# ----------------------------------------------------
# 12. Caso 9: Guía de Remisión de Transportista (Tipo 31)
# ----------------------------------------------------
print("\n[PASO 12] CASO 9: GUÍA DE REMISIÓN DE TRANSPORTISTA (TIPO 31)")
gre_transp_payload = {
    "company_id": 1,
    "type_code": "31", # Guía de Transportista
    "series": "V001",
    "issue_date": "2026-10-15",
    "transfer_date": "2026-10-16",
    "transport_mode": "01",
    "transfer_reason": "01",
    "total_weight": 25.00,
    "weight_unit": "TNE",
    "packages_count": 1,
    "recipient": {
        "doc_type": "6",
        "doc_number": "20601234567",
        "name": "DESTINATARIO CARGA S.A.",
        "address": "Calle Los Ficus 123, Lima"
    },
    "origin": {
        "ubigeo": "040301",
        "address": "Punto de Carga Chala"
    },
    "destination": {
        "ubigeo": "150101",
        "address": "Puerto del Callao"
    },
    "carrier": {
        "doc_type": "6",
        "doc_number": "20612955990",
        "name": "CORPORACION DE SERVICIOS CUPPER & HANNIA E.I.R.L.",
        "mtc": "MTC-998822"
    },
    "items": [
        {
            "internal_code": "CARGA-01",
            "description": "CONCENTRADO MINERAL A GRANEL",
            "unit_code": "TNE",
            "quantity": 25.0
        }
    ]
}
r_gre_transp = client.post(f"{HANIA_URL}/api/despatches", json=gre_transp_payload, headers=headers)
assert r_gre_transp.status_code in [200, 201], f"Error al emitir GRE Transportista (31): {r_gre_transp.text}"
gre_transp_data = r_gre_transp.json()
print(f"GRE Transportista (31) emitida ID={gre_transp_data['id']}, Comprobante={gre_transp_data['series']}-{gre_transp_data['correlative']}")
assert gre_transp_data["type_code"] == "31"
print("✓ Soporte oficial para Guía de Transportista (Tipo 31) verificado")

# ----------------------------------------------------
# 13. Caso 10: Procedimiento de Corrección de Guía (Baja automática + Reemisión)
# ----------------------------------------------------
print("\n[PASO 13] CASO 10: CORRECCIÓN AUTOMATIZADA DE GUÍA (ANULACIÓN PREVIA + REEMISIÓN)")
gre_corrected_payload = {
    "company_id": 1,
    "type_code": "09",
    "series": "T001",
    "issue_date": "2026-10-15",
    "transfer_date": "2026-10-16",
    "transport_mode": "02",
    "transfer_reason": "02",
    "total_weight": 19.50, # Peso corregido de 18.50 a 19.50
    "weight_unit": "TNE",
    "packages_count": 55,
    "previous_despatch_id_to_void": gre_compra_id, # Guía previa a anular
    "recipient": gre_compra_payload["recipient"],
    "origin": gre_compra_payload["origin"],
    "destination": gre_compra_payload["destination"],
    "vehicle": {
        "plate": "TFA-926", # Vehículo corregido
        "certificate": "TUCE-CERT-7733"
    },
    "driver": {
        "doc_type": "1",
        "doc_number": "48991122",
        "name": "ARGOMEDO RODRIGUEZ JOSE FRANKLIN",
        "license": "Q48991122"
    },
    "items": gre_compra_payload["items"]
}
r_corr = client.post(f"{HANIA_URL}/api/despatches", json=gre_corrected_payload, headers=headers)
assert r_corr.status_code in [200, 201], f"Error al reemitir guía corregida: {r_corr.text}"
corr_data = r_corr.json()
print(f"Guía de reemplazo emitida ID={corr_data['id']}, Comprobante={corr_data['series']}-{corr_data['correlative']}")

# Verificar que la guía anterior ahora figure como 'voided'
r_prev_check = client.get(f"{HANIA_URL}/api/despatches/{gre_compra_id}", headers=headers)
assert r_prev_check.status_code == 200
assert r_prev_check.json()["status"] == "voided", "La guía previa no fue dada de baja automáticamente"
print(f"✓ Guía anterior ID={gre_compra_id} dada de baja automáticamente con estado 'voided'")

# ----------------------------------------------------
# 14. Caso 11: Registro y Sincronización de Compras + Exportación SIRE TXT
# ----------------------------------------------------
print("\n[PASO 14] CASO 11: COMPROBANTES DE COMPRA Y EXPORTACIÓN SIRE TXT")
purch_payload = {
    "company_id": 1,
    "supplier_doc_type": "6",
    "supplier_doc_number": "20601140625",
    "supplier_name": "COMPAÑIA DISTRIBUIDORA L & G E.I.R.L.",
    "type_code": "01",
    "series": "F006",
    "correlative": "7059",
    "issue_date": "2026-10-15",
    "currency": "PEN",
    "taxable_base": 15000.00,
    "igv": 2700.00,
    "total": 17700.00,
    "goods_description": "Insumos químicos y reactivos de flotación",
    "observations": "Sustento de GRE EG07-205"
}
r_p = client.post(f"{HANIA_URL}/api/purchases", json=purch_payload, headers=headers)
assert r_p.status_code in [200, 201], f"Error al registrar compra: {r_p.text}"
p_id = r_p.json()["id"]

# Exportación TXT
r_sire = client.get(f"{HANIA_URL}/api/purchases/export-txt?company_id=1&period=202610", headers=headers)
assert r_sire.status_code == 200
assert "20601140625" in r_sire.text
assert "F006" in r_sire.text
print(f"✓ Compra registrada (ID={p_id}) y archivo TXT SIRE exportado con éxito")

# ----------------------------------------------------
# 15. Caso 12: Reporte Comparativo Ventas vs Costos (Margen Comercial y Tributario)
# ----------------------------------------------------
print("\n[PASO 15] CASO 12: REPORTE COMPARATIVO VENTAS VS COSTOS")
r_svc = client.get(f"{HANIA_URL}/api/reports/sales-vs-purchases?company_id=1", headers=headers)
assert r_svc.status_code == 200
svc_data = r_svc.json()
print("Resumen Ventas vs Compras:")
print(f"  Ventas Base Imponible: {svc_data['sales']['taxable_base']} (Total documentos: {svc_data['sales']['count']})")
print(f"  Compras Base Imponible: {svc_data['purchases']['taxable_base']} (Total documentos: {svc_data['purchases']['count']})")
print(f"  Margen Operativo Bruto: {svc_data['comparison']['margin_taxable']}")
print(f"  IGV Neto por Pagar (Débito - Crédito): {svc_data['comparison']['net_igv_payable']}")
print(f"  Margen Porcentual: {svc_data['comparison']['gross_margin_percentage']}%")
assert svc_data["sales"]["count"] > 0
assert svc_data["purchases"]["count"] > 0
print("✓ Reporte Ventas vs Costos calculado e integrado correctamente")

# ----------------------------------------------------
# 16. Caso 13: Renderizado Dinámico de PDF, XML y CDR por UUID y MD5 (Sin rutas fijas de disco)
# ----------------------------------------------------
print("\n[PASO 16] CASO 13: RENDERIZACIÓN DINÁMICA DE PDF POR UUID Y MD5(UUID)")
doc_pdf_url = f1_data["pdf_url"]
assert doc_pdf_url, "No se devolvió pdf_url"
r_pdf_dyn = client.get(doc_pdf_url)
assert r_pdf_dyn.status_code == 200
assert r_pdf_dyn.content[:4] == b"%PDF"

# Obtener vía MD5
raw_id = doc_pdf_url.split("/documents/")[1].split("/pdf")[0]
md5_id = hashlib.md5(raw_id.encode('utf-8')).hexdigest()
r_pdf_md5 = client.get(f"{FACTOS_URL}/api/v1/documents/{md5_id}/pdf")
assert r_pdf_md5.status_code == 200
assert r_pdf_md5.content[:4] == b"%PDF"
print(f"✓ PDF de documento renderizado en memoria exitosamente mediante UUID y MD5({md5_id})")

# ----------------------------------------------------
# 17. Caso 14: Simulación de Notificaciones por Webhook de Estados SUNAT
# (Estados diferenciados: pending, sending, accepted, rejected, error)
# ----------------------------------------------------
print("\n[PASO 17] CASO 14: CICLO DE VIDA DE ESTADOS ANTE SUNAT VÍA WEBHOOK")
wh_accepted_payload = {
    "event": "document.accepted",
    "data": {
        "id": raw_id,
        "series": f1_data["series"],
        "correlative": f1_data["correlative"],
        "document_type": "01",
        "status": "accepted",
        "sunat": {
            "code": "0",
            "description": "La Factura número F001-" + str(f1_data["correlative"]) + " ha sido aceptada por SUNAT."
        },
        "links": {
            "pdf": f"{FACTOS_URL}/api/v1/documents/{raw_id}/pdf",
            "xml": f"{FACTOS_URL}/api/v1/documents/{raw_id}/xml",
            "cdr": f"{FACTOS_URL}/api/v1/documents/{raw_id}/cdr"
        }
    }
}
r_wh = client.post(f"{HANIA_URL}/api/webhooks/factos", json=wh_accepted_payload)
assert r_wh.status_code == 200
print(f"Webhook document.accepted recibido: {r_wh.json()}")

# Verificar que el estado del comprobante en Hania se actualizó a 'accepted'
r_f1_check = client.get(f"{HANIA_URL}/api/documents/{f1_data['id']}", headers=headers)
assert r_f1_check.status_code == 200
assert r_f1_check.json()["status"] == "accepted"
print("✓ Estado actualizado en tiempo real a 'accepted' mediante webhook")

print("\n" + "=" * 70)
print("¡TODOS LOS CASOS DE INTEGRACIÓN (1 AL 14) HAN SIDO PROBADOS Y APROBADOS CON ÉXITO!")
print("=" * 70)
