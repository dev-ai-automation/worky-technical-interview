"""Contratos completos del spec master-dataset-assembly, sobre el dataset real y el fixture sintetico.

Extiende `tests/test_build_contracts.py` (que ya cubre los siete contratos
de `run_contracts` sobre el fixture sintetico) con: el conteo de 650 filas
y la unicidad de `master_id` sobre el dataset real, las referencias
cruzadas de `match_audit` contra su tabla de origen, el dominio de
valores de `tickets.priority` sobre la tabla cruda, y la ausencia de
huecos internos en las series de `product_usage`. No repite ninguna
prueba que ya exista en `test_build_contracts.py`.
"""

from __future__ import annotations

import pandas as pd
import pytest

from tests.fixtures.mini_dataset import build_mini_dataset
from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset, open_connection
from worky_engine.quality import ContractViolation, run_contracts
from worky_engine.quality.contracts import (
    assert_source_id_in_origin_table,
    assert_tickets_priority_domain,
    assert_usage_months_no_internal_gaps,
)
from worky_engine.sources import load_raw_tables


@pytest.fixture(scope="module")
def real_assembled(data_dir, tmp_path_factory) -> dict[str, pd.DataFrame]:
    raw_tables = load_raw_tables(data_dir)
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    db_path = tmp_path_factory.mktemp("assembly_contracts_real") / "worky.duckdb"
    con = open_connection(db_path)
    try:
        outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
    finally:
        con.close()
    outputs.update(identity_outputs)
    outputs["raw_tables"] = raw_tables
    return outputs


@pytest.fixture(scope="module")
def synthetic_assembled(tmp_path_factory) -> dict[str, pd.DataFrame]:
    raw_tables = build_mini_dataset()
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    db_path = tmp_path_factory.mktemp("assembly_contracts_synthetic") / "worky.duckdb"
    con = open_connection(db_path)
    try:
        outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
    finally:
        con.close()
    outputs.update(identity_outputs)
    outputs["raw_tables"] = raw_tables
    return outputs


@pytest.mark.dataset
def test_los_contratos_de_run_contracts_pasan_sobre_el_dataset_real(real_assembled: dict) -> None:
    """Corre los diez contratos, incluidos los tres que cablea `cmd_build` (tarea 3.12), como en un build real."""
    run_contracts(
        real_assembled["master_dataset"], real_assembled["identity_crosswalk"], real_assembled["exceptions_log"],
        real_assembled["match_audit"], real_assembled["raw_tables"],
    )
    assert len(real_assembled["master_dataset"]) == 650
    assert not real_assembled["master_dataset"]["master_id"].duplicated().any()


@pytest.mark.dataset
def test_source_id_de_match_audit_existe_en_su_tabla_de_origen_en_el_dataset_real(real_assembled: dict) -> None:
    assert_source_id_in_origin_table(real_assembled["match_audit"], real_assembled["raw_tables"])


@pytest.mark.dataset
def test_tickets_priority_dentro_del_dominio_conocido_en_el_dataset_real(real_assembled: dict) -> None:
    assert_tickets_priority_domain(real_assembled["raw_tables"]["raw_tickets"])


@pytest.mark.dataset
def test_series_de_uso_sin_huecos_internos_en_el_dataset_real(real_assembled: dict) -> None:
    assert_usage_months_no_internal_gaps(real_assembled["raw_tables"]["raw_product_usage"])


def test_source_id_fuera_del_origen_viola_el_contrato(synthetic_assembled: dict) -> None:
    broken = synthetic_assembled["match_audit"].copy()
    broken.loc[broken.index[0], "source_id"] = "no-existe-en-ninguna-tabla-cruda"
    with pytest.raises(ContractViolation, match="source_id_in_origin_table"):
        assert_source_id_in_origin_table(broken, synthetic_assembled["raw_tables"])


def test_tickets_priority_fuera_del_dominio_viola_el_contrato(synthetic_assembled: dict) -> None:
    broken = synthetic_assembled["raw_tables"]["raw_tickets"].copy()
    broken.loc[broken.index[0], "priority"] = "Critica"
    with pytest.raises(ContractViolation, match="tickets_priority_domain"):
        assert_tickets_priority_domain(broken)


def test_series_de_uso_con_hueco_viola_el_contrato(synthetic_assembled: dict) -> None:
    usage = synthetic_assembled["raw_tables"]["raw_product_usage"]
    # ACC-9001 trae 2024-06, 2024-07 y 2024-08 seguidos; quitar el mes de
    # en medio deja un hueco entre 2024-06 y 2024-08 para esa cuenta.
    broken = usage[~((usage["account_id"] == "ACC-9001") & (usage["month"] == "2024-07"))]
    with pytest.raises(ContractViolation, match="usage_months_no_internal_gaps"):
        assert_usage_months_no_internal_gaps(broken)


def test_series_de_uso_sin_huecos_pasa_sobre_el_fixture_sintetico(synthetic_assembled: dict) -> None:
    assert_usage_months_no_internal_gaps(synthetic_assembled["raw_tables"]["raw_product_usage"])
