"""Harness de backtest de las seis formulas de tendencia del ADR-003.

Reproduce, dentro del repositorio, la comparacion que documenta el
ADR-003: evalua las seis formulas en k = 0, 2 y 3 meses antes del mes de
referencia, sobre las empresas con baja que tienen uso y las empresas
activas, y reporta la proporcion definida, el AUC, la precision y el
recall a la tasa de marcado configurable (spec `trend-backtest-harness`).

Promueve el prototipo que corrio la medicion original del ADR-003,
ahora leyendo las tres bases con `worky_engine.sources.load_raw_tables`
(solo lectura) y normalizando las fechas con `worky_engine.normalization.
normalize_date`, algo que el prototipo no hacia. Es el motivo por el que
un AUC de esta corrida puede diferir en algunas milesimas del que
publica el ADR-003: el prototipo mezclaba fechas en DD/MM/YYYY y en ISO
sin normalizar antes de comparar meses.

No depende de `assemble_master_dataset` ni de DuckDB a proposito: el
comando `backtest` corre independiente de `build` (seccion 5.3 del
diseno), asi que este modulo solo necesita pandas y numpy.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from worky_engine.normalization import normalize_date

DEFAULT_FLAG_RATE = 0.20
DEFAULT_K_VALUES = (0, 2, 3)

# Las seis formulas del ADR-003, en el mismo orden en que aparecen en su
# tabla de comparacion. "E_ewma_momentum" es la elegida para trend_usage.
FORMULA_LABELS: dict[str, str] = {
    "A_first3_vs_last3": "Primeros 3 meses contra ultimos 3 meses",
    "B_last3_vs_prev3": "Ultimos 3 meses contra los 3 meses anteriores",
    "C_norm_slope6": "Pendiente normalizada a 6 meses",
    "D_pct_of_peak": "Caida desde el mejor promedio de 3 meses",
    "E_ewma_momentum": "Momentum, EWMA span 3 contra span 9 (elegida)",
    "F_last_vs_prev1": "Mes contra mes anterior",
}


@dataclass(frozen=True)
class FormulaMetrics:
    """Una fila de metricas: una formula, un k, y sus cuatro numeros reportados."""

    formula: str
    k: int
    defined_ratio: float
    auc: float
    precision: float
    recall: float


def _company_universe(raw_companies: pd.DataFrame, raw_accounts: pd.DataFrame) -> pd.DataFrame:
    """Empresas reales (HS-1xxxxx) con su account_id y su fecha de baja, ya en ISO."""
    companies = raw_companies[raw_companies["hubspot_id"].str.startswith("HS-1")].copy()
    companies["churn_date"] = companies["churn_date"].apply(
        lambda value: None if pd.isna(value) else normalize_date(str(value))
    )
    return raw_accounts.merge(companies[["hubspot_id", "churn_date"]], on="hubspot_id", how="inner")


def _usage_series(raw_product_usage: pd.DataFrame) -> dict[str, pd.Series]:
    """Una serie de `active_users` indexada por mes (`Period`), ordenada, por cada account_id."""
    usage = raw_product_usage.copy()
    usage["period"] = pd.PeriodIndex(usage["month"], freq="M")
    return {
        account_id: group.sort_values("period").set_index("period")["active_users"]
        for account_id, group in usage.groupby("account_id")
    }


def _features(series: pd.Series, asof: pd.Period) -> dict[str, float]:
    """Las seis formulas del ADR-003 sobre `series`, usando solo meses hasta `asof` (resguardo de fuga)."""
    windowed = series[series.index <= asof]
    n = len(windowed)
    out: dict[str, float] = {"n": n}
    if n == 0:
        for key in FORMULA_LABELS:
            out[key] = float("nan")
        return out

    values = windowed.values.astype(float)
    last3 = values[-3:].mean()
    first3 = values[:3].mean()
    out["A_first3_vs_last3"] = (last3 / first3 - 1) if n >= 6 and first3 > 0 else float("nan")

    prev3 = values[-6:-3].mean() if n >= 6 else float("nan")
    out["B_last3_vs_prev3"] = (last3 / prev3 - 1) if n >= 6 and prev3 > 0 else float("nan")

    if n >= 4:
        window = values[-6:]
        slope = np.polyfit(np.arange(len(window)), window, 1)[0]
        out["C_norm_slope6"] = (slope / window.mean()) if window.mean() > 0 else float("nan")
    else:
        out["C_norm_slope6"] = float("nan")

    peak = pd.Series(values).rolling(3).mean().max() if n >= 3 else float("nan")
    out["D_pct_of_peak"] = (last3 / peak - 1) if n >= 3 and peak and peak > 0 else float("nan")

    if n >= 3:
        ewma_short = pd.Series(values).ewm(span=3, adjust=True).mean().iloc[-1]
        ewma_long = pd.Series(values).ewm(span=9, adjust=True).mean().iloc[-1]
        out["E_ewma_momentum"] = (ewma_short / ewma_long - 1) if ewma_long > 0 else float("nan")
    else:
        out["E_ewma_momentum"] = float("nan")

    out["F_last_vs_prev1"] = (values[-1] / values[-2] - 1) if n >= 2 and values[-2] > 0 else float("nan")
    return out


def _auc(positive: pd.Series, negative: pd.Series) -> float:
    """Probabilidad de que una empresa con baja muestre una tendencia peor que una activa."""
    pos = positive.dropna().values
    neg = negative.dropna().values
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    wins = (pos[:, None] < neg[None, :]).mean()
    ties = (pos[:, None] == neg[None, :]).mean()
    return float(wins + 0.5 * ties)


# Alias publico de `_auc` para `worky_engine.health.metrics` (D4 del
# diseno de A3): mismo objeto, verificado en test_harness_regression.py.
auc = _auc


def run_backtest(
    raw_tables: dict[str, pd.DataFrame],
    k_values: tuple[int, ...] = DEFAULT_K_VALUES,
    flag_rate: float = DEFAULT_FLAG_RATE,
) -> pd.DataFrame:
    """Corre las seis formulas en cada `k`, sobre las empresas con baja con uso y las activas.

    Devuelve un DataFrame largo, una fila por combinacion de formula y k,
    con las columnas de `FormulaMetrics`.
    """
    universe = _company_universe(raw_tables["raw_companies"], raw_tables["raw_accounts"])
    series_by_account = _usage_series(raw_tables["raw_product_usage"])
    end_month = pd.Period(str(raw_tables["raw_product_usage"]["month"].max()), freq="M")

    feature_rows: list[dict] = []
    for _, company in universe.iterrows():
        series = series_by_account.get(company["account_id"])
        if series is None:
            continue
        churned = pd.notna(company["churn_date"])
        reference_month = pd.Period(str(company["churn_date"])[:7], freq="M") if churned else end_month
        for k in k_values:
            row = _features(series, reference_month - k)
            row.update(account_id=company["account_id"], churned=churned, k=k)
            feature_rows.append(row)
    long_frame = pd.DataFrame(feature_rows)

    metrics: list[FormulaMetrics] = []
    for k in k_values:
        subset = long_frame[long_frame["k"] == k]
        churned_mask = subset["churned"]
        for formula in FORMULA_LABELS:
            positive = subset.loc[churned_mask, formula]
            negative = subset.loc[~churned_mask, formula]
            threshold = subset[formula].quantile(flag_rate)
            flagged = subset[formula] <= threshold
            precision = float(subset.loc[flagged, "churned"].mean()) if flagged.any() else float("nan")
            recall = float(flagged[churned_mask].mean()) if churned_mask.any() else float("nan")
            metrics.append(
                FormulaMetrics(
                    formula=formula,
                    k=k,
                    defined_ratio=float(subset[formula].notna().mean()),
                    auc=_auc(positive, negative),
                    precision=precision,
                    recall=recall,
                )
            )
    return pd.DataFrame(metric.__dict__ for metric in metrics)


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def format_report(metrics: pd.DataFrame, k_values: tuple[int, ...] = DEFAULT_K_VALUES) -> str:
    """Arma `backtest_report.md`: una tabla por `k`, en el mismo orden de formulas del ADR-003.

    Determinista: sin hora de reloj, orden fijo de formulas y de `k`.
    """
    sections = [
        "# Reporte de backtest de tendencia de uso (ADR-003)",
        "Reproduce, con las tres bases de datos reales, la comparacion de las seis formulas de "
        "tendencia sobre las empresas con baja que tienen uso y las empresas activas. En k = 0 "
        "(el propio mes de baja) el AUC queda cercano a 1.0 para casi todas las formulas: eso es "
        "evidencia de fuga de datos, no de una formula buena, tal como advierte el ADR-003.",
    ]
    for k in k_values:
        subset = metrics[metrics["k"] == k]
        rows = [
            [
                FORMULA_LABELS[row["formula"]],
                f"{row['defined_ratio'] * 100:.0f}%",
                f"{row['auc']:.3f}",
                f"{row['precision']:.3f}" if pd.notna(row["precision"]) else "",
                f"{row['recall']:.3f}" if pd.notna(row["recall"]) else "",
            ]
            for _, row in subset.iterrows()
        ]
        sections.append(
            f"## k = {k}\n\n" + _md_table(["Formula", "Definida", "AUC", "Precision", "Recall"], rows)
        )
    return "\n\n".join(sections) + "\n"
