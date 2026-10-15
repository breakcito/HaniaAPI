import httpx
import json
import hashlib
import sys

HANIA_URL = "http://127.0.0.1:8000"
FACTOS_URL = "http://127.0.0.1:8050"

client = httpx.Client(timeout=30.0)

print("==================================================")
print("INICIANDO PRUEBAS DE INTEGRACIÓN FACTOS & HANIA")
print("==================================================")

# 1. Health checks
r_factos = client.get(f"{FACTOS_URL}/api/health")
print(f"[FACTOS HEALTH] {r_factos.status_code} -> {r_factos.text}")
assert r_factos.status_code == 200, "Factos API no está disponible"

r_hania = client.get(f"{HANIA_URL}/api/health")
print(f"[HANIA HEALTH] {r_hania.status_code} -> {r_hania.text}")
assert r_hania.status_code == 200, "Hania API no está disponible"

# 2. Login to Hania to get JWT
print("\n--- 1. AUTENTICACIÓN EN HANIA ---")
login_payload = {
    "username": "admin",
    "password": "Password123!"
}
r_login = client.post(f"{HANIA_URL}/api/auth/login", data=login_payload)
if r_login.status_code != 200:
    r_login = client.post(f"{HANIA_URL}/api/auth/login", json=login_payload)

print(f"Login response status: {r_login.status_code}")
if r_login.status_code != 200:
    print(f"Login error detail: {r_login.text}")
    sys.exit(1)

token_data = r_login.json()
token = token_data.get("access_token")
assert token, "No se obtuvo token de acceso"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print("Token obtenido con éxito.")

# 3. Test Establishments in Hania
print("\n--- 2. ESTABLECIMIENTOS MULTI-LOCAL EN HANIA ---")
est_payload = {
    "entity_type": "company",
    "entity_id": 1,
    "code": "0001",
    "description": "Planta de Beneficio Chala",
    "address": "Km 610 Panamericana Sur",
    "ubigeo": "040301",
    "department": "Arequipa",
    "province": "Caravelí",
    "district": "Chala",
    "is_primary": False
}
r_est = client.post(f"{HANIA_URL}/api/establishments", json=est_payload, headers=headers)
print(f"Crear establecimiento: {r_est.status_code}")
assert r_est.status_code in [200, 201], f"Fallo al crear establecimiento: {r_est.text}"
est_id = r_est.json().get("id")

r_est_list = client.get(f"{HANIA_URL}/api/establishments?entity_type=company&entity_id=1", headers=headers)
print(f"Listar establecimientos: {r_est_list.status_code}, total encontrados: {len(r_est_list.json())}")
assert any(e["id"] == est_id for e in r_est_list.json()), "El establecimiento creado no se encuentra en el listado"

# 4. Test Purchases in Hania & Factos
print("\n--- 3. REGISTRO Y GESTIÓN DE COMPRAS EN HANIA Y FACTOS ---")
purchase_payload = {
    "company_id": 1,
    "supplier_doc_type": "6",
    "supplier_doc_number": "20456789123",
    "supplier_name": "PROVEEDOR MINERO DEL SUR S.A.C.",
    "type_code": "01",
    "series": "F001",
    "correlative": "00008899",
    "issue_date": "2026-10-15",
    "currency": "PEN",
    "taxable_base": 5000.00,
    "igv": 900.00,
    "other_taxes": 0.00,
    "total": 5900.00,
    "observations": "Compra de insumos químicos para procesamiento"
}
r_purch = client.post(f"{HANIA_URL}/api/purchases", json=purchase_payload, headers=headers)
print(f"Crear compra en Hania: {r_purch.status_code}")
assert r_purch.status_code in [200, 201], f"Fallo al registrar compra: {r_purch.text}"
purch_id = r_purch.json().get("id")

# Export TXT SIRE
r_txt = client.get(f"{HANIA_URL}/api/purchases/export-txt?company_id=1&period=202610", headers=headers)
print(f"Exportar compras TXT SIRE: {r_txt.status_code}")
assert r_txt.status_code == 200, f"Fallo al exportar TXT: {r_txt.text}"
assert "20456789123" in r_txt.text, "El RUC del proveedor debe figurar en el reporte SIRE"

# 5. Emit Advance Invoice via Hania
print("\n--- 4. EMISIÓN DE ANTICIPO EN HANIA & FACTOS ---")
advance_doc_payload = {
    "company_id": 1,
    "type_code": "01",
    "series": "F001",
    "issue_date": "2026-10-15",
    "currency": "PEN",
    "is_advance": True,
    "client": {
        "doc_type": "6",
        "doc_number": "20601234567",
        "name": "MINERA AURIFERA DEL SUR S.A.C.",
        "address": "Av. Las Minas 456, Arequipa",
        "email": "contacto@mineraurifera.pe"
    },
    "items": [
        {
            "internal_code": "ANT-OP-01",
            "description": "ANTICIPO POR COMPRA DE CONCENTRADO DE MINERAL",
            "unit_code": "NIU",
            "quantity": 1.0,
            "unit_value": 5000.0,
            "unit_price": 5900.0,
            "igv_type": "10",
            "igv_amount": 900.0,
            "total": 5900.0
        }
    ],
    "observations": "" # Deberá autocompletarse con el formato BBVA DOLARES...
}

