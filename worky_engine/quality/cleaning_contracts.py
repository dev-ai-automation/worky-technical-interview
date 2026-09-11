"""Contratos de `worky_engine.cleaning`, incluida la imputacion del ADR-002 (seccion 5 del diseno de A6).

Mismo patron que `worky_engine.quality.contracts`: cada `assert_*`
valida una sola regla sobre DataFrames ya materializados y lanza
`ContractViolation` con el nombre del contrato en el mensaje.
"""

from __future__ import annotations

import re

import pandas as pd

from worky_engine.cleaning.rules import CLONE_ID_PATTERN
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
    "mrr_not_numeric": ("missing_mrr", "not_numeric"),
    "mrr_unresolved": ("missing_mrr", "unresolved"),
    "deal_amount_not_numeric": ("missing_mrr", "deal_amount_not_numeric"),
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


def assert_no_null_mrr_after_imputation(clean: pd.DataFrame) -> None:
    """`mrr_mxn` solo puede quedar vacio en filas `unresolved` o `clone_excluded` (D6, D7)."""
    allowed_empty = {"unresolved", "clone_excluded"}
    bad = clean[(clean["mrr_mxn"] == "") & (~clean["mrr_source"].isin(allowed_empty))]
    if not bad.empty:
        raise ContractViolation(
            f"contrato assert_no_null_mrr_after_imputation: mrr_mxn vacio sin motivo en {sorted(bad['hubspot_id'])}"
        )


def assert_currency_all_mxn(clean: pd.DataFrame, exceptions: pd.DataFrame) -> None:
    """Toda fila sale con `currency = 'MXN'`, salvo la que trae su propia excepcion `currency_unsupported`.

    Una fila con `currency_unsupported` conserva su moneda original en
    `currency` y `currency_original` (D9): el contrato la deja pasar
    solo cuando la excepcion existe para ese `hubspot_id`, para no
    tapar una moneda no soportada que se cuele sin reportarse.
    """
    unsupported_ids = (
        set(exceptions.loc[exceptions["exception_code"] == "currency_unsupported", "source_id"])
        if not exceptions.empty
        else set()
    )
    for hubspot_id, currency, currency_original in zip(
        clean["hubspot_id"], clean["currency"], clean["currency_original"]
    ):
        if currency == "MXN" and currency_original in {"MXN", "USD"}:
            continue
        if hubspot_id in unsupported_ids and currency == currency_original:
            continue
        raise ContractViolation(
            f"contrato assert_currency_all_mxn: '{hubspot_id}' tiene currency='{currency}' "
            f"currency_original='{currency_original}' sin excepcion currency_unsupported"
        )


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


def assert_clone_deals_absent(deals: pd.DataFrame) -> None:
    """Ningun deal de `deals.csv` apunta a un `hubspot_id` `HS-9000xx`: el supuesto que sostiene la equivalencia con `mart_mrr` (seccion 3 del diseno)."""
    clone_ids = sorted(set(deals.loc[deals["hubspot_id"].str.match(CLONE_ID_PATTERN.pattern), "hubspot_id"]))
    if clone_ids:
        raise ContractViolation(f"contrato assert_clone_deals_absent: deals.csv trae filas para clones {clone_ids}")


def run_cleaning_contracts(
    clean: pd.DataFrame,
    companies_in: pd.DataFrame,
    exceptions: pd.DataFrame,
    counts: dict,
    run_clean,
    deals: pd.DataFrame,
) -> None:
    """Corre en orden fijo los nueve contratos de forma, imputacion, moneda, fecha, unicidad, conteos e idempotencia."""
    assert_clean_row_count_preserved(clean, companies_in)
    assert_clean_columns_and_order(clean)
    assert_no_null_mrr_after_imputation(clean)
    assert_currency_all_mxn(clean, exceptions)
    assert_dates_iso_or_empty(clean, exceptions)
    assert_exception_ids_unique(exceptions)
    assert_counts_match_exceptions(counts, exceptions)
    assert_clean_is_idempotent(run_clean, clean, deals)
    assert_clone_deals_absent(deals)
