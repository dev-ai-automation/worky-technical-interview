"""Pruebas unitarias de `mart_usage.sql`: la forma cerrada del EWMA (ADR-003) y `trend_status`.

La primera prueba reproduce, con DuckDB, exactamente el fragmento SQL
que usa `mart_usage.sql` para `ewma_3` y `ewma_9` (mismo `alpha`, mismos
pesos `(1-alpha)^k`, misma normalizacion por la suma de pesos) y lo
compara contra `pandas.Series.ewm(span=s, adjust=True).mean().iloc[-1]`
dentro de 1e-9, sobre 20 series sinteticas de longitudes distintas,
incluidas series con ceros. Las otras dos pruebas corren el ensamblaje
completo sobre un fixture minimo de tres empresas activas, una por cada
estado de `trend_status`, y confirman que `ewma_9 = 0` da exactamente
`0.000000`.
"""

from __future__ import annotations

import random

import duckdb
import pandas as pd
import pytest

from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset, open_connection

TOLERANCE = 1e-9


def _closed_form_ewma_sql(con: duckdb.DuckDBPyConnection, values: list[float], span: int) -> float:
    """Corre el mismo fragmento SQL de la CTE `ewma` de `mart_usage.sql` sobre una sola serie.

    `k` es la distancia en meses hacia atras desde el mes mas reciente
    (indice `n - 1`), tal como lo calcula `datediff('month', month,
    trend_asof_month)` en produccion cuando la serie no tiene huecos.
    """
    n = len(values)
    rows = ", ".join(f"({idx}, {value})" for idx, value in enumerate(values))
    con.execute(f"CREATE OR REPLACE TABLE w AS SELECT * FROM (VALUES {rows}) AS s(idx, active_users)")
    alpha = 2.0 / (span + 1)
    query = f"""
        SELECT SUM(active_users * pow(1 - {alpha}, {n - 1} - idx))
             / SUM(pow(1 - {alpha}, {n - 1} - idx))
        FROM w
    """
    return con.execute(query).fetchone()[0]


def _synthetic_series() -> list[list[float]]:
    """20 series sinteticas de longitudes distintas (1 a 20 meses), deterministas por semilla fija."""
    rng = random.Random(20260908)
    series = [[rng.randint(0, 300) for _ in range(length)] for length in range(1, 20)]
    series.append([0] * 6)  # serie de puros ceros: ejercita el caso ewma_9 = 0
    return series


def test_forma_cerrada_sql_coincide_con_pandas_ewm_dentro_de_1e9() -> None:
    con = duckdb.connect()
    try:
        for values in _synthetic_series():
            for span in (3, 9):
                pandas_value = pd.Series(values, dtype=float).ewm(span=span, adjust=True).mean().iloc[-1]
                sql_value = _closed_form_ewma_sql(con, values, span)
                assert abs(sql_value - pandas_value) < TOLERANCE, (values, span, sql_value, pandas_value)
    finally:
        con.close()


