"""Equivalencia entre `sql/health/h2_usage_signals.sql` y `_features` del harness (decision D5).

El SQL es el camino de produccion; `_features` de
`worky_engine.harness.backtest` es la referencia. Compara
`sig_momentum`/`sig_mom`/`sig_drawdown` contra `E_ewma_momentum`/
`F_last_vs_prev1`/`D_pct_of_peak` sobre las mismas series, con
excepcion explicita de los tres casos degenerados de D15 (NaN en el
harness, 0.0 en el SQL).

h2 solo necesita `master_id`, `account_id` y `asof_month` de
`health_company_asof`, y `account_id`/`month`/`active_users` de
`stg_product_usage`: esta prueba registra esas dos tablas minimas
directo en DuckDB, sin pasar por identity_resolution ni por el resto
del ensamblaje, porque la equivalencia es una propiedad del archivo
h2 sobre una serie, no del pipeline completo.
"""

from __future__ import annotations

import duckdb
import pandas as pd
import pytest

from worky_engine.harness.backtest import _features
from worky_engine.master_dataset.assemble import SQL_DIR

_ASOF_MONTH = "2024-06"

# account_id -> (mes, active_users), en orden cronologico hasta el
# mes de corte compartido (_ASOF_MONTH).
_SERIES_BY_ACCOUNT: dict[str, list[tuple[str, int]]] = {
    "ACC-8301": [("2024-01", 10), ("2024-02", 12), ("2024-03", 15), ("2024-04", 20), ("2024-05", 25), ("2024-06", 30)],
    "ACC-8302": [("2024-03", 0), ("2024-04", 0), ("2024-05", 0), ("2024-06", 0)],
    "ACC-8303": [("2024-03", 10), ("2024-04", 10), ("2024-05", 0), ("2024-06", 10)],
}


@pytest.fixture(scope="module")
def usage_signals() -> pd.DataFrame:
    asof_rows = [
        {"master_id": account_id, "account_id": account_id, "asof_month": _ASOF_MONTH}
        for account_id in _SERIES_BY_ACCOUNT
    ]
    usage_rows = [
        {"account_id": account_id, "month": month, "active_users": users}
        for account_id, series in _SERIES_BY_ACCOUNT.items()
        for month, users in series
    ]
    con = duckdb.connect()
    try:
        con.register("health_company_asof", pd.DataFrame(asof_rows))
        con.register("stg_product_usage", pd.DataFrame(usage_rows))
        con.execute((SQL_DIR / "health/h2_usage_signals.sql").read_text(encoding="utf-8"))
        return con.execute("SELECT * FROM health_usage_signals ORDER BY master_id").df().set_index("master_id")
    finally:
        con.close()


def _reference_features(account_id: str) -> dict[str, float]:
    """`_features` del harness sobre la misma serie, hasta el mismo `_ASOF_MONTH` (resguardo de fuga compartido)."""
    series = _SERIES_BY_ACCOUNT[account_id]
    values = pd.Series(
        [users for _, users in series], index=pd.PeriodIndex([month for month, _ in series], freq="M"), dtype=float
    )
    return _features(values, pd.Period(_ASOF_MONTH, freq="M"))


def test_caso_tipico_no_degenerado_coincide_con_el_harness(usage_signals: pd.DataFrame) -> None:
    row = usage_signals.loc["ACC-8301"]
    reference = _reference_features("ACC-8301")
    assert row["sig_momentum"] == pytest.approx(reference["E_ewma_momentum"], abs=1e-6)
    assert row["sig_mom"] == pytest.approx(reference["F_last_vs_prev1"], abs=1e-6)
    assert row["sig_drawdown"] == pytest.approx(reference["D_pct_of_peak"], abs=1e-6)


def test_serie_en_cero_dispara_momentum_y_drawdown_degenerados(usage_signals: pd.DataFrame) -> None:
    """Excepcion D15: con la serie entera en cero, el SQL da 0.0 donde `_features` da NaN."""
    row = usage_signals.loc["ACC-8302"]
    reference = _reference_features("ACC-8302")
    assert pd.isna(reference["E_ewma_momentum"])
    assert pd.isna(reference["D_pct_of_peak"])
    assert pd.isna(reference["F_last_vs_prev1"])
    assert row["sig_momentum"] == 0.0
    assert row["sig_drawdown"] == 0.0
    assert row["sig_mom"] == 0.0


def test_mes_previo_en_cero_dispara_solo_sig_mom_degenerado(usage_signals: pd.DataFrame) -> None:
    """Excepcion D15 aislada: momentum y drawdown siguen coincidiendo con el harness en la misma fila."""
    row = usage_signals.loc["ACC-8303"]
    reference = _reference_features("ACC-8303")
    assert pd.isna(reference["F_last_vs_prev1"]), "el harness regresa NaN cuando el mes previo es cero"
    assert row["sig_mom"] == 0.0
    assert row["sig_momentum"] == pytest.approx(reference["E_ewma_momentum"], abs=1e-6)
    assert row["sig_drawdown"] == pytest.approx(reference["D_pct_of_peak"], abs=1e-6)
