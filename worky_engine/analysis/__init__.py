"""Capa de analisis de A1 sobre la sabana de A0 (ADR-004).

Expone `run_analysis`, el punto de entrada que usa el subcomando
`analyze` de la CLI. `format_report` se agrega en el PR 3, cuando
`worky_engine/analysis/report.py` existe (desviacion de la tarea 1.1,
que anticipaba ambos nombres antes de que `report.py` se escribiera).
"""

from __future__ import annotations

from worky_engine.analysis.runner import run_analysis

__all__ = ["run_analysis"]
