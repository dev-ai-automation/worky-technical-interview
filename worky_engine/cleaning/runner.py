"""Orquestador de la limpieza (D1): encadena fechas, moneda y deteccion de mrr nulo, en ese orden fijo.

La imputacion del ADR-002 se conecta en PR2, justo despues de
`detect_missing_mrr` (D6 del diseno). `run_clean` tambien arma la
bitacora completa (`counts`, listo para `cleaning_log.json` y
`cleaning_log.md`). No hay passthrough: las tres reglas corren sobre
todas las filas en cada corrida, y la idempotencia (D8) depende de que
cada regla sea convergente por construccion en vez de un atajo
estructural (una fecha ISO se queda ISO, una moneda ya en MXN no
vuelve a corregirse, un clon reporta `clone_excluded` en cada pasada
porque es un reporte y no una correccion).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pandas as pd

from worky_engine.cleaning.rules import AUDIT_COLUMNS, Correction, convert_currency, detect_missing_mrr, normalize_dates

CLEANING_SCHEMA = "worky.cleaning-log/v1"
RULESET_VERSION = "1.0.0"

ORIGINAL_COLUMNS = (
    "hubspot_id",
    "name",
    "domain",
    "segment",
    "industry",
    "mrr",
    "currency",
    "signup_date",
    "csm_owner",
    "plan",
    "state",
    "churn_date",
)
CLEAN_COLUMNS = ORIGINAL_COLUMNS + AUDIT_COLUMNS
EXCEPTIONS_COLUMNS = (
    "exception_id",
    "exception_code",
    "source_system",
    "source_id",
    "field_name",
    "original_value",
    "applied_value",
    "evidence_ref",
    "confidence",
    "ruleset_version",
)


@dataclass(frozen=True)
class CleanResult:
    """Las tres salidas de una corrida de `run_clean`, antes de escribirse a disco."""

    clean: pd.DataFrame
    exceptions: pd.DataFrame
    counts: dict


def _exception_id(code: str, source_system: str, source_id: str, field_name: str) -> str:
    """`sha256("<code>|<source_system>|<source_id>|<field_name>")` truncado a 12 hex (misma convencion de A0)."""
    digest = hashlib.sha256(f"{code}|{source_system}|{source_id}|{field_name}".encode("utf-8")).hexdigest()
    return digest[:12]


def _build_exceptions_frame(corrections: list[Correction]) -> pd.DataFrame:
    """Arma `cleaning_exceptions.csv`: diez columnas, orden determinista por codigo, id de origen y campo (D11)."""
    rows = [
        {
            "exception_id": _exception_id(c.exception_code, c.source_system, c.source_id, c.field_name),
            "exception_code": c.exception_code,
            "source_system": c.source_system,
            "source_id": c.source_id,
            "field_name": c.field_name,
            "original_value": c.original_value,
            "applied_value": c.applied_value,
            "evidence_ref": c.evidence_ref,
            "confidence": c.confidence,
            "ruleset_version": RULESET_VERSION,
        }
        for c in corrections
    ]
    frame = pd.DataFrame(rows, columns=EXCEPTIONS_COLUMNS)
    if frame.empty:
        return frame
    return frame.sort_values(["exception_code", "source_id", "field_name"]).reset_index(drop=True)


def _count(corrections: list[Correction], code: str) -> int:
    return sum(1 for c in corrections if c.exception_code == code)


def _build_counts(
    clean: pd.DataFrame,
    deals: pd.DataFrame,
    corrections: list[Correction],
    exceptions: pd.DataFrame,
    rows_in: int,
    companies_filename: str,
    deals_filename: str,
) -> dict:
    """Arma el diccionario que se escribe como `cleaning_log.json`, esquema `worky.cleaning-log/v1` (D10)."""
    date_normalized = _count(corrections, "date_normalized")
    date_ambiguous = sum(
        1 for c in corrections if c.exception_code == "date_normalized" and c.evidence_ref == "dd_mm_yyyy_ambiguous"
    )
    date_unresolved = _count(corrections, "date_unresolved")

    currency_corrected = _count(corrections, "currency_converted_to_mxn")
    currency_unresolved = _count(corrections, "currency_unsupported")

    mrr_excluded_clones = int((clean["mrr_source"] == "clone_excluded").sum())
    mrr_corrected = int((clean["mrr_source"] == "imputed_from_deal").sum())
    # `mrr_source == 'unresolved'` en este punto solo significa "todavia no se
    # intento imputar" (PR1 no conecta impute.py, D6): no es lo mismo que un
    # intento de imputacion que fallo, que es lo unico que cuenta para el
    # campo `unresolved` del log y para la excepcion `mrr_unresolved` (PR2).
    mrr_pending = int((clean["mrr_source"] == "unresolved").sum())
    mrr_unresolved = _count(corrections, "mrr_unresolved")
    mrr_not_numeric = _count(corrections, "mrr_not_numeric")
    mrr_detected = mrr_excluded_clones + mrr_corrected + mrr_pending
    mrr_annualized = _count(corrections, "mrr_deal_annualized")

    deals_in = len(deals)
    deals_matched = int(deals["hubspot_id"].isin(clean["hubspot_id"]).sum()) if deals_in else 0

    total_corrections = mrr_corrected + mrr_annualized + currency_corrected + date_normalized

    return {
        "schema": CLEANING_SCHEMA,
        "ruleset_version": RULESET_VERSION,
        "inputs": {
            "companies": companies_filename,
            "deals": deals_filename,
            "rows_in": rows_in,
            "deals_in": deals_in,
            "deals_matched": deals_matched,
        },
        "rules": [
            {
                "rule": "missing_mrr",
                "columns": ["mrr"],
                "detected": mrr_detected,
                "corrected": mrr_corrected,
                "excluded_clones": mrr_excluded_clones,
                "annualized_deals": mrr_annualized,
                "not_numeric": mrr_not_numeric,
                "ambiguous": 0,
                "unresolved": mrr_unresolved,
            },
            {
                "rule": "currency_to_mxn",
                "columns": ["mrr", "currency"],
                "detected": currency_corrected + currency_unresolved,
                "corrected": currency_corrected,
                "ambiguous": 0,
                "unresolved": currency_unresolved,
            },
            {
                "rule": "date_format",
                "columns": ["signup_date", "churn_date"],
                "detected": date_normalized + date_unresolved,
                "corrected": date_normalized,
                "ambiguous": date_ambiguous,
                "unresolved": date_unresolved,
            },
        ],
        "totals": {
            "rows_out": len(clean),
            "corrections": total_corrections,
            "exception_rows": len(exceptions),
        },
        "outputs": ["companies_clean.csv", "cleaning_exceptions.csv", "cleaning_log.json", "cleaning_log.md"],
    }


def run_clean(
    companies: pd.DataFrame,
    deals: pd.DataFrame,
    companies_filename: str = "crm_hubspot__companies.csv",
    deals_filename: str = "crm_hubspot__deals.csv",
) -> CleanResult:
    """Corre las tres reglas en orden fijo (fechas, moneda, mrr nulo) y arma las tres salidas.

    `deals` ya es un parametro obligatorio en este PR, aunque la
    imputacion del ADR-002 todavia no lo consuma: `deals_matched` en
    `cleaning_log.json` se calcula aqui por una simple pertenencia de
    `hubspot_id`, sin repetir la logica de `impute.py` que llega en
    PR2.
    """
    rows_in = len(companies)

    dated, date_corrections = normalize_dates(companies)
    converted, currency_corrections = convert_currency(dated)
    detected, mrr_corrections = detect_missing_mrr(converted)

    clean = detected[list(CLEAN_COLUMNS)].reset_index(drop=True)

    corrections = [*date_corrections, *currency_corrections, *mrr_corrections]
    exceptions = _build_exceptions_frame(corrections)
    counts = _build_counts(clean, deals, corrections, exceptions, rows_in, companies_filename, deals_filename)

    return CleanResult(clean=clean, exceptions=exceptions, counts=counts)


def format_cleaning_log(counts: dict) -> str:
    """Arma `cleaning_log.md`: el mismo contenido de `counts` en espanol, en una tabla por regla."""
    inputs = counts["inputs"]
    totals = counts["totals"]
    lines = [
        "# Bitacora de limpieza",
        "",
        f"Corrida sobre `{inputs['companies']}` y `{inputs['deals']}`: "
        f"{inputs['rows_in']} filas de entrada, {totals['rows_out']} filas de salida. "
        f"De los {inputs['deals_in']} deals leidos, {inputs['deals_matched']} apuntan a una empresa del dataset.",
        "",
        "| Regla | Columnas | Detectado | Corregido | Ambiguo | Sin resolver |",
        "|---|---|---|---|---|---|",
    ]
    for rule in counts["rules"]:
        columns = ", ".join(rule["columns"])
        lines.append(
            f"| {rule['rule']} | {columns} | {rule['detected']} | {rule['corrected']} | "
            f"{rule['ambiguous']} | {rule['unresolved']} |"
        )
    missing_mrr = next(rule for rule in counts["rules"] if rule["rule"] == "missing_mrr")
    lines.extend(
        [
            "",
            f"Clones excluidos de la imputacion (ADR-001): {missing_mrr['excluded_clones']}. "
            f"Deals anualizados (ADR-002, adenda 1): {missing_mrr['annualized_deals']}.",
            "",
            f"Total de correcciones: {totals['corrections']}. "
            f"Filas en `cleaning_exceptions.csv`: {totals['exception_rows']}.",
        ]
    )
    return "\n".join(lines) + "\n"
