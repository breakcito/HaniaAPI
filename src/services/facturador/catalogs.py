"""Catálogos Oficiales de SUNAT para Facturación Electrónica y Guías de Remisión.

Este módulo provee la metadata estándar de SUNAT para su consumo desacoplado
por cualquier ERP, POS o sistema de facturación.
"""

from typing import Dict, List, Any

# Catálogo 01: Tipo de Documento Electrónico
DOCUMENT_TYPES: List[Dict[str, str]] = [
    {"code": "01", "name": "Factura Electrónica", "short": "Factura", "series_prefix": "F"},
    {"code": "03", "name": "Boleta de Venta Electrónica", "short": "Boleta", "series_prefix": "B"},
    {"code": "07", "name": "Nota de Crédito Electrónica", "short": "Nota Crédito", "series_prefix": "FC/BC"},
    {"code": "08", "name": "Nota de Débito Electrónica", "short": "Nota Débito", "series_prefix": "FD/BD"},
    {"code": "09", "name": "Guía de Remisión Remitente", "short": "GRE Remitente", "series_prefix": "T"},
    {"code": "31", "name": "Guía de Remisión Transportista", "short": "GRE Transportista", "series_prefix": "V"},
]

# Catálogo 06: Tipos de Documento de Identidad
IDENTITY_DOCUMENT_TYPES: List[Dict[str, Any]] = [
    {"code": "6", "name": "RUC (Registro Único de Contribuyentes)", "short": "RUC", "length": 11, "is_numeric": True},
    {"code": "1", "name": "DNI (Documento Nacional de Identidad)", "short": "DNI", "length": 8, "is_numeric": True},
    {"code": "4", "name": "Carnet de Extranjería", "short": "C.E.", "length": 12, "is_numeric": False},
    {"code": "7", "name": "Pasaporte", "short": "Pasaporte", "length": 12, "is_numeric": False},
    {"code": "0", "name": "Doc. Trib. No Domiciliado Sin RUC", "short": "Sin Doc", "length": 15, "is_numeric": False},
]

# Catálogo 07: Tipos de Afectación al IGV
IGV_TYPES: List[Dict[str, str]] = [
    {"code": "10", "name": "Gravado - Operación Onerosa", "rate": 0.18, "group": "taxable"},
    {"code": "11", "name": "Gravado - Retiro por premio", "rate": 0.18, "group": "taxable"},
    {"code": "12", "name": "Gravado - Retiro por donación", "rate": 0.18, "group": "taxable"},
    {"code": "20", "name": "Exonerado - Operación Onerosa", "rate": 0.00, "group": "exonerated"},
    {"code": "21", "name": "Exonerado - Transferencia Gratuita", "rate": 0.00, "group": "exonerated"},
    {"code": "30", "name": "Inafecto - Operación Onerosa", "rate": 0.00, "group": "unaffected"},
    {"code": "31", "name": "Inafecto - Retiro por Bonificación", "rate": 0.00, "group": "unaffected"},
    {"code": "40", "name": "Exportación de Bienes o Servicios", "rate": 0.00, "group": "exportation"},
]

# Catálogo 09: Tipos de Nota de Crédito Electrónica
CREDIT_NOTE_REASONS: List[Dict[str, str]] = [
    {"code": "01", "name": "Anulación de la operación"},
    {"code": "02", "name": "Anulación por error en el RUC"},
    {"code": "03", "name": "Corrección por error en la descripción"},
    {"code": "04", "name": "Descuento global"},
    {"code": "05", "name": "Descuento por ítem"},
    {"code": "06", "name": "Devolución total"},
    {"code": "07", "name": "Devolución por ítem"},
    {"code": "08", "name": "Bonificación"},
    {"code": "09", "name": "Disminución en el valor"},
    {"code": "10", "name": "Otros Conceptos"},
    {"code": "11", "name": "Ajustes de operaciones de exportación"},
    {"code": "13", "name": "Ajustes - montos y/o fechas de pago"},
]

