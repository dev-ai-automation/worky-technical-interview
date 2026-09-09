"""Contratos de forma y banda del health score (ADR-005), calculables en memoria.

Mismo patron que `worky_engine.quality.contracts` y
`analysis_contracts`: cada `assert_*` valida una sola regla sobre el
DataFrame que ya produce `compute_scores`, sin abrir DuckDB. Los tres
contratos que necesitan el archivo materializado o la sabana, y
`run_health_contracts`, llegan en el PR 2 con `runner.py` (brecha
documentada en tasks.md).
"""

from __future__ import annotations

import pandas as pd

from worky_engine.health.scoring import FLAG_RATES, MIN_USAGE_MONTHS, WEIGHTS
from worky_engine.quality.contracts import ContractViolation

BAND_DOMAIN = {"sin historia", "riesgo alto", "riesgo medio", "riesgo bajo"}
SUBSCORE_COLUMNS = ("score_momentum", "score_mom", "score_drawdown", "score_tenure", "activation_score")


def assert_health_one_row_per_company(scores: pd.DataFrame) -> None:
    """Una fila por `master_id`, sin repetidos."""
    duplicated = scores["master_id"].duplicated()
    if duplicated.any():
        raise ContractViolation(f"contrato assert_health_one_row_per_company: {int(duplicated.sum())} repetidos")


def assert_health_score_within_range(scores: pd.DataFrame) -> None:
    """`health_score` y los cinco subpuntajes caen en [0, 100] cuando tienen valor."""
    for column in ("health_score",) + SUBSCORE_COLUMNS:
        values = pd.to_numeric(scores[column], errors="coerce").dropna()
        invalid = (values < 0) | (values > 100)
        if invalid.any():
            raise ContractViolation(
                f"contrato assert_health_score_within_range: '{column}' fuera de [0, 100] en "
                f"{int(invalid.sum())} filas"
            )


def assert_health_band_domain(scores: pd.DataFrame) -> None:
    """`risk_band` solo toma los cuatro valores del dominio."""
    invalid = set(scores["risk_band"].dropna()) - BAND_DOMAIN
    if invalid:
        raise ContractViolation(f"contrato assert_health_band_domain: valores no permitidos {sorted(invalid)}")


def assert_health_band_matches_score(scores: pd.DataFrame) -> None:
    """`health_score` vacio si y solo si `risk_band = 'sin historia'`."""
    is_sin_historia = scores["risk_band"] == "sin historia"
    has_score = scores["health_score"].notna()
    if (is_sin_historia & has_score).any():
        raise ContractViolation("contrato assert_health_band_matches_score: 'sin historia' con health_score")
    if (~is_sin_historia & ~has_score).any():
        raise ContractViolation("contrato assert_health_band_matches_score: fuera de 'sin historia' sin health_score")


def assert_health_subscores_match_history(scores: pd.DataFrame) -> None:
    """Los tres subpuntajes de uso tienen valor si y solo si `usage_months_asof >= 3`."""
    has_history = scores["usage_months_asof"] >= MIN_USAGE_MONTHS
    for column in ("score_momentum", "score_mom", "score_drawdown"):
        has_value = scores[column].notna()
        if (has_history != has_value).any():
            raise ContractViolation(f"contrato assert_health_subscores_match_history: '{column}' vs usage_months_asof")


def assert_health_score_matches_weights(scores: pd.DataFrame) -> None:
    """Recalcular la suma ponderada desde las columnas reproduce `health_score` en toda fila con score."""
    has_score = scores["health_score"].notna()
    recomputed = (
        scores.loc[has_score, "score_momentum"] * WEIGHTS["momentum"]
        + scores.loc[has_score, "score_mom"] * WEIGHTS["mom"]
        + scores.loc[has_score, "score_drawdown"] * WEIGHTS["drawdown"]
        + scores.loc[has_score, "score_tenure"] * WEIGHTS["tenure"]
    ).round(2)
    mismatched = recomputed != scores.loc[has_score, "health_score"].round(2)
    if mismatched.any():
        raise ContractViolation(f"contrato assert_health_score_matches_weights: {int(mismatched.sum())} filas no cuadran")


def assert_health_flags_match_rates(scores: pd.DataFrame) -> None:
    """Cada `flagged_r` marca cerca de la proporcion r del libro activo con score, y las tres marcas quedan anidadas."""
    active_book = scores.loc[(~scores["churned"].astype(bool)) & scores["health_score"].notna()]
    if not active_book.empty:
        for rate in FLAG_RATES:
            label = f"flagged_{int(rate * 100)}"
            flagged_count = int(active_book[label].sum())
            expected = round(rate * len(active_book))
            tolerance = max(1, int(0.05 * len(active_book)))
            if abs(flagged_count - expected) > tolerance:
                raise ContractViolation(
                    f"contrato assert_health_flags_match_rates: '{label}' marca {flagged_count} cuentas, "
                    f"se esperaban cerca de {expected} ({rate:.0%} de {len(active_book)})"
                )
    nested_10_15 = (~scores["flagged_10"] | scores["flagged_15"]).all()
    nested_15_20 = (~scores["flagged_15"] | scores["flagged_20"]).all()
    if not (nested_10_15 and nested_15_20):
        raise ContractViolation("contrato assert_health_flags_match_rates: las marcas no quedan anidadas")


def assert_health_support_non_negative(scores: pd.DataFrame) -> None:
    """`tickets_window_total`, `tickets_window_urgent` y `activation_score` nunca son negativos, y urgentes <= total."""
    for column in ("tickets_window_total", "tickets_window_urgent"):
        if (pd.to_numeric(scores[column], errors="coerce") < 0).any():
            raise ContractViolation(f"contrato assert_health_support_non_negative: '{column}' negativo")
    activation = pd.to_numeric(scores["activation_score"], errors="coerce").dropna()
    if (activation < 0).any():
        raise ContractViolation("contrato assert_health_support_non_negative: activation_score negativo")
    if (scores["tickets_window_urgent"] > scores["tickets_window_total"]).any():
        raise ContractViolation("contrato assert_health_support_non_negative: urgentes > total en alguna fila")