r_adv_doc = client.post(f"{HANIA_URL}/api/documents", json=advance_doc_payload, headers=headers)
print(f"Emitir factura anticipo: {r_adv_doc.status_code}")
assert r_adv_doc.status_code in [200, 201, 202], f"Error al emitir anticipo: {r_adv_doc.text}"
adv_doc_data = r_adv_doc.json()
adv_doc_id = adv_doc_data.get("id")
adv_series_num = f"{adv_doc_data.get('series')}-{adv_doc_data.get('correlative') or adv_doc_data.get('number')}"
print(f"Anticipo emitido con éxito ID={adv_doc_id}, Comprobante={adv_series_num}")

# Check observations auto-populated
assert "DOLARES:BANCO BBVA" in adv_doc_data.get("observations", ""), "Observaciones BBVA no se autocompletaron"
print("✓ Observaciones autocompletadas correctamente con formato BBVA")

# Check product auto-creation for uncataloged item
r_prod_check = client.get(f"{HANIA_URL}/api/products?query=ANTICIPO", headers=headers)
print(f"Productos autoguardados encontrados: {len(r_prod_check.json())}")
assert any("ANTICIPO POR COMPRA" in (p.get("description") or p.get("name", "")) for p in r_prod_check.json()), "El producto no se guardó automáticamente en el catálogo"
print("✓ Producto no registrado guardado automáticamente en el catálogo de productos")

# 6. Verify Available Advances in Hania
print("\n--- 5. CONSULTA DE ANTICIPOS DISPONIBLES EN HANIA ---")
r_avail = client.get(f"{HANIA_URL}/api/documents/advances/available?company_id=1&client_doc_number=20601234567", headers=headers)
print(f"Anticipos disponibles para el cliente: {r_avail.status_code}")
assert r_avail.status_code == 200, f"Error al consultar anticipos: {r_avail.text}"
avail_advances = r_avail.json()
print(f"Total anticipos disponibles: {len(avail_advances)}")
matching_adv = next((a for a in avail_advances if a["id"] == adv_doc_id), None)
assert matching_adv is not None, "El anticipo recién emitido debe figurar en la lista de disponibles"
assert float(matching_adv["balance"]) == 5900.0, f"El saldo inicial debe ser 5900.0, recibido: {matching_adv['balance']}"
print(f"✓ Anticipo identificado con saldo disponible de S/ {matching_adv['balance']}")

# 7. Issue Regular Invoice Deducting the Advance
print("\n--- 6. DEDUCCIÓN DE ANTICIPO EN FACTURA POSTERIOR ---")
deduct_amount = 2500.00
inv_deduct_payload = {
    "company_id": 1,
    "type_code": "01",
    "series": "F001",
    "issue_date": "2026-10-15",
    "currency": "PEN",
    "client": {
        "doc_type": "6",
        "doc_number": "20601234567",
        "name": "MINERA AURIFERA DEL SUR S.A.C.",
        "address": "Av. Las Minas 456, Arequipa",
        "email": "contacto@mineraurifera.pe"
    },
    "items": [
        {
            "internal_code": "MIN-CU-01",
            "description": "CONCENTRADO DE COBRE Y PLATA LOTE 2026-A",
            "unit_code": "TNE",
            "quantity": 2.0,
            "unit_value": 4000.0,
            "unit_price": 4720.0,
            "igv_type": "10",
            "igv_amount": 1440.0,
            "total": 9440.0
        }
    ],
    "applied_advances": [
        {
            "advance_document_id": adv_doc_id,
            "type_code": "01",
            "series": adv_doc_data.get('series'),
            "correlative": adv_doc_data.get('correlative'),
            "amount": deduct_amount,
            "description": "Deducción de anticipo F001"
        }
    ],
    "observations": "Liquidación final con deducción de anticipo"
}

r_inv_deduct = client.post(f"{HANIA_URL}/api/documents", json=inv_deduct_payload, headers=headers)
print(f"Emitir factura con deducción: {r_inv_deduct.status_code}")
assert r_inv_deduct.status_code in [200, 201, 202], f"Error al emitir con deducción: {r_inv_deduct.text}"
inv_deduct_data = r_inv_deduct.json()
print(f"Factura con deducción emitida con éxito ID={inv_deduct_data.get('id')}")

# Verify updated advance balance
r_avail_after = client.get(f"{HANIA_URL}/api/documents/advances/available?company_id=1&client_doc_number=20601234567", headers=headers)
avail_advances_after = r_avail_after.json()
matching_adv_after = next((a for a in avail_advances_after if a["id"] == adv_doc_id), None)
expected_balance = 5900.00 - deduct_amount
print(f"Saldo restante esperado: {expected_balance}, Saldo obtenido: {matching_adv_after['balance']}")
assert abs(float(matching_adv_after["balance"]) - expected_balance) < 0.01, "El saldo del anticipo no se decrementó correctamente"
print("✓ Saldo del anticipo actualizado correctamente tras la deducción")

