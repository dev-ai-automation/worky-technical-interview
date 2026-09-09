"""Una prueba por regla del ADR-005 sobre un fixture minimo propio (seccion 9 del diseno de A3).

No extiende `tests/fixtures/mini_dataset.py` (moveria conteos ya
fijados en otras pruebas); `runner.py` (con `HEALTH_FILES` compartida)
llega en el PR 2. Las reglas de SQL (exclusion por corte, denominadores
degenerados, antiguedad recortada) corren sobre un fixture minimo via
DuckDB; las de `scoring.py` (empates, "sin historia", suma ponderada,
marcas) corren directo sobre `compute_scores` con un DataFrame
sintetico, sin repetir el ensamblaje completo.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worky_engine.health.scoring import compute_scores
from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset, open_connection
from worky_engine.master_dataset.assemble import run_sql_files
from worky_engine.quality import health_contracts as hc

HEALTH_FILES = [
    "health/h1_company_asof.sql",
    "health/h2_usage_signals.sql",
    "health/h3_tenure.sql",
    "health/h4_support_asof.sql",
    "health/h5_activation.sql",
    "health/h6_asof_inputs.sql",
]

_EMPTY_DEALS = pd.DataFrame(columns=["deal_id", "hubspot_id", "stage", "amount", "created_date", "close_date", "pipeline", "lead_source"])
_EMPTY_TOUCHES = pd.DataFrame(columns=["touch_id", "hubspot_id", "channel", "touch_date", "campaign"])


def _company(hubspot_id: str, name: str, domain: str, signup_date: str, churn_date: str | None = None) -> dict:
    return {
        "hubspot_id": hubspot_id, "name": name, "domain": domain, "segment": "SMB",
        "industry": "Retail", "mrr": 1000.0, "currency": "MXN", "signup_date": signup_date,
        "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": churn_date,
    }


def _usage_rows(account_id: str, months_users: list[tuple[str, int]]) -> list[dict]:
    return [
        {
            "account_id": account_id, "month": month, "active_users": users, "logins": users * 2,
            "payroll_runs_completed": 1, "features_used": 3, "api_calls": users * 5,
        }
        for month, users in months_users
    ]


def _minimal_raw_tables() -> dict[str, pd.DataFrame]:
    """Tres empresas, cada una para una regla que solo el SQL puede probar.

    `HS-810001` (con baja, asof_month = 2024-06 con k = 2): 5 meses de
    uso creciente hasta el corte, mas un mes de fuga en 2024-07 con un
    salto enorme que la exclusion debe descartar; dos tickets, uno el
    primer dia del mes siguiente al corte (excluido) y otro el ultimo
    dia del mes de corte (incluido). `HS-810003`: 3 meses de uso en
    cero, los tres denominadores degenerados a la vez. `HS-810004`:
    alta el mes siguiente al corte, antiguedad recortada a cero.
    """
    companies = [
        _company("HS-810001", "Fuga Uso SA de CV", "fuga810.com.mx", "2022-01-01", "2024-08-15"),
        _company("HS-810003", "Cero Absoluto SA de CV", "cero810.com.mx", "2021-01-01"),
        _company("HS-810004", "Alta Tardia SA de CV", "tardia810.com.mx", "2024-07-01"),
    ]
    accounts = [
        {"account_id": "ACC-8101", "hubspot_id": "HS-810001", "account_name": "Fuga Uso", "created_at": "2022-01-01"},
        {"account_id": "ACC-8103", "hubspot_id": "HS-810003", "account_name": "Cero Absoluto", "created_at": "2021-01-01"},
    ]
    usage = _usage_rows(
        "ACC-8101", [("2024-02", 40), ("2024-03", 45), ("2024-04", 50), ("2024-05", 55), ("2024-06", 60), ("2024-07", 99999)]
    ) + _usage_rows("ACC-8103", [("2024-04", 0), ("2024-05", 0), ("2024-06", 0)])
    tickets = [
        # Excluido: primer dia del mes siguiente al corte (asof_month = 2024-06).
        {"ticket_id": "T-8101a", "vitally_id": "cus_8101", "created_date": "2024-07-01", "priority": "Urgent",
         "status": "closed", "category": "bug", "resolution_hours": 2, "csat_score": 4},
        # Incluido: ultimo dia del mes de corte.
        {"ticket_id": "T-8101b", "vitally_id": "cus_8101", "created_date": "2024-06-30", "priority": "Low",
         "status": "closed", "category": "billing", "resolution_hours": 1, "csat_score": 3},
    ]
    customers = [
        {"vitally_id": "cus_8101", "domain": "fuga810.com.mx", "company_name": "Fuga Uso SA de CV", "csm_email": "x@worky.mx"},
    ]
    return {
        "raw_companies": pd.DataFrame(companies),
        "raw_accounts": pd.DataFrame(accounts),
        "raw_product_usage": pd.DataFrame(usage),
        "raw_deals": _EMPTY_DEALS,
        "raw_marketing_touches": _EMPTY_TOUCHES,
        "raw_customers": pd.DataFrame(customers),
        "raw_tickets": pd.DataFrame(tickets),
    }


@pytest.fixture(scope="module")
def asof_inputs(tmp_path_factory) -> pd.DataFrame:
    raw_tables = _minimal_raw_tables()
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    db_path = tmp_path_factory.mktemp("health_rules") / "worky_health.duckdb"
    con = open_connection(db_path)
    try:
        assemble_master_dataset(con, raw_tables, identity_outputs)
        con.execute("CREATE OR REPLACE TABLE health_params AS SELECT 2 AS k_months, 2 AS active_offset")
        run_sql_files(con, HEALTH_FILES)
        return con.execute("SELECT * FROM health_asof_inputs ORDER BY master_id").df().set_index("hubspot_id")
    finally:
        con.close()


def _closed_form_momentum(values: list[float]) -> float:
    """EWMA span 3 contra span 9, con la misma regla de `ewma_9 = 0 -> 0.0` que h2_usage_signals.sql."""
    series = pd.Series(values, dtype=float)
    ewma_3 = series.ewm(span=3, adjust=True).mean().iloc[-1]
    ewma_9 = series.ewm(span=9, adjust=True).mean().iloc[-1]
    if ewma_9 == 0:
        return 0.0
    return float(ewma_3 / ewma_9 - 1)


def test_mes_de_uso_posterior_al_corte_queda_excluido(asof_inputs: pd.DataFrame) -> None:
    """El mes de fuga (2024-07, con un salto a 99999) no debe mover sig_momentum ni usage_months_asof."""
    row = asof_inputs.loc["HS-810001"]
    assert int(row["usage_months_asof"]) == 5, "el mes de fuga no debe contarse en usage_months_asof"
    expected = _closed_form_momentum([40, 45, 50, 55, 60])
    assert row["sig_momentum"] == pytest.approx(expected, abs=1e-6)
    leaked = _closed_form_momentum([40, 45, 50, 55, 60, 99999])
    assert leaked - row["sig_momentum"] > 0.5, "si el mes de fuga hubiera entrado, el momentum se dispararia"


def test_ticket_excluido_el_primer_dia_del_mes_siguiente_e_incluido_el_ultimo_dia_del_corte(
    asof_inputs: pd.DataFrame,
) -> None:
    row = asof_inputs.loc["HS-810001"]
    assert int(row["tickets_window_total"]) == 1, "solo el ticket del ultimo dia del mes de corte debe entrar"
    assert int(row["tickets_window_urgent"]) == 0, "el ticket urgente cae fuera de la ventana"


def test_tres_denominadores_degenerados_valen_cero(asof_inputs: pd.DataFrame) -> None:
    row = asof_inputs.loc["HS-810003"]
    assert row["sig_momentum"] == 0.0
    assert row["sig_mom"] == 0.0
    assert row["sig_drawdown"] == 0.0
    assert int(row["usage_months_asof"]) >= 3, "3 meses de uso ya alcanzan para tener subpuntajes"


def test_antiguedad_se_recorta_a_cero_para_una_empresa_dada_de_alta_despues_del_corte(
    asof_inputs: pd.DataFrame,
) -> None:
    row = asof_inputs.loc["HS-810004"]
    assert int(row["sig_tenure"]) == 0


def _synthetic_asof_inputs(rows: list[dict]) -> pd.DataFrame:
    """Filas sinteticas con la forma minima que `compute_scores` necesita, sin pasar por DuckDB.

    Los empates, la banda "sin historia", la suma ponderada y las
    marcas de capacidad son reglas de `scoring.py` (tabla de modulos,
    seccion 1 del diseno), no del SQL: probarlas aqui evita repetir el
    ensamblaje completo de identidad y marts por cada una.
    """
    defaults = {
        "sig_momentum": None, "sig_mom": None, "sig_drawdown": None, "activation_raw": None,
        "tickets_window_total": 0, "tickets_window_urgent": 0,
    }
    return pd.DataFrame([{**defaults, **row} for row in rows])


def test_empates_en_el_rango_percentil_producen_el_mismo_subpuntaje() -> None:
    frame = _synthetic_asof_inputs(
        [
            {"master_id": "A", "churned": False, "usage_months_asof": 3, "sig_momentum": 0.1, "sig_mom": 0.1, "sig_drawdown": 0.1, "sig_tenure": 24},
            {"master_id": "B", "churned": False, "usage_months_asof": 3, "sig_momentum": 0.1, "sig_mom": 0.1, "sig_drawdown": 0.1, "sig_tenure": 24},
            {"master_id": "C", "churned": False, "usage_months_asof": 3, "sig_momentum": 0.5, "sig_mom": 0.5, "sig_drawdown": 0.5, "sig_tenure": 40},
        ]
    )
    scores = compute_scores(frame).set_index("master_id")
    for column in ("score_momentum", "score_mom", "score_drawdown", "score_tenure", "health_score"):
        assert scores.loc["A", column] == scores.loc["B", column], f"'{column}' deberia empatar"


def test_cuenta_de_dos_meses_cae_en_sin_historia_con_antiguedad_y_sin_subpuntajes_de_uso() -> None:
    frame = _synthetic_asof_inputs([{"master_id": "A", "churned": False, "usage_months_asof": 2, "sig_tenure": 10}])
    row = compute_scores(frame).iloc[0]
    assert row["risk_band"] == "sin historia"
    assert pd.isna(row["health_score"])
    assert pd.isna(row["score_momentum"])
    assert pd.notna(row["score_tenure"]), "la antiguedad tiene cobertura total, incluso en 'sin historia'"


def test_suma_ponderada_recomputable_a_mano() -> None:
    frame = _synthetic_asof_inputs(
        [
            {"master_id": "A", "churned": False, "usage_months_asof": 5, "sig_momentum": 0.2, "sig_mom": 0.05, "sig_drawdown": -0.1, "sig_tenure": 30},
            {"master_id": "B", "churned": False, "usage_months_asof": 5, "sig_momentum": 0.05, "sig_mom": 0.2, "sig_drawdown": 0.3, "sig_tenure": 10},
        ]
    )
    row = compute_scores(frame).set_index("master_id").loc["A"]
    recomputed = round(
        0.35 * row["score_momentum"] + 0.20 * row["score_mom"] + 0.15 * row["score_drawdown"] + 0.30 * row["score_tenure"], 2
    )
    assert recomputed == row["health_score"]


@pytest.fixture(scope="module")
def capacity_scores() -> pd.DataFrame:
    """20 empresas activas, la misma senal de uso empatada y solo la antiguedad distinta (0 a 19)."""
    rows = [
        {"master_id": f"M{index:03d}", "churned": False, "usage_months_asof": 3, "sig_momentum": 0.0, "sig_mom": 0.0, "sig_drawdown": 0.0, "sig_tenure": index}
        for index in range(20)
    ]
    return compute_scores(_synthetic_asof_inputs(rows))


def test_las_tres_marcas_anidadas_con_proporcion_exacta_y_los_ocho_contratos(capacity_scores: pd.DataFrame) -> None:
    assert int(capacity_scores["flagged_10"].sum()) == 2
    assert int(capacity_scores["flagged_15"].sum()) == 3
    assert int(capacity_scores["flagged_20"].sum()) == 4
    assert (~capacity_scores["flagged_10"] | capacity_scores["flagged_15"]).all()
    assert (~capacity_scores["flagged_15"] | capacity_scores["flagged_20"]).all()
    # Las marcadas al 15% son las de menor antiguedad (indices 0, 1, 2).
    assert set(capacity_scores.loc[capacity_scores["flagged_15"], "master_id"]) == {"M000", "M001", "M002"}
    # Cobertura minima de health_contracts.py (tarea 1.9): ninguno truena sobre este libro.
    for check in (
        hc.assert_health_one_row_per_company, hc.assert_health_score_within_range, hc.assert_health_band_domain,
        hc.assert_health_band_matches_score, hc.assert_health_subscores_match_history,
        hc.assert_health_score_matches_weights, hc.assert_health_flags_match_rates,
        hc.assert_health_support_non_negative,
    ):
        check(capacity_scores)
