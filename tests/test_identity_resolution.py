"""Pruebas de `worky_engine.identity_resolution`: cascada T0 a T3, veto y revision manual.

Corre `resolve_identity` sobre el fixture sintetico de doce empresas y
confirma los casos que fija la seccion 7 del diseno: la cascada
completa, el veto de un dominio compartido, el nombre truncado resuelto
por T2, y un bloque de fecha con mas de un candidato que no se puede
resolver ni siquiera en T3.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from tests.fixtures.mini_dataset import build_mini_dataset
from worky_engine.identity_resolution import resolve_identity


@pytest.fixture(scope="module")
def mini_result() -> dict[str, pd.DataFrame]:
    return resolve_identity(build_mini_dataset(), existing_crosswalk=None, reuse_crosswalk=True)


def _audit_row(audit: pd.DataFrame, source_id: str) -> pd.Series:
    matches = audit[audit["source_id"] == source_id]
    assert len(matches) == 1, f"se esperaba exactamente una fila de match_audit para {source_id!r}"
    return matches.iloc[0]


def _empty_raw_tables() -> dict[str, pd.DataFrame]:
    """Las cinco tablas que un caso construido a mano no necesita, ya vacias.

    `raw_companies` y `raw_accounts` los sobreescribe cada prueba que la
    use; el resto queda vacio porque estos casos no ejercitan T1, deals
    ni las columnas de calibracion.
    """
    return {
        "raw_deals": pd.DataFrame(
            columns=["deal_id", "hubspot_id", "stage", "amount", "created_date", "close_date", "pipeline", "lead_source"]
        ),
        "raw_marketing_touches": pd.DataFrame(
            columns=["touch_id", "hubspot_id", "channel", "touch_date", "campaign"]
        ),
        "raw_product_usage": pd.DataFrame(
            columns=["account_id", "month", "active_users", "logins", "payroll_runs_completed", "features_used", "api_calls"]
        ),
        "raw_customers": pd.DataFrame(columns=["vitally_id", "domain", "company_name", "csm_email"]),
        "raw_tickets": pd.DataFrame(
            columns=["ticket_id", "vitally_id", "created_date", "priority", "status", "category", "resolution_hours", "csat_score"]
        ),
    }


def test_cascada_t0_por_hubspot_id(mini_result: dict[str, pd.DataFrame]) -> None:
    row = _audit_row(mini_result["match_audit"], "ACC-9001")
    assert row["tier"] == "T0"
    assert row["blocking_rule"] == "hubspot_id"
    # T0 no calcula puntaje: la celda debe quedar vacia, nunca la cadena
    # literal "nan" que produce pandas al convertir None a NaN y luego
    # formatearlo sin revertir esa conversion.
    assert row["score"] == ""


def test_cascada_t1_por_dominio_y_token_set_ratio(mini_result: dict[str, pd.DataFrame]) -> None:
    row = _audit_row(mini_result["match_audit"], "cus_9001")
    assert row["tier"] == "T1"
    assert row["blocking_rule"] == "domain_label"
    assert float(row["score"]) >= 90


def test_cascada_t2_con_nombre_truncado_acc_2027(mini_result: dict[str, pd.DataFrame]) -> None:
    # ACC-9002 tiene el nombre truncado "Torres y Compa" contra "Torres y Compania" (HS-200003),
    # el mismo patron que el caso ACC-2027 del dataset real resuelto contra HS-100028.
    row = _audit_row(mini_result["match_audit"], "ACC-9002")
    assert row["tier"] == "T2"
    assert row["blocking_rule"] == "signup_date"
    assert float(row["score"]) == 100.0
    assert row["master_id"] == _audit_row(mini_result["match_audit"], "HS-200003")["master_id"]


def test_veto_club290_domain_compartido(mini_result: dict[str, pd.DataFrame]) -> None:
    # HS-200004 y HS-200005 comparten club300.com.mx, con nombres distintos,
    # fechas de alta distintas y MRR en ambas: el mismo patron que club290.com.mx.
    row_a = _audit_row(mini_result["match_audit"], "HS-200004")
    row_b = _audit_row(mini_result["match_audit"], "HS-200005")

    assert row_a["tier"] == "S"
    assert row_b["tier"] == "S"
    assert bool(row_a["veto_applied"])
    assert bool(row_b["veto_applied"])
    assert row_a["veto_reason"] == "shared_domain_distinct_company"
    assert row_b["veto_reason"] == "shared_domain_distinct_company"
    # cada empresa conserva su propio master_id: no se fusionan entre si.
    assert row_a["master_id"] != row_b["master_id"]


def test_bloque_de_fecha_con_dos_candidatos_termina_en_revision_manual() -> None:
    # Dos empresas con la misma signup_date y nombres que ambos superan
    # partial_ratio >= 90 contra la cuenta: T2 no puede elegir un unico
    # candidato, baja a T3, y como ahi tampoco hay margen, termina en M.
    raw_tables = {
        **_empty_raw_tables(),
        "raw_companies": pd.DataFrame(
            [
                {
                    "hubspot_id": "HS-300001", "name": "Constructora del Norte",
                    "domain": "norte300.com.mx", "segment": "SMB", "industry": "Construccion",
                    "mrr": 4000.0, "currency": "MXN", "signup_date": "2022-03-01",
                    "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": None,
                },
                {
                    "hubspot_id": "HS-300002", "name": "Constructora del Sur",
                    "domain": "sur300.com.mx", "segment": "SMB", "industry": "Construccion",
                    "mrr": 5000.0, "currency": "MXN", "signup_date": "2022-03-01",
                    "csm_owner": "Y", "plan": "Basico", "state": "CDMX", "churn_date": None,
                },
            ]
        ),
        "raw_accounts": pd.DataFrame(
            [{"account_id": "ACC-3001", "hubspot_id": None, "account_name": "Constructora", "created_at": "2022-03-01"}]
        ),
    }

    result = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)

    row = _audit_row(result["match_audit"], "ACC-3001")
    assert row["tier"] == "M"
    assert bool(row["needs_review"])
    assert row["candidate_count"] == 2
    assert pd.isna(row["master_id"])
    # nunca se desempata por orden de filas: el margen medido queda en cero.
    assert float(row["score_margin"]) == 0.0


def test_cascada_t3_por_wratio_global_con_margen(mini_result: dict[str, pd.DataFrame]) -> None:
    # La cuenta no tiene hubspot_id ni signup_date que calce con ninguna
    # empresa (T0 y T2 no aplican), pero su WRatio contra la empresa
    # correcta es 94 o mas con un margen de al menos 10 sobre la segunda
    # mejor candidata: se resuelve en T3 con confianza media.
    raw_tables = {
        **_empty_raw_tables(),
        "raw_companies": pd.DataFrame(
            [
                {
                    "hubspot_id": "HS-400001", "name": "Manufacturas Aguilar",
                    "domain": "aguilar400.com.mx", "segment": "SMB", "industry": "Manufactura",
                    "mrr": 3000.0, "currency": "MXN", "signup_date": "2021-01-15",
                    "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": None,
                },
                {
                    "hubspot_id": "HS-400002", "name": "Distribuidora Ponce",
                    "domain": "ponce400.com.mx", "segment": "SMB", "industry": "Logistica",
                    "mrr": 4000.0, "currency": "MXN", "signup_date": "2021-02-15",
                    "csm_owner": "Y", "plan": "Basico", "state": "CDMX", "churn_date": None,
                },
                {
                    "hubspot_id": "HS-400003", "name": "Servicios del Bajio",
                    "domain": "bajio400.com.mx", "segment": "SMB", "industry": "Servicios",
                    "mrr": 5000.0, "currency": "MXN", "signup_date": "2021-03-15",
                    "csm_owner": "Z", "plan": "Basico", "state": "CDMX", "churn_date": None,
                },
            ]
        ),
        "raw_accounts": pd.DataFrame(
            [{"account_id": "ACC-4001", "hubspot_id": None, "account_name": "Manufacturas Aguilar SA", "created_at": "2023-09-09"}]
        ),
    }

    result = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)

    row = _audit_row(result["match_audit"], "ACC-4001")
    assert row["tier"] == "T3"
    assert row["blocking_rule"] == "global"
    assert float(row["score"]) >= 94
    assert float(row["score_margin"]) >= 10
    crosswalk = result["identity_crosswalk"]
    linked = crosswalk[crosswalk["hubspot_id"] == "HS-400001"].iloc[0]
    assert linked["master_id"] == row["master_id"]
    assert linked["account_match_tier"] == "T3"


def test_quarantine_fila_clon_aislada(mini_result: dict[str, pd.DataFrame]) -> None:
    # HS-900010 es el clon de HS-200001 en el fixture: debe quedar en
    # quarantine_companies con su codigo de razon y nunca aparecer en el
    # crosswalk, sin fusionarse ni eliminarse.
    quarantine = mini_result["quarantine_companies"]
    clone_rows = quarantine[quarantine["hubspot_id"] == "HS-900010"]
    assert len(clone_rows) == 1
    clone_row = clone_rows.iloc[0]
    assert clone_row["reason_code"] == "duplicate_company_clone"
    assert clone_row["survivor_hubspot_id"] == "HS-200001"

    crosswalk = mini_result["identity_crosswalk"]
    assert (crosswalk["hubspot_id"] == "HS-900010").sum() == 0


def test_quarantine_deal_huerfano_aislado(mini_result: dict[str, pd.DataFrame]) -> None:
    # D-9002 apunta a HS-999999, que no existe en companies: debe quedar
    # en quarantine_deals con su monto, y no puede ser un cruce de nada.
    orphan_deals = mini_result["quarantine_deals"]
    orphan_rows = orphan_deals[orphan_deals["deal_id"] == "D-9002"]
    assert len(orphan_rows) == 1
    orphan_row = orphan_rows.iloc[0]
    assert orphan_row["hubspot_id"] == "HS-999999"
    assert orphan_row["amount"] == "3000.00"
    assert orphan_row["reason_code"] == "orphan_deal_missing_company"

    crosswalk = mini_result["identity_crosswalk"]
    assert (crosswalk["hubspot_id"] == "HS-999999").sum() == 0


def test_fila_completa_de_crosswalk_con_los_tres_ids(mini_result: dict[str, pd.DataFrame]) -> None:
    # HS-200001 se resuelve en los tres sistemas del fixture (cuenta
    # ACC-9001, cliente cus_9001): su fila de crosswalk debe traer los
    # tres ids de origen a la vez.
    crosswalk = mini_result["identity_crosswalk"]
    row = crosswalk[crosswalk["hubspot_id"] == "HS-200001"].iloc[0]

    assert row["account_id"] == "ACC-9001"
    assert row["vitally_id"] == "cus_9001"
    assert pd.notna(row["master_id"]) and row["master_id"] != ""
    assert row["confidence_tier"] in {"T0", "T1", "T2", "T3"}


def test_dos_accounts_al_mismo_master_id_se_contienen_sin_abortar() -> None:
    # Dos accounts con el mismo hubspot_id resuelven ambos por T0 a la
    # misma empresa: el crosswalk solo tiene una fila por company, y
    # ahora conserva el primer account_id por orden de entrada (JD-01,
    # contencion) en vez de abortar la corrida. La segunda decision
    # queda marcada para revision manual con la evidencia de cual id se
    # conservo y cual se descarto.
    raw_tables = {
        **_empty_raw_tables(),
        "raw_companies": pd.DataFrame(
            [
                {
                    "hubspot_id": "HS-500002", "name": "Colision ProductDB SA de CV",
                    "domain": "colision502.com.mx", "segment": "SMB", "industry": "Retail",
                    "mrr": 1000.0, "currency": "MXN", "signup_date": "2022-01-01",
                    "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": None,
                },
            ]
        ),
        "raw_accounts": pd.DataFrame(
            [
                {"account_id": "ACC-500001", "hubspot_id": "HS-500002", "account_name": "Colision ProductDB", "created_at": "2022-01-01"},
                {"account_id": "ACC-500002", "hubspot_id": "HS-500002", "account_name": "Colision ProductDB Otra", "created_at": "2022-02-01"},
            ]
        ),
    }

    result = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)

    crosswalk_row = result["identity_crosswalk"]
    crosswalk_row = crosswalk_row[crosswalk_row["hubspot_id"] == "HS-500002"].iloc[0]
    assert crosswalk_row["account_id"] == "ACC-500001"

    kept_row = _audit_row(result["match_audit"], "ACC-500001")
    assert not bool(kept_row["needs_review"])
    assert "duplicate_link" not in json.loads(kept_row["evidence_json"])

    dropped_row = _audit_row(result["match_audit"], "ACC-500002")
    assert bool(dropped_row["needs_review"])
    assert json.loads(dropped_row["evidence_json"])["duplicate_link"] == {
        "kept": "ACC-500001", "dropped": "ACC-500002", "field": "account_id",
    }


def test_dos_customers_al_mismo_master_id_se_contienen_sin_abortar() -> None:
    # Dos customers de Vitally comparten dominio y coinciden por nombre
    # con la unica empresa de ese dominio: ambos resuelven en T1 al
    # mismo master_id, y el crosswalk conserva el primer vitally_id por
    # orden de entrada (JD-01, contencion) en vez de abortar la corrida.
    raw_tables = {
        **_empty_raw_tables(),
        "raw_companies": pd.DataFrame(
            [
                {
                    "hubspot_id": "HS-500001", "name": "Colision Vitally SA de CV",
                    "domain": "colision500.com.mx", "segment": "SMB", "industry": "Retail",
                    "mrr": 1000.0, "currency": "MXN", "signup_date": "2022-01-01",
                    "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": None,
                },
            ]
        ),
        "raw_accounts": pd.DataFrame(columns=["account_id", "hubspot_id", "account_name", "created_at"]),
        "raw_customers": pd.DataFrame(
            [
                {"vitally_id": "cus_500001", "domain": "colision500.com.mx", "company_name": "Colision Vitally SA de CV", "csm_email": "x@worky.mx"},
                {"vitally_id": "cus_500002", "domain": "colision500.com.mx", "company_name": "Colision Vitally SA de CV", "csm_email": "y@worky.mx"},
            ]
        ),
    }

    result = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)

    crosswalk_row = result["identity_crosswalk"]
    crosswalk_row = crosswalk_row[crosswalk_row["hubspot_id"] == "HS-500001"].iloc[0]
    assert crosswalk_row["vitally_id"] == "cus_500001"

    kept_row = _audit_row(result["match_audit"], "cus_500001")
    assert not bool(kept_row["needs_review"])
    assert "duplicate_link" not in json.loads(kept_row["evidence_json"])

    dropped_row = _audit_row(result["match_audit"], "cus_500002")
    assert bool(dropped_row["needs_review"])
    assert json.loads(dropped_row["evidence_json"])["duplicate_link"] == {
        "kept": "cus_500001", "dropped": "cus_500002", "field": "vitally_id",
    }


def test_mismo_account_id_repetido_se_tolera_en_silencio() -> None:
    # El mismo account_id (identico, no solo el mismo hubspot_id) puede
    # llegar dos veces en raw_accounts sin que eso sea una colision real:
    # ambas filas resuelven al mismo master_id con el mismo id, y ninguna
    # de las dos debe quedar marcada para revision manual.
    raw_tables = {
        **_empty_raw_tables(),
        "raw_companies": pd.DataFrame(
            [
                {
                    "hubspot_id": "HS-500010", "name": "Repetido SA de CV",
                    "domain": "repetido510.com.mx", "segment": "SMB", "industry": "Retail",
                    "mrr": 1000.0, "currency": "MXN", "signup_date": "2022-01-01",
                    "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": None,
                },
            ]
        ),
        "raw_accounts": pd.DataFrame(
            [
                {"account_id": "ACC-500010", "hubspot_id": "HS-500010", "account_name": "Repetido", "created_at": "2022-01-01"},
                {"account_id": "ACC-500010", "hubspot_id": "HS-500010", "account_name": "Repetido", "created_at": "2022-01-01"},
            ]
        ),
    }

    result = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)

    rows = result["match_audit"]
    rows = rows[rows["source_id"] == "ACC-500010"]
    assert len(rows) == 2
    assert not rows["needs_review"].any()
    for evidence_json in rows["evidence_json"]:
        assert "duplicate_link" not in json.loads(evidence_json)

    crosswalk_row = result["identity_crosswalk"]
    crosswalk_row = crosswalk_row[crosswalk_row["hubspot_id"] == "HS-500010"].iloc[0]
    assert crosswalk_row["account_id"] == "ACC-500010"


def test_cuarentena_vacia_trae_el_esquema_completo_con_cero_filas() -> None:
    """Tarea 4.15: sin clones ni deals huerfanos, las dos cuarentenas deben seguir siendo registrables en DuckDB.

    Antes del arreglo, `_to_quarantine_companies_frame`/`_to_quarantine_deals_frame`
    devolvian un DataFrame sin columnas cuando la lista de entrada venia
    vacia, y `con.register()` de DuckDB rechazaba esa forma con "Need a
    DataFrame with at least one column".
    """
    companies = [
        {"hubspot_id": "HS-800001", "name": "Sin Clones Uno SA de CV", "domain": "sinclones801.com.mx",
         "segment": "SMB", "industry": "Retail", "mrr": 1000.0, "currency": "MXN", "signup_date": "2022-01-01",
         "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": None},
        {"hubspot_id": "HS-800002", "name": "Sin Clones Dos SA de CV", "domain": "sinclones802.com.mx",
         "segment": "SMB", "industry": "Retail", "mrr": 2000.0, "currency": "MXN", "signup_date": "2022-02-01",
         "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": None},
    ]
    deals = [
        # El deal apunta a una de las dos empresas reales: no hay huerfano.
        {"deal_id": "D-8001", "hubspot_id": "HS-800001", "stage": "closedwon", "amount": 1000.0,
         "created_date": "2022-01-15", "close_date": "2022-01-20", "pipeline": "New Business", "lead_source": "Web"},
    ]
    raw_tables = {
        "raw_companies": pd.DataFrame(companies),
        "raw_deals": pd.DataFrame(deals),
        "raw_marketing_touches": pd.DataFrame(columns=["touch_id", "hubspot_id", "channel", "touch_date", "campaign"]),
        "raw_accounts": pd.DataFrame(columns=["account_id", "hubspot_id", "account_name", "created_at"]),
        "raw_product_usage": pd.DataFrame(columns=["account_id", "month", "active_users"]),
        "raw_customers": pd.DataFrame(columns=["vitally_id", "domain", "company_name", "csm_email"]),
        "raw_tickets": pd.DataFrame(
            columns=["ticket_id", "vitally_id", "created_date", "priority", "status", "category", "resolution_hours", "csat_score"]
        ),
    }
    outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)

    quarantine_companies = outputs["quarantine_companies"]
    quarantine_deals = outputs["quarantine_deals"]
    assert len(quarantine_companies) == 0
    assert len(quarantine_deals) == 0
    assert list(quarantine_companies.columns) == [
        "hubspot_id", "company_name", "domain", "mrr", "currency", "signup_date",
        "churn_date", "reason_code", "survivor_hubspot_id", "survivor_master_id",
        "evidence_json", "ruleset_version", "decided_at",
    ]
    assert list(quarantine_deals.columns) == [
        "deal_id", "hubspot_id", "stage", "amount", "created_date", "close_date",
        "pipeline", "lead_source", "reason_code", "ruleset_version", "decided_at",
    ]

    # El registro en DuckDB, que era el sintoma original del hallazgo, no
    # debe volver a fallar con "Need a DataFrame with at least one column".
    import duckdb

    con = duckdb.connect()
    try:
        con.register("quarantine_companies", quarantine_companies)
        con.register("quarantine_deals", quarantine_deals)
    finally:
        con.close()
