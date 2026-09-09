"""Pruebas de integracion de la contencion de enlaces de origen duplicados.

design.md 3.6 y el ledger de Judgment Day (JD-01): dos accounts de
product_db (o dos customers de Vitally) que resuelven al mismo
master_id ya no abortan el build, se contienen. Sigue el mismo patron
de `tests/test_deal_remap_clone.py`
(ensamblaje completo sobre un fixture minimo) para comprobar que el
enlace descartado deja exactamente una fila en `exceptions_log`
(exception_code `duplicate_source_link`), que `master_dataset` sigue
teniendo una sola fila por empresa, y que la cola de revision manual
(`coverage_manual_queue`) cuenta ese registro.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset, open_connection

_EMPTY_USAGE = pd.DataFrame(columns=["account_id", "month", "active_users", "logins", "payroll_runs_completed", "features_used", "api_calls"])
_EMPTY_CUSTOMERS = pd.DataFrame(columns=["vitally_id", "domain", "company_name", "csm_email"])
_EMPTY_TICKETS = pd.DataFrame(
    columns=["ticket_id", "vitally_id", "created_date", "priority", "status", "category", "resolution_hours", "csat_score"]
)
_EMPTY_TOUCHES = pd.DataFrame(columns=["touch_id", "hubspot_id", "channel", "touch_date", "campaign"])
_EMPTY_DEALS = pd.DataFrame(
    columns=["deal_id", "hubspot_id", "stage", "amount", "created_date", "close_date", "pipeline", "lead_source"]
)


def _company_row() -> list[dict]:
    return [
        {
            "hubspot_id": "HS-700001", "name": "Duplicado SA de CV", "domain": "duplicado700.com.mx",
            "segment": "SMB", "industry": "Retail", "mrr": 3000.0, "currency": "MXN",
            "signup_date": "2022-01-01", "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": None,
        },
    ]


def _assemble(raw_tables: dict[str, pd.DataFrame], tmp_path_factory) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    db_path = tmp_path_factory.mktemp("duplicate_link_containment") / "worky.duckdb"
    con = open_connection(db_path)
    try:
        outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
    finally:
        con.close()
    return outputs, identity_outputs


@pytest.fixture(scope="module")
def con_duplicado(tmp_path_factory) -> dict[str, pd.DataFrame]:
    """Dos accounts con el mismo hubspot_id, ambos resuelven por T0 a la misma empresa."""
    raw_tables = {
        "raw_companies": pd.DataFrame(_company_row()),
        "raw_accounts": pd.DataFrame(
            [
                {"account_id": "ACC-700001", "hubspot_id": "HS-700001", "account_name": "Duplicado Uno", "created_at": "2022-01-01"},
                {"account_id": "ACC-700002", "hubspot_id": "HS-700001", "account_name": "Duplicado Dos", "created_at": "2022-02-01"},
            ]
        ),
        "raw_product_usage": _EMPTY_USAGE,
        "raw_customers": _EMPTY_CUSTOMERS,
        "raw_tickets": _EMPTY_TICKETS,
        "raw_marketing_touches": _EMPTY_TOUCHES,
        "raw_deals": _EMPTY_DEALS,
    }
    outputs, identity_outputs = _assemble(raw_tables, tmp_path_factory)
    assert not set(identity_outputs) & set(outputs)
    return {**identity_outputs, **outputs}


@pytest.fixture(scope="module")
def con_triplicado(tmp_path_factory) -> dict[str, pd.DataFrame]:
    """Accounts A, B, B: el segundo id aparece dos veces, pero el enlace descartado es uno solo."""
    raw_tables = {
        "raw_companies": pd.DataFrame(_company_row()),
        "raw_accounts": pd.DataFrame(
            [
                {"account_id": "ACC-700001", "hubspot_id": "HS-700001", "account_name": "Duplicado Uno", "created_at": "2022-01-01"},
                {"account_id": "ACC-700002", "hubspot_id": "HS-700001", "account_name": "Duplicado Dos", "created_at": "2022-02-01"},
                {"account_id": "ACC-700002", "hubspot_id": "HS-700001", "account_name": "Duplicado Dos", "created_at": "2022-02-01"},
            ]
        ),
        "raw_product_usage": _EMPTY_USAGE,
        "raw_customers": _EMPTY_CUSTOMERS,
        "raw_tickets": _EMPTY_TICKETS,
        "raw_marketing_touches": _EMPTY_TOUCHES,
        "raw_deals": _EMPTY_DEALS,
    }
    outputs, identity_outputs = _assemble(raw_tables, tmp_path_factory)
    assert not set(identity_outputs) & set(outputs)
    return {**identity_outputs, **outputs}


@pytest.fixture(scope="module")
def con_limpio(tmp_path_factory) -> dict[str, pd.DataFrame]:
    """La misma empresa, pero con una sola account: no debe generar ningun duplicado."""
    raw_tables = {
        "raw_companies": pd.DataFrame(_company_row()),
        "raw_accounts": pd.DataFrame(
            [{"account_id": "ACC-700001", "hubspot_id": "HS-700001", "account_name": "Duplicado Uno", "created_at": "2022-01-01"}]
        ),
        "raw_product_usage": _EMPTY_USAGE,
        "raw_customers": _EMPTY_CUSTOMERS,
        "raw_tickets": _EMPTY_TICKETS,
        "raw_marketing_touches": _EMPTY_TOUCHES,
        "raw_deals": _EMPTY_DEALS,
    }
    outputs, identity_outputs = _assemble(raw_tables, tmp_path_factory)
    assert not set(identity_outputs) & set(outputs)
    return {**identity_outputs, **outputs}


def test_exceptions_log_trae_exactamente_una_fila_de_enlace_duplicado(con_duplicado: dict[str, pd.DataFrame]) -> None:
    exceptions_log = con_duplicado["exceptions_log"]
    dup_rows = exceptions_log[exceptions_log["exception_code"] == "duplicate_source_link"]
    assert len(dup_rows) == 1
    row = dup_rows.iloc[0]
    assert row["source_system"] == "product_db"
    assert row["source_id"] == "ACC-700002"
    assert row["field_name"] == "account_id"
    assert row["original_value"] == "ACC-700002"
    assert row["applied_value"] == "ACC-700001"
    master_dataset = con_duplicado["master_dataset"]
    assert row["master_id"] == master_dataset.set_index("hubspot_id").loc["HS-700001", "master_id"]


def test_master_dataset_conserva_una_sola_fila_por_empresa(con_duplicado: dict[str, pd.DataFrame]) -> None:
    master_dataset = con_duplicado["master_dataset"]
    assert len(master_dataset) == 1
    assert master_dataset.iloc[0]["hubspot_id"] == "HS-700001"


def test_la_cola_de_revision_manual_cuenta_el_enlace_duplicado(con_duplicado: dict[str, pd.DataFrame]) -> None:
    manual_queue = con_duplicado["coverage_manual_queue"]
    assert int(manual_queue["manual_queue_size"].iloc[0]) == 1

    match_audit = con_duplicado["match_audit"]
    dropped = match_audit[match_audit["source_id"] == "ACC-700002"].iloc[0]
    assert bool(dropped["needs_review"])


def test_build_sin_duplicados_no_genera_filas_ni_cola_manual(con_limpio: dict[str, pd.DataFrame]) -> None:
    exceptions_log = con_limpio["exceptions_log"]
    dup_rows = exceptions_log[exceptions_log["exception_code"] == "duplicate_source_link"]
    assert len(dup_rows) == 0

    manual_queue = con_limpio["coverage_manual_queue"]
    assert int(manual_queue["manual_queue_size"].iloc[0]) == 0


def test_un_source_id_repetido_deja_una_sola_fila_con_exception_id_unico(con_triplicado: dict[str, pd.DataFrame]) -> None:
    # Las dos filas de match_audit de ACC-700002 quedan marcadas, pero el
    # enlace descartado es uno y exceptions_log no puede repetir su id.
    match_audit = con_triplicado["match_audit"]
    marked = match_audit[(match_audit["source_id"] == "ACC-700002") & match_audit["needs_review"]]
    assert len(marked) == 2

    exceptions_log = con_triplicado["exceptions_log"]
    dup_rows = exceptions_log[exceptions_log["exception_code"] == "duplicate_source_link"]
    assert len(dup_rows) == 1
    assert dup_rows.iloc[0]["source_id"] == "ACC-700002"
    assert exceptions_log["exception_id"].is_unique
