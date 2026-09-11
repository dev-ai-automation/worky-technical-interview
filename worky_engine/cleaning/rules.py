"""Reglas puras de deteccion y normalizacion de companies.csv, una funcion por regla (D1).

Cada funcion recibe el DataFrame completo de companies en texto crudo
y devuelve el mismo DataFrame con sus columnas corregidas mas la lista
de `Correction` que describe cada cambio, lista para convertirse en
una fila de `cleaning_exceptions.csv`. Cada regla corre sobre todas
las filas en cada corrida: no hay atajo por passthrough, asi que la
idempotencia depende de que cada regla sea convergente por
construccion (una fecha ISO se queda ISO, una moneda ya en MXN no
vuelve a corregirse). Ninguna funcion escribe a disco ni conoce la
imputacion del ADR-002: esa regla vive aparte en `impute.py` porque es
la unica que lee una segunda entrada (D6).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import pandas as pd

from worky_engine.normalization.currency import to_mxn
from worky_engine.normalization.dates import normalize_date
from worky_engine.writers import format_money

AUDIT_COLUMNS = ("mrr_mxn", "mrr_original", "currency_original", "mrr_source", "mrr_confidence")
DATE_COLUMNS = ("signup_date", "churn_date")

CLONE_ID_PATTERN = re.compile(r"^HS-9000\d{2}$")


def parse_finite_amount(text: str) -> float:
    """Convierte un monto en texto a float y rechaza lo que `float` acepta pero un monto no admite.

    `float("nan")`, `float("inf")` y `float("-inf")` no lanzan `ValueError`,
    asi que sin esta guardia esos textos entrarian como monto, dejarian
    `mrr_mxn` vacio al formatearse y reventarian un contrato en vez de
    reportarse como no numericos.
    """
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"monto no finito: {text!r}")
    return value
_DMY_PATTERN = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_SUPPORTED_CURRENCIES = frozenset({"MXN", "USD"})


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
    fuera de una excepcion (`assert_currency_all_mxn`). Un `mrr` que no
    es numerico (`mrr_not_numeric`) se detecta antes de intentar
    convertir: la fila conserva su texto original, `mrr_mxn` se queda
    vacio y nunca recibe el texto crudo. Una moneda fuera de
    `{USD, MXN}` (`currency_unsupported`) tampoco revienta la corrida:
    la fila conserva su moneda original y `mrr_mxn` se queda vacio, y
    esta excepcion se vuelve a emitir en cada corrida porque es un
    reporte, no una correccion (igual que `clone_excluded`).

    Una fila con `mrr_mxn` ya poblado (viene de una corrida anterior,
    D8) no se vuelve a convertir: recalcular perderia el monto y la
    moneda originales. `currency_original` no sirve como esa señal
    porque tambien se llena cuando `mrr` no es numerico (lo exige
    `assert_currency_all_mxn`); ese caso se revisa en cada corrida
    igual que `currency_unsupported`, porque tambien es un reporte.
    """
    result = companies.copy()
    if "currency_original" not in result.columns:
        result["currency_original"] = ""
    if "mrr_original" not in result.columns:
        result["mrr_original"] = ""
    if "mrr_mxn" not in result.columns:
        result["mrr_mxn"] = ""
    corrections: list[Correction] = []
    for index, row in result.iterrows():
        raw_amount = row["mrr"]
        raw_currency = row["currency"]
        hubspot_id = row["hubspot_id"]
        already_audited = row["currency_original"] != ""
        already_converted = row["mrr_mxn"] != ""

        if raw_currency not in _SUPPORTED_CURRENCIES:
            corrections.append(
                Correction(
                    exception_code="currency_unsupported",
                    source_system="crm_hubspot",
                    source_id=hubspot_id,
                    field_name="currency",
                    original_value=raw_currency,
                    applied_value="",
                    evidence_ref=raw_currency,
                )
            )
            if not already_audited:
                result.at[index, "currency_original"] = raw_currency
            continue

        if not already_audited:
            result.at[index, "currency_original"] = raw_currency

        if raw_amount == "":
            result.at[index, "currency"] = "MXN"
            continue

        if already_converted:
            # ya se convirtio en una corrida anterior: `mrr` es el monto en
            # MXN, no el original, asi que reprocesarlo perderia el rastro.
            continue

        try:
            amount = parse_finite_amount(raw_amount)
        except ValueError:
            corrections.append(
                Correction(
                    exception_code="mrr_not_numeric",
                    source_system="crm_hubspot",
                    source_id=hubspot_id,
                    field_name="mrr",
                    original_value=raw_amount,
                    applied_value="",
                    evidence_ref=raw_amount,
                )
            )
            result.at[index, "currency"] = "MXN"
            continue

        converted = to_mxn(amount, raw_currency)
        result.at[index, "mrr"] = format_money(converted.mxn)
        result.at[index, "mrr_original"] = format_money(converted.original_amount)
        result.at[index, "mrr_mxn"] = format_money(converted.mxn)
        result.at[index, "currency"] = "MXN"
        if raw_currency == "USD":
            corrections.append(
                Correction(
                    exception_code="currency_converted_to_mxn",
                    source_system="crm_hubspot",
                    source_id=hubspot_id,
                    field_name="mrr_mxn",
                    original_value=format_money(converted.original_amount),
                    applied_value=format_money(converted.mxn),
                    evidence_ref="USD@18.5",
                )
            )
    return result, corrections


