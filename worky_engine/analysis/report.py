"""Arma `outputs/analysis/report.md` a partir de un `AnalysisResult` ya materializado.

No abre conexion ni lee ningun archivo (decision D13 del diseno): el
SQL que se inserta en cada seccion es el texto que `runner.run_analysis`
ya leyo, y las tablas de resultado salen de los DataFrames que ya
corrieron. Eso es lo que garantiza que el reporte describe exactamente
lo que escribio `analyze` en el mismo `--out-dir`, sin que las dos
piezas se desincronicen con el tiempo.

Una seccion por item de A1.1 a A1.6, en ese orden, cada una con cuatro
bloques (definicion del ADR-004, motor, SQL, resultado). A1.6 agrega la
justificacion de tres a cuatro lineas. A1.7 es una seccion narrativa sin
consulta, con DDL ilustrativo marcado como no ejecutable (D13). El
documento no lleva ninguna hora de reloj: la unica marca temporal es
`dataset_asof`, que sale de los datos.
"""

from __future__ import annotations

import pandas as pd

ENGINE = "DuckDB 1.5.5"
ANALYZE_COMMAND = "python -m worky_engine analyze --data-dir <ruta> --out-dir outputs/analysis"
HEAD_ROWS = 15


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _frame_to_rows(frame: pd.DataFrame) -> list[list[str]]:
    return [["" if pd.isna(value) else str(value) for value in row] for row in frame.itertuples(index=False)]


def _full_table(frame: pd.DataFrame) -> str:
    return _md_table(list(frame.columns), _frame_to_rows(frame))


def _head_and_total_table(frame: pd.DataFrame, csv_name: str) -> str:
    """Primeras `HEAD_ROWS` filas más una línea con el total, con el CSV que trae todo (D8, sección 4 del diseño)."""
    head = _full_table(frame.head(HEAD_ROWS))
    return f"{head}\n\nTotal: {len(frame)} filas. La tabla completa está en `{csv_name}`."


def _pivot_a1_03(cohort_retention: pd.DataFrame) -> str:
    """Pivotea A1.3 de formato largo a una fila por cohorte y una columna por k, con celdas censuradas vacias."""
    k_values = sorted(int(k) for k in cohort_retention["k"].unique())
    headers = ["cohort_month", "cohort_size"] + [f"k={k}" for k in k_values]
    rows = []
    for cohort_month, group in cohort_retention.sort_values("cohort_month").groupby("cohort_month", sort=False):
        by_k = group.set_index("k")
        row = [cohort_month, str(int(by_k["cohort_size"].iloc[0]))]
        for k in k_values:
            pct = by_k.loc[k, "retention_pct"]
            row.append("" if pd.isna(pct) else str(pct))
        rows.append(row)
    return _md_table(headers, rows)


def _header_section(result) -> str:
    counts = [
        [name, str(len(result.outputs[view]))]
        for view, name in (
            ("analysis_a1_01_active_mrr", "a1_01_active_mrr"),
            ("analysis_a1_02_usage_drop", "a1_02_usage_drop"),
            ("analysis_a1_03_cohort_retention", "a1_03_cohort_retention"),
            ("analysis_a1_04_attribution", "a1_04_attribution"),
            ("analysis_a1_05_orphan_deals", "a1_05_orphan_deals"),
            ("analysis_a1_06_negative_hours", "a1_06_negative_hours"),
            ("analysis_exceptions", "analysis_exceptions"),
        )
    ]
    info_rows = [
        ["motor", ENGINE],
        ["dataset_asof", result.dataset_asof],
        ["ruleset_version", result.ruleset_version],
        ["comando", ANALYZE_COMMAND],
    ]
    return (
        "## Encabezado\n\n"
        + _md_table(["Campo", "Valor"], info_rows)
        + "\n\n"
        + _md_table(["Salida", "Filas"], counts)
    )


def _sql_block(sql_text: str) -> str:
    return f"```sql\n{sql_text.rstrip()}\n```"


