"""Capa de analisis de A1 sobre la sabana de A0 (ADR-004).

Expone `run_analysis`, el punto de entrada que usa el subcomando
`analyze` de la CLI, y `format_report`, que arma `report.md` a partir
del `AnalysisResult` que ya produjo `run_analysis` (PR 3).
"""

from __future__ import annotations

from worky_engine.analysis.report import format_report
from worky_engine.analysis.runner import run_analysis

__all__ = ["format_report", "run_analysis"]
