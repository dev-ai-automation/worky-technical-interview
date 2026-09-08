"""Harness de backtest de tendencia de uso, ADR-003 (spec `trend-backtest-harness`).

Expone `run_backtest` y `format_report`, el punto de entrada que usa el
comando `backtest` de la CLI.
"""

from __future__ import annotations

from worky_engine.harness.backtest import (
    DEFAULT_FLAG_RATE,
    DEFAULT_K_VALUES,
    FORMULA_LABELS,
    format_report,
    run_backtest,
)

__all__ = [
    "DEFAULT_FLAG_RATE",
    "DEFAULT_K_VALUES",
    "FORMULA_LABELS",
    "format_report",
    "run_backtest",
]
