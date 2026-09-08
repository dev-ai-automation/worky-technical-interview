"""Contratos de datos en tiempo de build, para las columnas disponibles en este PR.

Cada `assert_*` valida una sola regla y lanza `ContractViolation` con el
nombre del contrato en el mensaje cuando la regla no se cumple, tal
como exige el requisito de mensajes claros de `build-cli`. `run_contracts`
las corre todas en orden; el llamador decide el codigo de salida del
proceso (1 para un contrato violado).
"""

from __future__ import annotations

import pandas as pd

# Columnas que el spec de `master-dataset-assembly` marca como no
# nulables, acotadas a las que este PR ya produce (uso, soporte y
# comercial llegan en el PR 4).
REQUIRED_MASTER_DATASET_COLUMNS = (
    "master_id",
    "hubspot_id",
    "company_name",
    "domain",
    "segment",
    "plan",
    "signup_date",
    "churn_status",
    "reference_month",
    "mrr_source",
    "mrr_confidence",
    "currency_original",
    "trend_status",
    "trend_asof_month",
    "tickets_total",
    "tickets_urgent",
    "acquisition_channel",
    "closed_revenue_mxn",
)
# `confidence_tier` no entra aqui a proposito: el diseno lo marca "no
# nulable" porque el dataset real tiene cobertura total de Vitally
# (T1 resuelve las 650 cuentas, seccion 3.4), pero la regla que arma
# `identity_crosswalk` (`_weakest_tier`) deja la columna en null cuando
# una empresa no tiene ni cuenta de producto ni cliente de Vitally
# vinculado, algo que si ocurre en un fixture pequeno sin cobertura
# total. Forzarlo aqui haria el contrato fragil fuera del dataset real.

MRR_SOURCE_VALUES = {"crm", "imputed_from_deal", "unresolved"}
MRR_CONFIDENCE_VALUES = {"high", "medium", "none"}
CHURN_STATUS_VALUES = {"active", "churned"}
TREND_STATUS_VALUES = {"computed", "insufficient_history", "no_usage"}


class ContractViolation(Exception):
    """Un contrato de datos no se cumplio; el mensaje nombra cual."""


def assert_row_count_matches_crosswalk(master_dataset: pd.DataFrame, crosswalk: pd.DataFrame) -> None:
    """Una fila de master_dataset por cada empresa real del crosswalk, ni una mas ni una menos."""
    if len(master_dataset) != len(crosswalk):
        raise ContractViolation(
            "contrato row_count: master_dataset tiene "
            f"{len(master_dataset)} filas, identity_crosswalk tiene {len(crosswalk)}"
        )


def assert_unique_master_id(master_dataset: pd.DataFrame) -> None:
    duplicated = master_dataset["master_id"].duplicated()
    if duplicated.any():
        raise ContractViolation(
            f"contrato unique_master_id: {int(duplicated.sum())} master_id repetidos en master_dataset"
        )


def assert_required_columns_not_null(master_dataset: pd.DataFrame) -> None:
    for column in REQUIRED_MASTER_DATASET_COLUMNS:
        if master_dataset[column].isna().any():
            raise ContractViolation(
                f"contrato required_not_null: la columna '{column}' de master_dataset tiene valores nulos"
            )


def assert_master_id_in_crosswalk(master_dataset: pd.DataFrame, crosswalk: pd.DataFrame) -> None:
    missing = set(master_dataset["master_id"]) - set(crosswalk["master_id"])
    if missing:
        raise ContractViolation(
            f"contrato master_id_in_crosswalk: {len(missing)} master_id de master_dataset sin fila en identity_crosswalk"
        )


def assert_exceptions_master_id_in_dataset(exceptions_log: pd.DataFrame, master_dataset: pd.DataFrame) -> None:
    if exceptions_log.empty:
        return
    missing = set(exceptions_log["master_id"].dropna()) - set(master_dataset["master_id"])
    if missing:
        raise ContractViolation(
            f"contrato exceptions_master_id_in_dataset: {len(missing)} master_id de exceptions_log ausentes en master_dataset"
        )


def assert_value_domains(master_dataset: pd.DataFrame) -> None:
    _assert_domain(master_dataset, "mrr_source", MRR_SOURCE_VALUES)
    _assert_domain(master_dataset, "mrr_confidence", MRR_CONFIDENCE_VALUES)
    _assert_domain(master_dataset, "churn_status", CHURN_STATUS_VALUES)
    _assert_domain(master_dataset, "trend_status", TREND_STATUS_VALUES)


