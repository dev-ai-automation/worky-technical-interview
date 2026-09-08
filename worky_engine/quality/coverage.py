"""Genera `coverage_report.md`, las nueve secciones fijas de la seccion 2 del diseno.

Todos los numeros salen de las salidas ya materializadas: los conteos por
sistema y por nivel de `mart_coverage.sql`, que a su vez se recalculan
desde `match_audit` en cada build, y los conteos de MRR y excepciones
directamente de `master_dataset` y `exceptions_log`. Ningun porcentaje se
escribe a mano; el unico calculo que hace este modulo en Python es la
proporcion imputada de MRR, porque cruza `master_dataset` con su propia
suma y no vive en ningun mart.
"""

from __future__ import annotations

import pandas as pd

_PENDING_PR4_NOTE = (
    "Pendiente para el PR 4: esta seccion se completa cuando `mart_usage` "
    "y `mart_commercial` esten disponibles y agreguen sus columnas a "
    "`master_dataset` (tarea 4.5 de las tareas del cambio)."
)


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def generate_coverage_report(
    identity_outputs: dict[str, pd.DataFrame],
    assembly_outputs: dict[str, pd.DataFrame],
) -> str:
    """Arma el texto completo de `coverage_report.md` a partir de las salidas ya materializadas."""
    crosswalk = identity_outputs["identity_crosswalk"]
    match_audit = identity_outputs["match_audit"]
    quarantine_companies = identity_outputs["quarantine_companies"]
    quarantine_deals = identity_outputs["quarantine_deals"]
    master_dataset = assembly_outputs["master_dataset"]
    exceptions_log = assembly_outputs["exceptions_log"]

    dataset_asof = str(crosswalk["resolved_at"].max())
    ruleset_version = str(crosswalk["ruleset_version"].iloc[0])

    sections = [
        "# Reporte de cobertura del dataset maestro",
        _section_header(
            dataset_asof, ruleset_version, crosswalk, match_audit,
            quarantine_companies, quarantine_deals, exceptions_log, master_dataset,
        ),
        _section_by_system(assembly_outputs["coverage_by_system"]),
        _section_by_tier(assembly_outputs["coverage_by_tier"]),
        _section_manual_queue(assembly_outputs["coverage_manual_queue"]),
        _section_mrr(master_dataset),
        _section_quarantine(assembly_outputs["coverage_quarantine"]),
        "## 7. Tendencia de uso\n\n" + _PENDING_PR4_NOTE,
        _section_exceptions(exceptions_log),
        "## 9. Canal de adquisicion\n\n" + _PENDING_PR4_NOTE,
    ]
    return "\n\n".join(sections) + "\n"


def _section_header(
    dataset_asof: str, ruleset_version: str, crosswalk: pd.DataFrame, match_audit: pd.DataFrame,
    quarantine_companies: pd.DataFrame, quarantine_deals: pd.DataFrame,
    exceptions_log: pd.DataFrame, master_dataset: pd.DataFrame,
) -> str:
    rows = [
        ["dataset_asof", dataset_asof],
        ["ruleset_version", ruleset_version],
        ["identity_crosswalk", str(len(crosswalk))],
        ["match_audit", str(len(match_audit))],
        ["quarantine_companies", str(len(quarantine_companies))],
        ["quarantine_deals", str(len(quarantine_deals))],
        ["exceptions_log", str(len(exceptions_log))],
        ["master_dataset", str(len(master_dataset))],
    ]
    return "## 1. Encabezado\n\n" + _md_table(["Campo", "Valor"], rows)


def _section_by_system(by_system: pd.DataFrame) -> str:
    rows = [
        [row["source_system"], str(int(row["total_rows"])), str(int(row["resolved_rows"])), f"{row['coverage_pct']:.2f}%"]
        for _, row in by_system.iterrows()
    ]
    return "## 2. Cobertura por sistema\n\n" + _md_table(
        ["Sistema", "Filas totales", "Filas resueltas", "Cobertura"], rows
    )


def _section_by_tier(by_tier: pd.DataFrame) -> str:
    rows = [
        [row["tier"], str(int(row["row_count"])), f"{row['coverage_pct']:.2f}%"]
        for _, row in by_tier.iterrows()
    ]
    return "## 3. Cobertura por nivel de confianza\n\n" + _md_table(["Nivel", "Filas", "Porcentaje"], rows)


def _section_manual_queue(manual_queue: pd.DataFrame) -> str:
    size = int(manual_queue["manual_queue_size"].iloc[0])
    return f"## 4. Cola de revision manual\n\n{size} registros en el nivel M, la respuesta directa a A0.3."


def _section_mrr(master_dataset: pd.DataFrame) -> str:
    mrr = master_dataset[["mrr_source", "mrr_confidence", "mrr_mxn"]].copy()
    mrr["mrr_mxn"] = pd.to_numeric(mrr["mrr_mxn"], errors="coerce").fillna(0.0)
    total_crm = mrr.loc[mrr["mrr_source"] == "crm", "mrr_mxn"].sum()
    total_with_imputed = mrr.loc[mrr["mrr_source"].isin(["crm", "imputed_from_deal"]), "mrr_mxn"].sum()
    imputed_amount = total_with_imputed - total_crm
    ratio = (imputed_amount / total_with_imputed) if total_with_imputed else 0.0

    imputed = mrr[mrr["mrr_source"] == "imputed_from_deal"]
    confidence_counts = imputed["mrr_confidence"].value_counts()
    totals_rows = [
        ["MRR reportado del CRM (mensual, MXN)", f"{total_crm:.2f}"],
        ["MRR total incluyendo imputados (mensual, MXN)", f"{total_with_imputed:.2f}"],
        ["Proporcion imputada", f"{ratio * 100:.2f}%"],
    ]
    confidence_rows = [
        [confidence, str(int(confidence_counts.get(confidence, 0)))] for confidence in ("high", "medium")
    ]
    return (
        "## 5. MRR\n\n"
        + _md_table(["Metrica", "Valor"], totals_rows)
        + "\n\n"
        + _md_table(["mrr_confidence (filas imputadas)", "Filas"], confidence_rows)
    )


def _section_quarantine(quarantine: pd.DataFrame) -> str:
    row = quarantine.iloc[0]
    rows = [
        ["Empresas clon (quarantine_companies)", str(int(row["quarantine_companies_count"]))],
        ["Deals huerfanos (quarantine_deals)", str(int(row["quarantine_deals_count"]))],
        ["Monto excluido, unidades mezcladas (MXN/USD, mensual/anual)", f"{row['quarantine_deals_amount_raw']:.2f}"],
        ["Monto excluido, normalizado a mensual con la regla 12x", f"{row['quarantine_deals_amount_normalized']:.2f}"],
    ]
    return "## 6. Cuarentena\n\n" + _md_table(["Concepto", "Valor"], rows)


def _section_exceptions(exceptions_log: pd.DataFrame) -> str:
    counts = exceptions_log["exception_code"].value_counts()
    rows = [[code, str(int(count))] for code, count in counts.items()]
    return "## 8. Excepciones\n\n" + _md_table(["exception_code", "Filas"], rows)
