"""Metricas de validacion contra `churn_date`: AUC, precision, recall y capacidad (ADR-005, seccion 6 del diseno).

Todas se calculan sobre los DataFrames de score que ya produce
`health.runner.run_health` (numericos, antes de formatear a texto para
el CSV); ninguna funcion abre conexion de DuckDB ni lee un archivo. El
AUC reusa el alias publico `worky_engine.harness.auc` (decision D4 del
diseno de A3), nunca una copia del calculo.
"""

from __future__ import annotations

import pandas as pd

from worky_engine.harness import auc as harness_auc

FLAG_RATES: tuple[float, ...] = (0.10, 0.15, 0.20)
FIXED_CUT_SCORE = 40.0
CSM_COUNT = 7

# Direccion de riesgo por senal (D12, D15, ADR-005): "low" es mas bajo
# es mas riesgo (el mismo sentido que health_score, donde 100 es lo mas
# sano); "high" es al reves, solo el conteo de tickets.
SIGNAL_DIRECTIONS: dict[str, str] = {
    "sig_momentum": "low",
    "sig_mom": "low",
    "sig_drawdown": "low",
    "sig_tenure": "low",
    "activation_score": "low",
    "csat_window_avg": "low",
    "tickets_window_total": "high",
    "tickets_window_urgent": "high",
    "health_score": "low",
}


def _churned_mask(scores: pd.DataFrame) -> pd.Series:
    return scores["churned"].astype(bool)


def auc_by_signal(scores: pd.DataFrame, columns: list[str] | None = None) -> dict[str, float]:
    """AUC del harness por columna: probabilidad de que una baja muestre peor senal que una activa.

    "Peor" depende de la direccion de `SIGNAL_DIRECTIONS`: para las de
    direccion "high" (tickets), se invierten los dos grupos antes de
    llamar al alias, porque `harness.auc(a, b)` siempre mide
    `P(a < b)` (mas bajo es peor senal en el primer argumento).
    """
    columns = columns or list(SIGNAL_DIRECTIONS)
    churned = _churned_mask(scores)
    result: dict[str, float] = {}
    for column in columns:
        values = pd.to_numeric(scores[column], errors="coerce")
        churned_values, active_values = values[churned], values[~churned]
        direction = SIGNAL_DIRECTIONS.get(column, "low")
        if direction == "low":
            result[column] = harness_auc(churned_values, active_values)
        else:
            result[column] = harness_auc(active_values, churned_values)
    return result


def undetectable_count(scores: pd.DataFrame) -> int:
    """Bajas en banda 'sin historia': no detectables por falta de historia de uso (D17, D19)."""
    return int((_churned_mask(scores) & (scores["risk_band"] == "sin historia")).sum())


def precision_recall(scores: pd.DataFrame, flagged_column: str) -> dict[str, float]:
    """Precision sobre toda la poblacion evaluada; recall general sobre las bajas con `account_id` (D17).

    `recall_detectable` mide sobre el subconjunto de bajas que si
    recibio `health_score` (D17, D19): esa es la poblacion sobre la que
    la regla de aceptacion de D18 se restablecio en la Adenda 1 del
    ADR-005, porque una baja "sin historia" nunca recibe `health_score`
    y nunca puede marcarse, sin importar el peso de ningun subpuntaje.
    `undetectable` es el conteo de bajas fuera de esa poblacion, el
    mismo que `undetectable_count` calcula sobre todo el DataFrame.
    """
    churned = _churned_mask(scores)
    flagged = scores[flagged_column].astype(bool)
    has_score = scores["health_score"].notna()
    denominator = int(churned.sum())
    detected = int((churned & flagged).sum())
    total_flagged = int(flagged.sum())
    detectable_denominator = int((churned & has_score).sum())
    detectable_detected = int((churned & has_score & flagged).sum())
    return {
        "flagged": total_flagged,
        "denominator": denominator,
        "detected": detected,
        "precision": (detected / total_flagged) if total_flagged else float("nan"),
        "recall": (detected / denominator) if denominator else float("nan"),
        "detectable_denominator": detectable_denominator,
        "recall_detectable": (detectable_detected / detectable_denominator) if detectable_denominator else float("nan"),
        "undetectable": denominator - detectable_denominator,
    }


