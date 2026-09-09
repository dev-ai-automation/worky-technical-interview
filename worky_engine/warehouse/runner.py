"""Corredor del esquema en estrella (A4): `WAREHOUSE_FILES`, las tablas persistidas y `run_warehouse`.

Este PR deja el esqueleto que fija la seccion 1 del diseno: el orden
fijo de las cinco vistas de `sql/warehouse/`, el DDL de las tres tablas
persistidas de D9 y `run_warehouse`, que en este PR materializa
`identity_overrides` (con las filas ya validadas por `load_overrides`,
si el archivo existe) y `map_source_identity`. El DDL de `dim_company`
ya vive aqui, vacio, para que `w4_company_snapshot.sql` y
`w5_facts.sql` puedan crearse sin fallar por un objeto ausente; el
algoritmo de SCD2 que la puebla (D4 a D8) y el DDL de
`fact_health_score_monthly` (D12) llegan en el PR3, que solo agrega
sentencias sobre esta misma tabla sin volver a tocar ningun archivo
`.sql` de `sql/warehouse/`.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb
import pandas as pd

from worky_engine.identity_resolution.overrides import OVERRIDE_COLUMNS
from worky_engine.master_dataset.assemble import SQL_DIR, run_sql_files

WAREHOUSE_FILES = [
    "warehouse/w1_dim_date.sql",            # calendario diario derivado de los datos
    "warehouse/w2_dim_csm_plan.sql",        # dim_csm y dim_plan, valores distintos
    "warehouse/w3_map_source_identity.sql", # crosswalk y overrides, un renglon por vinculo
    "warehouse/w4_company_snapshot.sql",    # foto actual con attributes_hash, entrada del SCD2
    "warehouse/w5_facts.sql",               # los hechos de este PR, con company_sk por fecha
]

# Veinte columnas, en el orden de la seccion 3 del diseno (llenado por
# el PR3): company_sk, master_id, hubspot_id, account_id, vitally_id,
# company_name, domain_label, segment, industry, plan, csm_owner,
# state, signup_date, churn_date, churn_status, attributes_hash,
# effective_from, effective_to, is_current, ruleset_version.
_DIM_COMPANY_DDL = """
CREATE TABLE IF NOT EXISTS dim_company (
    company_sk VARCHAR(12) PRIMARY KEY,
    master_id VARCHAR(12),
    hubspot_id VARCHAR,
    account_id VARCHAR,
    vitally_id VARCHAR,
    company_name VARCHAR,
    domain_label VARCHAR,
    segment VARCHAR,
    industry VARCHAR,
    plan VARCHAR,
    csm_owner VARCHAR,
    state VARCHAR,
    signup_date DATE,
    churn_date DATE,
    churn_status VARCHAR,
    attributes_hash VARCHAR(12),
    effective_from DATE,
    effective_to DATE,
    is_current BOOLEAN,
    ruleset_version VARCHAR
)
"""

_IDENTITY_OVERRIDES_DDL = """
CREATE TABLE IF NOT EXISTS identity_overrides (
    source_system VARCHAR,
    source_id VARCHAR,
    master_id VARCHAR,
    decided_by VARCHAR,
    decided_at VARCHAR,
    reason VARCHAR
)
"""


@dataclass(frozen=True)
class WarehouseResult:
    """Salidas de esta corrida. `dim_company` y la foto de health se agregan en el PR3."""

    map_source_identity: pd.DataFrame
    overrides: pd.DataFrame
    sql_text: dict[str, str]


def _ensure_persisted_tables(con: duckdb.DuckDBPyConnection) -> None:
    """Crea `dim_company` e `identity_overrides` si no existen todavia (D9).

    `dim_company` queda vacia hasta que el algoritmo de SCD2 del PR3 la
    puebla; existir ya, aunque sin filas, es lo que le permite a
    `w5_facts.sql` unirse contra ella sin que DuckDB rechace la vista
    por un objeto ausente.
    """
    con.execute(_DIM_COMPANY_DDL)
    con.execute(_IDENTITY_OVERRIDES_DDL)


def _materialize_overrides(con: duckdb.DuckDBPyConnection, overrides: pd.DataFrame | None) -> pd.DataFrame:
    """Reemplaza el contenido de `identity_overrides` con las filas ya validadas por `load_overrides`.

    Sin archivo (`overrides` es `None`), la tabla queda con sus seis
    columnas y cero filas: mismo patron de esquema fijo que
    `_to_quarantine_companies_frame` usa para no romper el `register`
    de DuckDB con un DataFrame vacio sin columnas.
    """
    frame = overrides if overrides is not None else pd.DataFrame(columns=list(OVERRIDE_COLUMNS))
    con.execute("DELETE FROM identity_overrides")
    con.register("_identity_overrides_staging", frame)
    con.execute("INSERT INTO identity_overrides SELECT * FROM _identity_overrides_staging")
    con.unregister("_identity_overrides_staging")
    return frame


def run_warehouse(con: duckdb.DuckDBPyConnection, overrides: pd.DataFrame | None = None) -> WarehouseResult:
    """Crea las tablas persistidas, corre `WAREHOUSE_FILES` y materializa `map_source_identity` (D19).

    `con` ya debe traer registrados los `raw_*`, `identity_crosswalk`,
    `match_audit` y las dos cuarentenas, y ya debe haber corrido
    `assemble_master_dataset` (mismo orden que `cmd_analyze`/`cmd_health`,
    D1). `overrides` es el DataFrame que regresa `load_overrides`, o
    `None` cuando `--overrides` no existe.
    """
    sql_text = {
        relative_path: (SQL_DIR / relative_path).read_text(encoding="utf-8")
        for relative_path in WAREHOUSE_FILES
    }
    _ensure_persisted_tables(con)
    materialized_overrides = _materialize_overrides(con, overrides)
    run_sql_files(con, WAREHOUSE_FILES)
    map_source_identity = con.execute(
        "SELECT * FROM map_source_identity ORDER BY source_system, source_id"
    ).df()
    return WarehouseResult(
        map_source_identity=map_source_identity, overrides=materialized_overrides, sql_text=sql_text
    )
