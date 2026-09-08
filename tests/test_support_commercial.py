"""Pruebas de integracion de `mart_support.sql` y `mart_commercial.sql` (seccion 4.5 del diseno).

Corre el ensamblaje completo sobre un fixture minimo de cinco empresas
activas, cada una construida para ejercitar una regla distinta:
conteos de tickets y `tickets_urgent`, el promedio de `csat_score` solo
sobre los tickets que trajeron puntaje, el desempate del primer touch
por `touch_id`, el respaldo a `lead_source` cuando no hay touch, el
valor `unknown` cuando no hay ni touch ni deal, y `closed_revenue_mxn`
normalizado a mensual (regla 12x del ADR-002) sin el deal huerfano ni
el deal abierto. Sigue el mismo patron que `tests/test_usage_trend.py`.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset, open_connection


def _company(hubspot_id: str, name: str, domain: str) -> dict:
    return {
        "hubspot_id": hubspot_id, "name": name, "domain": domain, "segment": "SMB",
        "industry": "Retail", "mrr": 1000.0, "currency": "MXN", "signup_date": "2022-01-01",
        "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": None,
    }


def _minimal_raw_tables() -> dict[str, pd.DataFrame]:
    companies = [
        _company("HS-700001", "Touch Multi SA de CV", "touch700.com.mx"),
        _company("HS-700002", "Fallback Lead SA de CV", "fallback700.com.mx"),
        _company("HS-700003", "Sin Nada SA de CV", "sinnada700.com.mx"),
        _company("HS-700004", "Csat Parcial SA de CV", "csat700.com.mx"),
        _company("HS-700005", "Cero Tickets SA de CV", "cero700.com.mx"),
    ]
    accounts = [
        {"account_id": "ACC-7001", "hubspot_id": "HS-700001", "account_name": "Touch Multi", "created_at": "2022-01-01"},
    ]
    usage = [
        {"account_id": "ACC-7001", "month": "2024-08", "active_users": 10, "logins": 20,
         "payroll_runs_completed": 1, "features_used": 3, "api_calls": 100},
    ]
    customers = [
        {"vitally_id": "cus_7001", "domain": "touch700.com.mx", "company_name": "Touch Multi SA de CV", "csm_email": "x@worky.mx"},
        {"vitally_id": "cus_7004", "domain": "csat700.com.mx", "company_name": "Csat Parcial SA de CV", "csm_email": "x@worky.mx"},
        {"vitally_id": "cus_7005", "domain": "cero700.com.mx", "company_name": "Cero Tickets SA de CV", "csm_email": "x@worky.mx"},
    ]
    tickets = [
        # HS-700001 (via cus_7001): 3 tickets, 1 Urgent, csat solo en 2 de 3 -> promedio (4+2)/2 = 3.00
        {"ticket_id": "T-7001a", "vitally_id": "cus_7001", "created_date": "2024-06-01", "priority": "Urgent", "status": "closed", "category": "bug", "resolution_hours": 2, "csat_score": 4},
        {"ticket_id": "T-7001b", "vitally_id": "cus_7001", "created_date": "2024-06-02", "priority": "Low", "status": "closed", "category": "billing", "resolution_hours": 1, "csat_score": 2},
        {"ticket_id": "T-7001c", "vitally_id": "cus_7001", "created_date": "2024-06-03", "priority": "Medium", "status": "closed", "category": "bug", "resolution_hours": 3, "csat_score": None},
        # HS-700004 (via cus_7004): 2 tickets, ninguno Urgent, csat solo en 1 -> promedio exactamente ese valor
        {"ticket_id": "T-7004a", "vitally_id": "cus_7004", "created_date": "2024-06-01", "priority": "Low", "status": "closed", "category": "bug", "resolution_hours": 2, "csat_score": 5},
        {"ticket_id": "T-7004b", "vitally_id": "cus_7004", "created_date": "2024-06-02", "priority": "Low", "status": "closed", "category": "billing", "resolution_hours": 1, "csat_score": None},
        # HS-700005 (via cus_7005): sin ningun ticket -> 0, 0, csat vacio
    ]
    marketing_touches = [
        # HS-700001: dos touches con la misma fecha, mas antigua que la tercera;
        # el desempate por touch_id debe elegir "MT-A700" (Paid Search), no
        # "MT-B700" (Organic) ni el touch mas reciente (Referral).
        {"touch_id": "MT-B700", "hubspot_id": "HS-700001", "channel": "Organic", "touch_date": "2022-02-01", "campaign": "spring"},
        {"touch_id": "MT-A700", "hubspot_id": "HS-700001", "channel": "Paid Search", "touch_date": "2022-02-01", "campaign": "spring"},
        {"touch_id": "MT-C700", "hubspot_id": "HS-700001", "channel": "Referral", "touch_date": "2022-03-01", "campaign": "spring"},
    ]
    deals = [
        # HS-700002: sin touch, respaldo de lead_source por el primer deal por
        # created_date ("Referral", el mas antiguo). Dos deals closedwon, uno
        # cotizado al valor anual (12x el mensual) para probar la normalizacion
        # en closed_revenue_mxn, y un tercero abierto que debe quedar fuera.
        {"deal_id": "D-7002A", "hubspot_id": "HS-700002", "stage": "closedwon", "amount": 5000.0,
         "created_date": "2022-03-01", "close_date": "2022-03-15", "pipeline": "New Business", "lead_source": "Referral"},
        {"deal_id": "D-7002B", "hubspot_id": "HS-700002", "stage": "closedwon", "amount": 60000.0,
         "created_date": "2022-04-01", "close_date": "2022-04-15", "pipeline": "Renewal", "lead_source": "Web"},
        {"deal_id": "D-7002C", "hubspot_id": "HS-700002", "stage": "qualifiedtobuy", "amount": 9999.0,
         "created_date": "2022-05-01", "close_date": None, "pipeline": "New Business", "lead_source": "Web"},
        # Deal huerfano: su hubspot_id no pertenece a ninguna empresa de este
        # fixture, asi que resolve_identity lo manda a quarantine_deals y no
        # debe sumar en el closed_revenue_mxn de nadie.
        {"deal_id": "D-9999999", "hubspot_id": "HS-999999", "stage": "closedwon", "amount": 3000.0,
         "created_date": "2022-01-01", "close_date": "2022-01-10", "pipeline": "New Business", "lead_source": "Web"},
    ]
    return {
        "raw_companies": pd.DataFrame(companies),
        "raw_accounts": pd.DataFrame(accounts),
        "raw_product_usage": pd.DataFrame(usage),
        "raw_deals": pd.DataFrame(deals),
        "raw_marketing_touches": pd.DataFrame(marketing_touches),
        "raw_customers": pd.DataFrame(customers),
        "raw_tickets": pd.DataFrame(tickets),
    }


@pytest.fixture(scope="module")
def minimal_master_dataset(tmp_path_factory) -> pd.DataFrame:
    raw_tables = _minimal_raw_tables()
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    # Sin clones ni deals huerfanos ligados a companies (D-9999999 si es
    # huerfano, asi que quarantine_deals no queda vacia): ejercita de paso
    # el arreglo de la tarea 4.15 sobre quarantine_companies, que aqui si
    # sale con cero filas.
    assert len(identity_outputs["quarantine_companies"]) == 0
    db_path = tmp_path_factory.mktemp("support_commercial") / "worky.duckdb"
    con = open_connection(db_path)
    try:
        outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
    finally:
        con.close()
    return outputs["master_dataset"].set_index("hubspot_id")


def test_conteo_de_tickets_y_urgentes(minimal_master_dataset: pd.DataFrame) -> None:
    row = minimal_master_dataset.loc["HS-700001"]
    assert int(row["tickets_total"]) == 3
    assert int(row["tickets_urgent"]) == 1


def test_csat_avg_promedia_solo_los_tickets_con_puntaje(minimal_master_dataset: pd.DataFrame) -> None:
    assert minimal_master_dataset.loc["HS-700001", "csat_avg"] == "3.00"
    assert minimal_master_dataset.loc["HS-700004", "csat_avg"] == "5.00"


def test_empresa_sin_tickets_queda_en_cero_y_csat_vacio(minimal_master_dataset: pd.DataFrame) -> None:
    row = minimal_master_dataset.loc["HS-700005"]
    assert int(row["tickets_total"]) == 0
    assert int(row["tickets_urgent"]) == 0
    assert pd.isna(row["csat_avg"])


def test_primer_touch_desempatado_por_touch_id(minimal_master_dataset: pd.DataFrame) -> None:
    assert minimal_master_dataset.loc["HS-700001", "acquisition_channel"] == "Paid Search"


def test_respaldo_de_lead_source_sin_touch(minimal_master_dataset: pd.DataFrame) -> None:
    assert minimal_master_dataset.loc["HS-700002", "acquisition_channel"] == "Referral"


def test_unknown_sin_touch_ni_deal(minimal_master_dataset: pd.DataFrame) -> None:
    assert minimal_master_dataset.loc["HS-700003", "acquisition_channel"] == "unknown"


def test_closed_revenue_normalizado_sin_deal_abierto_ni_huerfano(minimal_master_dataset: pd.DataFrame) -> None:
    # 5000 (mensual) + 60000 normalizado a 5000 (12x el minimo) = 10000;
    # el deal abierto (9999) y el huerfano (3000) quedan fuera.
    assert minimal_master_dataset.loc["HS-700002", "closed_revenue_mxn"] == "10000.00"
    assert minimal_master_dataset.loc["HS-700003", "closed_revenue_mxn"] == "0.00"
