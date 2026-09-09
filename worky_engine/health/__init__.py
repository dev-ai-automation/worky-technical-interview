"""Health score de A3 (ADR-005) y su validacion medida.

Expone `run_health` (el corredor de las tres corridas) y
`format_validation` (el texto de `validation.md`) juntos, ahora que
`report.py` existe.
"""

from __future__ import annotations

from worky_engine.health.report import format_validation
from worky_engine.health.runner import HealthResult, run_health

__all__ = ["HealthResult", "format_validation", "run_health"]