# Catálogo 10: Tipos de Nota de Débito Electrónica
DEBIT_NOTE_REASONS: List[Dict[str, str]] = [
    {"code": "01", "name": "Intereses por mora"},
    {"code": "02", "name": "Aumento en el valor"},
    {"code": "03", "name": "Penalidades / otros conceptos"},
    {"code": "10", "name": "Ajustes de operaciones de exportación"},
    {"code": "11", "name": "Ajustes que afecten al IVAP"},
]

# Catálogo 17: Código de Tipo de Operación
OPERATION_TYPES: List[Dict[str, str]] = [
    {"code": "0101", "name": "Venta Interna"},
    {"code": "0102", "name": "Exportación"},
    {"code": "0103", "name": "No Domiciliados"},
    {"code": "1001", "name": "Operación Sujeta a Detracción"},
    {"code": "1002", "name": "Operación Sujeta a Detracción - Recursos Hidrobiológicos"},
    {"code": "1003", "name": "Operación Sujeta a Detracción - Servicios de Transporte"},
    {"code": "2001", "name": "Operación Sujeta a Percepción"},
]

# Catálogo 20: Motivos de Traslado para Guías de Remisión
DESPATCH_REASONS: List[Dict[str, str]] = [
    {"code": "01", "name": "Venta"},
    {"code": "02", "name": "Compra"},
    {"code": "04", "name": "Traslado entre establecimientos de la misma empresa"},
    {"code": "08", "name": "Importación"},
    {"code": "09", "name": "Exportación"},
    {"code": "13", "name": "Otros motivos de traslado"},
    {"code": "14", "name": "Venta sujeta a confirmación del comprador"},
    {"code": "18", "name": "Traslado emisor itinerante de comprobantes"},
    {"code": "19", "name": "Traslado a zona primaria"},
]

# Catálogo 54: Bienes y Servicios Sujetos a Detracción SUNAT
DETRACTION_SERVICES: List[Dict[str, Any]] = [
    {"code": "023", "name": "Recursos hidrobiológicos", "default_percent": 4.0},
    {"code": "024", "name": "Mantenimiento y reparación de bienes muebles", "default_percent": 12.0},
    {"code": "025", "name": "Minerales y carbón (Oro, carbón y demás concentrados)", "default_percent": 10.0},
    {"code": "027", "name": "Demás servicios empresariales", "default_percent": 12.0},
    {"code": "030", "name": "Contratos de construcción", "default_percent": 4.0},
    {"code": "037", "name": "Transporte de bienes por vía terrestre", "default_percent": 4.0},
    {"code": "022", "name": "Otros servicios empresariales gravados con IGV", "default_percent": 12.0},
]

# Catálogo Unidades de Medida comerciales comunes
UNITS_OF_MEASURE: List[Dict[str, str]] = [
    {"code": "TNE", "name": "Toneladas Métricas (TNE)"},
    {"code": "NIU", "name": "Unidades (NIU)"},
    {"code": "KGM", "name": "Kilogramos (KGM)"},
    {"code": "ZZ", "name": "Servicio / Unidad de Servicio (ZZ)"},
    {"code": "LTR", "name": "Litros (LTR)"},
    {"code": "MTR", "name": "Metros (MTR)"},
    {"code": "GLI", "name": "Galones (GLI)"},
    {"code": "BX", "name": "Cajas (BX)"},
    {"code": "BG", "name": "Bolsas / Sacos (BG)"},
]

def get_all_sunat_catalogs() -> Dict[str, Any]:
    """Retorna un diccionario consolidado con todos los catálogos normativos SUNAT."""
    return {
        "document_types": DOCUMENT_TYPES,
        "identity_document_types": IDENTITY_DOCUMENT_TYPES,
        "igv_types": IGV_TYPES,
        "credit_note_reasons": CREDIT_NOTE_REASONS,
        "debit_note_reasons": DEBIT_NOTE_REASONS,
        "operation_types": OPERATION_TYPES,
        "despatch_reasons": DESPATCH_REASONS,
        "detraction_services": DETRACTION_SERVICES,
        "units_of_measure": UNITS_OF_MEASURE,
    }
