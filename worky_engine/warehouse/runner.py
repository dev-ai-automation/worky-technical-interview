"""Corredor del esquema en estrella (A4): `WAREHOUSE_FILES`, las tablas persistidas y `run_warehouse`.

Este PR agrega el algoritmo de SCD2 de `dim_company` (seccion 3 del
diseno, D4 a D8) y la foto de `fact_health_score_monthly` (D12) al
esqueleto que dejo el PR2. El orden de la seccion 1 del diseno queda
asi: `w1` a `w4` de `WAREHOUSE_FILES` (calendario, dimensiones, mapa de
identidad y la foto de entrada del SCD2), despues las cuatro sentencias
fijas del algoritmo sobre `dim_company`, despues `w5` (los cinco
hechos, que ya pueden unirse contra `dim_company` poblada) y por ultimo
la foto de health, que llama a `run_health(con)` de A3 en el mismo
proceso.
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
    "warehouse/w5_facts.sql",               # los cinco hechos, con company_sk por fecha
]

# w1 a w4 corren antes del algoritmo de SCD2, porque w4 produce su
# entrada (warehouse_company_snapshot); w5 corre despues, porque sus
# hechos se unen contra dim_company ya actualizada (seccion 1 del
# diseno).
_PRE_SCD2_FILES = WAREHOUSE_FILES[:4]
_POST_SCD2_FILES = WAREHOUSE_FILES[4:]

# Veinte columnas, en el orden de la seccion 3 del diseno: company_sk,
# master_id, hubspot_id, account_id, vitally_id, company_name,
# domain_label, segment, industry, plan, csm_owner, state,
# signup_date, churn_date, churn_status, attributes_hash,
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

# Diez columnas (seccion 5 del diseno): company_sk, master_id,
# run_date, reference_month, asof_month, health_score, risk_band,
# flagged_10, flagged_15, flagged_20. No es golden (D19): crece con
# cada fecha de corrida, asi que solo se persiste dentro del `.duckdb`.
_FACT_HEALTH_SCORE_MONTHLY_DDL = """
CREATE TABLE IF NOT EXISTS fact_health_score_monthly (
    company_sk VARCHAR(12),
    master_id VARCHAR(12),
    run_date DATE,
    reference_month VARCHAR,
    asof_month VARCHAR,
    health_score DOUBLE,
    risk_band VARCHAR,
    flagged_10 BOOLEAN,
    flagged_15 BOOLEAN,
    flagged_20 BOOLEAN
)
"""

# Paso 1, reemplazo de banda del mismo dia (D4): si una fila vigente ya
# se abrio en esta misma run_date pero la foto mas reciente trae un
# hash distinto (por ejemplo, dos corridas seguidas con la misma fecha
# y un cambio de por medio), se borra para que el paso 3 la reabra con
# los valores correctos, en vez de dejar una banda obsoleta mas una
# banda duplicada.
_SCD2_REPLACE_SAME_DAY_SQL = """
DELETE FROM dim_company
WHERE is_current = true
  AND effective_from = ?
  AND master_id IN (
      SELECT s.master_id
      FROM warehouse_company_snapshot s
      JOIN dim_company d
        ON d.master_id = s.master_id AND d.is_current = true AND d.effective_from = ?
      WHERE d.attributes_hash <> s.attributes_hash
  )
"""

# Paso 2, cierre (D5, D7): la fila vigente que abrio antes de esta
# corrida y cuyo attributes_hash ya no coincide con la foto queda
# cerrada en run_date, con is_current en false.
_SCD2_CLOSE_SQL = """
UPDATE dim_company AS d
SET effective_to = ?, is_current = false
FROM warehouse_company_snapshot AS s
WHERE d.master_id = s.master_id
  AND d.is_current = true
  AND d.effective_from < ?
  AND d.attributes_hash <> s.attributes_hash
