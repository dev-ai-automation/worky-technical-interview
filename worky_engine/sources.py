"""Lectura de las tres bases SQLite de origen, siempre en modo solo lectura.

Abre cada archivo `.db` con `sqlite3` de la libreria estandar usando el
modo URI de solo lectura (`file:...?mode=ro`, `uri=True`), para que el
motor nunca pueda escribir sobre los datos de origen (decision D3 del
diseno). `sqlite3` decodifica las columnas TEXT como UTF-8 por omision,
asi que un nombre o un dominio acentuado llega intacto a los DataFrames.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

REQUIRED_DB_FILES = ("crm_hubspot.db", "product_db.db", "vitally_support.db")

# Mapa de archivo de origen a tabla SQL y al nombre `raw_*` que espera
# `master_dataset/assemble.py` al registrar los DataFrames en DuckDB.
_TABLE_MAP: dict[str, dict[str, str]] = {
    "crm_hubspot.db": {
        "companies": "raw_companies",
        "deals": "raw_deals",
        "marketing_touches": "raw_marketing_touches",
    },
    "product_db.db": {
        "accounts": "raw_accounts",
        "product_usage": "raw_product_usage",
    },
    "vitally_support.db": {
        "customers": "raw_customers",
        "tickets": "raw_tickets",
    },
}


def load_raw_tables(data_dir: str | Path) -> dict[str, pd.DataFrame]:
    """Lee las tres bases SQLite de `data_dir` y entrega un DataFrame por tabla.

    Las claves del diccionario resultante son los nombres `raw_*` del
    contrato entre Python y SQL que fija la seccion 1 del diseno.
    """
    data_path = Path(data_dir)
    tables: dict[str, pd.DataFrame] = {}
    for db_file, table_names in _TABLE_MAP.items():
        db_path = data_path / db_file
        connection_uri = f"file:{db_path.as_posix()}?mode=ro"
        connection = sqlite3.connect(connection_uri, uri=True)
        try:
            for source_table, output_name in table_names.items():
                tables[output_name] = pd.read_sql_query(
                    f"SELECT * FROM {source_table}", connection
                )
        finally:
            connection.close()
    return tables
