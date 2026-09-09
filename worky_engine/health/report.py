"""Arma `outputs/health/validation.md` a partir de un `HealthResult` ya materializado.

No abre conexion de DuckDB ni lee ningun archivo (decision D13, mismo
patron que `worky_engine.analysis.report`): el SQL que se inserta en el
apendice es el texto que `runner.run_health` ya leyo de cada archivo
`.sql`, y las tablas de metricas salen de los DataFrames que ya
calculo `worky_engine.health.metrics` sobre los scores ya materializados.

Doce secciones fijas, en el orden de la seccion 7 del diseno de A3
(encabezado, formula y pesos, AUC por senal, metricas a las tres tasas,
matriz de confusion, no detectables, deteccion temprana, sensibilidades,
capacidad por CSM, narrativa de A3.4, contexto comercial, referencias),
mas un apendice con el SQL de las seis vistas de `sql/health/` (brecha
del diseno: la seccion 7 no listaba un apendice de SQL, pero el patron
ya establecido en A1 y el requisito de auditar cada cifra piden que el
SQL este disponible junto al reporte, igual que `analysis/report.py`
hace por item en vez de al final). Cada cifra se etiqueta "en este
dataset"; el documento no lleva ninguna hora de reloj, la única marca
temporal es `dataset_asof`, que sale de los datos.
"""

from __future__ import annotations

import pandas as pd

from worky_engine.health import metrics as hm
from worky_engine.health.runner import HEALTH_FILES

ENGINE = "DuckDB 1.5.5"
HEALTH_COMMAND = "python -m worky_engine health --data-dir <ruta> --out-dir outputs/health"
CSM_COUNT = 7

# Etiqueta, peso en la formula (0.0 para las senales medidas sin peso)
# por columna de `auc_by_signal` (ADR-005, seccion 3 del diseno).
_SIGNAL_LABELS: tuple[tuple[str, str, float], ...] = (
    ("sig_momentum", "Momentum de uso (EWMA span 3 contra span 9)", 0.35),
    ("sig_mom", "Cambio mes a mes de active_users", 0.20),
    ("sig_drawdown", "Caída desde el mejor promedio de 3 meses", 0.15),
    ("sig_tenure", "Antigüedad al mes de corte", 0.30),
    ("tickets_window_total", "Tickets totales en la ventana de 3 meses", 0.0),
    ("tickets_window_urgent", "Tickets urgentes en la ventana de 3 meses", 0.0),
    ("csat_window_avg", "CSAT promedio en la ventana de 3 meses", 0.0),
    ("activation_score", "Activacion en los primeros 3 meses de uso", 0.0),
)

_BAND_ORDER = ("riesgo alto", "riesgo medio", "riesgo bajo", "sin historia")


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _sql_block(sql_text: str) -> str:
    return f"```sql\n{sql_text.rstrip()}\n```"


def _num(value: float | None, decimals: int = 3) -> str:
    """Formatea un número con `decimals` decimales fijos; 'sin dato' cuando es nulo o NaN."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "sin dato"
    return f"{value:.{decimals}f}"


def _percent(value: float | None, decimals: int = 1) -> str:
    """Formatea una razón 0 a 1 como porcentaje; 'sin dato' cuando es nula o NaN."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "sin dato"
    return f"{value * 100:.{decimals}f} %"


def _month_word(months: int) -> str:
    return "1 mes" if months == 1 else f"{months} meses"


def _churned_mask(scores: pd.DataFrame) -> pd.Series:
    return scores["churned"].astype(bool)


def _undetectable_breakdown(scores: pd.DataFrame) -> dict[int, int]:
    """Cuantas bajas 'sin historia' tienen 0, 1 o 2 meses de uso al corte, en ese orden (ADR-005, Adenda 1)."""
    mask = _churned_mask(scores) & (scores["risk_band"] == "sin historia")
    return scores.loc[mask, "usage_months_asof"].value_counts().sort_index().to_dict()


def _breakdown_text(breakdown: dict[int, int], suffix: str = "") -> str:
    """Texto de 'N con M meses' por cada meses de uso, o una nota explicita cuando no hay ninguna."""
    if not breakdown:
        return "ninguna baja cae en esa banda en este dataset"
    return ", ".join(f"{count} con {_month_word(int(months))}{suffix}" for months, count in breakdown.items())