"""

# Paso 3, apertura (D6, D7, D8): una fila nueva por cada master_id de
# la foto que se quedo sin fila vigente, sea porque nunca tuvo una
# (empresa nueva), porque el paso 2 acaba de cerrar la suya, o porque
# el paso 1 acaba de borrarla. company_sk es un hash determinista de
# master_id y run_date (D6), nunca un contador. Una empresa ausente de
# la foto (D8) no aparece aqui y su fila vigente anterior no se toca.
_SCD2_OPEN_SQL = """
INSERT INTO dim_company (
    company_sk, master_id, hubspot_id, account_id, vitally_id, company_name,
    domain_label, segment, industry, plan, csm_owner, state, signup_date,
    churn_date, churn_status, attributes_hash, effective_from, effective_to,
    is_current, ruleset_version
)
SELECT
    substr(sha256(s.master_id || '|' || ?), 1, 12) AS company_sk,
    s.master_id, s.hubspot_id, s.account_id, s.vitally_id, s.company_name,
    s.domain_label, s.segment, s.industry, s.plan, s.csm_owner, s.state,
    s.signup_date, s.churn_date, s.churn_status, s.attributes_hash,
    CAST(? AS DATE) AS effective_from, CAST(NULL AS DATE) AS effective_to, true AS is_current,
    s.ruleset_version
FROM warehouse_company_snapshot s
WHERE NOT EXISTS (
    SELECT 1 FROM dim_company d WHERE d.master_id = s.master_id AND d.is_current = true
)
"""

# Paso 4, tipo 1 (seccion 3 del diseno): las nueve columnas no
# rastreadas (company_name, domain_label, segment, industry, state,
# signup_date, churn_date, churn_status, ruleset_version) se
# sobrescriben en sitio sobre la fila vigente que sobrevive, sin abrir
# banda. hubspot_id, account_id y vitally_id no entran aqui: quedan
# fijos desde que la banda se abrio, junto con plan y csm_owner, que
# solo cambian por los pasos 2 y 3.
_SCD2_TYPE1_SQL = """
UPDATE dim_company AS d
SET
    company_name = s.company_name,
    domain_label = s.domain_label,
    segment = s.segment,
    industry = s.industry,
    state = s.state,
    signup_date = s.signup_date,
    churn_date = s.churn_date,
    churn_status = s.churn_status,
    ruleset_version = s.ruleset_version
