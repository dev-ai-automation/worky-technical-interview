"""Health score de A3 (ADR-005) y su validacion medida.

Expone `run_health` desde este PR; `format_validation` llega con
`report.py` en el PR 3.
"""

from __future__ import annotations

from worky_engine.health.runner import HealthResult, run_health

__all__ = ["HealthResult", "run_health"]
