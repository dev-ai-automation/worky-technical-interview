"""Harness de backtest de tendencia de uso, ADR-003 (spec `trend-backtest-harness`).

Expone `run_backtest`, `format_report`, y `auc` (alias de `_auc`, D4 del diseno de A3).
"""

from __future__ import annotations

from worky_engine.harness.backtest import (
    DEFAULT_FLAG_RATE,
    DEFAULT_K_VALUES,
    FORMULA_LABELS,
    auc,
    format_report,
    run_backtest,
)

__all__ = [
    "DEFAULT_FLAG_RATE",
    "DEFAULT_K_VALUES",
    "FORMULA_LABELS",
    "auc",
    "format_report",
    "run_backtest",
]
