"""Etiqueta de dominio registrable, segun la seccion 3.1 del diseno.

Reduce cualquier variante de un mismo dominio (con o sin subdominio, con
o sin sufijo de pais) a una sola etiqueta comparable. La regla es propia
del proyecto y no usa la Public Suffix List, porque los datos traen
acentos dentro del hostname (`gaitan115.com.mx`) que no son una etiqueta
DNS valida, y una dependencia externa resolveria un problema que estos
datos no tienen (decision D10 del diseno).
"""

from __future__ import annotations

import unicodedata

_KNOWN_SUBDOMAINS = {"www", "app", "mail", "portal"}
_GENERIC_SUFFIXES = {"com", "org", "net", "gob", "edu"}


def domain_label(raw: str | None) -> str | None:
    """Reduce un dominio a su etiqueta registrable, sin acentos ni subdominios.

    `app.cordero501.com.mx` y `cordero501.mx` producen ambos `cordero501`.
    Devuelve None cuando el valor de entrada esta vacio.
    """
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None

    value = value.lower()
    value = _strip_accents(value)
    value = _strip_scheme_and_path(value)

    labels = [label for label in value.split(".") if label]
    if not labels:
        return None

    while labels and labels[0] in _KNOWN_SUBDOMAINS:
        labels.pop(0)

    if len(labels) > 1:
        labels.pop()  # el sufijo de pais o de tipo de sitio, por ejemplo "mx"

    if len(labels) > 1 and labels[-1] in _GENERIC_SUFFIXES:
        labels.pop()

    return ".".join(labels) if labels else None


def _strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _strip_scheme_and_path(value: str) -> str:
    if "//" in value:
        value = value.split("//", 1)[1]
    return value.split("/", 1)[0]
