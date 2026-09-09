"""Pruebas de fixture minimo para las consultas de A1 disponibles en este PR.

Construye su propio fixture, con la forma de `_minimal_raw_tables` de
`tests/test_support_commercial.py`, y no extiende
`tests/fixtures/mini_dataset.py` (decision del diseno, seccion 6):
agregar empresas ahi moveria los conteos que ya fijan las pruebas de
identidad y de imputacion. El fixture ejercita, a proposito: dos
empresas activas en segmentos distintos para A1.1; cuatro cuentas con
churn para A1.2 (mes de baja excluido, windows_overlap en una cuenta de
tres meses, drop_status 'no_usage' y 'final_window_empty'); y un deal
huerfano mas un deal de un clon en cuarentena para A1.5.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worky_engine.analysis import run_analysis
from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset, open_connection
from worky_engine.quality.analysis_contracts import run_analysis_contracts

_EMPTY_CUSTOMERS = pd.DataFrame(columns=["vitally_id", "domain", "company_name", "csm_email"])
_EMPTY_TICKETS = pd.DataFrame(
    columns=["ticket_id", "vitally_id", "created_date", "priority", "status", "category", "resolution_hours", "csat_score"]
)
_EMPTY_TOUCHES = pd.DataFrame(columns=["touch_id", "hubspot_id", "channel", "touch_date", "campaign"])


def _company(hubspot_id: str, name: str, domain: str, segment: str, industry: str, mrr, churn_date=None) -> dict:
    return {
        "hubspot_id": hubspot_id, "name": name, "domain": domain, "segment": segment,
        "industry": industry, "mrr": mrr, "currency": "MXN", "signup_date": "2022-01-01",
        "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": churn_date,
    }


def _usage(account_id: str, month: str, active_users: int) -> dict:
    return {
        "account_id": account_id, "month": month, "active_users": active_users,
        "logins": active_users * 2, "payroll_runs_completed": 1, "features_used": 3, "api_calls": 100,
    }


def _minimal_raw_tables() -> dict[str, pd.DataFrame]:
    companies = [
        _company("HS-810001", "Activa Uno SA de CV", "activa810uno.com.mx", "SMB", "Retail", 1000.0),
        _company("HS-810002", "Activa Dos SA de CV", "activa810dos.com.mx", "Enterprise", "Tech", 5000.0),
        _company("HS-810003", "Superviviente SA de CV", "survivor810.com.mx", "SMB", "Retail", 300.0),
        # Clon del sobreviviente anterior: mismo nombre y dominio
        # normalizados, sin mrr y sin ningun account que lo referencie
        # (patron de tests/test_deal_remap_clone.py).
        {
            "hubspot_id": "HS-900081", "name": "SUPERVIVIENTE, S.A. DE C.V.", "domain": "survivor810.com.mx",
            "segment": "SMB", "industry": "Retail", "mrr": None, "currency": "MXN", "signup_date": "2022-01-01",
            "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": None,
        },
        # ACC-8110: 8 meses de uso, churn en 2024-08; el mes de baja trae
        # un pico de uso que debe quedar fuera de la ventana final.
        _company("HS-810010", "Excluye Mes Baja SA de CV", "excl810.com.mx", "SMB", "Retail", 1000.0, "2024-08-15"),
        # ACC-8111: exactamente 3 meses de uso; ventana inicial y final
        # comparten los mismos tres meses (windows_overlap).
        _company("HS-810011", "Ventana Tres SA de CV", "vtres810.com.mx", "SMB", "Retail", 1000.0, "2024-04-15"),
        # ACC-8112: sin ninguna fila de uso -> drop_status = 'no_usage'.
        _company("HS-810012", "Sin Uso SA de CV", "sinuso810.com.mx", "SMB", "Retail", 1000.0, "2024-06-15"),
        # ACC-8113: uso solo en 2021, muy antes del churn -> ventana final vacia.
        _company("HS-810013", "Ventana Vacia SA de CV", "vvacia810.com.mx", "SMB", "Retail", 1000.0, "2024-06-15"),
        # ACC-8114 y ACC-8115: el uso sube antes de la baja, asi que la
        # caida relativa es negativa; fijan el orden numerico descendente.
        _company("HS-810014", "Sube Mucho SA de CV", "submucho810.com.mx", "SMB", "Retail", 1000.0, "2024-06-15"),
        _company("HS-810015", "Sube Poco SA de CV", "subpoco810.com.mx", "SMB", "Retail", 1000.0, "2024-06-15"),
    ]
    accounts = [
        {"account_id": "ACC-8110", "hubspot_id": "HS-810010", "account_name": "Excluye Mes Baja", "created_at": "2022-01-01"},
        {"account_id": "ACC-8111", "hubspot_id": "HS-810011", "account_name": "Ventana Tres", "created_at": "2022-01-01"},
        {"account_id": "ACC-8112", "hubspot_id": "HS-810012", "account_name": "Sin Uso", "created_at": "2022-01-01"},
        {"account_id": "ACC-8113", "hubspot_id": "HS-810013", "account_name": "Ventana Vacia", "created_at": "2022-01-01"},
        {"account_id": "ACC-8114", "hubspot_id": "HS-810014", "account_name": "Sube Mucho", "created_at": "2022-01-01"},
        {"account_id": "ACC-8115", "hubspot_id": "HS-810015", "account_name": "Sube Poco", "created_at": "2022-01-01"},
    ]
    usage = [
        *[
            _usage("ACC-8110", month, users)
            for month, users in zip(
                ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06", "2024-07"],
                [20, 18, 16, 12, 10, 8, 6],
            )
        ],
        _usage("ACC-8110", "2024-08", 999),  # mes de baja: no debe entrar al promedio final
        _usage("ACC-8111", "2024-01", 100),
        _usage("ACC-8111", "2024-02", 50),
        _usage("ACC-8111", "2024-03", 25),
        _usage("ACC-8113", "2021-01", 10),
        _usage("ACC-8113", "2021-02", 10),
        _usage("ACC-8113", "2021-03", 10),
        # ACC-8114: primeros 3 meses 10; ventana final (2024-03 a 2024-05) 10, 20, 60 -> caida -2.0
        _usage("ACC-8114", "2024-01", 10), _usage("ACC-8114", "2024-02", 10), _usage("ACC-8114", "2024-03", 10),
        _usage("ACC-8114", "2024-04", 20), _usage("ACC-8114", "2024-05", 60),
        # ACC-8115: primeros 3 meses 10; ventana final 10, 10, 15 -> caida -0.166667
        _usage("ACC-8115", "2024-01", 10), _usage("ACC-8115", "2024-02", 10), _usage("ACC-8115", "2024-03", 10),
        _usage("ACC-8115", "2024-04", 10), _usage("ACC-8115", "2024-05", 15),
    ]
    deals = [
        # Deal huerfano: hubspot_id sin ninguna empresa real ni clon.
        {"deal_id": "D-819999", "hubspot_id": "HS-819999", "stage": "closedwon", "amount": 500.0,
         "created_date": "2022-01-01", "close_date": "2022-01-10", "pipeline": "New Business", "lead_source": "Web"},
        # Deal sobre el clon HS-900081: se remapea al sobreviviente
        # HS-810003 y no debe aparecer como huerfano.
        {"deal_id": "D-810081", "hubspot_id": "HS-900081", "stage": "closedwon", "amount": 300.0,
         "created_date": "2022-02-01", "close_date": "2022-02-10", "pipeline": "New Business", "lead_source": "Web"},
    ]
    return {
        "raw_companies": pd.DataFrame(companies),
        "raw_accounts": pd.DataFrame(accounts),
        "raw_product_usage": pd.DataFrame(usage),
        "raw_deals": pd.DataFrame(deals),
        "raw_marketing_touches": _EMPTY_TOUCHES,
        "raw_customers": _EMPTY_CUSTOMERS,
        "raw_tickets": _EMPTY_TICKETS,
    }


@pytest.fixture(scope="module")
def analysis_fixture(tmp_path_factory):
    raw_tables = _minimal_raw_tables()
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    assert len(identity_outputs["quarantine_companies"]) == 1
    db_path = tmp_path_factory.mktemp("analysis_rules") / "worky.duckdb"
    con = open_connection(db_path)
    try:
        assembly_outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
        result = run_analysis(con)
    finally:
        con.close()
    return result, assembly_outputs, identity_outputs


def test_a1_01_dos_columnas_mrr_y_fila_de_totales(analysis_fixture) -> None:
    result, _, _ = analysis_fixture
    active_mrr = result.outputs["analysis_a1_01_active_mrr"]
    total = active_mrr.loc[active_mrr["row_type"] == "total"].iloc[0]
    assert total["mrr_crm_mxn"] == "6300.00"
    assert total["mrr_total_mxn"] == "6300.00"
    segments = active_mrr.loc[active_mrr["row_type"] == "segment"]
    assert set(zip(segments["segment"], segments["industry"])) == {("SMB", "Retail"), ("Enterprise", "Tech")}


def test_a1_01_total_coincide_con_master_dataset(analysis_fixture) -> None:
    result, assembly_outputs, _ = analysis_fixture
    active_mrr = result.outputs["analysis_a1_01_active_mrr"]
    total = active_mrr.loc[active_mrr["row_type"] == "total"].iloc[0]
    master_dataset = assembly_outputs["master_dataset"]
    active = master_dataset.loc[master_dataset["churn_status"] == "active", "mrr_mxn"]
    expected = round(pd.to_numeric(active, errors="coerce").fillna(0).sum(), 2)
    assert round(float(total["mrr_total_mxn"]), 2) == expected


def test_a1_02_mes_de_baja_excluido_de_la_ventana(analysis_fixture) -> None:
    result, _, _ = analysis_fixture
    usage_drop = result.outputs["analysis_a1_02_usage_drop"].set_index("hubspot_id")
    row = usage_drop.loc["HS-810010"]
    assert row["avg_users_last_3_before_churn"] == "8.00"
    assert bool(row["windows_overlap"]) is False
    assert row["drop_status"] == "computed"


def test_a1_02_windows_overlap_en_cuenta_de_tres_meses(analysis_fixture) -> None:
    result, _, _ = analysis_fixture
    usage_drop = result.outputs["analysis_a1_02_usage_drop"].set_index("hubspot_id")
    row = usage_drop.loc["HS-810011"]
    assert bool(row["windows_overlap"]) is True
    assert row["drop_status"] == "computed"
    assert row["drop_relative"] == "0.000000"


def test_a1_02_drop_status_sin_uso(analysis_fixture) -> None:
    result, _, _ = analysis_fixture
    usage_drop = result.outputs["analysis_a1_02_usage_drop"].set_index("hubspot_id")
    row = usage_drop.loc["HS-810012"]
    assert row["drop_status"] == "no_usage"
    assert pd.isna(row["drop_relative"])


def test_a1_02_drop_status_ventana_final_vacia(analysis_fixture) -> None:
    result, _, _ = analysis_fixture
    usage_drop = result.outputs["analysis_a1_02_usage_drop"].set_index("hubspot_id")
    row = usage_drop.loc["HS-810013"]
    assert row["drop_status"] == "final_window_empty"
    assert row["avg_users_first_3"] == "10.00"
    assert pd.isna(row["drop_relative"])


def test_a1_05_deal_huerfano_detectado(analysis_fixture) -> None:
    result, _, identity_outputs = analysis_fixture
    orphan_deals = result.outputs["analysis_a1_05_orphan_deals"]
    assert set(orphan_deals["deal_id"]) == set(identity_outputs["quarantine_deals"]["deal_id"])
    assert "D-819999" in set(orphan_deals["deal_id"])


def test_a1_05_deal_de_clon_remapeado_no_es_huerfano(analysis_fixture) -> None:
    result, _, _ = analysis_fixture
    orphan_deals = result.outputs["analysis_a1_05_orphan_deals"]
    assert "D-810081" not in set(orphan_deals["deal_id"])


def test_analysis_contracts_pasan_sobre_el_fixture(analysis_fixture) -> None:
    result, assembly_outputs, identity_outputs = analysis_fixture
    run_analysis_contracts(
        result.outputs, assembly_outputs["master_dataset"], identity_outputs["quarantine_deals"]
    )


def test_a1_02_orden_numerico_descendente_con_negativos(analysis_fixture) -> None:
    # R3-a1-02: drop_relative es texto, pero el orden debe ser numerico:
    # los negativos van al final de las filas calculadas, del menos al mas negativo.
    result, _, _ = analysis_fixture
    usage_drop = result.outputs["analysis_a1_02_usage_drop"]
    computed = usage_drop[usage_drop["drop_status"] == "computed"]
    values = [float(v) for v in computed["drop_relative"]]
    assert values == sorted(values, reverse=True)
    assert values[-1] == -2.0
    assert computed.iloc[-1]["hubspot_id"] == "HS-810014"
    assert computed.iloc[-2]["hubspot_id"] == "HS-810015"
    first_uncomputed = usage_drop.index[usage_drop["drop_status"] != "computed"].min()
    assert first_uncomputed > computed.index.max()
