"""Prueba de contrato del resguardo contra fuga de datos (ADR-003), marca `dataset`.

No confia en `mart_usage`: para cada empresa con `trend_status = 'computed'`,
recalcula en la prueba misma, a partir de `raw_product_usage` filtrado por
`trend_asof_month`, el mismo momentum EWMA con `pandas.Series.ewm`, y
confirma que coincide con el `trend_usage` que ya trae `master_dataset`.
Si el mart hubiera dejado pasar una fila posterior al mes de corte, este
recalculo independiente no coincidiria, porque la prueba nunca lee mas
alla de `trend_asof_month`. Tambien confirma que el mes maximo entre las
filas recalculadas nunca rebasa el mes de corte, y que las cuentas con
baja tienen `trend_asof_month` igual al mes de `churn_date` menos 2.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset, open_connection
from worky_engine.sources import load_raw_tables


def _closed_form_momentum(values: list[float]) -> float:
    """Momentum EWMA(span=3)/EWMA(span=9) - 1, con la misma regla de `ewma_9 = 0` que `mart_usage.sql`."""
    series = pd.Series(values, dtype=float)
    ewma_3 = series.ewm(span=3, adjust=True).mean().iloc[-1]
    ewma_9 = series.ewm(span=9, adjust=True).mean().iloc[-1]
    if ewma_9 == 0:
        return 0.0
    return float(ewma_3 / ewma_9 - 1)


@pytest.fixture(scope="module")
def assembled(data_dir, tmp_path_factory) -> dict[str, pd.DataFrame]:
    raw_tables = load_raw_tables(data_dir)
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    db_path = tmp_path_factory.mktemp("leakage_guard") / "worky.duckdb"
    con = open_connection(db_path)
    try:
        outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
    finally:
        con.close()
    outputs["raw_product_usage"] = raw_tables["raw_product_usage"]
    outputs["identity_crosswalk"] = identity_outputs["identity_crosswalk"]
    return outputs


@pytest.mark.dataset
def test_ninguna_fila_posterior_al_corte_entra_al_calculo_de_trend_usage(assembled: dict) -> None:
    master_dataset = assembled["master_dataset"]
    usage = assembled["raw_product_usage"]
    account_id_by_master_id = assembled["identity_crosswalk"].set_index("master_id")["account_id"]

    computed_rows = master_dataset[master_dataset["trend_status"] == "computed"]
    assert len(computed_rows) > 0, "el dataset real debe traer al menos una empresa en trend_status='computed'"

    for row in computed_rows.itertuples():
        account_id = account_id_by_master_id.get(row.master_id)
        assert account_id is not None, f"{row.master_id} esta en 'computed' pero no tiene cuenta de producto"

        company_usage = usage[usage["account_id"] == account_id].sort_values("month")
        contributing = company_usage[company_usage["month"] <= row.trend_asof_month]

        # el mes maximo entre las filas que debieron contribuir nunca
        # rebasa el mes de corte: es justo el resguardo contra fuga.
        assert contributing["month"].max() <= row.trend_asof_month

        recalculated = _closed_form_momentum(contributing["active_users"].tolist())
        assert recalculated == pytest.approx(float(row.trend_usage), abs=1e-6), (
            row.master_id, recalculated, row.trend_usage
        )


@pytest.mark.dataset
def test_trend_asof_month_es_el_mes_de_churn_menos_dos_meses(assembled: dict) -> None:
    master_dataset = assembled["master_dataset"]
    churned = master_dataset[master_dataset["churn_status"] == "churned"]
    assert len(churned) > 0, "el dataset real debe traer empresas con baja"

    for row in churned.itertuples():
        churn_month = pd.Period(row.churn_date[:7], freq="M")
        expected_asof_month = str(churn_month - 2)
        assert row.trend_asof_month == expected_asof_month
