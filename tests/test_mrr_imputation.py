"""Prueba de integracion de la imputacion de MRR (ADR-002), marca `dataset`.

Corre `resolve_identity` y despues el ensamblaje sobre las tres bases
reales, y verifica los numeros exactos que fija la seccion 4.3 del
diseno: 28 empresas imputadas, 4 en `high` porque tienen un deal
`closedwon` y 24 en `medium`, ningun valor del CRM sobrescrito, y el
monto original junto a su moneda intactos frente al valor ya convertido
a MXN con el tipo de cambio de 18.5 del ADR-002. No lleva marca
`dataset` en el sentido de "opcional": estos numeros son hechos del
dataset real y no se pueden reproducir sobre el fixture sintetico.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset, open_connection
from worky_engine.sources import load_raw_tables

USD_TO_MXN_RATE = 18.5


@pytest.fixture(scope="module")
def master_dataset(data_dir, tmp_path_factory) -> pd.DataFrame:
    raw_tables = load_raw_tables(data_dir)
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    db_path = tmp_path_factory.mktemp("mrr") / "worky.duckdb"
    con = open_connection(db_path)
    try:
        outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
    finally:
        con.close()
    return outputs["master_dataset"]


@pytest.mark.dataset
def test_28_empresas_se_imputan_desde_su_deal(master_dataset: pd.DataFrame) -> None:
    imputed = master_dataset[master_dataset["mrr_source"] == "imputed_from_deal"]
    assert len(imputed) == 28


@pytest.mark.dataset
def test_confianza_se_reparte_4_alta_24_media(master_dataset: pd.DataFrame) -> None:
    imputed = master_dataset[master_dataset["mrr_source"] == "imputed_from_deal"]
    counts = imputed["mrr_confidence"].value_counts()
    assert counts.get("high", 0) == 4
    assert counts.get("medium", 0) == 24


@pytest.mark.dataset
def test_ningun_valor_del_crm_se_sobrescribe(master_dataset: pd.DataFrame) -> None:
    from_crm = master_dataset[master_dataset["mrr_source"] == "crm"]
    assert len(from_crm) == len(master_dataset) - 28
    assert from_crm["mrr_mxn"].notna().all()


@pytest.mark.dataset
def test_mrr_original_y_moneda_original_quedan_intactos(master_dataset: pd.DataFrame) -> None:
    imputed = master_dataset[master_dataset["mrr_source"] == "imputed_from_deal"]
    assert imputed["mrr_original"].isna().all()
    assert imputed["currency_original"].notna().all()


@pytest.mark.dataset
def test_conversion_usd_a_mxn_usa_18_5(master_dataset: pd.DataFrame) -> None:
    crm_usd_rows = master_dataset[
        (master_dataset["currency_original"] == "USD") & (master_dataset["mrr_source"] == "crm")
    ]
    assert not crm_usd_rows.empty
    for _, row in crm_usd_rows.iterrows():
        expected = round(float(row["mrr_original"]) * USD_TO_MXN_RATE, 2)
        assert float(row["mrr_mxn"]) == pytest.approx(expected, abs=0.01)


@pytest.mark.dataset
def test_totales_de_mrr_reportado_y_con_imputados(master_dataset: pd.DataFrame) -> None:
    """Asercion de humo: los dos totales que exige el cierre del PR (tarea 3.17)."""
    from_crm = master_dataset[master_dataset["mrr_source"] == "crm"]
    total_reportado = from_crm["mrr_mxn"].astype(float).sum()
    total_con_imputados = master_dataset["mrr_mxn"].astype(float).sum()
    assert total_con_imputados > total_reportado
    print(f"MRR reportado del CRM: {total_reportado:.2f}; MRR total con imputados: {total_con_imputados:.2f}")
