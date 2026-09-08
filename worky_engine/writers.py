"""Escritura determinista de CSV y Markdown para las salidas del motor.

Fija el formato exacto que exige la seccion 7 del diseno: UTF-8 sin
marca de orden de bytes, salto de linea `\\n`, sin columna de indice y
nulo escrito como campo vacio, para que dos corridas sobre la misma
entrada produzcan archivos identicos byte a byte.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


def write_csv(frame: pd.DataFrame, path: str | Path) -> None:
    """Escribe `frame` como CSV determinista en `path`.

    Abre el archivo con `encoding="utf-8"` y `newline=""` de forma
    explicita para que pandas nunca traduzca el salto de linea, y para
    que un caracter acentuado se conserve igual que en el origen.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as handle:
        frame.to_csv(handle, lineterminator="\n", index=False, na_rep="")


def write_markdown(content: str, path: str | Path) -> None:
    """Escribe `content` como documento Markdown en `path`, con salto `\\n`.

    Se usa para `coverage_report.md`, cuyo texto ya viene formateado por
    `worky_engine.quality.coverage`.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_content = content.replace("\r\n", "\n")
    with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(normalized_content)


def _is_missing(value: float | None) -> bool:
    """Un valor cuenta como nulo si es None o NaN (asi llega un nulo desde pandas)."""
    return value is None or (isinstance(value, float) and math.isnan(value))


def format_money(value: float | None) -> str:
    """Formatea un monto con dos decimales fijos; cadena vacia cuando es nulo o NaN."""
    return "" if _is_missing(value) else f"{value:.2f}"


def format_ratio(value: float | None) -> str:
    """Formatea una razon con seis decimales fijos; cadena vacia cuando es nula o NaN."""
    return "" if _is_missing(value) else f"{value:.6f}"
