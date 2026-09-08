"""Pruebas de `worky_engine.identity_resolution`: cascada T0 a T3, veto y revision manual.

Corre `resolve_identity` sobre el fixture sintetico de doce empresas y
confirma los casos que fija la seccion 7 del diseno: la cascada
completa, el veto de un dominio compartido, el nombre truncado resuelto
por T2, y un bloque de fecha con mas de un candidato que no se puede
resolver ni siquiera en T3.
"""

from __future__ import annotations

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
