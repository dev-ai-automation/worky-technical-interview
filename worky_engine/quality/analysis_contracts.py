"""Contratos de las salidas de analisis de A1 disponibles en este PR.

Mismo patron que `worky_engine.quality.contracts`: cada `assert_*`
valida una sola regla, sobre DataFrames ya materializados, y lanza
`ContractViolation` con el nombre del contrato en el mensaje. Los
numeros reales del ADR-004 (89, 35, 667251.00, y los deals atribuidos
por modelo) no viven aqui (decision D12 del diseno): se fijan en las
pruebas marcadas `dataset`. `run_analysis_contracts` los corre en orden
fijo; `cmd_analyze` decide el codigo de salida del proceso (1 para un
contrato violado).

PR 2 agrego los contratos de A1.3 (retencion por cohorte) y A1.4
(atribucion). PR 3 agrega los de A1.6 (horas negativas) y de
`analysis_exceptions`.
"""

from __future__ import annotations

import pandas as pd

from worky_engine.quality.contracts import ContractViolation

_EXCEPTIONS_LOG_COLUMNS = (
    "exception_id", "exception_code", "source_system", "source_id", "master_id",
    "field_name", "original_value", "applied_value", "evidence_ref", "ruleset_version", "decided_at",
)


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


def assert_a1_03_pct_within_range(cohort_retention: pd.DataFrame) -> None:
    """`retention_pct` tiene valor si y solo si `cell_status` es 'computed', y ese valor cae en [0, 100]."""
    is_computed = cohort_retention["cell_status"] == "computed"
    has_value = cohort_retention["retention_pct"].notna()
    if (is_computed != has_value).any():
        raise ContractViolation(
            "contrato a1_03_pct_within_range: retention_pct debe tener valor "
            "unicamente cuando cell_status es 'computed'"
        )
    computed_pct = cohort_retention.loc[is_computed, "retention_pct"].astype(float)
    if ((computed_pct < 0) | (computed_pct > 100)).any():
        raise ContractViolation("contrato a1_03_pct_within_range: retention_pct fuera de [0, 100]")


def assert_a1_03_monotone_non_increasing(cohort_retention: pd.DataFrame) -> None:
    """Dentro de una cohorte, `retained` no crece al crecer k entre las celdas calculadas."""
    computed = cohort_retention.loc[cohort_retention["cell_status"] == "computed"].sort_values(
        ["cohort_month", "k"]
    )
    for cohort_month, group in computed.groupby("cohort_month"):
        values = group["retained"].astype(int).tolist()
        if any(values[i] < values[i + 1] for i in range(len(values) - 1)):
            raise ContractViolation(
                f"contrato a1_03_monotone_non_increasing: retained sube dentro de la cohorte {cohort_month}"
            )


def assert_a1_03_retained_within_cohort_size(cohort_retention: pd.DataFrame) -> None:
    """`retained` nunca supera `cohort_size` en ninguna celda calculada."""
    computed = cohort_retention.loc[cohort_retention["cell_status"] == "computed"]
    if (computed["retained"].astype(int) > computed["cohort_size"].astype(int)).any():
        raise ContractViolation("contrato a1_03_retained_within_cohort_size: retained > cohort_size en alguna celda")


def assert_a1_04_rate_within_unit(attribution: pd.DataFrame) -> None:
    """`conversion_rate` esta en [0, 1] y `deals_won` nunca supera `deals_attributed`."""
    rate = attribution["conversion_rate"].astype(float)
    if ((rate < 0) | (rate > 1)).any():
        raise ContractViolation("contrato a1_04_rate_within_unit: conversion_rate fuera de [0, 1]")
    if (attribution["deals_won"].astype(int) > attribution["deals_attributed"].astype(int)).any():
        raise ContractViolation("contrato a1_04_rate_within_unit: deals_won > deals_attributed en alguna fila")


def assert_a1_04_models_cover_same_deals(attribution: pd.DataFrame) -> None:
    """La suma de `deals_attributed` es igual en los dos modelos de atribucion."""
    totals = attribution.groupby("model")["deals_attributed"].sum()
    if totals.nunique() != 1:
        raise ContractViolation(
            f"contrato a1_04_models_cover_same_deals: los modelos no cubren los mismos deals ({totals.to_dict()})"
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


def assert_a1_06_all_hours_negative(negative_hours: pd.DataFrame) -> None:
    """Toda fila de la vista de detalle de A1.6 trae `resolution_hours` negativo."""
    hours = negative_hours["resolution_hours"].astype(float)
    if (hours >= 0).any():
        raise ContractViolation("contrato a1_06_all_hours_negative: alguna fila trae resolution_hours >= 0")


def assert_analysis_exceptions_shape(exceptions: pd.DataFrame, negative_hours: pd.DataFrame) -> None:
    """`analysis_exceptions` trae las once columnas de `exceptions_log`, en orden, con una fila por ticket negativo."""
    if tuple(exceptions.columns) != _EXCEPTIONS_LOG_COLUMNS:
        raise ContractViolation(
            f"contrato analysis_exceptions_shape: columnas {tuple(exceptions.columns)} "
            f"no coinciden con exceptions_log {_EXCEPTIONS_LOG_COLUMNS}"
        )
    if exceptions["exception_id"].duplicated().any():
        raise ContractViolation("contrato analysis_exceptions_shape: exception_id repetido")
    if exceptions["exception_code"].nunique() > 1:
        raise ContractViolation("contrato analysis_exceptions_shape: exception_code no es constante")
    if len(exceptions) != len(negative_hours):
        raise ContractViolation(
            f"contrato analysis_exceptions_shape: {len(exceptions)} excepciones no iguala "
            f"las {len(negative_hours)} filas de a1_06_negative_hours"
        )


def run_analysis_contracts(
    outputs: dict[str, pd.DataFrame],
    master_dataset: pd.DataFrame,
    quarantine_deals: pd.DataFrame,
) -> None:
    """Corre los contratos de las siete consultas de A1, en orden fijo."""
    active_mrr = outputs["analysis_a1_01_active_mrr"]
    usage_drop = outputs["analysis_a1_02_usage_drop"]
    cohort_retention = outputs["analysis_a1_03_cohort_retention"]
    attribution = outputs["analysis_a1_04_attribution"]
    orphan_deals = outputs["analysis_a1_05_orphan_deals"]
    negative_hours = outputs["analysis_a1_06_negative_hours"]
    exceptions = outputs["analysis_exceptions"]

    assert_a1_01_total_row_matches_segments(active_mrr)
    assert_a1_01_crm_within_total(active_mrr)
    assert_a1_01_total_matches_master_dataset(active_mrr, master_dataset)
    assert_a1_02_one_row_per_churned_account(usage_drop)
    assert_a1_02_drop_matches_status(usage_drop)
    assert_a1_03_pct_within_range(cohort_retention)
    assert_a1_03_monotone_non_increasing(cohort_retention)
    assert_a1_03_retained_within_cohort_size(cohort_retention)
    assert_a1_04_rate_within_unit(attribution)
    assert_a1_04_models_cover_same_deals(attribution)
    assert_a1_05_matches_quarantine_deals(orphan_deals, quarantine_deals)
    assert_a1_06_all_hours_negative(negative_hours)
    assert_analysis_exceptions_shape(exceptions, negative_hours)