def assert_trend_usage_matches_status(master_dataset: pd.DataFrame) -> None:
    """`trend_usage` tiene valor si y solo si `trend_status` es 'computed' (ADR-003), nunca un nulo silencioso."""
    is_computed = master_dataset["trend_status"] == "computed"
    trend_usage_present = master_dataset["trend_usage"].notna()
    if (is_computed != trend_usage_present).any():
        raise ContractViolation(
            "contrato trend_usage_matches_status: trend_usage debe tener valor "
            "unicamente cuando trend_status es 'computed'"
        )


def assert_trend_asof_month_is_reference_minus_two(master_dataset: pd.DataFrame) -> None:
    """`trend_asof_month` es el mes de referencia menos 2 meses (k = 2), en todas las filas (ADR-003)."""
    expected = (
        pd.to_datetime(master_dataset["reference_month"] + "-01") - pd.DateOffset(months=2)
    ).dt.strftime("%Y-%m")
    mismatched = master_dataset["trend_asof_month"] != expected
    if mismatched.any():
        raise ContractViolation(
            f"contrato trend_asof_month_reference_minus_two: {int(mismatched.sum())} filas "
            "con trend_asof_month distinto de reference_month menos 2 meses"
        )


def assert_mrr_confidence_matches_source(master_dataset: pd.DataFrame) -> None:
    """`mrr_confidence` es 'none' solo cuando `mrr_source` es 'unresolved', y `mrr_mxn` solo queda vacio ahi."""
    is_unresolved = master_dataset["mrr_source"] == "unresolved"
    confidence_is_none = master_dataset["mrr_confidence"] == "none"
    if (is_unresolved != confidence_is_none).any():
        raise ContractViolation(
            "contrato mrr_confidence_matches_source: mrr_confidence debe ser 'none' unicamente cuando mrr_source es 'unresolved'"
        )
    mrr_is_empty = master_dataset["mrr_mxn"].fillna("") == ""
    if (is_unresolved != mrr_is_empty).any():
        raise ContractViolation(
            "contrato mrr_confidence_matches_source: mrr_mxn debe quedar vacio unicamente cuando mrr_source es 'unresolved'"
        )


_ORIGIN_TABLE_BY_SOURCE_SYSTEM = {
    "crm_hubspot": ("raw_companies", "hubspot_id"),
    "product_db": ("raw_accounts", "account_id"),
    "vitally": ("raw_customers", "vitally_id"),
}


def assert_source_id_in_origin_table(match_audit: pd.DataFrame, raw_tables: dict[str, pd.DataFrame]) -> None:
    """Cada `source_id` de match_audit existe en la tabla cruda de su propio sistema de origen."""
    for source_system, (table_name, id_column) in _ORIGIN_TABLE_BY_SOURCE_SYSTEM.items():
        known_ids = set(raw_tables[table_name][id_column].dropna())
        observed_ids = set(match_audit.loc[match_audit["source_system"] == source_system, "source_id"])
        missing = observed_ids - known_ids
        if missing:
            raise ContractViolation(
                f"contrato source_id_in_origin_table: {len(missing)} source_id de '{source_system}' "
                f"ausentes en {table_name}.{id_column}"
            )


TICKETS_PRIORITY_VALUES = {"Low", "Medium", "High", "Urgent"}


def assert_tickets_priority_domain(raw_tickets: pd.DataFrame) -> None:
    """`tickets.priority`, sobre la tabla cruda, solo trae los cuatro valores del dominio conocido."""
    observed = set(raw_tickets["priority"].dropna())
    invalid = observed - TICKETS_PRIORITY_VALUES
    if invalid:
        raise ContractViolation(f"contrato tickets_priority_domain: valores no permitidos {sorted(invalid)}")


def assert_usage_months_no_internal_gaps(raw_product_usage: pd.DataFrame) -> None:
    """Por cada cuenta con uso, los meses observados son consecutivos entre el minimo y el maximo."""
    for account_id, group in raw_product_usage.groupby("account_id"):
        months = sorted({pd.Period(str(month), freq="M") for month in group["month"].dropna()})
        if not months:
            continue
        expected_span = (months[-1] - months[0]).n + 1
        if len(months) != expected_span:
            raise ContractViolation(
                f"contrato usage_months_no_internal_gaps: la cuenta '{account_id}' tiene huecos en su serie de uso"
            )