def detect_missing_mrr(companies: pd.DataFrame) -> tuple[pd.DataFrame, list[Correction]]:
    """Separa clones, mrr sin resolver y empresas reales con `mrr` nulo (D6, parte de deteccion).

    Una fila con `mrr` presente y `mrr_mxn` presente (la conversion de
    `convert_currency` funciono) queda como `mrr_source = 'crm'`. Una
    fila con `mrr` presente pero `mrr_mxn` vacio ya trae su propia
    excepcion `mrr_not_numeric` o `currency_unsupported` de
    `convert_currency`, asi que aqui solo se marca `unresolved` sin
    duplicar la excepcion. Un clon con `mrr` vacio queda como
    `clone_excluded` y sale como excepcion en cada corrida, porque el
    ADR-001 lo manda en cuarentena y es un reporte, no una correccion.
    Una empresa real con `mrr` vacio queda como `unresolved`, lista
    para que `impute.py` la resuelva a continuacion (D6).

    Una fila que ya trae `mrr_source == 'imputed_from_deal'` de una
    corrida anterior (D8, "un mrr_source ya resuelto no produce
    correccion") se preserva tal cual, con su `mrr_confidence`
    original: en esa fila `mrr` ya no esta vacio, y sin esta guarda
    quedaria reclasificada como `crm`, perdiendo la procedencia de la
    imputacion en cada corrida siguiente. Si ese frame trae
    `mrr_source` pero no `mrr_confidence` (columna ausente), se usa el
    mismo `'none'` por omision en vez de leerla y reventar.
    """
    result = companies.copy()
    previous_source = companies["mrr_source"] if "mrr_source" in companies.columns else None
    previous_confidence = companies["mrr_confidence"] if "mrr_confidence" in companies.columns else None
    result["mrr_source"] = "crm"
    result["mrr_confidence"] = "none"
    corrections: list[Correction] = []
    for index, row in result.iterrows():
        hubspot_id = row["hubspot_id"]
        if previous_source is not None and previous_source.at[index] == "imputed_from_deal":
            result.at[index, "mrr_source"] = "imputed_from_deal"
            result.at[index, "mrr_confidence"] = (
                previous_confidence.at[index] if previous_confidence is not None else "none"
            )
            continue
        # `row.get` porque una llamada aislada a esta funcion (fuera de
        # `run_clean`) puede no traer todavia la columna `mrr_mxn` de
        # `convert_currency`; sin ella, el valor por omision repite
        # `row["mrr"]` y la condicion nunca dispara.
        if row["mrr"] != "" and row.get("mrr_mxn", row["mrr"]) == "":
            result.at[index, "mrr_source"] = "unresolved"
            continue
        if row["mrr"] != "":
            continue
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