# 8. Test Dynamic PDF Rendering from Factos via UUID and MD5
print("\n--- 7. RENDERIZACIÓN DINÁMICA DE PDF EN FACTOS (UUID & MD5) ---")
factos_pdf_url = inv_deduct_data.get("pdf_url")
print(f"PDF URL devuelto por la API: {factos_pdf_url}")
assert factos_pdf_url, "No se devolvió enlace de previsualización inmediata de PDF"

r_pdf = client.get(factos_pdf_url)
print(f"Descarga PDF inmediata: {r_pdf.status_code}, tamaño={len(r_pdf.content)} bytes")
assert r_pdf.status_code == 200, "Fallo al obtener PDF de comprobante"
assert r_pdf.content[:4] == b"%PDF", "El contenido devuelto no es un archivo PDF válido"
print("✓ PDF generado al vuelo en memoria exitosamente (Magic bytes %PDF confirmados)")

factos_doc_id = factos_pdf_url.split("/documents/")[1].split("/pdf")[0]
md5_id = hashlib.md5(factos_doc_id.encode('utf-8')).hexdigest()
md5_pdf_url = f"{FACTOS_URL}/api/v1/documents/{md5_id}/pdf"
r_md5_pdf = client.get(md5_pdf_url)
print(f"Descarga PDF vía MD5 ({md5_id}): {r_md5_pdf.status_code}, tamaño={len(r_md5_pdf.content)} bytes")
assert r_md5_pdf.status_code == 200, "Fallo al obtener PDF vía MD5"
assert r_md5_pdf.content[:4] == b"%PDF", "El contenido vía MD5 no es un PDF válido"
print("✓ PDF obtenido correctamente utilizando MD5(id) sin depender de rutas físicas fijas")

# 9. Test Despatches (Guía de Remisión) in Hania
print("\n--- 8. EMISIÓN DE GUÍA DE REMISIÓN EN HANIA & FACTOS ---")
despatch_payload = {
    "company_id": 1,
    "series": "T001",
    "issue_date": "2026-10-15",
    "transfer_date": "2026-10-16",
    "delivery_date": "2026-10-15",
    "transport_mode": "02",
    "transfer_reason": "02",
    "total_weight": 28.50,
    "weight_unit": "TNE",
    "is_referential_weight": True,
    "vehicle_certificate": "TUCE-CERT-884920",
    "recipient": {
        "doc_type": "6",
        "doc_number": "20601234567",
        "name": "MINERA AURIFERA DEL SUR S.A.C.",
        "address": "Av Industrial 789"
    },
    "origin": {
        "ubigeo": "040301",
        "address": "Mina La Rinconada Km 12"
    },
    "destination": {
        "ubigeo": "150101",
        "address": "Planta Industrial Lima Sur"
    },
    "driver": {
        "doc_type": "1",
        "doc_number": "45678912",
        "name": "CARLOS ALBERTO PEREZ GOMEZ",
        "license": "Q45678912"
    },
    "vehicle": {
        "plate": "V4B-890",
        "certificate": "TUCE-CERT-884920"
    },
    "items": [],
    "observations": ""
}

r_desp = client.post(f"{HANIA_URL}/api/despatches", json=despatch_payload, headers=headers)
print(f"Emitir guía de remisión: {r_desp.status_code}")
assert r_desp.status_code in [200, 201, 202], f"Error al emitir guía: {r_desp.text}"
desp_data = r_desp.json()
print(f"Guía emitida con éxito ID={desp_data.get('id')}, Comprobante={desp_data.get('series')}-{desp_data.get('correlative') or desp_data.get('number')}")

# Verify default item
assert len(desp_data.get("items", [])) > 0, "No se autocompletaron los ítems por defecto"
assert "Mineral en bruto sin procesar" in desp_data["items"][0]["description"], "El ítem por defecto no es 'Mineral en bruto sin procesar'"
print("✓ Ítem por defecto 'Mineral en bruto sin procesar' asignado automáticamente")

# Verify referential weight observation
assert "EL PESO ES REFERENCIAL" in desp_data.get("observations", ""), "La observación 'EL PESO ES REFERENCIAL' no se autocompletó"
print("✓ Observación automática 'EL PESO ES REFERENCIAL' asignada correctamente")

# Verify Despatch PDF
desp_pdf_url = desp_data.get("pdf_url")
print(f"Guía PDF URL: {desp_pdf_url}")
assert desp_pdf_url, "No se devolvió enlace de PDF para la guía"
r_desp_pdf = client.get(desp_pdf_url)
print(f"Descarga PDF de Guía: {r_desp_pdf.status_code}, tamaño={len(r_desp_pdf.content)} bytes")
assert r_desp_pdf.status_code == 200, "Fallo al descargar PDF de guía"
assert r_desp_pdf.content[:4] == b"%PDF", "El contenido de la guía no es un PDF válido"
print("✓ PDF de Guía de Remisión generado dinámicamente con éxito")

print("\n==================================================")
print("¡TODAS LAS PRUEBAS DE INTEGRACIÓN PASARON CON ÉXITO!")
print("==================================================")
