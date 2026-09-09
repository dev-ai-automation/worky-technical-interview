"""Reglas puras de deteccion y normalizacion de companies.csv, una funcion por regla (D1).

Cada funcion recibe el DataFrame de companies en texto crudo (las
filas que `runner._passthrough_if_clean` dejo pasar a proceso) y
devuelve el mismo DataFrame con sus columnas corregidas mas la lista
de `Correction` que describe cada cambio, lista para convertirse en
una fila de `cleaning_exceptions.csv`. Ninguna funcion escribe a disco
ni conoce la imputacion del ADR-002: esa regla vive aparte en
`impute.py` porque es la unica que lee una segunda entrada (D6).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from worky_engine.normalization.currency import to_mxn
from worky_engine.normalization.dates import normalize_date
from worky_engine.writers import format_money

AUDIT_COLUMNS = ("mrr_mxn", "mrr_original", "currency_original", "mrr_source", "mrr_confidence")
DATE_COLUMNS = ("signup_date", "churn_date")

CLONE_ID_PATTERN = re.compile(r"^HS-9000\d{2}$")
_DMY_PATTERN = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


@dataclass(frozen=True)
class Correction:
    """Una fila de `cleaning_exceptions.csv` en construccion, antes de calcular su `exception_id`."""

    exception_code: str
    source_system: str
    source_id: str
    field_name: str
    original_value: str
    applied_value: str
    evidence_ref: str
    confidence: str = ""


def normalize_dates(companies: pd.DataFrame) -> tuple[pd.DataFrame, list[Correction]]:
    """Normaliza `signup_date` y `churn_date` a ISO; reporta cada DD/MM/YYYY corregido (D4).

    Una celda vacia se queda vacia y no cuenta. Una fecha DD/MM/YYYY
    valida se normaliza y cuenta como correccion; si el dia es menor o
    igual a 12 cuenta ademas como ambigua (`dd_mm_yyyy_ambiguous`). Una
    fecha invalida o de formato desconocido conserva su valor original
    en la celda y sale como excepcion `date_unresolved`, sin abortar la
    corrida.
    """
    result = companies.copy()
    corrections: list[Correction] = []
    for column in DATE_COLUMNS:
        for index, raw in result[column].items():
            if raw == "":
                continue
            normalized = normalize_date(raw)
            if normalized is None:
                corrections.append(
                    Correction(
                        exception_code="date_unresolved",
                        source_system="crm_hubspot",
                        source_id=result.at[index, "hubspot_id"],
                        field_name=column,
                        original_value=raw,
                        applied_value="",
                        evidence_ref="formato desconocido",
                    )
                )
                continue
            dmy_match = _DMY_PATTERN.match(raw)
            if dmy_match is None:
                # ya estaba en ISO: normalize_date la deja igual, no es correccion
                continue
            day = int(dmy_match.group(1))
            evidence = "dd_mm_yyyy_ambiguous" if day <= 12 else "dd_mm_yyyy"
            corrections.append(
                Correction(
                    exception_code="date_normalized",
                    source_system="crm_hubspot",
                    source_id=result.at[index, "hubspot_id"],
                    field_name=column,
                    original_value=raw,
                    applied_value=normalized,
                    evidence_ref=evidence,
                )
            )
            result.at[index, column] = normalized
    return result, corrections


def convert_currency(companies: pd.DataFrame) -> tuple[pd.DataFrame, list[Correction]]:
    """Convierte `mrr` a MXN con `to_mxn`; conserva el monto y la moneda originales (D5, D9).

    Una celda de `mrr` vacia no se convierte: solo se fuerza `currency`
    a `MXN`, porque el dominio final de la columna no admite otro valor
    (`assert_currency_all_mxn`). Una moneda fuera de `{USD, MXN}` no
    revienta la corrida: la fila queda intacta y sale como excepcion
    `currency_unsupported`.
    """
    result = companies.copy()
    result["mrr_original"] = ""
    result["currency_original"] = result["currency"]
    corrections: list[Correction] = []
    for index, row in result.iterrows():
        raw_amount = row["mrr"]
        raw_currency = row["currency"]
        if raw_amount == "":
            result.at[index, "currency"] = "MXN"
            continue
        try:
            converted = to_mxn(float(raw_amount), raw_currency)
        except ValueError:
            corrections.append(
                Correction(
                    exception_code="currency_unsupported",
                    source_system="crm_hubspot",
                    source_id=row["hubspot_id"],
                    field_name="currency",
                    original_value=raw_currency,
                    applied_value="",
                    evidence_ref=raw_currency,
                )
            )
            continue
        result.at[index, "mrr"] = format_money(converted.mxn)
        result.at[index, "mrr_original"] = format_money(converted.original_amount)
        result.at[index, "currency"] = "MXN"
        if raw_currency == "USD":
            corrections.append(
                Correction(
                    exception_code="currency_converted_to_mxn",
                    source_system="crm_hubspot",
                    source_id=row["hubspot_id"],
                    field_name="mrr_mxn",
                    original_value=format_money(converted.original_amount),
                    applied_value=format_money(converted.mxn),
                    evidence_ref="USD@18.5",
                )
            )
    return result, corrections


def detect_missing_mrr(companies: pd.DataFrame) -> tuple[pd.DataFrame, list[Correction]]:
    """Separa las filas clon `HS-9000xx` de las empresas reales con `mrr` nulo (D6, parte de deteccion).

    Una fila con `mrr` presente queda como `mrr_source = 'crm'`. Un
    clon queda como `clone_excluded` y sale como excepcion, porque el
    ADR-001 lo manda en cuarentena. Una empresa real con `mrr` nulo
    queda como `unresolved`: la imputacion del ADR-002 que puede
    resolverla se conecta en PR2, asi que este PR todavia no intenta
    resolverla y por lo tanto no emite su excepcion `mrr_unresolved`
    (esa solo tiene sentido despues de intentar la imputacion).
    """
    result = companies.copy()
    result["mrr_source"] = "crm"
    result["mrr_confidence"] = "none"
    corrections: list[Correction] = []
    for index, row in result.iterrows():
        if row["mrr"] != "":
            continue
        hubspot_id = row["hubspot_id"]
        if CLONE_ID_PATTERN.match(hubspot_id):
            result.at[index, "mrr_source"] = "clone_excluded"
            corrections.append(
                Correction(
                    exception_code="clone_excluded",
                    source_system="crm_hubspot",
                    source_id=hubspot_id,
                    field_name="mrr_mxn",
                    original_value="",
                    applied_value="",
                    evidence_ref="ADR-001 HS-9000xx",
                )
            )
        else:
            result.at[index, "mrr_source"] = "unresolved"
    return result, corrections
