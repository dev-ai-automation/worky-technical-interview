"""Contratos del esquema en estrella del warehouse (A4, seccion 8 del diseno).

Mismo patron que `worky_engine.quality.contracts`: cada `assert_*`
valida una sola regla sobre DataFrames ya materializados y lanza
`ContractViolation` con el nombre del contrato en el mensaje. Este PR
agrega los seis contratos de `dim_company` y de la foto de health, y
extiende `assert_map_source_identity_unique` con la mitad que dependia
de `dim_company`, ya poblada por el algoritmo de SCD2 de este PR.
"""

from __future__ import annotations

import pandas as pd

from worky_engine.quality.contracts import ContractViolation


def assert_dim_company_one_current_per_master(dim_company: pd.DataFrame) -> None:
    """Exactamente una fila con `is_current = True` por `master_id`."""
    current_counts = dim_company[dim_company["is_current"]].groupby("master_id").size()
    zero_current = set(dim_company["master_id"]) - set(current_counts.index)
    more_than_one = current_counts[current_counts > 1]
    if zero_current or not more_than_one.empty:
        raise ContractViolation(
            "contrato assert_dim_company_one_current_per_master: "
            f"{len(zero_current)} master_id sin fila vigente, {len(more_than_one)} con mas de una"
        )


def assert_dim_company_sk_unique(dim_company: pd.DataFrame) -> None:
    """`company_sk` nunca se repite en `dim_company`."""
    duplicated = dim_company.duplicated(subset=["company_sk"])
    if duplicated.any():
        raise ContractViolation(
            f"contrato assert_dim_company_sk_unique: {int(duplicated.sum())} company_sk repetidos"
        )


def assert_dim_company_bands_are_contiguous(dim_company: pd.DataFrame) -> None:
    """Por empresa, ordenadas por `effective_from`, `effective_to` de una banda iguala el `effective_from`
    de la siguiente, y solo la ultima banda queda abierta (`effective_to` vacio)."""
    offenders: set[str] = set()
    for master_id, group in dim_company.sort_values("effective_from").groupby("master_id"):
        rows = group.reset_index(drop=True)
        for position in range(len(rows) - 1):
            closes_at = rows.loc[position, "effective_to"]
            opens_at = rows.loc[position + 1, "effective_from"]
            if pd.isna(closes_at) or closes_at != opens_at:
                offenders.add(str(master_id))
        if not pd.isna(rows.loc[len(rows) - 1, "effective_to"]):
            offenders.add(str(master_id))
    if offenders:
        raise ContractViolation(
            f"contrato assert_dim_company_bands_are_contiguous: {len(offenders)} empresas con bandas no contiguas"
        )


def assert_dim_company_tracked_attributes_change(dim_company: pd.DataFrame) -> None:
    """Dos bandas consecutivas de la misma empresa difieren en `plan` o en `csm_owner`."""
    offenders: set[str] = set()
    for master_id, group in dim_company.sort_values("effective_from").groupby("master_id"):
        rows = group.reset_index(drop=True)
        for position in range(len(rows) - 1):
            same_plan = rows.loc[position, "plan"] == rows.loc[position + 1, "plan"]
            same_csm = rows.loc[position, "csm_owner"] == rows.loc[position + 1, "csm_owner"]
            if same_plan and same_csm:
                offenders.add(str(master_id))
    if offenders:
        raise ContractViolation(
            "contrato assert_dim_company_tracked_attributes_change: "
            f"{len(offenders)} empresas con bandas consecutivas sin cambio en plan ni csm_owner"
        )


def assert_map_source_identity_unique(map_source_identity: pd.DataFrame, dim_company: pd.DataFrame) -> None:
    """El par `source_system`/`source_id` no se repite, y todo `master_id` existe en `dim_company`."""
    duplicated = map_source_identity.duplicated(subset=["source_system", "source_id"])
    if duplicated.any():
        raise ContractViolation(
            f"contrato assert_map_source_identity_unique: {int(duplicated.sum())} pares "
            "source_system/source_id repetidos"
        )
    known_master_ids = set(dim_company["master_id"])
    missing_master_ids = set(map_source_identity["master_id"]) - known_master_ids
    if missing_master_ids:
        raise ContractViolation(
            f"contrato assert_map_source_identity_unique: {len(missing_master_ids)} master_id de "
            "map_source_identity sin fila en dim_company"
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


def assert_health_snapshot_unique(fact_health_score_monthly: pd.DataFrame) -> None:
    """El par `master_id` y `run_date` no se repite en `fact_health_score_monthly`."""
    duplicated = fact_health_score_monthly.duplicated(subset=["master_id", "run_date"])
    if duplicated.any():
        raise ContractViolation(
            f"contrato assert_health_snapshot_unique: {int(duplicated.sum())} pares master_id/run_date repetidos"
        )


def assert_warehouse_row_order(dim_company: pd.DataFrame, map_source_identity: pd.DataFrame) -> None:
    """`dim_company` sale ordenado por `master_id` y `effective_from`; `map_source_identity`, por
    `source_system` y `source_id` (seccion 7 del diseno)."""
    expected_dim_company = dim_company.sort_values(
        ["master_id", "effective_from"], kind="mergesort"
    ).reset_index(drop=True)
    if not dim_company.reset_index(drop=True).equals(expected_dim_company):
        raise ContractViolation(
            "contrato assert_warehouse_row_order: dim_company no esta ordenado por master_id y effective_from"
        )
    expected_map_source_identity = map_source_identity.sort_values(
        ["source_system", "source_id"], kind="mergesort"
    ).reset_index(drop=True)
    if not map_source_identity.reset_index(drop=True).equals(expected_map_source_identity):
        raise ContractViolation(
            "contrato assert_warehouse_row_order: map_source_identity no esta ordenado por source_system y source_id"
        )


def run_warehouse_contracts(
    map_source_identity: pd.DataFrame,
    overrides: pd.DataFrame,
    dim_company: pd.DataFrame,
    fact_health_score_monthly: pd.DataFrame,
) -> None:
    """Corre los ocho contratos del esquema en estrella, en el orden de la seccion 8 del diseno."""
    assert_dim_company_one_current_per_master(dim_company)
    assert_dim_company_sk_unique(dim_company)
    assert_dim_company_bands_are_contiguous(dim_company)
    assert_dim_company_tracked_attributes_change(dim_company)
    assert_map_source_identity_unique(map_source_identity, dim_company)
    assert_overrides_are_reflected(overrides, map_source_identity)
    assert_health_snapshot_unique(fact_health_score_monthly)
    assert_warehouse_row_order(dim_company, map_source_identity)
