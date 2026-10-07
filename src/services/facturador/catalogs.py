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
    {"code": "001", "name": "Azúcar y melaza de caña", "description": "Azúcar y melaza de caña", "percent": 10.0, "default_percent": 10.0},
    {"code": "002", "name": "Arroz", "description": "Arroz", "percent": 4.0, "default_percent": 4.0},
    {"code": "003", "name": "Alcohol etílico", "description": "Alcohol etílico", "percent": 10.0, "default_percent": 10.0},
    {"code": "004", "name": "Recursos hidrobiológicos", "description": "Recursos hidrobiológicos", "percent": 4.0, "default_percent": 4.0},
    {"code": "005", "name": "Maíz amarillo duro", "description": "Maíz amarillo duro", "percent": 4.0, "default_percent": 4.0},
    {"code": "007", "name": "Caña de azúcar", "description": "Caña de azúcar", "percent": 10.0, "default_percent": 10.0},
    {"code": "008", "name": "Madera", "description": "Madera", "percent": 4.0, "default_percent": 4.0},
    {"code": "009", "name": "Arena y piedra", "description": "Arena y piedra", "percent": 10.0, "default_percent": 10.0},
    {"code": "010", "name": "Residuos, subproductos, desechos, recortes y desperdicios", "description": "Residuos, subproductos, desechos, recortes y desperdicios", "percent": 15.0, "default_percent": 15.0},
    {"code": "011", "name": "Bienes del inciso A) del Apéndice I de la Ley del IGV", "description": "Bienes del inciso A) del Apéndice I de la Ley del IGV", "percent": 1.5, "default_percent": 1.5},
    {"code": "012", "name": "Intermediación laboral y tercerización", "description": "Intermediación laboral y tercerización", "percent": 12.0, "default_percent": 12.0},
    {"code": "013", "name": "Animales vivos", "description": "Animales vivos", "percent": 10.0, "default_percent": 10.0},
    {"code": "014", "name": "Carnes y despojos comestibles", "description": "Carnes y despojos comestibles", "percent": 4.0, "default_percent": 4.0},
    {"code": "017", "name": "Harina, polvo y 'pellets' de pescado", "description": "Harina, polvo y 'pellets' de pescado", "percent": 4.0, "default_percent": 4.0},
    {"code": "019", "name": "Arrendamiento de bienes muebles", "description": "Arrendamiento de bienes muebles", "percent": 10.0, "default_percent": 10.0},
    {"code": "020", "name": "Mantenimiento y reparación de bienes muebles", "description": "Mantenimiento y reparación de bienes muebles", "percent": 12.0, "default_percent": 12.0},
    {"code": "021", "name": "Movimiento de carga", "description": "Movimiento de carga", "percent": 10.0, "default_percent": 10.0},
    {"code": "022", "name": "Otros servicios empresariales gravados con IGV", "description": "Otros servicios empresariales gravados con IGV", "percent": 12.0, "default_percent": 12.0},
    {"code": "023", "name": "Leche", "description": "Leche", "percent": 4.0, "default_percent": 4.0},
    {"code": "024", "name": "Comisiones mercantiles", "description": "Comisiones mercantiles", "percent": 10.0, "default_percent": 10.0},
    {"code": "025", "name": "Fabricación de bienes por encargo", "description": "Fabricación de bienes por encargo", "percent": 10.0, "default_percent": 10.0},
    {"code": "026", "name": "Servicio de transporte de personas", "description": "Servicio de transporte de personas", "percent": 10.0, "default_percent": 10.0},
    {"code": "027", "name": "Servicio de transporte de carga y/o mercancías", "description": "Servicio de transporte de carga y/o mercancías", "percent": 4.0, "default_percent": 4.0},
    {"code": "030", "name": "Contratos de construcción", "description": "Contratos de construcción", "percent": 4.0, "default_percent": 4.0},
    {"code": "031", "name": "Oro gravado con el IGV", "description": "Oro gravado con el IGV", "percent": 10.0, "default_percent": 10.0},
    {"code": "032", "name": "Páprika y otros frutos de los géneros capsicum o pimienta", "description": "Páprika y otros frutos de los géneros capsicum o pimienta", "percent": 10.0, "default_percent": 10.0},
    {"code": "034", "name": "Minerales metálicos no auríferos", "description": "Minerales metálicos no auríferos", "percent": 10.0, "default_percent": 10.0},
    {"code": "035", "name": "Bienes exonerados del IGV", "description": "Bienes exonerados del IGV", "percent": 1.5, "default_percent": 1.5},
    {"code": "036", "name": "Oro y demás minerales metálicos exonerados del IGV", "description": "Oro y demás minerales metálicos exonerados del IGV", "percent": 1.5, "default_percent": 1.5},
    {"code": "037", "name": "Demás servicios gravados con el IGV", "description": "Demás servicios gravados con el IGV", "percent": 12.0, "default_percent": 12.0},
    {"code": "039", "name": "Minerales no metálicos (Carbón y derivados)", "description": "Minerales no metálicos (Carbón y derivados)", "percent": 10.0, "default_percent": 10.0},
    {"code": "040", "name": "Bien inmueble gravado con IGV", "description": "Bien inmueble gravado con IGV", "percent": 4.0, "default_percent": 4.0},
    {"code": "041", "name": "Plomo", "description": "Plomo", "percent": 15.0, "default_percent": 15.0},
]

