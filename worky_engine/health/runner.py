"""Corredor de las tres corridas de health: `health_params`, `HEALTH_FILES` y `compute_scores` (D8, D9, D20).

`run_health(con)` corre la corrida principal (k = 2 para bajas y
activas) y las dos sensibilidades de `SENSITIVITY_RUNS` (k = 3 y la
lectura literal del caso), cada una sobre la misma conexion que ya
registro `assemble_master_dataset` (D2 del diseno de A0): nunca abre su
propia conexion ni registra tablas por su cuenta. Regresa un
`HealthResult` con los scores numericos de la corrida principal (para
los contratos y `metrics.py`), la version ya formateada a texto para
`health_scores.csv`, las dos corridas de sensibilidad y el texto de
cada archivo `.sql` de `HEALTH_FILES`, leido una sola vez.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from worky_engine.health.scoring import compute_scores
from worky_engine.master_dataset.assemble import SQL_DIR, run_sql_files
from worky_engine.writers import format_money

HEALTH_FILES = [
    "health/h1_company_asof.sql",     # identidad, mes de referencia y mes de corte
    "health/h2_usage_signals.sql",    # momentum, mes a mes, caida, meses de uso
    "health/h3_tenure.sql",           # antiguedad al corte
    "health/h4_support_asof.sql",     # mart_support_asof: ventana de 3 meses
    "health/h5_activation.sql",       # activacion de los primeros 3 meses
    "health/h6_asof_inputs.sql",      # health_asof_inputs: una fila por empresa
]

# ("etiqueta", k_months, active_offset): la principal usa el mismo
# desplazamiento para bajas y activas; "literal" evalua a las activas
# en su propio mes de referencia (D8 del diseno).
SENSITIVITY_RUNS: tuple[tuple[str, int, int], ...] = (
    ("primaria", 2, 2),
    ("k3", 3, 3),
    ("literal", 2, 0),
)

# Columnas de `health_scores.csv`, en el orden de la seccion 7 del
# diseno; las senales crudas (sig_momentum, sig_mom, sig_drawdown,
# activation_raw) no se publican, solo sus subpuntajes normalizados.
_OUTPUT_COLUMNS = [
    "master_id", "hubspot_id", "segment", "acquisition_channel", "mrr_mxn", "churned",
    "reference_month", "asof_month", "usage_months_asof",
    "score_momentum", "score_mom", "score_drawdown", "score_tenure",
    "tickets_window_total", "tickets_window_urgent", "csat_window_avg", "activation_score",
    "health_score", "risk_band", "flagged_10", "flagged_15", "flagged_20",
]

# Subpuntajes que se escriben como texto de 2 decimales (D14); mrr_mxn
# y csat_window_avg ya llegan formateados desde SQL (h1 y h4).
_TEXT_NUMERIC_COLUMNS = ("score_momentum", "score_mom", "score_drawdown", "score_tenure", "activation_score", "health_score")


@dataclass(frozen=True)
class HealthResult:
    """Scores de la corrida principal (numericos y ya formateados a texto), sensibilidades y SQL leido.

    `dataset_asof` y `ruleset_version` se agregan en el PR 3 (extension
    menor sobre el diseno, mismo patron que `AnalysisResult` de A1):
    `report.py` no abre conexion ni lee archivos (D13), y necesita los
    dos valores para el encabezado de `validation.md`.
    """

    scores: pd.DataFrame
    formatted: pd.DataFrame
    sensitivities: dict[str, pd.DataFrame]
    sql_text: dict[str, str]
    dataset_asof: str
    ruleset_version: str


def _dataset_metadata(con: duckdb.DuckDBPyConnection) -> tuple[str, str]:
    """Lee `dataset_asof` y `ruleset_version` de `mart_master_dataset`, mismo patron que `analysis/runner.py`."""
    row = con.execute("SELECT dataset_asof, ruleset_version FROM mart_master_dataset LIMIT 1").fetchone()
    if row is None:
        raise RuntimeError("health: mart_master_dataset no tiene filas, no se puede fechar validation.md")
    return str(row[0]), str(row[1])


def _run_once(con: duckdb.DuckDBPyConnection, k_months: int, active_offset: int) -> pd.DataFrame:
    """Crea `health_params` con una sola fila, corre `HEALTH_FILES` y calcula los scores de esa corrida."""
    con.execute(
        "CREATE OR REPLACE TABLE health_params AS SELECT ? AS k_months, ? AS active_offset",
        [k_months, active_offset],
    )
    run_sql_files(con, HEALTH_FILES)
    asof_inputs = con.execute("SELECT * FROM health_asof_inputs ORDER BY master_id").df()
    return compute_scores(asof_inputs)


def _order_rows(scores: pd.DataFrame) -> pd.DataFrame:
    """`health_score` ascendente, vacios al final, `master_id` de desempate, `mergesort` (seccion 7 del diseno)."""
    ordered = scores.copy()
    ordered["_sort_key"] = pd.to_numeric(ordered["health_score"], errors="coerce")
    ordered = ordered.sort_values(["_sort_key", "master_id"], na_position="last", kind="mergesort")
    return ordered.drop(columns="_sort_key").reset_index(drop=True)


def _format_for_csv(scores: pd.DataFrame) -> pd.DataFrame:
    """Selecciona las columnas de salida y formatea los subpuntajes a texto de 2 decimales."""
    formatted = scores[_OUTPUT_COLUMNS].copy()
    for column in _TEXT_NUMERIC_COLUMNS:
        formatted[column] = formatted[column].apply(format_money)
    return formatted


def run_health(con: duckdb.DuckDBPyConnection) -> HealthResult:
    """Corre las tres corridas de `SENSITIVITY_RUNS` sobre `con` y regresa `HealthResult`."""
    sql_text = {
        relative_path: (SQL_DIR / relative_path).read_text(encoding="utf-8") for relative_path in HEALTH_FILES
    }
    runs = {label: _run_once(con, k_months, active_offset) for label, k_months, active_offset in SENSITIVITY_RUNS}

    primary = _order_rows(runs["primaria"])
    formatted = _format_for_csv(primary)
    sensitivities = {label: runs[label] for label in ("k3", "literal")}
    dataset_asof, ruleset_version = _dataset_metadata(con)
    return HealthResult(
        scores=primary,
        formatted=formatted,
        sensitivities=sensitivities,
        sql_text=sql_text,
        dataset_asof=dataset_asof,
        ruleset_version=ruleset_version,
    )
