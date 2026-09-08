"""Pruebas de los contratos de datos en tiempo de build, sobre el fixture sintetico.

Corre el ensamblaje completo sobre las 13 empresas reales de
`tests/fixtures/mini_dataset.py` (dos de ellas sin MRR ni deal unico,
para probar la rama `unresolved`) para confirmar que los siete contratos
disponibles en este PR pasan sobre un dataset valido, y prueba cada
violacion por separado sobre copias del resultado, para no depender de
las 650 filas del dataset real. `tests/test_assembly_contracts.py`
(tarea 3.12) extiende esta cobertura en el PR 3b con las columnas de
uso, soporte y comercial.
"""

from __future__ import annotations

import builtins
import sys

import pandas as pd
import pytest

from tests.fixtures.mini_dataset import build_mini_dataset
from worky_engine.cli import main as cli_main
from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset, open_connection
from worky_engine.quality import ContractViolation, run_contracts
from worky_engine.writers import write_csv


@pytest.fixture(scope="module")
def assembled(tmp_path_factory) -> dict[str, pd.DataFrame]:
    raw_tables = build_mini_dataset()
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    db_path = tmp_path_factory.mktemp("contracts") / "worky.duckdb"
    con = open_connection(db_path)
    try:
        outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
    finally:
        con.close()
    outputs["identity_crosswalk"] = identity_outputs["identity_crosswalk"]
    return outputs


def test_los_seis_contratos_pasan_sobre_el_fixture_sintetico(assembled: dict[str, pd.DataFrame]) -> None:
    run_contracts(assembled["master_dataset"], assembled["identity_crosswalk"], assembled["exceptions_log"])


def test_master_id_repetido_viola_el_contrato_de_unicidad(assembled: dict[str, pd.DataFrame]) -> None:
    broken = assembled["master_dataset"].copy()
    broken.loc[broken.index[0], "master_id"] = broken.loc[broken.index[1], "master_id"]
    with pytest.raises(ContractViolation, match="unique_master_id"):
        run_contracts(broken, assembled["identity_crosswalk"], assembled["exceptions_log"])


def test_columna_obligatoria_nula_viola_el_contrato(assembled: dict[str, pd.DataFrame]) -> None:
    broken = assembled["master_dataset"].copy()
    broken.loc[broken.index[0], "company_name"] = None
    with pytest.raises(ContractViolation, match="required_not_null"):
        run_contracts(broken, assembled["identity_crosswalk"], assembled["exceptions_log"])


def test_master_id_fuera_del_crosswalk_viola_el_contrato(assembled: dict[str, pd.DataFrame]) -> None:
    broken = assembled["master_dataset"].copy()
    broken.loc[broken.index[0], "master_id"] = "ffffffffffff"
    with pytest.raises(ContractViolation, match="master_id_in_crosswalk"):
        run_contracts(broken, assembled["identity_crosswalk"], assembled["exceptions_log"])


def test_master_id_de_exceptions_log_ausente_en_el_dataset_viola_el_contrato(
    assembled: dict[str, pd.DataFrame],
) -> None:
    broken_exceptions = pd.DataFrame(
        [{"master_id": "ffffffffffff", "exception_code": "mrr_imputed_from_deal"}]
    )
    with pytest.raises(ContractViolation, match="exceptions_master_id_in_dataset"):
        run_contracts(assembled["master_dataset"], assembled["identity_crosswalk"], broken_exceptions)


def test_valor_fuera_de_dominio_viola_el_contrato(assembled: dict[str, pd.DataFrame]) -> None:
    broken = assembled["master_dataset"].copy()
    broken.loc[broken.index[0], "churn_status"] = "desconocido"
    with pytest.raises(ContractViolation, match="value_domain_churn_status"):
        run_contracts(broken, assembled["identity_crosswalk"], assembled["exceptions_log"])


def test_empresas_sin_deal_unico_quedan_unresolved_sin_nan_ni_none_literal(
    assembled: dict[str, pd.DataFrame], tmp_path
) -> None:
    """HS-200012 (dos montos distintos) y HS-200013 (sin deals) quedan unresolved."""
    md = assembled["master_dataset"]
    unresolved = md[md["mrr_source"] == "unresolved"]
    assert set(unresolved["hubspot_id"]) == {"HS-200012", "HS-200013"}
    assert (unresolved["mrr_mxn"] == "").all()
    assert (unresolved["mrr_confidence"] == "none").all()

    csv_path = tmp_path / "master_dataset.csv"
    write_csv(md, csv_path)
    fields = csv_path.read_text(encoding="utf-8").replace("\n", ",").split(",")
    assert "nan" not in fields
    assert "None" not in fields


