"""Contratos de datos en tiempo de build, calculados sobre las salidas ya materializadas."""

from __future__ import annotations

from worky_engine.quality.contracts import ContractViolation, run_contracts
from worky_engine.quality.coverage import generate_coverage_report

__all__ = ["ContractViolation", "run_contracts", "generate_coverage_report"]
