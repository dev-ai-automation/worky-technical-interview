"""Pruebas de los contratos de datos en tiempo de build, sobre el fixture sintetico.

Corre el ensamblaje completo sobre las 11 empresas reales de
`tests/fixtures/mini_dataset.py` para confirmar que los seis contratos
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
