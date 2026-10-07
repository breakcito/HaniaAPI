from fastapi import APIRouter
from src.services.facturador.catalogs import (
    DOCUMENT_TYPES,
    IDENTITY_DOCUMENT_TYPES,
    IGV_TYPES,
    CREDIT_NOTE_REASONS,
    DEBIT_NOTE_REASONS,
    OPERATION_TYPES,
    DESPATCH_REASONS,
    DETRACTION_SERVICES,
    UNITS_OF_MEASURE,
)

router = APIRouter(prefix="/catalogs", tags=["Catálogos SUNAT"])

@router.get("/sunat")
def get_all_sunat_catalogs():
    """Devuelve todos los catálogos normativos oficiales de SUNAT para emisión y validación electrónica."""
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

@router.get("/document-types")
def get_document_types():
    return DOCUMENT_TYPES

@router.get("/credit-note-reasons")
def get_credit_note_reasons():
    return CREDIT_NOTE_REASONS

@router.get("/debit-note-reasons")
def get_debit_note_reasons():
    return DEBIT_NOTE_REASONS

@router.get("/detraction-services")
def get_detraction_services():
    return DETRACTION_SERVICES
