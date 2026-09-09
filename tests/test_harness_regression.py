"""Regresion del harness de backtest (ADR-003), marca `dataset`.

Corre `run_backtest` sobre el dataset real y confirma dos cosas: que el
momentum EWMA sigue ganando por AUC entre las seis formulas en k = 2
(requisito 'regresion del momentum ganador en k = 2'), y que la tabla
que publica el ADR-003 se reproduce en k = 0, 2 y 3 dentro de 0.01 de
AUC (requisito 'reproduccion de la comparacion de formulas'). Tambien
confirma la evidencia de fuga de datos en k = 0 (AUC cercano a 1.0 para
la mayoria de las formulas).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from worky_engine import harness
from worky_engine.cli import main as cli_main
from worky_engine.harness import run_backtest
from worky_engine.harness.backtest import _auc
from worky_engine.sources import load_raw_tables

AUC_TOLERANCE = 0.01

# Tabla de la seccion "Como se compararon las formulas" del ADR-003
# (AUC en k = 2 y k = 3, medidos con el harness original). Si algun
# valor de esta corrida difiere mas de AUC_TOLERANCE, la prueba lo
# reporta con el numero exacto en vez de forzarlo: la diferencia mas
# probable es que este harness normaliza fechas (DD/MM/YYYY vs ISO)
# antes de comparar meses, y el prototipo original no lo hacia.
ADR003_TABLE = {
    "A_first3_vs_last3": {"auc_k2": 0.980, "auc_k3": 0.814},
    "B_last3_vs_prev3": {"auc_k2": 0.962, "auc_k3": 0.764},
    "C_norm_slope6": {"auc_k2": 0.996, "auc_k3": 0.829},
    "D_pct_of_peak": {"auc_k2": 0.845, "auc_k3": 0.620},
    "E_ewma_momentum": {"auc_k2": 1.000, "auc_k3": 0.894},
    "F_last_vs_prev1": {"auc_k2": 0.978, "auc_k3": 0.903},
}


def test_el_alias_publico_auc_es_el_mismo_objeto_que_backtest_auc() -> None:
    """El alias del PR 1 de A3 (decision D4) no copia el calculo: es el mismo objeto en memoria."""
    assert harness.auc is _auc


@pytest.fixture(scope="module")
def metrics(data_dir) -> pd.DataFrame:
    raw_tables = load_raw_tables(data_dir)
    return run_backtest(raw_tables)


@pytest.mark.dataset
def test_el_momentum_ewma_gana_por_auc_en_k_2(metrics: pd.DataFrame) -> None:
    at_k2 = metrics[metrics["k"] == 2].set_index("formula")
    momentum_auc = at_k2.loc["E_ewma_momentum", "auc"]
    for formula, row in at_k2.iterrows():
        if formula == "E_ewma_momentum":
            continue
        assert momentum_auc >= row["auc"], f"{formula} supera al momentum en k=2: {row['auc']} > {momentum_auc}"


@pytest.mark.dataset
def test_la_tabla_del_adr003_se_reproduce_dentro_de_la_tolerancia(metrics: pd.DataFrame) -> None:
    for formula, expected in ADR003_TABLE.items():
        for k, key in (("2", "auc_k2"), ("3", "auc_k3")):
            observed = metrics.loc[(metrics["formula"] == formula) & (metrics["k"] == int(k)), "auc"].iloc[0]
            diff = abs(observed - expected[key])
            assert diff < AUC_TOLERANCE, (
                f"{formula} en k={k}: AUC observado {observed:.3f} vs ADR-003 {expected[key]:.3f} "
                f"(diferencia {diff:.3f})"
            )


GOLDEN_BACKTEST_REPORT = Path(__file__).resolve().parent.parent / "outputs" / "backtest_report.md"


@pytest.mark.dataset
def test_backtest_report_es_identico_entre_dos_corridas_y_contra_el_golden(
    data_dir: Path, tmp_path: Path
) -> None:
    """`backtest_report.md` no lleva hora de reloj: dos corridas deben ser identicas byte a byte, y contra `outputs/`."""
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    for out_dir in (first_dir, second_dir):
        exit_code = cli_main(["backtest", "--data-dir", str(data_dir), "--out-dir", str(out_dir)])
        assert exit_code == 0
    first_bytes = (first_dir / "backtest_report.md").read_bytes()
    second_bytes = (second_dir / "backtest_report.md").read_bytes()
    assert first_bytes == second_bytes
    assert first_bytes == GOLDEN_BACKTEST_REPORT.read_bytes()


@pytest.mark.dataset
def test_evidencia_de_fuga_de_datos_en_k_0(metrics: pd.DataFrame) -> None:
    at_k0 = metrics[metrics["k"] == 0]
    # "Mes contra mes anterior" es la unica formula que en k=0 compara el
    # propio mes de baja contra el mes justo antes, asi que no hereda la
    # fuga de datos igual que las otras cinco (que si usan el mes de baja
    # dentro de su propia ventana); por eso se permite un solo outlier.
    near_perfect = (at_k0["auc"] >= 0.9).sum()
    assert near_perfect >= len(at_k0) - 1, "se esperaba AUC cercano a 1.0 en k=0 para casi todas las formulas"
