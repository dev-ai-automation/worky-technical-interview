"""Percentiles, banda "sin historia", suma ponderada y marcas por capacidad (ADR-005).

`compute_scores` recibe el DataFrame que ya arma la vista
`health_asof_inputs` (seccion 1 del diseno, reparto SQL/pandas de la
decision D3) y regresa un DataFrame con los cuatro subpuntajes
normalizados, `activation_score`, el `health_score` como suma
ponderada, `risk_band` y las tres marcas de capacidad. No abre
conexion de DuckDB ni lee ningun archivo: solo transforma el
DataFrame que le entregan.
"""

from __future__ import annotations

import pandas as pd

# Pesos del ADR-005, el juego de juicio original (decision D18 del
# diseno): momentum 0.35, cambio mes a mes 0.20, caida 0.15, antiguedad
# 0.30. La prueba de aceptacion marcada `dataset` (PR 2, tarea 2.5)
# corrio sobre el dataset real con estos pesos y midio AUC 0.997, pero
# el recall general se quedo en 0.753 porque 22 de las 89 empresas
# dadas de baja caen en la banda "sin historia" y nunca reciben
# `health_score` (D17, D19): es un techo estructural, no un problema de
# pesos, y probarlo con la mezcla medida (adenda descartada) no lo
# movio. Por eso la regla de aceptacion se mide sobre las empresas
# detectables (con `health_score`), no sobre el total; la Adenda 1 de
# `docs/decisions/ADR-005-health-score-model.md` explica la medicion
# completa y por que se descarto cambiar los pesos.
WEIGHTS: dict[str, float] = {
    "momentum": 0.35,
    "mom": 0.20,
    "drawdown": 0.15,
    "tenure": 0.30,
}

# Tasas de marcado que reporta validation.md (10 %, 15 % operativo,
# 20 %): la seccion 5 del diseno fija el 15 % como el umbral que
# reparte, en el dataset del caso, 78 cuentas del libro activo con
# score entre 7 CSM (ADR-005).
FLAG_RATES: tuple[float, ...] = (0.10, 0.15, 0.20)

MIN_USAGE_MONTHS = 3


def percentile_score(values: pd.Series) -> pd.Series:
    """0 a 100 por rango percentil, empates promediados; 100 es lo mas sano (decision D12).

    Los nulos se preservan: `rank` los deja en NaN y no entran a la
    poblacion evaluada, que es la de las empresas con esa senal
    definida en el mismo mes de corte, bajas y activas juntas
    (decision D13).
    """
    return (values.rank(pct=True, method="average") * 100).round(2)


def _weighted_sum(scores: pd.DataFrame) -> pd.Series:
    """Suma ponderada de los cuatro subpuntajes ya redondeados (decision D14).

    `activation_score` no entra a esta suma: `WEIGHTS` no trae una
    entrada de activacion, asi que una activacion nula (empresa sin
    los primeros tres meses de uso todavia) nunca envenena el
    `health_score` de nadie. `activation_score` se calcula y se publica
    aparte, como senal medida con peso cero (ADR-005).
    """
    total = (
        scores["score_momentum"] * WEIGHTS["momentum"]
        + scores["score_mom"] * WEIGHTS["mom"]
        + scores["score_drawdown"] * WEIGHTS["drawdown"]
        + scores["score_tenure"] * WEIGHTS["tenure"]
    )
    return total.round(2)


def _risk_band(scores: pd.DataFrame, threshold_alto: float, threshold_medio: float) -> pd.Series:
    """`risk_band` en {sin historia, riesgo alto, riesgo medio, riesgo bajo} (decision D19).

    `threshold_alto` y `threshold_medio` ya vienen calculados sobre el
    libro de empresas activas con `health_score` definido (decision
    D16): alto es el 15 % marcado, medio es el siguiente 15 %, bajo es
    el resto. Una empresa sin `health_score` siempre cae en
    "sin historia", sin importar el resto de sus senales.
    """
    has_score = scores["health_score"].notna()
    band = pd.Series("riesgo bajo", index=scores.index)
    band[has_score & (scores["health_score"] <= threshold_medio)] = "riesgo medio"
    band[has_score & (scores["health_score"] <= threshold_alto)] = "riesgo alto"
    band[~has_score] = "sin historia"
    return band


def compute_scores(asof_inputs: pd.DataFrame) -> pd.DataFrame:
    """Convierte `health_asof_inputs` en el DataFrame de scores del ADR-005.

    Regla de la banda "sin historia" (decision D19, seccion 4 del
    diseno): una empresa con `usage_months_asof < 3` no recibe los tres
    subpuntajes de uso ni `health_score`, si recibe `score_tenure`, y
    su `risk_band` es "sin historia" sin importar el resto de sus
    senales.

    El umbral operativo (decision D16) sale del percentil de la tasa de
    marcado sobre las empresas ACTIVAS (`churned = False`) con
    `health_score` definido, y ese mismo valor se aplica a activas y a
    bajas por igual, con `interpolation="lower"` para que el corte sea
    un score que si existe en los datos.
    """
    scores = asof_inputs.copy()
    has_history = scores["usage_months_asof"] >= MIN_USAGE_MONTHS

    scores["score_momentum"] = percentile_score(scores["sig_momentum"].where(has_history))
    scores["score_mom"] = percentile_score(scores["sig_mom"].where(has_history))
    scores["score_drawdown"] = percentile_score(scores["sig_drawdown"].where(has_history))
    scores["score_tenure"] = percentile_score(scores["sig_tenure"])
    scores["activation_score"] = percentile_score(scores["activation_raw"])

    weighted = _weighted_sum(scores)
    scores["health_score"] = weighted.where(has_history)

    active_book = scores.loc[(~scores["churned"].astype(bool)) & scores["health_score"].notna(), "health_score"]
    for rate in FLAG_RATES:
        label = f"flagged_{int(rate * 100)}"
        if active_book.empty:
            scores[label] = False
            continue
        threshold = active_book.quantile(rate, interpolation="lower")
        scores[label] = scores["health_score"].notna() & (scores["health_score"] <= threshold)

    if active_book.empty:
        threshold_alto = threshold_medio = float("-inf")
    else:
        threshold_alto = active_book.quantile(0.15, interpolation="lower")
        threshold_medio = active_book.quantile(0.30, interpolation="lower")
    scores["risk_band"] = _risk_band(scores, threshold_alto, threshold_medio)

    return scores
