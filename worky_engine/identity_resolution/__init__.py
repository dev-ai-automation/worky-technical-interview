"""Resolucion de identidad entre HubSpot, Product DB y Vitally (ADR-001).

Expone el punto de entrada `resolve_identity` y `compute_dataset_asof`,
que los PR siguientes tambien reutilizan para la marca de tiempo de sus
propias salidas.
"""

from __future__ import annotations

from worky_engine.identity_resolution.cascade import compute_dataset_asof, resolve_identity

__all__ = ["compute_dataset_asof", "resolve_identity"]