def _header_section(result) -> str:
    scores = result.scores
    churned_total = int(_churned_mask(scores).sum())
    undetectable_total = hm.undetectable_count(scores)
    breakdown_text = _breakdown_text(_undetectable_breakdown(scores))
    active_book = hm.capacity_by_csm(scores)["flagged_15"]["active_book"]
    band_counts = scores["risk_band"].value_counts().to_dict()

    info_rows = [
        ["motor", ENGINE],
        ["dataset_asof", result.dataset_asof],
        ["ruleset_version", result.ruleset_version],
        ["comando", HEALTH_COMMAND],
        ["empresas evaluadas en este dataset", str(len(scores))],
        ["bajas en este dataset", str(churned_total)],
        [
            "no detectables (banda 'sin historia') en este dataset",
            f"{undetectable_total} de {churned_total} bajas ({breakdown_text})",
        ],
        ["libro activo con health_score definido en este dataset", str(active_book)],
    ]
    band_rows = [[band, str(band_counts.get(band, 0))] for band in _BAND_ORDER]
    return (
        "## Encabezado\n\n"
        + _md_table(["Campo", "Valor"], info_rows)
        + "\n\n**Conteo por banda en este dataset:**\n\n"
        + _md_table(["Banda", "Empresas"], band_rows)
        + "\n\n**Mes de referencia y mes de corte:** el mes de referencia es el mes de `churn_date` para una "
        "empresa dada de baja, o el cierre de los datos (`dataset_asof`) para una activa. El mes de corte es "
        "el mes de referencia menos dos meses, con el mismo desplazamiento para las dos poblaciónes en este "
        "dataset (ADR-003, ADR-005)."
    )


def _formula_section() -> str:
    rows = [
        ["Momentum de uso", "0.35", "EWMA de 3 meses contra EWMA de 9 meses, en el mes de corte"],
        ["Cambio mes a mes", "0.20", "active_users del último mes contra el mes anterior, en el mes de corte"],
        [
            "Caída desde el mejor promedio",
            "0.15",
            "promedio de los últimos 3 meses contra el mejor promedio movil de 3 meses",
        ],
        ["Antigüedad", "0.30", "meses desde signup_date hasta el mes de corte, recortado a cero"],
    ]
    return (
        "## Fórmula y pesos\n\n"
        "En voz alta: el `health_score` es 0.35 veces el momentum de uso, más 0.20 veces el cambio mes a "
        "mes, más 0.15 veces la caída desde el mejor promedio de tres meses, más 0.30 veces la antigüedad. "
        "Cada subpuntaje ya está normalizado de 0 a 100 por rango percentil dentro de la población evaluada, "
        "con 100 como el valor más sano (ADR-005).\n\n"
        + _md_table(["Subpuntaje", "Peso", "Definición"], rows)
        + "\n\nUna empresa con menos de tres meses de uso al mes de corte no recibe los tres subpuntajes de "
        "uso ni `health_score`: cae en la banda 'sin historia' y cuenta en el denominador del recall general "
        "como no detectable, aunque si recibe su subpuntaje de antigüedad (ADR-003, ADR-005).\n\n"
        "**Resguardo de fuga:** ninguna fila de uso fechada despues del mes de corte entra a ningún "
        "subpuntaje; los tickets se leen de una ventana de tres meses que termina en el mes de corte "
        "(`mart_support_asof`, distinta de `mart_support`), y los primeros tres meses de activacion solo "
        "cuentan si el tercero cae en el mes de corte o antes."
    )


def _auc_section(scores: pd.DataFrame) -> str:
    auc_values = hm.auc_by_signal(scores)
    rows = [[label, _num(auc_values.get(column, float("nan"))), f"{weight:.2f}"] for column, label, weight in _SIGNAL_LABELS]
    return (
        "## AUC por señal, en este dataset\n\n"
        "AUC es la probabilidad de que una empresa dada de baja muestre peor señal que una activa; 0.5 es "
        "una moneda al aire. Se mide a k = 2, el mes de corte principal.\n\n"
        + _md_table(["Señal", "AUC (k = 2, en este dataset)", "Peso en la fórmula"], rows)
        + "\n\nLas señales de soporte (tickets totales, urgentes y CSAT en la ventana de tres meses) y la "
        "activacion de los primeros tres meses se miden y se publican, pero pesan cero en la fórmula: en "
        "este dataset ninguna separa tan bien como las cuatro señales que si entran al score, y se muestran "
        "aquí para que nadie tenga que creer que no sirven en vez de verlo medido (ADR-005)."
    )


