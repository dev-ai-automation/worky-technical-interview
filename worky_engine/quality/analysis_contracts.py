"""Contratos de las salidas de analisis de A1 disponibles en este PR.

Mismo patron que `worky_engine.quality.contracts`: cada `assert_*`
valida una sola regla, sobre DataFrames ya materializados, y lanza
`ContractViolation` con el nombre del contrato en el mensaje. Los
numeros reales del ADR-004 (89, 35, 667251.00) no viven aqui (decision
D12 del diseno): se fijan en las pruebas marcadas `dataset`.
`run_analysis_contracts` los corre en orden fijo; `cmd_analyze` decide
el codigo de salida del proceso (1 para un contrato violado).
"""

from __future__ import annotations

import pandas as pd

from worky_engine.quality.contracts import ContractViolation


def assert_a1_01_total_row_matches_segments(active_mrr: pd.DataFrame) -> None:
    """La fila `row_type = 'total'` iguala la suma de las filas de segmento."""
    total = active_mrr.loc[active_mrr["row_type"] == "total"].iloc[0]
    segments = active_mrr.loc[active_mrr["row_type"] == "segment"]
    for column in ("mrr_crm_mxn", "mrr_total_mxn"):
        expected = round(segments[column].astype(float).sum(), 2)
        actual = round(float(total[column]), 2)
        if expected != actual:
            raise ContractViolation(
                f"contrato a1_01_total_row_matches_segments: '{column}' de TOTAL ({actual}) "
                f"no iguala la suma de segmentos ({expected})"
            )
    for column in ("companies_active", "companies_imputed", "companies_unresolved"):
        if int(total[column]) != int(segments[column].sum()):
            raise ContractViolation(
                f"contrato a1_01_total_row_matches_segments: '{column}' de TOTAL no iguala la suma de segmentos"
            )


def assert_a1_01_crm_within_total(active_mrr: pd.DataFrame) -> None:
    """En toda fila, el MRR del CRM nunca supera el MRR total con imputados."""
    crm = active_mrr["mrr_crm_mxn"].astype(float)
    total = active_mrr["mrr_total_mxn"].astype(float)
    if (crm > total).any():
        raise ContractViolation("contrato a1_01_crm_within_total: mrr_crm_mxn > mrr_total_mxn en alguna fila")


def assert_a1_01_total_matches_master_dataset(active_mrr: pd.DataFrame, master_dataset: pd.DataFrame) -> None:
    """El total con imputados de A1.1 iguala la suma de `mrr_mxn` de las empresas activas de la sabana."""
    total_row = active_mrr.loc[active_mrr["row_type"] == "total"].iloc[0]
    reported = round(float(total_row["mrr_total_mxn"]), 2)
    active = master_dataset.loc[master_dataset["churn_status"] == "active", "mrr_mxn"]
    expected = round(pd.to_numeric(active, errors="coerce").fillna(0).sum(), 2)
    if reported != expected:
        raise ContractViolation(
            f"contrato a1_01_total_matches_master_dataset: total de A1.1 ({reported}) "
            f"no iguala la suma de master_dataset ({expected})"
        )


def assert_a1_02_one_row_per_churned_account(usage_drop: pd.DataFrame) -> None:
    """Una fila por empresa con churn y `account_id`; ningun `master_id` repetido."""
    duplicated = usage_drop["master_id"].duplicated()
    if duplicated.any():
        raise ContractViolation(
            f"contrato a1_02_one_row_per_churned_account: {int(duplicated.sum())} master_id repetidos"
        )


def assert_a1_02_drop_matches_status(usage_drop: pd.DataFrame) -> None:
    """`drop_relative` tiene valor si y solo si `drop_status` es 'computed'."""
    is_computed = usage_drop["drop_status"] == "computed"
    has_value = usage_drop["drop_relative"].notna()
    if (is_computed != has_value).any():
        raise ContractViolation(
            "contrato a1_02_drop_matches_status: drop_relative debe tener valor "
            "unicamente cuando drop_status es 'computed'"
        )


def assert_a1_05_matches_quarantine_deals(orphan_deals: pd.DataFrame, quarantine_deals: pd.DataFrame) -> None:
    """El conjunto de `deal_id` de la consulta iguala al de `quarantine_deals` del motor."""
    sql_ids = set(orphan_deals["deal_id"])
    engine_ids = set(quarantine_deals["deal_id"])
    if sql_ids != engine_ids:
        raise ContractViolation(
            f"contrato a1_05_matches_quarantine_deals: {len(sql_ids ^ engine_ids)} deal_id "
            "no coinciden entre la consulta y quarantine_deals"
        )


def run_analysis_contracts(
    outputs: dict[str, pd.DataFrame],
    master_dataset: pd.DataFrame,
    quarantine_deals: pd.DataFrame,
) -> None:
    """Corre los contratos de las consultas de A1 disponibles en este PR, en orden fijo."""
    active_mrr = outputs["analysis_a1_01_active_mrr"]
    usage_drop = outputs["analysis_a1_02_usage_drop"]
    orphan_deals = outputs["analysis_a1_05_orphan_deals"]

    assert_a1_01_total_row_matches_segments(active_mrr)
    assert_a1_01_crm_within_total(active_mrr)
    assert_a1_01_total_matches_master_dataset(active_mrr, master_dataset)
    assert_a1_02_one_row_per_churned_account(usage_drop)
    assert_a1_02_drop_matches_status(usage_drop)
    assert_a1_05_matches_quarantine_deals(orphan_deals, quarantine_deals)
