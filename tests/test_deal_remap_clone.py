"""Pruebas de integracion del remapeo de deals que apuntan a un clon en cuarentena.

design.md seccion 3.8 caso 2: un deal cuyo `hubspot_id` es el de un clon
en cuarentena no es huerfano, y debe remapearse al `master_id` del
sobreviviente en vez de quedar con `master_id` nulo y desaparecer sin
rastro. Sigue el mismo patron de `tests/test_support_commercial.py`
(ensamblaje completo sobre un fixture minimo) para comprobar que el
deal llega a `master_dataset`/`closed_revenue_mxn` bajo el master_id del
sobreviviente y que `exceptions_log` guarda la evidencia del remapeo.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset, open_connection

_EMPTY_ACCOUNTS = pd.DataFrame(columns=["account_id", "hubspot_id", "account_name", "created_at"])
_EMPTY_USAGE = pd.DataFrame(columns=["account_id", "month", "active_users", "logins", "payroll_runs_completed", "features_used", "api_calls"])
_EMPTY_CUSTOMERS = pd.DataFrame(columns=["vitally_id", "domain", "company_name", "csm_email"])
_EMPTY_TICKETS = pd.DataFrame(
    columns=["ticket_id", "vitally_id", "created_date", "priority", "status", "category", "resolution_hours", "csat_score"]
)
_EMPTY_TOUCHES = pd.DataFrame(columns=["touch_id", "hubspot_id", "channel", "touch_date", "campaign"])


def _companies_con_clon() -> list[dict]:
    return [
        {
            "hubspot_id": "HS-600001", "name": "Remap Clone SA de CV", "domain": "remap600.com.mx",
            "segment": "SMB", "industry": "Retail", "mrr": 5000.0, "currency": "MXN",
            "signup_date": "2022-01-01", "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": None,
        },
        # Clon de HS-600001: mismo nombre y dominio normalizados, sin mrr
        # y sin ningun account que lo referencie, igual que HS-900010 en
        # tests/fixtures/mini_dataset.py.
        {
            "hubspot_id": "HS-900060", "name": "REMAP CLONE, S.A. DE C.V.", "domain": "remap600.com.mx",
            "segment": "SMB", "industry": "Retail", "mrr": None, "currency": "MXN",
            "signup_date": "2022-01-01", "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": None,
        },
    ]


def _assemble(raw_tables: dict[str, pd.DataFrame], tmp_path_factory) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    db_path = tmp_path_factory.mktemp("deal_remap_clone") / "worky.duckdb"
    con = open_connection(db_path)
    try:
        outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
    finally:
        con.close()
    return outputs, identity_outputs


@pytest.fixture(scope="module")
def con_remap(tmp_path_factory) -> dict[str, pd.DataFrame]:
    raw_tables = {
        "raw_companies": pd.DataFrame(_companies_con_clon()),
        "raw_accounts": _EMPTY_ACCOUNTS,
        "raw_product_usage": _EMPTY_USAGE,
        "raw_customers": _EMPTY_CUSTOMERS,
        "raw_tickets": _EMPTY_TICKETS,
        "raw_marketing_touches": _EMPTY_TOUCHES,
        "raw_deals": pd.DataFrame(
            [
                # Apunta al clon HS-900060, no al sobreviviente: debe
                # remapearse a HS-600001 en vez de perderse.
                {
                    "deal_id": "D-6001", "hubspot_id": "HS-900060", "stage": "closedwon", "amount": 3000.0,
                    "created_date": "2022-02-01", "close_date": "2022-02-10", "pipeline": "New Business", "lead_source": "Web",
                },
            ]
        ),
    }
    outputs, identity_outputs = _assemble(raw_tables, tmp_path_factory)
    assert len(identity_outputs["quarantine_companies"]) == 1
    # Se fusionan las salidas de identidad (incluye quarantine_deals) con
    # las de master_dataset para que las pruebas puedan revisar ambas; las
    # diez claves de assemble_master_dataset y las cuatro de
    # resolve_identity nunca deben chocar (JD-07), o la fusion perderia
    # una tabla en silencio.
    assert not set(identity_outputs) & set(outputs)
    return {**identity_outputs, **outputs}


@pytest.fixture(scope="module")
def con_sin_remap(tmp_path_factory) -> dict[str, pd.DataFrame]:
    """El mismo clon, pero sin ningun deal que apunte a el: no debe generar remapeo."""
    raw_tables = {
        "raw_companies": pd.DataFrame(_companies_con_clon()),
        "raw_accounts": _EMPTY_ACCOUNTS,
        "raw_product_usage": _EMPTY_USAGE,
        "raw_customers": _EMPTY_CUSTOMERS,
        "raw_tickets": _EMPTY_TICKETS,
        "raw_marketing_touches": _EMPTY_TOUCHES,
        "raw_deals": pd.DataFrame(
            [
                {
                    "deal_id": "D-6002", "hubspot_id": "HS-600001", "stage": "closedwon", "amount": 4000.0,
                    "created_date": "2022-02-01", "close_date": "2022-02-10", "pipeline": "New Business", "lead_source": "Web",
                },
            ]
        ),
    }
    outputs, identity_outputs = _assemble(raw_tables, tmp_path_factory)
    assert len(identity_outputs["quarantine_companies"]) == 1
    # Misma forma fusionada que con_remap, para que las pruebas negativas
    # tambien puedan revisar quarantine_deals y quarantine_companies.
    assert not set(identity_outputs) & set(outputs)
    return {**identity_outputs, **outputs}


def test_deal_de_clon_se_remapea_al_master_id_del_sobreviviente(con_remap: dict[str, pd.DataFrame]) -> None:
    master_dataset = con_remap["master_dataset"].set_index("hubspot_id")
    assert master_dataset.loc["HS-600001", "closed_revenue_mxn"] == "3000.00"


def test_deal_remapeado_no_queda_en_quarantine_deals(con_remap: dict[str, pd.DataFrame]) -> None:
    # El remapeo no es un huerfano: no debe aparecer en quarantine_deals.
    quarantine_deals = con_remap["quarantine_deals"]
    assert (quarantine_deals["deal_id"] == "D-6001").sum() == 0


def test_exceptions_log_trae_exactamente_una_fila_de_remapeo(con_remap: dict[str, pd.DataFrame]) -> None:
    exceptions_log = con_remap["exceptions_log"]
    remap_rows = exceptions_log[exceptions_log["exception_code"] == "deal_remapped_from_clone"]
    assert len(remap_rows) == 1
    row = remap_rows.iloc[0]
    assert row["source_system"] == "crm_hubspot"
    assert row["source_id"] == "D-6001"
    assert row["field_name"] == "hubspot_id"
    assert row["original_value"] == "HS-900060"
    assert row["applied_value"] == "HS-600001"
    master_dataset = con_remap["master_dataset"]
    assert row["master_id"] == master_dataset.set_index("hubspot_id").loc["HS-600001", "master_id"]


def test_sin_deal_de_clon_no_hay_fila_de_remapeo(con_sin_remap: dict[str, pd.DataFrame]) -> None:
    exceptions_log = con_sin_remap["exceptions_log"]
    remap_rows = exceptions_log[exceptions_log["exception_code"] == "deal_remapped_from_clone"]
    assert len(remap_rows) == 0
    # El deal real (no de clon) tampoco debe caer en cuarentena, y el
    # clon sigue aislado en quarantine_companies pese a no tener ningun
    # deal remapeado en esta corrida.
    assert (con_sin_remap["quarantine_deals"]["deal_id"] == "D-6002").sum() == 0
    assert len(con_sin_remap["quarantine_companies"]) == 1


@pytest.fixture(scope="module")
def con_multiples_deals(tmp_path_factory) -> dict[str, pd.DataFrame]:
    """Dos deals sobre el mismo clon, mas un tercero sobre el sobreviviente real."""
    raw_tables = {
        "raw_companies": pd.DataFrame(_companies_con_clon()),
        "raw_accounts": _EMPTY_ACCOUNTS,
        "raw_product_usage": _EMPTY_USAGE,
        "raw_customers": _EMPTY_CUSTOMERS,
        "raw_tickets": _EMPTY_TICKETS,
        "raw_marketing_touches": _EMPTY_TOUCHES,
        "raw_deals": pd.DataFrame(
            [
                # Dos deals sobre el clon HS-900060: ambos deben remapearse.
                {
                    "deal_id": "D-6101", "hubspot_id": "HS-900060", "stage": "closedwon", "amount": 1000.0,
                    "created_date": "2022-02-01", "close_date": "2022-02-10", "pipeline": "New Business", "lead_source": "Web",
                },
                {
                    "deal_id": "D-6102", "hubspot_id": "HS-900060", "stage": "closedwon", "amount": 2000.0,
                    "created_date": "2022-03-01", "close_date": "2022-03-10", "pipeline": "New Business", "lead_source": "Web",
                },
                # Deal sobre el sobreviviente real: el clon existe en el
                # mismo build (la rama de remapeo existe), pero este deal
                # no debe producir ninguna fila de remapeo.
                {
                    "deal_id": "D-6103", "hubspot_id": "HS-600001", "stage": "closedwon", "amount": 500.0,
                    "created_date": "2022-04-01", "close_date": "2022-04-10", "pipeline": "New Business", "lead_source": "Web",
                },
            ]
        ),
    }
    outputs, identity_outputs = _assemble(raw_tables, tmp_path_factory)
    assert len(identity_outputs["quarantine_companies"]) == 1
    assert not set(identity_outputs) & set(outputs)
    return {**identity_outputs, **outputs}


def test_dos_deals_del_mismo_clon_producen_dos_filas_de_remapeo(con_multiples_deals: dict[str, pd.DataFrame]) -> None:
    exceptions_log = con_multiples_deals["exceptions_log"]
    remap_rows = exceptions_log[exceptions_log["exception_code"] == "deal_remapped_from_clone"]
    assert len(remap_rows) == 2
    assert set(remap_rows["source_id"]) == {"D-6101", "D-6102"}
    assert remap_rows["exception_id"].nunique() == 2


def test_deal_sobre_el_sobreviviente_real_no_produce_fila_de_remapeo(con_multiples_deals: dict[str, pd.DataFrame]) -> None:
    exceptions_log = con_multiples_deals["exceptions_log"]
    remap_rows = exceptions_log[exceptions_log["exception_code"] == "deal_remapped_from_clone"]
    assert (remap_rows["source_id"] == "D-6103").sum() == 0
    assert (con_multiples_deals["quarantine_deals"]["deal_id"] == "D-6103").sum() == 0