def _item_a1_01(result) -> str:
    active_mrr = result.outputs["analysis_a1_01_active_mrr"]
    unresolved = int(active_mrr.loc[active_mrr["row_type"] == "segment", "companies_unresolved"].sum())
    return (
        "## A1.1. MRR activo por segmento e industria\n\n"
        "**Definición (ADR-004):** tabla con una fila por segmento e industria de las empresas activas "
        "(`churn_date` nulo), con dos columnas de MRR: la que reporta el CRM y el total con los valores "
        "imputados del ADR-002, más una fila de totales. El MRR activo que se reporta es el total con "
        "imputados; el del CRM se muestra al lado.\n\n"
        f"**Motor:** {ENGINE}\n\n"
        "**SQL** (`a1_01_active_mrr.sql`):\n\n"
        + _sql_block(result.sql_text["analysis/a1_01_active_mrr.sql"])
        + "\n\n**Resultado** (`a1_01_active_mrr.csv`):\n\n"
        + _full_table(active_mrr)
        + f"\n\nEl total con imputados es el MRR activo. {unresolved} fila(s) de segmento quedan "
        "'unresolved' (aportan cero pesos y siguen contando en `companies_active`)."
    )


def _item_a1_02(result) -> str:
    usage_drop = result.outputs["analysis_a1_02_usage_drop"]
    overlap = int(usage_drop["windows_overlap"].sum())
    return (
        "## A1.2. Caída relativa de uso al churn\n\n"
        "**Definición (ADR-004):** para cada cuenta con churn y cuenta de producto, el promedio de "
        "`active_users` en los tres meses calendario anteriores al mes de baja (ese mes queda fuera) "
        "contra el promedio de los primeros tres meses con uso de la cuenta. La caída relativa es "
        "(inicial menos final) entre inicial, en orden descendente.\n\n"
        f"**Motor:** {ENGINE}\n\n"
        "**SQL** (`a1_02_usage_drop.sql`):\n\n"
        + _sql_block(result.sql_text["analysis/a1_02_usage_drop.sql"])
        + "\n\n**Resultado** (primeras filas, total en `a1_02_usage_drop.csv`):\n\n"
        + _head_and_total_table(usage_drop, "a1_02_usage_drop.csv")
        + f"\n\n{overlap} de {len(usage_drop)} cuentas traen `windows_overlap` en verdadero: tienen menos "
        "de seis meses de uso y sus dos ventanas pueden compartir algun mes."
    )


def _item_a1_03(result) -> str:
    cohort_retention = result.outputs["analysis_a1_03_cohort_retention"]
    censored = int((cohort_retention["cell_status"] == "censored").sum())
    return (
        "## A1.3. Retención por cohorte de alta\n\n"
        "**Definición (ADR-004):** cohorte por mes de `signup_date` de HubSpot. Una cuenta sigue activa "
        "en el mes k si no ha hecho churn k meses despues de su alta, para k en 1, 3, 6 y 12. Las celdas "
        "de cohortes que todavía no cumplen k meses al cierre de los datos quedan vacias, sin calcularse "
        "con dato parcial.\n\n"
        f"**Motor:** {ENGINE}\n\n"
        "**SQL** (`a1_03_cohort_retention.sql`):\n\n"
        + _sql_block(result.sql_text["analysis/a1_03_cohort_retention.sql"])
        + "\n\n**Resultado**, pivoteado a una fila por cohorte y una columna por k "
        "(`a1_03_cohort_retention.csv` trae el formato largo):\n\n"
        + _pivot_a1_03(cohort_retention)
        + f"\n\n{censored} de {len(cohort_retention)} celdas quedan censuradas: la cohorte todavía no "
        "cumple ese k al cierre de los datos, y una celda censurada no se calcula con dato parcial."
    )


def _item_a1_04(result) -> str:
    attribution = result.outputs["analysis_a1_04_attribution"]
    winners = attribution.loc[attribution["channel_rank"] == 1].set_index("model")
    first_winner = winners.loc["first_touch", "channel"]
    last_winner = winners.loc["last_touch", "channel"]
    changes = "cambia" if first_winner != last_winner else "no cambia"
    no_prior_touch_rows = attribution.loc[
        (attribution["model"] == "last_touch") & (attribution["channel"] == "no_prior_touch")
    ]
    no_prior_touch_size = int(no_prior_touch_rows["deals_attributed"].iloc[0]) if len(no_prior_touch_rows) else 0
    return (
        "## A1.4. Atribución por primer y último touch\n\n"
        "**Definición (ADR-004):** grano deal. Cada deal se atribuye a dos canales: el primer touch de su "
        "empresa y el último touch anterior a su fecha de creacion, con empate por `touch_id` igual que el "
        "motor. Convierte si su etapa es `closedwon`. La tasa por canal es deals ganados entre deals "
        "atribuidos, y se reportan ambos modelos lado a lado.\n\n"
        f"**Motor:** {ENGINE}\n\n"
        "**SQL** (`a1_04_attribution.sql`):\n\n"
        + _sql_block(result.sql_text["analysis/a1_04_attribution.sql"])
        + "\n\n**Resultado** (`a1_04_attribution.csv`):\n\n"
        + _full_table(attribution)
        + f"\n\nEl canal ganador (`channel_rank = 1`) es '{first_winner}' en el modelo de primer touch y "
        f"'{last_winner}' en el de último touch; el ganador {changes} entre modelos. En el modelo de "
        f"último touch, {no_prior_touch_size} deals caen en 'no_prior_touch': se crearon antes del "
        "primer touch registrado de su empresa, así que no tienen un último touch anterior que atribuirles."
    )