def mrr_weighted_recall(scores: pd.DataFrame, flagged_column: str) -> float:
    """Share del `mrr_mxn` de las bajas marcadas entre el `mrr_mxn` de todas las bajas del denominador (D17).

    Una baja `mrr_source = 'unresolved'` llega con `mrr_mxn` vacio, que
    `to_numeric` convierte en NaN; `fillna(0.0)` la hace aportar cero
    tanto al numerador como al denominador, nunca la descuenta.
    """
    churned = _churned_mask(scores)
    flagged = scores[flagged_column].astype(bool)
    mrr = pd.to_numeric(scores["mrr_mxn"], errors="coerce").fillna(0.0)
    denominator = float(mrr[churned].sum())
    if denominator == 0:
        return float("nan")
    return float(mrr[churned & flagged].sum() / denominator)


def rate_metrics(scores: pd.DataFrame) -> dict[str, dict]:
    """Precision, recall general, recall detectable y recall ponderado por MRR a las tres tasas de marcado (10, 15, 20 %)."""
    table = {}
    for rate in FLAG_RATES:
        column = f"flagged_{int(rate * 100)}"
        table[column] = {**precision_recall(scores, column), "recall_mrr": mrr_weighted_recall(scores, column)}
    return table


def confusion_matrix_15(scores: pd.DataFrame) -> dict[str, int]:
    """Matriz de confusion al 15 %, con los no detectables senalados dentro de los falsos negativos."""
    churned = _churned_mask(scores)
    flagged = scores["flagged_15"].astype(bool)
    return {
        "tp": int((churned & flagged).sum()),
        "fp": int((~churned & flagged).sum()),
        "fn": int((churned & ~flagged).sum()),
        "tn": int((~churned & ~flagged).sum()),
        "fn_undetectable": undetectable_count(scores),
    }


def fixed_cut_metrics(scores: pd.DataFrame, cutoff: float = FIXED_CUT_SCORE) -> dict[str, float]:
    """Corte fijo de referencia (`health_score < 40`), reportado aparte del umbral operativo (D19)."""
    score_values = pd.to_numeric(scores["health_score"], errors="coerce")
    churned = _churned_mask(scores)
    flagged = score_values.notna() & (score_values < cutoff)
    denominator = int(churned.sum())
    detected = int((churned & flagged).sum())
    total_flagged = int(flagged.sum())
    return {
        "threshold": cutoff,
        "flagged": total_flagged,
        "precision": (detected / total_flagged) if total_flagged else float("nan"),
        "recall": (detected / denominator) if denominator else float("nan"),
    }


def capacity_by_csm(scores: pd.DataFrame, csm_count: int = CSM_COUNT) -> dict[str, dict]:
    """Cuentas marcadas por cada una de las tres tasas, sobre el libro activo, repartidas entre los CSM."""
    active_book = scores.loc[(~_churned_mask(scores)) & scores["health_score"].notna()]
    table = {}
    for rate in FLAG_RATES:
        column = f"flagged_{int(rate * 100)}"
        flagged_count = int(active_book[column].sum()) if not active_book.empty else 0
        table[column] = {"active_book": len(active_book), "flagged": flagged_count, "per_csm": round(flagged_count / csm_count, 1)}
    return table


def early_detection_k3(primary_scores: pd.DataFrame, k3_scores: pd.DataFrame) -> dict[str, float]:
    """De las bajas marcadas al 15 % en k = 2, cuantas ya estaban marcadas un mes antes, en k = 3."""
    churned_flagged_ids = set(
        primary_scores.loc[_churned_mask(primary_scores) & primary_scores["flagged_15"].astype(bool), "master_id"]
    )
    if not churned_flagged_ids:
        return {"eligible": 0, "already_flagged": 0, "share": float("nan")}
    k3_by_id = k3_scores.set_index("master_id")
    eligible = [
        master_id
        for master_id in churned_flagged_ids
        if master_id in k3_by_id.index and pd.notna(k3_by_id.loc[master_id, "health_score"])
    ]
    already_flagged = [master_id for master_id in eligible if bool(k3_by_id.loc[master_id, "flagged_15"])]
    share = (len(already_flagged) / len(eligible)) if eligible else float("nan")
    return {"eligible": len(eligible), "already_flagged": len(already_flagged), "share": share}


def sensitivity_summary(scores: pd.DataFrame) -> dict[str, float]:
    """AUC y metricas al 20 % de una corrida de sensibilidad, comparables contra la corrida principal."""
    return {"auc": auc_by_signal(scores, ["health_score"])["health_score"], **precision_recall(scores, "flagged_20")}


