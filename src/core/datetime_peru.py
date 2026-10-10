"""Utilidades de fecha y hora para Perú (America/Lima, UTC-5)."""

from datetime import datetime, date
import zoneinfo

PERU_TZ = zoneinfo.ZoneInfo("America/Lima")


def now_peru() -> datetime:
    """Devuelve la fecha y hora actual en la zona horaria de Perú sin offset timezone (naive),

    ideal para persistir directamente en columnas MySQL DATETIME sin conversiones UTC.
    """
    return datetime.now(PERU_TZ).replace(tzinfo=None)


def today_peru() -> date:
    """Devuelve la fecha actual en Perú."""
    return datetime.now(PERU_TZ).date()