FROM warehouse_company_snapshot AS s
WHERE d.master_id = s.master_id AND d.is_current = true
"""


@dataclass(frozen=True)
class WarehouseResult:
    """Las tres salidas de esta corrida: el mapa de identidad, `dim_company` y la foto de health."""

    map_source_identity: pd.DataFrame
    dim_company: pd.DataFrame
    fact_health_score_monthly: pd.DataFrame
    overrides: pd.DataFrame
    sql_text: dict[str, str]


def _ensure_persisted_tables(con: duckdb.DuckDBPyConnection) -> None:
    """Crea `dim_company`, `identity_overrides` y `fact_health_score_monthly` si no existen todavia (D9)."""
    con.execute(_DIM_COMPANY_DDL)
    con.execute(_IDENTITY_OVERRIDES_DDL)
    con.execute(_FACT_HEALTH_SCORE_MONTHLY_DDL)


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


def _resolve_run_date(con: duckdb.DuckDBPyConnection) -> str:
    """Por omision, `dataset_asof` de `mart_master_dataset` (D3): nunca el reloj de pared."""
    row = con.execute("SELECT dataset_asof FROM mart_master_dataset LIMIT 1").fetchone()
    if row is None:
        raise RuntimeError("warehouse: mart_master_dataset no tiene filas, no se puede fechar la corrida")
    return str(row[0])


def _run_scd2(con: duckdb.DuckDBPyConnection, run_date: str) -> None:
    """Corre las cuatro sentencias fijas del SCD2 (seccion 3 del diseno), en orden, sobre `run_date`."""
    con.execute(_SCD2_REPLACE_SAME_DAY_SQL, [run_date, run_date])
    con.execute(_SCD2_CLOSE_SQL, [run_date, run_date])
    con.execute(_SCD2_OPEN_SQL, [run_date, run_date])
    con.execute(_SCD2_TYPE1_SQL)


def _snapshot_health(con: duckdb.DuckDBPyConnection, run_date: str) -> None:
    """Corre `run_health(con)` de A3 y guarda su foto en `fact_health_score_monthly` (D12).

    Borra las filas de esta `run_date` antes de insertar, para que una
    recorrida con la misma fecha sea idempotente y nunca duplique
    filas. `company_sk` sale de la fila vigente de `dim_company` para
    ese `master_id`, que ya quedo actualizada por `_run_scd2` antes de
    este paso.
    """
    from worky_engine.health.runner import run_health

    result = run_health(con)
    scores = result.scores[
        ["master_id", "reference_month", "asof_month", "health_score", "risk_band", "flagged_10", "flagged_15", "flagged_20"]
    ].copy()
    scores["run_date"] = run_date

    con.register("_health_snapshot_staging", scores)
    try:
        con.execute("DELETE FROM fact_health_score_monthly WHERE run_date = ?", [run_date])
        con.execute(
            """
            INSERT INTO fact_health_score_monthly (
                company_sk, master_id, run_date, reference_month, asof_month,
                health_score, risk_band, flagged_10, flagged_15, flagged_20
            )
            SELECT
                d.company_sk, h.master_id, CAST(h.run_date AS DATE), h.reference_month, h.asof_month,
                h.health_score, h.risk_band, h.flagged_10, h.flagged_15, h.flagged_20
            FROM _health_snapshot_staging h
            JOIN dim_company d ON d.master_id = h.master_id AND d.is_current = true
            """
        )
    finally:
        con.unregister("_health_snapshot_staging")


def run_warehouse(
    con: duckdb.DuckDBPyConnection,
    overrides: pd.DataFrame | None = None,
    run_date: str | None = None,
) -> WarehouseResult:
    """Crea las tablas persistidas, corre el esquema en estrella completo y el algoritmo de SCD2 (D19).

    `con` ya debe traer registrados los `raw_*`, `identity_crosswalk`,
    `match_audit` y las dos cuarentenas, y ya debe haber corrido
    `assemble_master_dataset` (mismo orden que `cmd_analyze`/`cmd_health`,
    D1). `overrides` es el DataFrame que regresa `load_overrides`, o
    `None` cuando `--overrides` no existe. `run_date` es la fecha de
    corrida en formato ISO; por omision, `dataset_asof` (D3).
    """
    sql_text = {
        relative_path: (SQL_DIR / relative_path).read_text(encoding="utf-8")
        for relative_path in WAREHOUSE_FILES
    }
    _ensure_persisted_tables(con)
    materialized_overrides = _materialize_overrides(con, overrides)
    run_sql_files(con, _PRE_SCD2_FILES)

    resolved_run_date = run_date or _resolve_run_date(con)
    _run_scd2(con, resolved_run_date)

    run_sql_files(con, _POST_SCD2_FILES)
    _snapshot_health(con, resolved_run_date)

    map_source_identity = con.execute(
        "SELECT * FROM map_source_identity ORDER BY source_system, source_id"
    ).df()
    dim_company = con.execute("SELECT * FROM dim_company ORDER BY master_id, effective_from").df()
    fact_health_score_monthly = con.execute(
        "SELECT * FROM fact_health_score_monthly ORDER BY master_id, run_date"
    ).df()
    return WarehouseResult(
        map_source_identity=map_source_identity,
        dim_company=dim_company,
        fact_health_score_monthly=fact_health_score_monthly,
        overrides=materialized_overrides,
        sql_text=sql_text,
    )
