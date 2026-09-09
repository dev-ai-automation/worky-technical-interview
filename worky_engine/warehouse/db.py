"""Conexion de DuckDB para `warehouse`, que persiste su archivo entre corridas (D2).

A diferencia de `master_dataset.assemble.open_connection`, que borra su
archivo en cada build (decision D6 de A0), `open_warehouse_connection`
no lo borra: el historial SCD2 del PR3 necesita que el `.duckdb`
sobreviva de una corrida a la siguiente para poder observarse. Esta es
la excepcion explicita a D6 (decision D2 de este diseno). La
configuracion de extensiones apagadas es la misma que usa A0.
"""

from __future__ import annotations

from pathlib import Path

import duckdb


def open_warehouse_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection:
    """Abre (o crea) el `.duckdb` de `warehouse` sin borrar el archivo anterior.

    `.build/` con `*.duckdb` ya esta en `.gitignore`, asi que este
    archivo persistido nunca se versiona por accidente.
    """
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(
        database=str(db_file),
        config={"autoinstall_known_extensions": False, "autoload_known_extensions": False},
    )
