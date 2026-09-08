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

import pandas as pd
import pytest

from tests.fixtures.mini_dataset import build_mini_dataset
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