def _metrics_section(scores: pd.DataFrame) -> str:
    rate_table = hm.rate_metrics(scores)
    fixed = hm.fixed_cut_metrics(scores)
    auc_score = hm.auc_by_signal(scores, ["health_score"])["health_score"]
    rows = []
    for rate in hm.FLAG_RATES:
        column = f"flagged_{int(rate * 100)}"
        row = rate_table[column]
        rows.append(
            [
                f"{int(rate * 100)} %",
                str(row["flagged"]),
                _num(row["precision"]),
                _num(row["recall"]),
                _num(row["recall_detectable"]),
                _num(row["recall_mrr"]),
            ]
        )
    rows.append(
        [
            f"corte fijo (score < {int(fixed['threshold'])})",
            str(fixed["flagged"]),
            _num(fixed["precision"]),
            _num(fixed["recall"]),
            "no aplica",
            "no aplica",
        ]
    )
    return (
        "## Métricas de validación contra churn_date, en este dataset\n\n"
        f"AUC del `health_score` en este dataset: {_num(auc_score)}.\n\n"
        + _md_table(
            [
                "Tasa de marcado",
                "Marcadas",
                "Precisión",
                "Recall general",
                "Recall detectable",
                "Recall ponderado por MRR",
            ],
            rows,
        )
        + "\n\nEl 15 % es el umbral operativo: reparte el trabajo del libro activo entre los CSM. El corte "
        "fijo de referencia se reporta aparte, solo como dato adicional, sin sustituir al umbral operativo "
        "(ADR-005)."
    )


def _confusion_section(scores: pd.DataFrame) -> str:
    matrix = hm.confusion_matrix_15(scores)
    rows = [
        ["Verdaderos positivos", str(matrix["tp"])],
        ["Falsos positivos", str(matrix["fp"])],
        [
            "Falsos negativos",
            f"{matrix['fn']} (de los cuales {matrix['fn_undetectable']} son no detectables por falta de historia)",
        ],
        ["Verdaderos negativos", str(matrix["tn"])],
    ]
    return "## Matriz de confusión al 15 %, en este dataset\n\n" + _md_table(["Celda", "Empresas"], rows)


def _undetectable_section(scores: pd.DataFrame) -> str:
    churned_total = int(_churned_mask(scores).sum())
    total = hm.undetectable_count(scores)
    if churned_total == 0:
        # R3-undetectable-zero-division: sin bajas no hay denominador ni
        # porcentaje que reportar; el reporte lo dice en vez de tronar.
        return (
            "## Empresas no detectables, en este dataset\n\n"
            "Este dataset no tiene bajas, así que no hay empresas no detectables que contar ni un "
            "recall que calcular; la banda 'sin historia' sigue aplicando a las cuentas con menos de "
            "tres meses de uso al mes de corte."
        )
    breakdown_text = _breakdown_text(_undetectable_breakdown(scores), suffix=" de uso")
    return (
        "## Empresas no detectables, en este dataset\n\n"
        f"{total} de las {churned_total} bajas de este dataset ({_percent(total / churned_total)}) caen en "
        "la banda 'sin historia': tienen menos de tres meses de uso al mes de corte, así que nunca reciben "
        "`health_score` y nunca pueden marcarse, sin importar el peso de ningún subpuntaje. Cuentan en el "
        "denominador del recall general porque son bajas reales, aunque el modelo por diseño no pueda "
        f"verlas todavía (ADR-005, Adenda 1). Desglose por meses de uso al mes de corte: {breakdown_text}."
    )


def _early_detection_section(result) -> str:
    early = hm.early_detection_k3(result.scores, result.sensitivities["k3"])
    return (
        "## Detección temprana en k = 3, en este dataset\n\n"
        f"De las bajas marcadas al 15 % con el mes de corte principal (k = 2), {early['eligible']} tenian "
        f"suficiente historia de uso para tener `health_score` también en k = 3, y de esas, "
        f"{early['already_flagged']} ya estaban marcadas un mes antes ({_num(early['share'])} de las que se "
        "pudieron evaluar): se habrian detectado con un mes extra de anticipacion."
    )


