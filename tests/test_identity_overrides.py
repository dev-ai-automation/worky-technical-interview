"""Pruebas de `worky_engine.identity_resolution.overrides`: D14 a D17 (`a4-warehouse-model`).

Fixture minimo propio, dos empresas y una sola cuenta de `product_db`
sin vinculo claro contra ninguna de las dos (cae en revision manual,
nivel M): la misma forma que usa `tests/test_support_commercial.py`
para no extender `tests/fixtures/mini_dataset.py`, cuyos conteos ya
fijan otras pruebas de identidad y de imputacion (seccion 9 del
diseno). Cubre los cinco escenarios del requisito "precedencia de
overrides sobre la cascada" (spec `identity-resolution`), mas la forma
del archivo que fija la seccion 4 del diseno.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from worky_engine.cli import _apply_overrides_if_present
from worky_engine.identity_resolution import resolve_identity
from worky_engine.identity_resolution.overrides import OverrideError, apply_overrides, load_overrides

OVERRIDE_HEADER = "source_system,source_id,master_id,decided_by,decided_at,reason\n"


def _company(hubspot_id: str, name: str, domain: str, signup_date: str) -> dict:
    return {
        "hubspot_id": hubspot_id, "name": name, "domain": domain, "segment": "SMB",
        "industry": "Retail", "mrr": 1000.0, "currency": "MXN", "signup_date": signup_date,
        "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": None,
    }


def _raw_tables() -> dict[str, pd.DataFrame]:
    companies = [
        _company("HS-9101", "Compania Alfa Industrial SA de CV", "alfa910.com.mx", "2022-01-01"),
        _company("HS-9102", "Compania Beta Servicios SA de CV", "beta910.com.mx", "2022-02-01"),
    ]
    accounts = [
        # Sin hubspot_id, y su created_at no calza con ningun signup_date del
        # fixture: T0 y T2 no aplican. El nombre tampoco se parece a ninguna
        # de las dos empresas, asi que el resguardo global T3/M termina en M
        # (revision manual), el punto de partida de este archivo.
        {
            "account_id": "ACC-9101", "hubspot_id": None,
            "account_name": "Consultoria Totalmente Distinta", "created_at": "2023-06-01",
        },
    ]
    customers = [
        {"vitally_id": "cus_9101", "domain": "beta910.com.mx", "company_name": "Compania Beta Servicios SA de CV", "csm_email": "x@worky.mx"},
    ]
    return {
        "raw_companies": pd.DataFrame(companies),
        "raw_accounts": pd.DataFrame(accounts),
        "raw_customers": pd.DataFrame(customers),
        "raw_deals": pd.DataFrame(
            columns=["deal_id", "hubspot_id", "stage", "amount", "created_date", "close_date", "pipeline", "lead_source"]
        ),
        "raw_marketing_touches": pd.DataFrame(
            columns=["touch_id", "hubspot_id", "channel", "touch_date", "campaign"]
        ),
        "raw_product_usage": pd.DataFrame(
            columns=["account_id", "month", "active_users", "logins", "payroll_runs_completed", "features_used", "api_calls"]
        ),
        "raw_tickets": pd.DataFrame(
            columns=["ticket_id", "vitally_id", "created_date", "priority", "status", "category", "resolution_hours", "csat_score"]
        ),
    }


def _identity_outputs() -> dict[str, pd.DataFrame]:
    return resolve_identity(_raw_tables(), existing_crosswalk=None, reuse_crosswalk=True)


def _master_id_for(crosswalk: pd.DataFrame, hubspot_id: str) -> str:
    return crosswalk.loc[crosswalk["hubspot_id"] == hubspot_id, "master_id"].iloc[0]


def _write_overrides(path: Path, rows: list[str]) -> Path:
    path.write_text(OVERRIDE_HEADER + "".join(rows), encoding="utf-8")
    return path


def test_punto_de_partida_acc_9101_queda_en_revision_manual() -> None:
    """Confirma la premisa del fixture antes de aplicar ningun override."""
    audit = _identity_outputs()["match_audit"]
    row = audit[audit["source_id"] == "ACC-9101"].iloc[0]
    assert row["tier"] == "M"
    assert bool(row["needs_review"])
    assert pd.isna(row["master_id"]) or row["master_id"] == ""


def test_override_fija_el_master_id_y_sale_de_revision_manual(tmp_path: Path) -> None:
    identity_outputs = _identity_outputs()
    master_id = _master_id_for(identity_outputs["identity_crosswalk"], "HS-9101")

    overrides_path = _write_overrides(
        tmp_path / "identity_overrides.csv",
        [f"product_db,ACC-9101,{master_id},ana.reyes,2024-08-15,cuenta confirmada por el CSM\n"],
    )
    overrides = load_overrides(overrides_path)
    result = apply_overrides(overrides, identity_outputs, _raw_tables())

    crosswalk_row = result["identity_crosswalk"]
    crosswalk_row = crosswalk_row[crosswalk_row["master_id"] == master_id].iloc[0]
    assert crosswalk_row["account_id"] == "ACC-9101"
    assert crosswalk_row["account_match_tier"] == "O"
    assert crosswalk_row["confidence_tier"] == "O"

    audit = result["match_audit"]
    override_rows = audit[(audit["source_id"] == "ACC-9101") & (audit["tier"] == "O")]
    assert len(override_rows) == 1
    override_row = override_rows.iloc[0]
    assert override_row["master_id"] == master_id
    assert not bool(override_row["needs_review"])
    assert override_row["blocking_rule"] == "override"
    assert override_row["decided_by"] == "ana.reyes"

    superseded_rows = audit[(audit["source_id"] == "ACC-9101") & (audit["tier"] == "M")]
    assert len(superseded_rows) == 1
    superseded_row = superseded_rows.iloc[0]
    assert not bool(superseded_row["needs_review"])
    assert "superseded_by" in json.loads(superseded_row["evidence_json"])

    # las cuarentenas de A0 no se tocan: siguen siendo las mismas salidas.
    assert result["quarantine_companies"] is identity_outputs["quarantine_companies"]
    assert result["quarantine_deals"] is identity_outputs["quarantine_deals"]


def test_override_que_repunta_source_id_ya_vinculado_limpia_el_master_anterior(tmp_path: Path) -> None:
    """R3-001: reapuntar un source_id que la cascada ya vinculo a otro master no debe dejarlo duplicado."""
    raw_tables = _raw_tables()
    raw_tables["raw_accounts"] = pd.concat(
        [
            raw_tables["raw_accounts"],
            pd.DataFrame(
                [
                    {
                        "account_id": "ACC-9102",
                        "hubspot_id": "HS-9101",
                        "account_name": "Compania Alfa Industrial SA de CV",
                        "created_at": "2022-01-01",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    crosswalk = identity_outputs["identity_crosswalk"]
    master_alfa = _master_id_for(crosswalk, "HS-9101")
    master_beta = _master_id_for(crosswalk, "HS-9102")

    # confirma la premisa: la cascada ya vinculo ACC-9102 a Alfa por T0 (hubspot_id).
    alfa_row = crosswalk[crosswalk["master_id"] == master_alfa].iloc[0]
    assert alfa_row["account_id"] == "ACC-9102"
    assert alfa_row["account_match_tier"] == "T0"

    overrides_path = _write_overrides(
        tmp_path / "identity_overrides.csv",
        [f"product_db,ACC-9102,{master_beta},ana.reyes,2024-08-15,se movio de compania por fusion\n"],
    )
    overrides = load_overrides(overrides_path)
    result = apply_overrides(overrides, identity_outputs, raw_tables)

    crosswalk = result["identity_crosswalk"]
    beta_row = crosswalk[crosswalk["master_id"] == master_beta].iloc[0]
    assert beta_row["account_id"] == "ACC-9102"
    assert beta_row["account_match_tier"] == "O"

    alfa_row = crosswalk[crosswalk["master_id"] == master_alfa].iloc[0]
    assert not alfa_row["account_id"] or pd.isna(alfa_row["account_id"])
    assert not alfa_row["account_match_tier"] or pd.isna(alfa_row["account_match_tier"])
    assert not alfa_row["confidence_tier"] or pd.isna(alfa_row["confidence_tier"])

    assert (crosswalk["account_id"] == "ACC-9102").sum() == 1


def test_override_con_master_id_inexistente_se_rechaza(tmp_path: Path) -> None:
    identity_outputs = _identity_outputs()
    overrides_path = _write_overrides(
        tmp_path / "identity_overrides.csv",
        ["product_db,ACC-9101,no-existe-1234,ana.reyes,2024-08-15,motivo cualquiera\n"],
    )
    overrides = load_overrides(overrides_path)

    with pytest.raises(OverrideError, match="master_id"):
        apply_overrides(overrides, identity_outputs, _raw_tables())


def test_source_id_duplicado_entre_overrides_se_rechaza(tmp_path: Path) -> None:
    master_id = _master_id_for(_identity_outputs()["identity_crosswalk"], "HS-9101")
    overrides_path = _write_overrides(
        tmp_path / "identity_overrides.csv",
        [
            f"product_db,ACC-9101,{master_id},ana.reyes,2024-08-15,primer motivo\n",
            f"product_db,ACC-9101,{master_id},luis.paz,2024-08-16,segundo motivo\n",
        ],
    )

    with pytest.raises(OverrideError, match="repite"):
        load_overrides(overrides_path)


def test_override_con_source_id_desconocido_se_rechaza(tmp_path: Path) -> None:
    identity_outputs = _identity_outputs()
    master_id = _master_id_for(identity_outputs["identity_crosswalk"], "HS-9101")
    overrides_path = _write_overrides(
        tmp_path / "identity_overrides.csv",
        [f"product_db,ACC-NO-EXISTE,{master_id},ana.reyes,2024-08-15,motivo cualquiera\n"],
    )
    overrides = load_overrides(overrides_path)

    with pytest.raises(OverrideError, match="raw_accounts"):
        apply_overrides(overrides, identity_outputs, _raw_tables())


def test_sin_archivo_de_overrides_la_salida_de_a0_no_cambia(tmp_path: Path) -> None:
    identity_outputs = _identity_outputs()
    missing_path = tmp_path / "no_existe.csv"

    result = _apply_overrides_if_present(
        load_overrides, apply_overrides, missing_path, identity_outputs, _raw_tables(), "build"
    )

    assert result is identity_outputs


def test_columnas_invalidas_se_rechaza(tmp_path: Path) -> None:
    path = tmp_path / "identity_overrides.csv"
    path.write_text("source_system,source_id,master_id,decided_by,decided_at\n", encoding="utf-8")

    with pytest.raises(OverrideError, match="columnas"):
        load_overrides(path)


def test_source_system_desconocido_se_rechaza(tmp_path: Path) -> None:
    path = tmp_path / "identity_overrides.csv"
    path.write_text(
        OVERRIDE_HEADER + "crm_hubspot,HS-9101,abc123456789,ana.reyes,2024-08-15,motivo\n",
        encoding="utf-8",
    )

    with pytest.raises(OverrideError, match="source_system"):
        load_overrides(path)


def test_campo_obligatorio_vacio_se_rechaza(tmp_path: Path) -> None:
    path = tmp_path / "identity_overrides.csv"
    path.write_text(
        OVERRIDE_HEADER + "product_db,ACC-9101,abc123456789,,2024-08-15,motivo\n",
        encoding="utf-8",
    )

    with pytest.raises(OverrideError, match="decided_by"):
        load_overrides(path)


def test_decided_at_no_iso_se_rechaza(tmp_path: Path) -> None:
    path = tmp_path / "identity_overrides.csv"
    path.write_text(
        OVERRIDE_HEADER + "product_db,ACC-9101,abc123456789,ana.reyes,15/08/2024,motivo\n",
        encoding="utf-8",
    )

    with pytest.raises(OverrideError, match="fecha ISO"):
        load_overrides(path)


def test_archivo_vacio_se_rechaza_con_override_error(tmp_path: Path) -> None:
    """R3-002: un archivo de cero bytes no debe tumbar `pd.read_csv` con una traza cruda."""
    path = tmp_path / "identity_overrides.csv"
    path.write_text("", encoding="utf-8")

    with pytest.raises(OverrideError) as error:
        load_overrides(path)
    assert str(path) in str(error.value)
    assert "vacio" in str(error.value)


def test_fila_mal_formada_se_rechaza_con_override_error(tmp_path: Path) -> None:
    """R3-002: una fila con una coma sin comillas (columnas de mas, forma dispareja) no debe tumbar el parser de pandas."""
    path = tmp_path / "identity_overrides.csv"
    path.write_text(
        OVERRIDE_HEADER
        + "product_db,ACC-9101,abc123456789,ana.reyes,2024-08-15,motivo\n"
        + "vitally,cus_9101,abc123456789,ana.reyes,2024-08-15,un motivo, con coma sin comillas\n",
        encoding="utf-8",
    )

    with pytest.raises(OverrideError) as error:
        load_overrides(path)
    assert str(path) in str(error.value)
