"""Corredor de las consultas de A1: ANALYSIS_FILES, ANALYSIS_OUTPUTS y run_analysis.

Corre sobre la misma conexion que ya registro `assemble_master_dataset`
(decision D2 del diseno): nunca registra tablas por su cuenta ni abre su
propia conexion. El orden de ejecucion se declara en una lista, igual
que `STAGING_FILES` y `MART_FILES` de `master_dataset/assemble.py`, y no
por orden alfabetico del directorio (decision D6).

PR 2 agrego `a1_00_last_touch.sql` (mart_last_touch, sin salida CSV
propia), `a1_03_cohort_retention.sql` y `a1_04_attribution.sql` a las
tres consultas del PR 1 (A1.1, A1.2 y A1.5). `a1_00` va primero porque
`a1_04` la consume (D6, D7).

PR 3 agrega `a1_06_negative_hours.sql`, que crea dos vistas: la lista
de detalle (`analysis_a1_06_negative_hours`) y `analysis_exceptions`,
asi que ambas quedan disponibles con un solo archivo en
`ANALYSIS_FILES`. `AnalysisResult` gana `dataset_asof` y
`ruleset_version`, leidos de `mart_master_dataset` despues de correr
`ANALYSIS_FILES`, porque `report.py` no abre conexion ni lee archivos
(decision D13 del diseno) y necesita esos dos valores para el
encabezado de `report.md` (extension menor sobre el diseno, que solo
describia `outputs` y `sql_text`).
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from worky_engine.master_dataset.assemble import SQL_DIR, run_sql_files
from worky_engine.quality.contracts import ContractViolation

ANALYSIS_FILES = [
    "analysis/a1_00_last_touch.sql",
    "analysis/a1_01_active_mrr.sql",
    "analysis/a1_02_usage_drop.sql",
    "analysis/a1_03_cohort_retention.sql",
    "analysis/a1_04_attribution.sql",
    "analysis/a1_05_orphan_deals.sql",
    "analysis/a1_06_negative_hours.sql",
]


@dataclass(frozen=True)
class AnalysisOutput:
    """Una salida de `analyze`: la vista que la produce, su archivo y su orden."""

    view: str
    file_name: str
    order_by: str


ANALYSIS_OUTPUTS: list[AnalysisOutput] = [
    AnalysisOutput("analysis_a1_01_active_mrr", "a1_01_active_mrr.csv", "row_type, segment, industry"),
    AnalysisOutput(
        "analysis_a1_02_usage_drop", "a1_02_usage_drop.csv", "CAST(drop_relative AS DOUBLE) DESC NULLS LAST, master_id"
    ),
    AnalysisOutput("analysis_a1_03_cohort_retention", "a1_03_cohort_retention.csv", "cohort_month, k"),
    AnalysisOutput("analysis_a1_04_attribution", "a1_04_attribution.csv", "model, channel_rank"),
    AnalysisOutput("analysis_a1_05_orphan_deals", "a1_05_orphan_deals.csv", "deal_id"),
    AnalysisOutput("analysis_a1_06_negative_hours", "a1_06_negative_hours.csv", "ticket_id"),
    AnalysisOutput("analysis_exceptions", "analysis_exceptions.csv", "exception_code, source_id"),
]


@dataclass(frozen=True)
class AnalysisResult:
    """Los DataFrames materializados, el texto de cada `.sql` y el encabezado que necesita `report.py`."""

    outputs: dict[str, pd.DataFrame]
    sql_text: dict[str, str]
    dataset_asof: str
    ruleset_version: str



def dataset_metadata(con: duckdb.DuckDBPyConnection) -> tuple[str, str]:
    """Lee `dataset_asof` y `ruleset_version` de `mart_master_dataset` para el encabezado del reporte.

    Con un dataset maestro vacio `fetchone()` regresa None; en vez de
    dejar que el desempaque truene con un TypeError sin contexto, se
    reporta como violacion de contrato con el nombre de la vista, y la
    CLI lo convierte en un mensaje claro con codigo de salida 1.
    """
    row = con.execute(
        "SELECT dataset_asof, ruleset_version FROM mart_master_dataset LIMIT 1"
    ).fetchone()
    if row is None:
        raise ContractViolation(
            "contrato analysis_dataset_metadata: mart_master_dataset no tiene filas, "
            "analyze no puede fechar el reporte"
        )
    return str(row[0]), str(row[1])


def run_analysis(con: duckdb.DuckDBPyConnection) -> AnalysisResult:
    """Corre `ANALYSIS_FILES` sobre `con` y materializa cada salida de `ANALYSIS_OUTPUTS`.

    El corredor repite, en el `SELECT` que materializa cada vista, la
    misma llave de orden que la vista ya declara en su propio
    `ORDER BY` (decision D6): un `GROUP BY` no garantiza orden estable
    entre corridas, y la comparacion byte a byte de la prueba de
    idempotencia es la que exige declarar el orden dos veces.
    """
    run_sql_files(con, ANALYSIS_FILES)
    outputs = {
        item.view: con.execute(f"SELECT * FROM {item.view} ORDER BY {item.order_by}").df()
        for item in ANALYSIS_OUTPUTS
    }
    sql_text = {
        relative_path: (SQL_DIR / relative_path).read_text(encoding="utf-8")
        for relative_path in ANALYSIS_FILES
    }
    dataset_asof, ruleset_version = dataset_metadata(con)
    return AnalysisResult(
        outputs=outputs, sql_text=sql_text, dataset_asof=dataset_asof, ruleset_version=ruleset_version
    )
