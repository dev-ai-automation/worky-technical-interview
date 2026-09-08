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
)
# `confidence_tier` no entra aqui a proposito: el diseno lo marca "no
# nulable" porque el dataset real tiene cobertura total de Vitally
# (T1 resuelve las 650 cuentas, seccion 3.4), pero la regla que arma
# `identity_crosswalk` (`_weakest_tier`) deja la columna en null cuando
# una empresa no tiene ni cuenta de producto ni cliente de Vitally
# vinculado, algo que si ocurre en un fixture pequeno sin cobertura
# total. Forzarlo aqui haria el contrato fragil fuera del dataset real.

MRR_SOURCE_VALUES = {"crm", "imputed_from_deal", "unresolved"}
MRR_CONFIDENCE_VALUES = {"high", "medium"}
CHURN_STATUS_VALUES = {"active", "churned"}


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
) -> None:
    """Corre los seis contratos disponibles en este PR, en orden fijo."""
    assert_row_count_matches_crosswalk(master_dataset, crosswalk)
    assert_unique_master_id(master_dataset)
    assert_required_columns_not_null(master_dataset)
    assert_master_id_in_crosswalk(master_dataset, crosswalk)
    assert_exceptions_master_id_in_dataset(exceptions_log, master_dataset)
    assert_value_domains(master_dataset)