def assert_tickets_urgent_within_total(master_dataset: pd.DataFrame) -> None:
    """`tickets_urgent` nunca puede superar `tickets_total`, en ninguna fila (seccion 4.5 del diseno)."""
    invalid = master_dataset["tickets_urgent"] > master_dataset["tickets_total"]
    if invalid.any():
        raise ContractViolation(
            f"contrato tickets_urgent_within_total: {int(invalid.sum())} filas con tickets_urgent > tickets_total"
        )


def assert_csat_avg_domain(master_dataset: pd.DataFrame) -> None:
    """`csat_avg` esta entre 1 y 5, o vacio cuando ningun ticket trajo puntaje."""
    csat = pd.to_numeric(master_dataset["csat_avg"], errors="coerce")
    present = csat.notna()
    invalid = present & ((csat < 1) | (csat > 5))
    if invalid.any():
        raise ContractViolation(
            f"contrato csat_avg_domain: {int(invalid.sum())} filas con csat_avg fuera de [1, 5]"
        )


def assert_closed_revenue_non_negative(master_dataset: pd.DataFrame) -> None:
    """`closed_revenue_mxn` nunca es negativo: es una suma de montos de deals cerrados."""
    revenue = pd.to_numeric(master_dataset["closed_revenue_mxn"], errors="coerce")
    invalid = revenue < 0
    if invalid.any():
        raise ContractViolation(
            f"contrato closed_revenue_non_negative: {int(invalid.sum())} filas con closed_revenue_mxn negativo"
        )


def count_unresolved(master_dataset: pd.DataFrame) -> int:
    """Cuenta filas `mrr_source = 'unresolved'`: estado legitimo, nunca hace fallar el build por si solo."""
    return int((master_dataset["mrr_source"] == "unresolved").sum())


def _assert_domain(frame: pd.DataFrame, column: str, allowed: set[str]) -> None:
    observed = set(frame[column].dropna())
    invalid = observed - allowed
    if invalid:
        raise ContractViolation(
            f"contrato value_domain_{column}: valores no permitidos {sorted(invalid)}"
        )


def run_contracts(
    master_dataset: pd.DataFrame,
    crosswalk: pd.DataFrame,
    exceptions_log: pd.DataFrame,
    match_audit: pd.DataFrame | None = None,
    raw_tables: dict[str, pd.DataFrame] | None = None,
) -> None:
    """Corre todos los contratos disponibles en tiempo de build, en orden fijo (seccion 6 del diseno).

    `match_audit` y `raw_tables` son opcionales para no romper las pruebas
    existentes que solo ejercitan `master_dataset`/`crosswalk`/`exceptions_log`
    (por ejemplo sobre copias rotas de una sola tabla); `cmd_build` los pasa
    siempre, asi que en un build real los tres contratos de la tarea 3.12
    (`source_id` de match_audit, `tickets.priority`, series de uso sin
    huecos) tambien corren y pueden terminar el build con codigo 1.
    """
    assert_row_count_matches_crosswalk(master_dataset, crosswalk)
    assert_unique_master_id(master_dataset)
    assert_required_columns_not_null(master_dataset)
    assert_master_id_in_crosswalk(master_dataset, crosswalk)
    assert_exceptions_master_id_in_dataset(exceptions_log, master_dataset)
    assert_value_domains(master_dataset)
    assert_mrr_confidence_matches_source(master_dataset)
    assert_trend_usage_matches_status(master_dataset)
    assert_trend_asof_month_is_reference_minus_two(master_dataset)
    assert_tickets_urgent_within_total(master_dataset)
    assert_csat_avg_domain(master_dataset)
    assert_closed_revenue_non_negative(master_dataset)
    if match_audit is not None and raw_tables is not None:
        assert_source_id_in_origin_table(match_audit, raw_tables)
        assert_tickets_priority_domain(raw_tables["raw_tickets"])
        assert_usage_months_no_internal_gaps(raw_tables["raw_product_usage"])

    unresolved_count = count_unresolved(master_dataset)
    if unresolved_count:
        print(f"contratos: {unresolved_count} filas con mrr_source='unresolved' (estado legitimo, no es una violacion)")
