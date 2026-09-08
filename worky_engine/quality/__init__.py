"""Contratos de datos en tiempo de build, calculados sobre las salidas ya materializadas."""

from __future__ import annotations

from worky_engine.quality.contracts import ContractViolation, run_contracts

__all__ = ["ContractViolation", "run_contracts"]