def _sensitivity_section(result) -> str:
    k3 = hm.sensitivity_summary(result.sensitivities["k3"])
    literal = hm.sensitivity_summary(result.sensitivities["literal"])
    equal = hm.equal_weights_sensitivity(result.scores)
    harness = hm.harness_convention_sensitivity(result.scores)
    rows = [
        [
            "k = 3 (un mes de corte más atras)",
            _num(k3["auc"]),
            _num(k3["recall"]),
            "El AUC y el recall bajan frente a k = 2: con un mes menos de datos, menos empresas llegan a los "
            "tres meses de historia que exige el score de uso.",
        ],
        [
            "Lectura literal (activas en su mes más reciente)",
            _num(literal["auc"]),
            _num(literal["recall"]),
            "Compara recencia y no salud: las activas se evaluan con datos más frescos que las bajas, y por "
            "eso se reporta solo como sensibilidad, nunca como regla principal.",
        ],
        [
            "Pesos iguales (0.25 cada subpuntaje)",
            _num(equal["auc"]),
            _num(equal["recall"]),
            "El AUC y el recall casi no cambian frente a los pesos del ADR-005: las cuatro señales de uso ya "
            "separan bien por si solas, y el reparto exacto de pesos entre ellas importa menos que juntarlas.",
        ],
        [
            "Convencion del harness (percentil sobre la población completa)",
            _num(harness["auc"]),
            _num(harness["recall"]),
            "Usa el mismo `health_score`, pero el umbral sale del percentil de bajas y activas juntas en vez "
            "del libro activo: sirve para comparar contra measurements.md, no como regla operativa (D16).",
        ],
    ]
    return "## Sensibilidades, en este dataset\n\n" + _md_table(["Corrida", "AUC", "Recall al 20 %", "Qué cambia"], rows)


def _capacity_section(scores: pd.DataFrame) -> str:
    capacity = hm.capacity_by_csm(scores, csm_count=CSM_COUNT)
    rows = [
        [
            f"{int(rate * 100)} %",
            str(capacity[f"flagged_{int(rate * 100)}"]["active_book"]),
            str(capacity[f"flagged_{int(rate * 100)}"]["flagged"]),
            str(capacity[f"flagged_{int(rate * 100)}"]["per_csm"]),
        ]
        for rate in hm.FLAG_RATES
    ]
    return (
        f"## Capacidad por CSM, en este dataset ({CSM_COUNT} CSM)\n\n"
        + _md_table(["Tasa de marcado", "Libro activo con score", "Marcadas", "Marcadas por CSM"], rows)
    )


def _a3_4_section() -> str:
    return (
        "## Respuesta a A3.4: qué error cuesta más, en este dataset\n\n"
        "Un falso positivo (marcar una cuenta sana como riesgo) cuesta horas de un CSM revisando una cuenta "
        "que en realidad está bien: es un costo real, pero acotado y recuperable. Muchos falsos positivos "
        "significan un umbral demasiado estricto, precisión baja y horas de CSM gastadas en cuentas sanas.\n\n"
        "Un falso negativo (no marcar una cuenta que si se va) cuesta el MRR completo de esa cuenta cuando "
        "hace churn sin que nadie haya intervenido antes: el equipo pierde el ingreso y la oportunidad de "
        "retenerla. Muchos falsos negativos significan un umbral demasiado laxo y MRR perdido sin alerta "
        "previa.\n\n"
        "En este dataset, el error más caro para Worky es un falso negativo en una cuenta grande: perder una "
        "cuenta de MRR alto sin ninguna alerta previa cuesta más que las horas de varios CSM revisando "
        "cuentas sanas. Por eso el umbral operativo se sesga hacia recall aunque baje la precisión, y la "
        "métrica que mejor lo mide es el recall ponderado por MRR, no el recall simple: ahi una cuenta "
        "grande que se detecta pesa más que diez cuentas pequenas.\n\n"
        "**Hallazgo de onboarding, para la Parte B (ADR-005, Adenda 1):** casi una cuarta parte de las bajas "
        "de este dataset ocurre antes de que la cuenta acumule tres meses de uso, así que el health score, "
        "por diseño, todavía no las puede ver. Esto no se corrige con otro reparto de pesos: las cuentas en "
        "su primer trimestre necesitan su propia señal o su propio playbook de onboarding, aparte del health "
        "score, para que el riesgo de baja temprana no quede invisible hasta que ya sea tarde para actuar."
    )


def _rate_table(scores: pd.DataFrame, group_column: str) -> str:
    rows = []
    for value, group in scores.groupby(group_column):
        churn_rate = _churned_mask(group).mean()
        flag_rate = group["flagged_15"].astype(bool).mean()
        rows.append([str(value), str(len(group)), _percent(churn_rate), _percent(flag_rate)])
    rows.sort(key=lambda row: row[0])
    return _md_table([group_column, "n", "Tasa de baja", "Tasa de marcado al 15 %"], rows)