def _item_a1_05(result) -> str:
    orphan_deals = result.outputs["analysis_a1_05_orphan_deals"]
    total_amount = orphan_deals["amount"].astype(float).sum()
    return (
        "## A1.5. Deals sin empresa real\n\n"
        "**Definición (ADR-004):** consulta SQL equivalente a la cuarentena del motor: deals de "
        "`crm_hubspot.deals` cuyo `hubspot_id` no existe en ninguna empresa real.\n\n"
        f"**Motor:** {ENGINE}\n\n"
        "**SQL** (`a1_05_orphan_deals.sql`):\n\n"
        + _sql_block(result.sql_text["analysis/a1_05_orphan_deals.sql"])
        + "\n\n**Resultado** (`a1_05_orphan_deals.csv`):\n\n"
        + _full_table(orphan_deals)
        + f"\n\n{len(orphan_deals)} deals por {total_amount:.2f} en unidades mezcladas (mensual y anual "
        "sin distincion, adenda 1 del ADR-002): cada deal es el único de su id, así que no hay forma "
        "rigurosa de saber en que unidad viene su monto."
    )


def _item_a1_06(result) -> str:
    negative_hours = result.outputs["analysis_a1_06_negative_hours"]
    return (
        "## A1.6. Tickets con horas de resolución negativas\n\n"
        "**Definición (ADR-004):** los tickets con `resolution_hours` negativo se dejan en nulo para "
        "cualquier promedio de tiempo de resolución, se conservan en conteos y CSAT, y se registran en "
        "`analysis_exceptions.csv` con las mismas columnas de `exceptions_log.csv`, sin tocar ninguna "
        "salida existente de A0.\n\n"
        f"**Motor:** {ENGINE}\n\n"
        "**SQL** (`a1_06_negative_hours.sql`, incluye la vista de detalle y `analysis_exceptions`):\n\n"
        + _sql_block(result.sql_text["analysis/a1_06_negative_hours.sql"])
        + "\n\n**Resultado** (primeras filas, total en `a1_06_negative_hours.csv`):\n\n"
        + _head_and_total_table(negative_hours, "a1_06_negative_hours.csv")
        + "\n\n**Justificación:**\n\n> "
        + _a1_06_justification(negative_hours)
    )


def _a1_06_justification(negative_hours: pd.DataFrame) -> str:
    """Texto de tres a cuatro líneas con la hipótesis de inversión de signo y su evidencia medida."""
    total = len(negative_hours)
    still_open = int((negative_hours["status"].str.lower() == "open").sum())
    return (
        f"Los {total} tickets con `resolution_hours` negativo se dejan en nulo para cualquier promedio de "
        "tiempo de resolución, se conservan para conteos y CSAT, y quedan registrados en "
        "`analysis_exceptions.csv`. Sin el signo, la mayoría caen en el rango normal de los tickets "
        "positivos, lo que apunta a un error de captura con las fechas invertidas, pero "
        f"{still_open} de los {total} siguen abiertos con horas ya registradas, así que voltear el signo "
        "sería asumir algo que el dato no confirma. Nulo con rastro es la única opción que no inventa "
        "datos, y la corrección en origen queda para A6."
    )