# Catálogo 03: Códigos de Unidades de Medida SUNAT
UNITS_OF_MEASURE: List[Dict[str, str]] = [
    {"code": "NIU", "name": "Unidades (NIU)"},
    {"code": "ZZ", "name": "Servicio / Unidad de Servicio (ZZ)"},
    {"code": "KGM", "name": "Kilogramos (KGM)"},
    {"code": "TNE", "name": "Toneladas Métricas (TNE)"},
    {"code": "LTR", "name": "Litros (LTR)"},
    {"code": "MTR", "name": "Metros (MTR)"},
    {"code": "GLI", "name": "Galones Ingleses (GLI)"},
    {"code": "GLL", "name": "Galones US (GLL)"},
    {"code": "BX", "name": "Cajas (BX)"},
    {"code": "BG", "name": "Bolsas / Sacos (BG)"},
    {"code": "PK", "name": "Paquetes (PK)"},
    {"code": "BJ", "name": "Baldes (BJ)"},
    {"code": "BLL", "name": "Barriles (BLL)"},
    {"code": "BO", "name": "Botellas (BO)"},
    {"code": "CA", "name": "Latas (CA)"},
    {"code": "CJ", "name": "Conos (CJ)"},
    {"code": "CL", "name": "Bobinas (CL)"},
    {"code": "CMK", "name": "Centímetros Cuadrados (CMK)"},
    {"code": "CMQ", "name": "Centímetros Cúbicos (CMQ)"},
    {"code": "CMT", "name": "Centímetros Lineales (CMT)"},
    {"code": "CY", "name": "Cilindros (CY)"},
    {"code": "DZN", "name": "Docenas (DZN)"},
    {"code": "FOT", "name": "Pies (FOT)"},
    {"code": "FTK", "name": "Pies Cuadrados (FTK)"},
    {"code": "FTQ", "name": "Pies Cúbicos (FTQ)"},
    {"code": "GRM", "name": "Gramos (GRM)"},
    {"code": "HLT", "name": "Hectolitros (HLT)"},
    {"code": "INH", "name": "Pulgadas (INH)"},
    {"code": "INK", "name": "Pulgadas Cuadradas (INK)"},
    {"code": "INQ", "name": "Pulgadas Cúbicas (INQ)"},
    {"code": "KMT", "name": "Kilómetros (KMT)"},
    {"code": "KWH", "name": "Kilovatios Hora (KWH)"},
    {"code": "LBR", "name": "Libras (LBR)"},
    {"code": "LEF", "name": "Hojas (LEF)"},
    {"code": "MIL", "name": "Millares (MIL)"},
    {"code": "MMK", "name": "Milímetros Cuadrados (MMK)"},
    {"code": "MMQ", "name": "Milímetros Cúbicos (MMQ)"},
    {"code": "MMT", "name": "Milímetros (MMT)"},
    {"code": "MTK", "name": "Metros Cuadrados (MTK)"},
    {"code": "MTQ", "name": "Metros Cúbicos (MTQ)"},
    {"code": "ONZ", "name": "Onzas (ONZ)"},
    {"code": "PF", "name": "Paletas / Pallets (PF)"},
    {"code": "PR", "name": "Pares (PR)"},
    {"code": "RO", "name": "Rollos (RO)"},
    {"code": "SET", "name": "Juegos / Sets (SET)"},
    {"code": "TU", "name": "Tubos (TU)"},
    {"code": "UM", "name": "Millón de Unidades (UM)"},
    {"code": "YRD", "name": "Yardas (YRD)"},
    {"code": "YDK", "name": "Yardas Cuadradas (YDK)"},
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
