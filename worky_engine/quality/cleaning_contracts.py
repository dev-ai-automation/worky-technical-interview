"""Contratos de `worky_engine.cleaning` disponibles sin imputacion (seccion 5 del diseno de A6).

Mismo patron que `worky_engine.quality.contracts`: cada `assert_*`
valida una sola regla sobre DataFrames ya materializados y lanza
`ContractViolation` con el nombre del contrato en el mensaje. Los
contratos que dependen de la imputacion del ADR-002
(`assert_no_null_mrr_after_imputation`, `assert_clone_deals_absent`)
llegan en PR2.
"""

from __future__ import annotations

import re

import pandas as pd

from worky_engine.quality.contracts import ContractViolation

CLEAN_COLUMNS = (
    "hubspot_id",
    "name",
    "domain",
    "segment",
    "industry",
    "mrr",
    "currency",
    "signup_date",
    "csm_owner",
    "plan",
    "state",
    "churn_date",
    "mrr_mxn",
    "mrr_original",
    "currency_original",
    "mrr_source",
    "mrr_confidence",
)
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Mapa de cada exception_code al par (regla, campo del conteo) que debe
# igualarlo en `cleaning_log.json`, para `assert_counts_match_exceptions`.
_CODE_TO_COUNT_PATH = {
    "date_normalized": ("date_format", "corrected"),
    "date_unresolved": ("date_format", "unresolved"),
    "currency_converted_to_mxn": ("currency_to_mxn", "corrected"),
    "currency_unsupported": ("currency_to_mxn", "unresolved"),
    "clone_excluded": ("missing_mrr", "excluded_clones"),
    "mrr_imputed_from_deal": ("missing_mrr", "corrected"),
    "mrr_deal_annualized": ("missing_mrr", "annualized_deals"),
    "mrr_unresolved": ("missing_mrr", "unresolved"),
}


def assert_clean_row_count_preserved(clean: pd.DataFrame, companies_in: pd.DataFrame) -> None:
    """`companies_clean.csv` tiene exactamente las mismas filas que `companies.csv` de entrada, sin agregar ni perder."""
    if len(clean) != len(companies_in):
        raise ContractViolation(
            "contrato assert_clean_row_count_preserved: "
            f"{len(clean)} filas de salida, {len(companies_in)} filas de entrada"
        )


def assert_clean_columns_and_order(clean: pd.DataFrame) -> None:
    """Las 17 columnas de la seccion 4 del diseno, en ese orden exacto."""
    actual = tuple(clean.columns)
    if actual != CLEAN_COLUMNS:
        raise ContractViolation(
            f"contrato assert_clean_columns_and_order: columnas {actual}, se esperaban {CLEAN_COLUMNS}"
        )


def assert_currency_all_mxn(clean: pd.DataFrame) -> None:
    """Toda fila sale con `currency = 'MXN'` y `currency_original` en `{MXN, USD}`."""
    if (clean["currency"] != "MXN").any():
        raise ContractViolation("contrato assert_currency_all_mxn: hay filas con currency distinto de 'MXN'")
    invalid = set(clean["currency_original"]) - {"MXN", "USD"}
    if invalid:
        raise ContractViolation(f"contrato assert_currency_all_mxn: currency_original invalido {sorted(invalid)}")


def assert_dates_iso_or_empty(clean: pd.DataFrame, exceptions: pd.DataFrame) -> None:
    """`signup_date` y `churn_date` son ISO o vacias, salvo la fila con su propia excepcion `date_unresolved`."""
    unresolved_ids = (
        set(exceptions.loc[exceptions["exception_code"] == "date_unresolved", "source_id"])
        if not exceptions.empty
        else set()
    )
    for column in ("signup_date", "churn_date"):
        for hubspot_id, value in zip(clean["hubspot_id"], clean[column]):
            if value == "" or _ISO_DATE_PATTERN.match(value):
                continue
            if hubspot_id in unresolved_ids:
                continue
            raise ContractViolation(
                f"contrato assert_dates_iso_or_empty: '{hubspot_id}'.{column} = '{value}' no es ISO ni vacio"
            )


def assert_exception_ids_unique(exceptions: pd.DataFrame) -> None:
    """`exception_id` nunca se repite en `cleaning_exceptions.csv`."""
    if exceptions.empty:
        return
    duplicated = exceptions["exception_id"].duplicated()
    if duplicated.any():
        ids = sorted(set(exceptions.loc[duplicated, "exception_id"]))
        raise ContractViolation(f"contrato assert_exception_ids_unique: exception_id repetido {ids}")


def assert_counts_match_exceptions(counts: dict, exceptions: pd.DataFrame) -> None:
    """Cada `exception_code` de la bitacora cuadra uno a uno con el conteo declarado en `cleaning_log.json`."""
    rules_by_name = {rule["rule"]: rule for rule in counts["rules"]}
    observed = exceptions["exception_code"].value_counts().to_dict() if not exceptions.empty else {}
    for code, (rule_name, field_name) in _CODE_TO_COUNT_PATH.items():
        expected = rules_by_name.get(rule_name, {}).get(field_name, 0)
        actual = observed.get(code, 0)
        if expected != actual:
            raise ContractViolation(
                f"contrato assert_counts_match_exceptions: '{code}' declara {expected} en el log "
                f"pero cleaning_exceptions.csv trae {actual} filas"
            )


def assert_clean_is_idempotent(run_clean, clean: pd.DataFrame, deals: pd.DataFrame) -> None:
    """Corre `run_clean` sobre su propia salida y confirma cero correcciones (seccion 5 del diseno).

    La segunda pasada se descarta sin escribirse: solo se valida el
    conteo total de correcciones del `counts` resultante.
    """
    second_pass = run_clean(clean, deals)
    second_total = second_pass.counts["totals"]["corrections"]
    if second_total != 0:
        raise ContractViolation(
            f"contrato assert_clean_is_idempotent: la segunda pasada reporto {second_total} "
            "correcciones, se esperaban 0"
        )


def run_cleaning_contracts(
    clean: pd.DataFrame,
    companies_in: pd.DataFrame,
    exceptions: pd.DataFrame,
    counts: dict,
    run_clean,
    deals: pd.DataFrame,
) -> None:
    """Corre en orden fijo los contratos de forma, moneda, fecha, unicidad, conteos e idempotencia disponibles en PR1."""
    assert_clean_row_count_preserved(clean, companies_in)
    assert_clean_columns_and_order(clean)
    assert_currency_all_mxn(clean)
    assert_dates_iso_or_empty(clean, exceptions)
    assert_exception_ids_unique(exceptions)
    assert_counts_match_exceptions(counts, exceptions)
    assert_clean_is_idempotent(run_clean, clean, deals)
