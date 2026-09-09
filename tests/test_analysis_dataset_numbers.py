"""Numeros reales de las consultas de A1 disponibles en este PR, marca `dataset` (ADR-004, decision D12).

Corre `resolve_identity` + `assemble_master_dataset` + `run_analysis`
sobre el dataset real, la misma secuencia que usa `cmd_analyze`, y fija
los numeros que el ADR-004 ya publico: 89 cuentas en A1.2 (30 con
`windows_overlap`), 35 deals por 667,251.00 en A1.5, y el total con
imputados de A1.1 igual a la suma de `mrr_mxn` de las empresas activas
en `master_dataset`.

PR 2 agrego los numeros reales de A1.3 y A1.4: los 962 deals atribuidos
(997 de HubSpot menos los 35 huerfanos de A1.5) son iguales en los dos
modelos, la monotonia de A1.3 nunca sube de un k al siguiente dentro de
una cohorte, y el canal ganador medido en cada modelo (que sobre este
dataset resulta ser el mismo canal en los dos, sin cambio de ganador).

PR 3 agrega el numero real de A1.6: 48 tickets con resolution_hours
negativo, y las medianas que cita la justificacion del reporte, 13.5
(valor absoluto de los negativos) contra 12.2 (los tickets positivos),
con tolerancia 0.05, medidas directamente sobre `vitally_support.db`
sin pasar por ninguna vista de analisis, para que la prueba no dependa
de la funcion de mediana de DuckDB.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from worky_engine.analysis import run_analysis
from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset, open_connection
from worky_engine.sources import load_raw_tables


@pytest.fixture(scope="module")
def real_analysis_result(data_dir: Path, tmp_path_factory):
    raw_tables = load_raw_tables(data_dir)
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    db_path = tmp_path_factory.mktemp("analysis_dataset_numbers") / "worky.duckdb"
    con = open_connection(db_path)
    try:
        assembly_outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
        result = run_analysis(con)
    finally:
        con.close()
    return result, assembly_outputs, identity_outputs


@pytest.mark.dataset
def test_a1_02_89_cuentas_33_con_windows_overlap(real_analysis_result) -> None:
    """89 filas coincide con el ADR-004; `windows_overlap` da 33, no las 30 que cita el ADR-004.

    La consulta implementa `usage_months < 6` tal cual (decision D6 del
    diseno, "windows_overlap implementa la regla del ADR-004 tal cual").
    Sobre el dataset real hay exactamente 33 cuentas con menos de seis
    meses de uso (0, 2, 3, 4 o 5 meses): 3 con 0, 1 con 2, 6 con 3, 12
    con 4 y 11 con 5. El numero medido se fija aqui, en vez de ajustar la
    consulta para forzar 30 (decision D12 y la nota de riesgos
    residuales del diseno: "el reporte publica el numero medido en
    lugar de que la prueba se ajuste").
    """
    usage_drop = real_analysis_result[0].outputs["analysis_a1_02_usage_drop"]
    assert len(usage_drop) == 89
    assert int(usage_drop["windows_overlap"].sum()) == 33


@pytest.mark.dataset
def test_a1_05_35_deals_667251_pesos_todos_closedwon(real_analysis_result) -> None:
    orphan_deals = real_analysis_result[0].outputs["analysis_a1_05_orphan_deals"]
    assert len(orphan_deals) == 35
    total = orphan_deals["amount"].astype(float).sum()
    assert round(total, 2) == 667251.00
    assert (orphan_deals["stage"] == "closedwon").all()


@pytest.mark.dataset
def test_a1_01_total_imputado_coincide_con_master_dataset(real_analysis_result) -> None:
    result, assembly_outputs, _ = real_analysis_result
    active_mrr = result.outputs["analysis_a1_01_active_mrr"]
    total_row = active_mrr.loc[active_mrr["row_type"] == "total"].iloc[0]
    master_dataset = assembly_outputs["master_dataset"]
    active = master_dataset.loc[master_dataset["churn_status"] == "active", "mrr_mxn"]
    expected = round(pd.to_numeric(active, errors="coerce").fillna(0).sum(), 2)
    assert round(float(total_row["mrr_total_mxn"]), 2) == expected


@pytest.mark.dataset
def test_a1_04_deals_atribuidos_iguales_997_menos_35_huerfanos(real_analysis_result) -> None:
    """Los dos modelos de atribucion cubren los mismos 962 deals (997 de HubSpot menos los 35 huerfanos de A1.5)."""
    attribution = real_analysis_result[0].outputs["analysis_a1_04_attribution"]
    totals = attribution.groupby("model")["deals_attributed"].sum()
    assert totals["first_touch"] == 962
    assert totals["last_touch"] == 962


@pytest.mark.dataset
def test_a1_04_canal_ganador_medido_por_modelo(real_analysis_result) -> None:
    """El canal ganador (channel_rank = 1) de cada modelo, medido sobre el dataset real.

    Sobre este dataset, el ganador es 'Paid Search' en los dos modelos:
    el canal no cambia. Se fija el numero medido en vez de asumir el
    cambio de ganador que anticipaba el diseno (decision D12).
    """
    attribution = real_analysis_result[0].outputs["analysis_a1_04_attribution"]
    winners = attribution.loc[attribution["channel_rank"] == 1].set_index("model")
    assert winners.loc["first_touch", "channel"] == "Paid Search"
    assert winners.loc["last_touch", "channel"] == "Paid Search"
    assert winners.loc["first_touch", "channel"] == winners.loc["last_touch", "channel"]


@pytest.mark.dataset
def test_a1_03_monotonia_no_creciente_sobre_dataset_real(real_analysis_result) -> None:
    """Dentro de cada una de las 30 cohortes, `retained` nunca sube al pasar de un k al siguiente."""
    cohort_retention = real_analysis_result[0].outputs["analysis_a1_03_cohort_retention"]
    assert cohort_retention["cohort_month"].nunique() == 30
    assert len(cohort_retention) == 120
    assert int((cohort_retention["cell_status"] == "censored").sum()) == 15
    computed = cohort_retention.loc[cohort_retention["cell_status"] == "computed"].sort_values(["cohort_month", "k"])
    for cohort_month, group in computed.groupby("cohort_month"):
        values = group["retained"].astype(int).tolist()
        assert values == sorted(values, reverse=True), f"retained sube en la cohorte {cohort_month}"


@pytest.mark.dataset
def test_a1_06_48_tickets_negativos_y_su_excepcion(real_analysis_result) -> None:
    result = real_analysis_result[0]
    negative_hours = result.outputs["analysis_a1_06_negative_hours"]
    exceptions = result.outputs["analysis_exceptions"]
    assert len(negative_hours) == 48
    assert len(exceptions) == 48
    assert (negative_hours["resolution_hours"].astype(float) < 0).all()


@pytest.mark.dataset
def test_a1_06_medianas_13_5_contra_12_2(data_dir: Path) -> None:
    """Medianas medidas directo sobre vitally_support.db, sin pasar por ninguna vista de DuckDB.

    Mitigacion del riesgo del diseno ("las medianas... no se reproducen
    con la convencion de mediana de DuckDB"): se calculan con pandas
    sobre `raw_tickets` y se comparan con tolerancia 0.05 contra los
    13.5 y 12.2 que cita la justificacion de A1.6 en el ADR-004.
    """
    raw_tables = load_raw_tables(data_dir)
    hours = pd.to_numeric(raw_tables["raw_tickets"]["resolution_hours"], errors="coerce")
    negative_abs_median = hours[hours < 0].abs().median()
    positive_median = hours[hours > 0].median()
    assert abs(negative_abs_median - 13.5) <= 0.05
    assert abs(positive_median - 12.2) <= 0.05