def _item_a1_07() -> str:
    changes_rows = [
        ["Particionar el uso por mes y agrupar fisicamente por cuenta",
         "Una consulta de un rango de meses lee solo esas particiones"],
        ["Agregado mensual precalculado con la llave (account_id, month)",
         "La sábana consume el agregado y no el detalle diario"],
        ["Tabla de marca de agua por partición",
         "Permite refrescar solo las particiones cuyos datos cambiaron"],
        ["Ventana de reproceso acotada para datos que llegan tarde",
         "Un registro con fecha de hace dos meses vuelve a agregar solo esa partición"],
    ]
    ddl = """-- DDL ilustrativo, no se ejecuta en este repositorio.

-- 1. Detalle diario particionado por mes y ordenado por cuenta.
CREATE TABLE usage_daily (
    account_id   VARCHAR NOT NULL,
    usage_date   DATE    NOT NULL,
    month        VARCHAR(7) NOT NULL,   -- llave de particion
    active_users INTEGER NOT NULL,
    logins       INTEGER NOT NULL,
    ingested_at  TIMESTAMP NOT NULL
) PARTITIONED BY (month);

-- 2. Agregado mensual, que es lo que consume la sabana.
CREATE TABLE usage_monthly_rollup (
    account_id        VARCHAR    NOT NULL,
    month             VARCHAR(7) NOT NULL,
    active_users      INTEGER    NOT NULL,
    logins            INTEGER    NOT NULL,
    source_max_ingest TIMESTAMP  NOT NULL,
    PRIMARY KEY (account_id, month)
);

-- 3. Marca de agua por particion: que se cargo y hasta cuando.
CREATE TABLE refresh_state (
    table_name     VARCHAR    NOT NULL,
    month          VARCHAR(7) NOT NULL,
    last_ingest_at TIMESTAMP  NOT NULL,
    PRIMARY KEY (table_name, month)
);

-- 4. Refresco incremental: solo los meses con datos nuevos o corregidos.
MERGE INTO usage_monthly_rollup AS target
USING (
    SELECT account_id, month, SUM(active_users) AS active_users, SUM(logins) AS logins,
           MAX(ingested_at) AS source_max_ingest
    FROM usage_daily
    WHERE month IN (
        SELECT d.month
        FROM usage_daily d
        LEFT JOIN refresh_state r
            ON r.table_name = 'usage_monthly_rollup' AND r.month = d.month
        GROUP BY d.month, r.last_ingest_at
        HAVING r.last_ingest_at IS NULL OR MAX(d.ingested_at) > r.last_ingest_at
    )
    GROUP BY account_id, month
) AS source
ON target.account_id = source.account_id AND target.month = source.month
WHEN MATCHED THEN UPDATE SET
    active_users = source.active_users, logins = source.logins, source_max_ingest = source.source_max_ingest
WHEN NOT MATCHED THEN INSERT (account_id, month, active_users, logins, source_max_ingest)
    VALUES (source.account_id, source.month, source.active_users, source.logins, source.source_max_ingest);"""
    return (
        "## A1.7. Respuesta de diseño para escalar\n\n"
        "A1.7 pregunta que cambia en el modelo y en el pipeline si la tabla de uso mensual crece a "
        "cientos de millones de filas por dia, en vez de las pocas miles de este caso. No es una "
        "consulta contra el dataset: es una decision de arquitectura, con este DDL como ilustracion, no "
        "ejecutable en este repositorio.\n\n"
        + _md_table(["Cambio", "Que resuelve"], changes_rows)
        + "\n\n"
        + _sql_block(ddl)
        + "\n\nEl crosswalk de identidad (`identity_crosswalk`) y los marts siguen calculandose por "
        "encima del agregado mensual, no del detalle diario: cada refresco solo recalcula las cuentas "
        "cuyo mes cambio, y `dataset_asof` derivado de los datos, que este cambio ya usa, sigue siendo "
        "lo que audita hasta donde llego cada refresco."
    )


def _references_section() -> str:
    return (
        "## Referencias\n\n"
        "- ADR-002: imputación y normalización de MRR "
        "(`docs/decisions/ADR-002-mrr-imputation-and-normalization.md`).\n"
        "- ADR-003: ventana de tendencia de uso y resguardo de fuga "
        "(`docs/decisions/ADR-003-usage-trend-and-leakage-guard.md`).\n"
        "- ADR-004: definiciones de las consultas de A1 "
        "(`docs/decisions/ADR-004-sql-analysis-definitions.md`)."
    )


def format_report(result) -> str:
    """Arma el texto completo de `report.md` a partir de un `AnalysisResult` ya materializado."""
    sections = [
        "# Reporte de análisis de A1 sobre la sábana",
        _header_section(result),
        _item_a1_01(result),
        _item_a1_02(result),
        _item_a1_03(result),
        _item_a1_04(result),
        _item_a1_05(result),
        _item_a1_06(result),
        _item_a1_07(),
        _references_section(),
    ]
    return "\n\n".join(sections) + "\n"