def test_mrr_confidence_none_fuera_de_unresolved_viola_el_contrato(assembled: dict[str, pd.DataFrame]) -> None:
    broken = assembled["master_dataset"].copy()
    broken.loc[broken.index[0], "mrr_confidence"] = "none"
    with pytest.raises(ContractViolation, match="mrr_confidence_matches_source"):
        run_contracts(broken, assembled["identity_crosswalk"], assembled["exceptions_log"])


def test_tickets_urgent_mayor_a_tickets_total_viola_el_contrato(assembled: dict[str, pd.DataFrame]) -> None:
    broken = assembled["master_dataset"].copy()
    broken.loc[broken.index[0], "tickets_total"] = 0
    broken.loc[broken.index[0], "tickets_urgent"] = 1
    with pytest.raises(ContractViolation, match="tickets_urgent_within_total"):
        run_contracts(broken, assembled["identity_crosswalk"], assembled["exceptions_log"])


def test_csat_avg_fuera_de_1_5_viola_el_contrato(assembled: dict[str, pd.DataFrame]) -> None:
    broken = assembled["master_dataset"].copy()
    broken.loc[broken.index[0], "csat_avg"] = "5.50"
    with pytest.raises(ContractViolation, match="csat_avg_domain"):
        run_contracts(broken, assembled["identity_crosswalk"], assembled["exceptions_log"])


def test_closed_revenue_negativo_viola_el_contrato(assembled: dict[str, pd.DataFrame]) -> None:
    broken = assembled["master_dataset"].copy()
    broken.loc[broken.index[0], "closed_revenue_mxn"] = "-1.00"
    with pytest.raises(ContractViolation, match="closed_revenue_non_negative"):
        run_contracts(broken, assembled["identity_crosswalk"], assembled["exceptions_log"])


def test_build_con_data_dir_inexistente_termina_con_codigo_2(tmp_path, capsys) -> None:
    """Tarea 3.18: falta una de las tres bases SQLite, mensaje en espanol y sin salidas parciales."""
    with pytest.raises(SystemExit) as exit_info:
        cli_main(["build", "--data-dir", str(tmp_path / "no-existe"), "--out-dir", str(tmp_path / "out")])
    assert exit_info.value.code == 2
    assert "no se encontraron las tres bases SQLite" in capsys.readouterr().err
    assert not (tmp_path / "out" / "master_dataset.csv").exists()


@pytest.mark.dataset
def test_build_con_contrato_violado_termina_con_codigo_1(
    monkeypatch: pytest.MonkeyPatch, data_dir, tmp_path, capsys
) -> None:
    """Tarea 3.18: una violacion forzada de contrato detiene el build con codigo 1 y nombra el contrato."""

    def _siempre_viola(*_args, **_kwargs) -> None:
        raise ContractViolation("contrato forzado_para_la_prueba: violacion simulada")

    monkeypatch.setattr("worky_engine.quality.contracts.assert_unique_master_id", _siempre_viola)
    exit_code = cli_main(
        ["build", "--data-dir", str(data_dir), "--out-dir", str(tmp_path / "out")]
    )
    assert exit_code == 1
    assert "forzado_para_la_prueba" in capsys.readouterr().err


def test_build_con_duckdb_faltante_termina_con_codigo_2(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys) -> None:
    """Tarea 3.18: ImportError de duckdb en el primer uso, mensaje en espanol con el pip install."""
    real_import = builtins.__import__

    def _fake_import(name: str, *args, **kwargs):
        if name == "duckdb":
            raise ImportError(name="duckdb")
        return real_import(name, *args, **kwargs)

    for cached in ("duckdb", "worky_engine.master_dataset", "worky_engine.master_dataset.assemble"):
        monkeypatch.delitem(sys.modules, cached, raising=False)
    monkeypatch.setattr(builtins, "__import__", _fake_import)

    with pytest.raises(SystemExit) as exit_info:
        cli_main(["build", "--data-dir", str(tmp_path / "no-existe"), "--out-dir", str(tmp_path / "out")])
    assert exit_info.value.code == 2
    stderr = capsys.readouterr().err
    assert "duckdb" in stderr
    assert "pip install duckdb" in stderr
