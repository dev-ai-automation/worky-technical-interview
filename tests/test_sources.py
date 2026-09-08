"""Pruebas de `worky_engine.sources`: la unica frontera de entrada y salida del motor."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from worky_engine.sources import REQUIRED_DB_FILES, load_raw_tables, readonly_uri

EXPECTED_KEYS = {
    "raw_companies", "raw_deals", "raw_marketing_touches",
    "raw_accounts", "raw_product_usage", "raw_customers", "raw_tickets",
}

_SCHEMA = {
    "crm_hubspot.db": {
        "companies": "hubspot_id TEXT, name TEXT",
        "deals": "deal_id TEXT, hubspot_id TEXT",
        "marketing_touches": "touch_id TEXT, hubspot_id TEXT",
    },
    "product_db.db": {
        "accounts": "account_id TEXT, account_name TEXT",
        "product_usage": "account_id TEXT, month TEXT",
    },
    "vitally_support.db": {
        "customers": "vitally_id TEXT, company_name TEXT",
        "tickets": "ticket_id TEXT, vitally_id TEXT",
    },
}


def _build_mini_databases(folder: Path) -> None:
    """Crea las tres bases con sus tablas y una fila acentuada en companies."""
    for db_file, tables in _SCHEMA.items():
        connection = sqlite3.connect(folder / db_file)
        for table, columns in tables.items():
            connection.execute(f"CREATE TABLE {table} ({columns})")
        if db_file == "crm_hubspot.db":
            connection.execute(
                "INSERT INTO companies VALUES (?, ?)", ("HS-1", "Gaitán, Olmos y Paredes")
            )
        connection.commit()
        connection.close()


def test_load_raw_tables_mapea_cada_tabla_a_su_nombre_raw(tmp_path: Path) -> None:
    _build_mini_databases(tmp_path)
    tables = load_raw_tables(tmp_path)
    assert set(tables) == EXPECTED_KEYS
    assert all(isinstance(frame, pd.DataFrame) for frame in tables.values())
    assert tables["raw_companies"].loc[0, "name"] == "Gaitán, Olmos y Paredes"
    assert len(tables["raw_deals"]) == 0


def test_readonly_uri_rechaza_escrituras(tmp_path: Path) -> None:
    db_path = tmp_path / "crm_hubspot.db"
    sqlite3.connect(db_path).execute("CREATE TABLE companies (hubspot_id TEXT)").connection.commit()
    connection = sqlite3.connect(readonly_uri(db_path), uri=True)
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        connection.execute("INSERT INTO companies VALUES ('HS-1')")
    connection.close()


def test_load_raw_tables_falla_si_falta_una_base(tmp_path: Path) -> None:
    _build_mini_databases(tmp_path)
    (tmp_path / REQUIRED_DB_FILES[1]).unlink()
    with pytest.raises(sqlite3.OperationalError):
        load_raw_tables(tmp_path)


def test_load_raw_tables_falla_si_falta_una_tabla(tmp_path: Path) -> None:
    _build_mini_databases(tmp_path)
    connection = sqlite3.connect(tmp_path / "vitally_support.db")
    connection.execute("DROP TABLE tickets")
    connection.commit()
    connection.close()
    with pytest.raises((sqlite3.OperationalError, pd.errors.DatabaseError)):
        load_raw_tables(tmp_path)


@pytest.mark.dataset
def test_load_raw_tables_lee_el_dataset_real_completo(data_dir: Path | None) -> None:
    if data_dir is None:
        pytest.skip("requiere el dataset real")
    tables = load_raw_tables(data_dir)
    expected_rows = {
        "raw_companies": 678, "raw_deals": 997, "raw_marketing_touches": 1635,
        "raw_accounts": 650, "raw_product_usage": 9793, "raw_customers": 650, "raw_tickets": 1888,
    }
    assert {key: len(frame) for key, frame in tables.items()} == expected_rows