# Pesos iguales para la sensibilidad "pesos iguales" (seccion 6 del
# diseno, tabla de metricas.py): mismos cuatro subpuntajes ya
# normalizados de la corrida principal, con 0.25 cada uno en vez de
# los pesos del ADR-005.
EQUAL_WEIGHTS: dict[str, float] = {"momentum": 0.25, "mom": 0.25, "drawdown": 0.25, "tenure": 0.25}


def _recompute_weighted_score(scores: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """Recalcula la suma ponderada con otro juego de pesos sobre los cuatro subpuntajes ya normalizados."""
    has_history = scores["score_momentum"].notna()
    total = (
        scores["score_momentum"] * weights["momentum"]
        + scores["score_mom"] * weights["mom"]
        + scores["score_drawdown"] * weights["drawdown"]
        + scores["score_tenure"] * weights["tenure"]
    ).round(2)
    return total.where(has_history)


def equal_weights_sensitivity(scores: pd.DataFrame, rate: float = 0.20) -> dict[str, float]:
    """Sensibilidad de pesos iguales (0.25 cada subpuntaje), mismo umbral del libro activo que D16.

    Recalcula el score de la corrida principal con `EQUAL_WEIGHTS` en
    vez de `WEIGHTS`, y marca con el mismo criterio de la seccion 5 del
    diseno: el umbral sale del percentil de la tasa sobre las empresas
    activas con score definido, aplicado por igual a activas y a bajas.
    """
    churned = _churned_mask(scores)
    alt_score = _recompute_weighted_score(scores, EQUAL_WEIGHTS)
    active_book = alt_score[(~churned) & alt_score.notna()]
    if active_book.empty:
        return {"auc": float("nan"), "recall": float("nan"), "flagged": 0}
    threshold = active_book.quantile(rate, interpolation="lower")
    flagged = alt_score.notna() & (alt_score <= threshold)
    denominator = int(churned.sum())
    detected = int((churned & flagged).sum())
    return {
        "auc": harness_auc(alt_score[churned], alt_score[~churned]),
        "recall": (detected / denominator) if denominator else float("nan"),
        "flagged": int(flagged.sum()),
    }


def harness_convention_sensitivity(scores: pd.DataFrame, rate: float = 0.20) -> dict[str, float]:
    """Sensibilidad con la convencion del harness (D16, rechazada como regla principal): umbral sobre la poblacion completa.

    Usa el mismo `health_score` de la corrida principal (pesos del
    ADR-005), pero el umbral de marcado sale del percentil de la tasa
    sobre bajas y activas juntas, en vez de solo el libro activo: es la
    convencion que ya usa `measurements.md`, publicada aqui solo para
    poder comparar los dos numeros lado a lado.
    """
    score_values = pd.to_numeric(scores["health_score"], errors="coerce")
    defined = score_values.dropna()
    if defined.empty:
        return {"auc": float("nan"), "recall": float("nan"), "flagged": 0}
    threshold = defined.quantile(rate, interpolation="lower")
    flagged = score_values.notna() & (score_values <= threshold)
    churned = _churned_mask(scores)
    denominator = int(churned.sum())
    detected = int((churned & flagged).sum())
    return {
        "auc": auc_by_signal(scores, ["health_score"])["health_score"],
        "recall": (detected / denominator) if denominator else float("nan"),
        "flagged": int(flagged.sum()),
    }


def acceptance_check(scores: pd.DataFrame, auc_threshold: float = 0.95, recall_threshold: float = 0.85) -> dict:
    """Regla de aceptacion restablecida en la Adenda 1 del ADR-005 (D18): AUC >= 0.95 y recall_detectable >= 0.85 al 20 %.

    `recall_detectable` se mide sobre las bajas que si recibieron
    `health_score` (D17, D19), no sobre el total: una baja "sin
    historia" nunca recibe `health_score` y nunca puede marcarse, asi
    que el recall general trae un techo estructural que ningun peso
    puede mover. El recall general y el conteo de no detectables se
    siguen reportando aparte, como hallazgo de onboarding para la
    Parte B (Adenda 1).
    """
    auc_score = auc_by_signal(scores, ["health_score"])["health_score"]
    metrics_20 = precision_recall(scores, "flagged_20")
    recall_20 = metrics_20["recall"]
    recall_detectable_20 = metrics_20["recall_detectable"]
    return {
        "auc": auc_score,
        "recall_20": recall_20,
        "recall_detectable_20": recall_detectable_20,
        "undetectable": metrics_20["undetectable"],
        "passed": bool(auc_score >= auc_threshold and recall_detectable_20 >= recall_threshold),
    }
