"""Contratos del esquema en estrella del warehouse (A4, seccion 8 del diseno).

Mismo patron que `worky_engine.quality.contracts`: cada `assert_*`
valida una sola regla sobre DataFrames ya materializados y lanza
`ContractViolation` con el nombre del contrato en el mensaje. Este PR
trae los dos contratos de `map_source_identity`; los seis de
`dim_company` y de la foto de health llegan en el PR3, sobre las
salidas que agrega su algoritmo de SCD2.
"""

from __future__ import annotations

import pandas as pd

from worky_engine.quality.contracts import ContractViolation


def assert_map_source_identity_unique(map_source_identity: pd.DataFrame) -> None:
    """El par `source_system`/`source_id` no se repite en `map_source_identity`.

    La seccion 8 del diseno tambien exige que todo `master_id` exista
    en `dim_company`; esa mitad del contrato se agrega en el PR3, sobre
    la tabla que su algoritmo de SCD2 puebla, porque en este PR
    `dim_company` todavia esta vacia.
    """
    duplicated = map_source_identity.duplicated(subset=["source_system", "source_id"])
    if duplicated.any():
        raise ContractViolation(
            f"contrato assert_map_source_identity_unique: {int(duplicated.sum())} pares "
            "source_system/source_id repetidos"
        )


def assert_overrides_are_reflected(overrides: pd.DataFrame, map_source_identity: pd.DataFrame) -> None:
    """Cada fila de `identity_overrides` aparece en `map_source_identity` con `link_source = 'override'`."""
    if overrides.empty:
        return
    override_rows = map_source_identity[map_source_identity["link_source"] == "override"]
    override_pairs = set(zip(override_rows["source_system"], override_rows["source_id"]))
    expected_pairs = set(zip(overrides["source_system"], overrides["source_id"]))
    missing = expected_pairs - override_pairs
    if missing:
        raise ContractViolation(
            f"contrato assert_overrides_are_reflected: {len(missing)} filas de identity_overrides "
            "sin reflejo en map_source_identity con link_source = 'override'"
        )


def run_warehouse_contracts(map_source_identity: pd.DataFrame, overrides: pd.DataFrame) -> None:
    """Corre los dos contratos de `map_source_identity` disponibles en este PR, en orden fijo."""
    assert_map_source_identity_unique(map_source_identity)
    assert_overrides_are_reflected(overrides, map_source_identity)
