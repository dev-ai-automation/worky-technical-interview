"""Registra los DataFrames en DuckDB y corre el SQL de staging y marts.

Este es el unico modulo que abre una conexion de DuckDB y el unico
punto donde Python le entrega el control a SQL: los nombres registrados
(`raw_*`, `identity_crosswalk`, `match_audit`, las dos cuarentenas) son
el contrato entre los dos lenguajes, segun la seccion 1 del diseno.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from worky_engine.normalization import domain_label, normalize_date

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

# Orden fijo de ejecucion, declarado en una lista y no por orden
# alfabetico del directorio, para que las dependencias entre archivos
# queden explicitas y revisables (seccion 4.2 del diseno).
STAGING_FILES = [
    "staging/stg_companies.sql",
    "staging/stg_deals.sql",
    "staging/stg_marketing_touches.sql",
    "staging/stg_accounts.sql",
    "staging/stg_product_usage.sql",
    "staging/stg_customers.sql",
    "staging/stg_tickets.sql",
]

MART_FILES = [
    "marts/mart_company_core.sql",
    "marts/mart_deal_normalized.sql",
    "marts/mart_mrr.sql",
    "marts/mart_usage.sql",
    "marts/mart_support.sql",
    "marts/mart_commercial.sql",
    "marts/mart_master_dataset.sql",
    "marts/mart_coverage.sql",
]

# Columnas de fecha que llegan en DD/MM/YYYY o ISO mezclados, segun la
# seccion 3.1 del diseno; se normalizan una sola vez, antes de registrar
# el DataFrame, para que el CAST a DATE del staging nunca falle.
_DATE_COLUMNS_BY_TABLE = {
    "raw_companies": ("signup_date", "churn_date"),
    "raw_deals": ("created_date", "close_date"),
}


def open_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection:
    """Abre DuckDB sin instalar ni cargar extensiones de forma automatica (decision D4).

    Borra el archivo `.duckdb` anterior si existe: se regenera en cada
    build y no se versiona (decision D6).
    """
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    if db_file.exists():
        db_file.unlink()
    return duckdb.connect(
        database=str(db_file),
        config={"autoinstall_known_extensions": False, "autoload_known_extensions": False},
    )


def register_tables(con: duckdb.DuckDBPyConnection, tables: dict[str, pd.DataFrame]) -> None:
    """Registra cada DataFrame con su nombre exacto de contrato entre Python y SQL."""
    for name, frame in tables.items():
        con.register(name, frame)


def run_sql_files(con: duckdb.DuckDBPyConnection, relative_paths: list[str]) -> None:
    """Ejecuta cada archivo `.sql` de `relative_paths`, en ese orden, con UTF-8 explicito."""
    for relative_path in relative_paths:
        sql_text = (SQL_DIR / relative_path).read_text(encoding="utf-8")
        con.execute(sql_text)


def _with_iso_dates(raw_tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Copia companies y deals con sus fechas ya en ISO, sin mutar `raw_tables`.

    `identity_resolution` normaliza las mismas columnas de forma interna
    sobre sus propias copias, asi que esto no duplica trabajo: es la
    unica vez que el staging de SQL necesita ver estas fechas.

    De paso, agrega `domain_label` a `raw_companies` con la misma
    funcion pura que usa `identity_resolution` (`worky_engine.
    normalization.domain_label`), para que `stg_companies.sql` solo
    tenga que pasarla de largo en vez de reimplementar el recorte de
    acentos y subdominios en SQL.
    """
    tables = dict(raw_tables)
    for table_name, columns in _DATE_COLUMNS_BY_TABLE.items():
        frame = tables[table_name].copy()
        for column in columns:
            frame[column] = frame[column].apply(
                lambda value: None if pd.isna(value) else normalize_date(str(value))
            )
        tables[table_name] = frame
    companies = tables["raw_companies"].copy()
    companies["domain_label"] = companies["domain"].apply(domain_label)
    tables["raw_companies"] = companies
    return tables


def assemble_master_dataset(
    con: duckdb.DuckDBPyConnection,
    raw_tables: dict[str, pd.DataFrame],
    identity_tables: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Registra las tablas, corre staging y marts, y entrega master_dataset, exceptions_log y cobertura.

    Las cuatro tablas `coverage_*` vienen de `mart_coverage.sql` (tarea 3.8):
    se materializan aqui, junto al resto, para que `worky_engine.quality.coverage`
    solo formatee texto y nunca vuelva a tocar la conexion de DuckDB.
    """
    register_tables(con, _with_iso_dates(raw_tables))
    register_tables(con, identity_tables)
    run_sql_files(con, STAGING_FILES)
    run_sql_files(con, MART_FILES)
    return {
        "master_dataset": con.execute("SELECT * FROM mart_master_dataset ORDER BY master_id").df(),
        "exceptions_log": con.execute(
            "SELECT * FROM exceptions_log ORDER BY exception_code, source_id"
        ).df(),
        "coverage_by_system": con.execute("SELECT * FROM mart_coverage_by_system").df(),
        "coverage_by_tier": con.execute("SELECT * FROM mart_coverage_by_tier").df(),
        "coverage_manual_queue": con.execute("SELECT * FROM mart_coverage_manual_queue").df(),
        "coverage_quarantine": con.execute("SELECT * FROM mart_coverage_quarantine").df(),
        "coverage_trend": con.execute("SELECT * FROM mart_coverage_trend").df(),
        "coverage_trend_median": con.execute("SELECT * FROM mart_coverage_trend_median").df(),
        "coverage_channel": con.execute("SELECT * FROM mart_coverage_channel").df(),
        "coverage_revenue": con.execute("SELECT * FROM mart_coverage_revenue").df(),
    }
