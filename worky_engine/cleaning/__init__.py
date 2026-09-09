"""Paquete de limpieza automatica de companies.csv (A6, ADR-002).

Concentra la deteccion, la normalizacion y el armado de la bitacora
como funciones puras que importan `normalize_date` y `to_mxn` sin
modificarlos (D1). `cli.cmd_clean` es el unico llamador: este paquete
no importa `worky_engine.quality`, `duckdb` ni `identity_resolution`.
"""

from __future__ import annotations

from worky_engine.cleaning.runner import CleanResult, format_cleaning_log, run_clean

__all__ = ["CleanResult", "format_cleaning_log", "run_clean"]
