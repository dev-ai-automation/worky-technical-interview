"""Normalizacion de fecha: acepta ISO y DD/MM/YYYY, segun el ADR-001.

Las tres bases de origen mezclan fechas en formato ISO (YYYY-MM-DD) con
fechas en formato DD/MM/YYYY. Esta funcion convierte ambas al mismo
formato antes de que identity_resolution compare cualquier registro,
para que una diferencia de formato nunca se lea como una diferencia
real entre dos empresas.
"""

from __future__ import annotations

import datetime
import re

_ISO_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_DMY_PATTERN = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


def normalize_date(raw: str | None) -> str | None:
    """Convierte una fecha DD/MM/YYYY a formato ISO; deja ISO sin cambios.

    Devuelve None cuando el valor no calza con ninguno de los dos
    formatos aceptados, o cuando describe una fecha calendario
    inexistente, tal como fija el requisito de normalizacion de fecha
    del ADR-001.
    """
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None

    iso_match = _ISO_PATTERN.match(value)
    if iso_match:
        year, month, day = iso_match.groups()
        return value if _is_calendar_date(year, month, day) else None

    dmy_match = _DMY_PATTERN.match(value)
    if dmy_match:
        day, month, year = dmy_match.groups()
        if not _is_calendar_date(year, month, day):
            return None
        return f"{year}-{month}-{day}"

    return None


def _is_calendar_date(year: str, month: str, day: str) -> bool:
    """Confirma que la terna de texto describe una fecha calendario real."""
    try:
        datetime.date(int(year), int(month), int(day))
    except ValueError:
        return False
    return True