def _commercial_context_section(scores: pd.DataFrame) -> str:
    return (
        "## Contexto comercial, fuera del score, en este dataset\n\n"
        "`acquisition_channel` y `segment` se miden y se publican como factores de riesgo comerciales, pero "
        "no entran a la fórmula del `health_score`: en este dataset explican churn a nivel de portafolio, no "
        "a nivel de cuenta individual, así que se reportan aparte (ADR-005).\n\n"
        "**Por canal de adquisición:**\n\n"
        + _rate_table(scores, "acquisition_channel")
        + "\n\n**Por segmento:**\n\n"
        + _rate_table(scores, "segment")
    )


def _acceptance_section(scores: pd.DataFrame) -> str:
    """Resultado de la regla de aceptacion del ADR-005 (Adenda 1), con la salida de respaldo si falla.

    La regla se mide entre las bajas detectables al 20 % de marcado; si
    no se cumple, el reporte recomienda la mezcla medida (uso 70 %,
    antiguedad 15 %, activacion 15 %) y una adenda al ADR-005, que es
    la salida humana que fija la decision D18: la constante WEIGHTS no
    cambia sola en tiempo de corrida.
    """
    if int(_churned_mask(scores).sum()) == 0:
        # Sin bajas no hay clase positiva: ni AUC ni recall se pueden medir,
        # asi que la regla queda sin evaluar y el reporte lo dice.
        return (
            "## Regla de aceptación del ADR-005, en este dataset\n\n"
            "Este dataset no tiene bajas, así que la regla de aceptación (AUC de al menos 0.95 y recall de al "
            "menos 0.85 al 20 % entre las bajas detectables) no se puede medir y queda sin evaluar."
        )
    check = hm.acceptance_check(scores)
    verdict = "cumplida" if check["passed"] else "no cumplida"
    text = (
        "## Regla de aceptación del ADR-005, en este dataset\n\n"
        "Umbrales: AUC de al menos 0.95 y recall de al menos 0.85 al 20 % de marcado entre las bajas "
        "detectables (Adenda 1 del ADR-005). "
        f"Medido: AUC {_num(check['auc'])}, recall entre detectables {_num(check['recall_detectable_20'])}, "
        f"recall general {_num(check['recall_20'])} con {check['undetectable']} bajas no detectables. "
        f"Regla {verdict}."
    )
    if not check["passed"]:
        text += (
            " Como la regla no se cumple con los pesos del ADR-005, la recomendación es adoptar la mezcla "
            "medida (uso 70 %: momentum 0.35, cambio mes a mes 0.20, caída 0.15; antigüedad 15 %; activación "
            "15 %), cambiar la constante WEIGHTS a mano y dejar una adenda en el ADR-005 con ambos juegos de "
            "números; el comando no cambia los pesos por su cuenta."
        )
    return text


def _references_section() -> str:
    return (
        "## Referencias\n\n"
        "- ADR-003: ventana de tendencia de uso y resguardo de fuga "
        "(`docs/decisions/ADR-003-usage-trend-and-leakage-guard.md`).\n"
        "- ADR-004: definiciónes de las consultas de A1 "
        "(`docs/decisions/ADR-004-sql-analysis-definitions.md`).\n"
        "- ADR-005: el modelo del health score, sus pesos y la Adenda 1 sobre el techo del recall "
        "(`docs/decisions/ADR-005-health-score-model.md`)."
    )


def _sql_appendix_section(result) -> str:
    blocks = []
    for relative_path in HEALTH_FILES:
        file_name = relative_path.rsplit("/", maxsplit=1)[-1]
        blocks.append(f"### `{file_name}`\n\n" + _sql_block(result.sql_text[relative_path]))
    return "## Apéndice: SQL de las vistas de health, tal como está en cada archivo\n\n" + "\n\n".join(blocks)


def format_validation(result) -> str:
    """Arma el texto completo de `validation.md` a partir de un `HealthResult` ya materializado."""
    scores = result.scores
    sections = [
        "# Reporte de validación del health score de A3",
        _header_section(result),
        _formula_section(),
        _auc_section(scores),
        _metrics_section(scores),
        _acceptance_section(scores),
        _confusion_section(scores),
        _undetectable_section(scores),
        _early_detection_section(result),
        _sensitivity_section(result),
        _capacity_section(scores),
        _a3_4_section(),
        _commercial_context_section(scores),
        _references_section(),
        _sql_appendix_section(result),
    ]
    return "\n\n".join(sections) + "\n"
