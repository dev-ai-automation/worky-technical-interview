"""Envoltorios de RapidFuzz para los tres puntajes de similitud del ADR-001.

Las tres funciones reciben nombres ya normalizados por
`worky_engine.normalization.normalize_company_name`: `token_set_ratio`
para T1 y para el veto, `partial_ratio` para T2, y `weighted_ratio`
(WRatio) para T3 y para la prueba de calibracion.
"""

from __future__ import annotations

from rapidfuzz import fuzz


def token_set_ratio(name_a: str, name_b: str) -> float:
    """Similitud insensible al orden de las palabras, usada por T1 y por el veto."""
    return fuzz.token_set_ratio(name_a, name_b)


def partial_ratio(name_a: str, name_b: str) -> float:
    """Similitud por subcadena, usada por T2; resuelve un nombre truncado contra el completo."""
    return fuzz.partial_ratio(name_a, name_b)


def weighted_ratio(name_a: str, name_b: str) -> float:
    """Similitud general ponderada (WRatio), usada por T3 y por la prueba de calibracion."""
    return fuzz.WRatio(name_a, name_b)
