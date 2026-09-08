"""Funciones puras de normalizacion, reutilizadas por identity_resolution y por A6.

Cada funcion es determinista, no depende de pandas ni de duckdb, y solo
usa la libreria estandar, para que el script de limpieza de A6 pueda
importar este paquete sin arrastrar el resto del motor.
"""

from __future__ import annotations

from worky_engine.normalization.currency import ConvertedAmount, to_mxn
from worky_engine.normalization.dates import normalize_date
from worky_engine.normalization.domains import domain_label
from worky_engine.normalization.names import normalize_company_name

__all__ = [
    "ConvertedAmount",
    "domain_label",
    "normalize_company_name",
    "normalize_date",
    "to_mxn",
]