def _minimal_raw_tables() -> dict[str, pd.DataFrame]:
    """Tres empresas activas, una por cada estado de `trend_status`.

    `HS-600001` no tiene cuenta de producto (`no_usage`). `HS-600002`
    solo trae dos meses de uso hasta el mes de corte (`insufficient_history`).
    `HS-600003` trae cinco meses en cero: tres quedan hasta el corte, lo
    que basta para `computed`, y con `active_users` siempre en cero
    `ewma_9` da exactamente cero, forzando `trend_usage = 0.000000`.
    """
    companies = [
        {"hubspot_id": h, "name": n, "domain": d, "segment": "SMB", "industry": "Retail", "mrr": 1000.0,
         "currency": "MXN", "signup_date": "2022-01-01", "csm_owner": "X", "plan": "Basico",
         "state": "CDMX", "churn_date": None}
        for h, n, d in [
            ("HS-600001", "Sin Cuenta SA de CV", "sincuenta600.com.mx"),
            ("HS-600002", "Historia Corta SA de CV", "corta600.com.mx"),
            ("HS-600003", "Cero Uso SA de CV", "cero600.com.mx"),
        ]
    ]
    accounts = [
        {"account_id": "ACC-6002", "hubspot_id": "HS-600002", "account_name": "Historia Corta", "created_at": "2022-01-01"},
        {"account_id": "ACC-6003", "hubspot_id": "HS-600003", "account_name": "Cero Uso", "created_at": "2022-01-01"},
    ]
    usage = (
        [
            {"account_id": "ACC-6002", "month": m, "active_users": 10, "logins": 20,
             "payroll_runs_completed": 1, "features_used": 3, "api_calls": 200}
            for m in ("2024-02", "2024-03")
        ]
        + [
            {"account_id": "ACC-6003", "month": m, "active_users": 0, "logins": 0,
             "payroll_runs_completed": 0, "features_used": 0, "api_calls": 0}
            for m in ("2024-01", "2024-02", "2024-03", "2024-04", "2024-05")
        ]
    )
    # Un clon de HS-600003 (mismo nombre y dominio, mrr nulo, sin cuenta
    # que lo referencie) y un deal huerfano: sin ellos, `resolve_identity`
    # entrega `quarantine_companies`/`quarantine_deals` vacias con cero
    # columnas, y `assemble_master_dataset` no puede registrarlas en
    # DuckDB (`Need a DataFrame with at least one column`). Este fixture
    # minimo los agrega solo para mantener esa forma valida; no son parte
    # de lo que prueba este archivo.
    companies.append(
        {"hubspot_id": "HS-900060", "name": "Cero Uso SA de CV", "domain": "cero600.com.mx", "segment": "SMB",
         "industry": "Retail", "mrr": None, "currency": "MXN", "signup_date": "2022-01-01", "csm_owner": "X",
         "plan": "Basico", "state": "CDMX", "churn_date": None}
    )
    deals = [
        {"deal_id": "D-9999", "hubspot_id": "HS-999999", "stage": "closedwon", "amount": 1000.0,
         "created_date": "2023-01-01", "close_date": "2023-01-15", "pipeline": "New Business", "lead_source": "Web"}
    ]
    return {
        "raw_companies": pd.DataFrame(companies),
        "raw_accounts": pd.DataFrame(accounts),
        "raw_product_usage": pd.DataFrame(usage),
        "raw_deals": pd.DataFrame(deals),
        "raw_marketing_touches": pd.DataFrame(columns=["touch_id", "hubspot_id", "channel", "touch_date", "campaign"]),
        "raw_customers": pd.DataFrame(columns=["vitally_id", "domain", "company_name", "csm_email"]),
        "raw_tickets": pd.DataFrame(
            columns=["ticket_id", "vitally_id", "created_date", "priority", "status", "category", "resolution_hours", "csat_score"]
        ),
    }


@pytest.fixture(scope="module")
def minimal_master_dataset(tmp_path_factory) -> pd.DataFrame:
    raw_tables = _minimal_raw_tables()
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    db_path = tmp_path_factory.mktemp("usage_trend") / "worky.duckdb"
    con = open_connection(db_path)
    try:
        outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
    finally:
        con.close()
    return outputs["master_dataset"].set_index("hubspot_id")


def test_los_tres_estados_de_trend_status(minimal_master_dataset: pd.DataFrame) -> None:
    assert minimal_master_dataset.loc["HS-600001", "trend_status"] == "no_usage"
    assert pd.isna(minimal_master_dataset.loc["HS-600001", "trend_usage"])
    assert minimal_master_dataset.loc["HS-600002", "trend_status"] == "insufficient_history"
    assert pd.isna(minimal_master_dataset.loc["HS-600002", "trend_usage"])
    assert minimal_master_dataset.loc["HS-600003", "trend_status"] == "computed"


def test_ewma_9_en_cero_da_trend_usage_0_000000(minimal_master_dataset: pd.DataFrame) -> None:
    assert minimal_master_dataset.loc["HS-600003", "trend_usage"] == "0.000000"
