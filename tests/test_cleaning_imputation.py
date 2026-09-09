"""Pruebas de la imputacion del ADR-002 (`worky_engine.cleaning.impute`), fixture minima propia.

Reutiliza `COMPANIES_COLUMNS`, `DEALS_COLUMNS` y el helper `_company`
de `tests/test_cleaning_rules.py` (misma fixture minima, seccion 7 del
diseno de A6) y corre `run_clean` de punta a punta: la imputacion se
conecta despues de `detect_missing_mrr` en el orden fijo del runner
(D6), asi que probarla end-to-end tambien cubre la interaccion con la
deteccion de mrr nulo sin duplicar fixtures.
"""

from __future__ import annotations

import pandas as pd

from tests.test_cleaning_rules import COMPANIES_COLUMNS, DEALS_COLUMNS, _company
from worky_engine.cleaning import run_clean
from worky_engine.cleaning.impute import impute_mrr_from_deals


def _deal(deal_id: str, hubspot_id: str, stage: str, amount: str) -> dict:
    return {
        "deal_id": deal_id,
        "hubspot_id": hubspot_id,
        "stage": stage,
        "amount": amount,
        "created_date": "2023-01-01",
        "close_date": "",
        "owner": "Sales_Ana",
        "pipeline": "New Business",
        "lead_source": "Organic",
    }


def test_imputacion_confianza_alta() -> None:
    """Un unico monto entre los deals de la empresa, con un deal closedwon, imputa con mrr_confidence en high."""
    companies = pd.DataFrame([_company("HS-200001", mrr="")], columns=COMPANIES_COLUMNS)
    deals = pd.DataFrame([_deal("D90001", "HS-200001", "closedwon", "4000")], columns=DEALS_COLUMNS)

    result = run_clean(companies, deals)

    row = result.clean.iloc[0]
    assert row["mrr_mxn"] == "4000.00"
    assert row["mrr_source"] == "imputed_from_deal"
    assert row["mrr_confidence"] == "high"
    exception = result.exceptions[result.exceptions["source_id"] == "HS-200001"].iloc[0]
    assert exception["exception_code"] == "mrr_imputed_from_deal"
    assert exception["evidence_ref"] == "D90001"
    assert exception["confidence"] == "high"


def test_imputacion_confianza_media() -> None:
    """El mismo caso sin ningun deal closedwon imputa con mrr_confidence en medium."""
    companies = pd.DataFrame([_company("HS-200002", mrr="")], columns=COMPANIES_COLUMNS)
    deals = pd.DataFrame([_deal("D90002", "HS-200002", "qualifiedtobuy", "4000")], columns=DEALS_COLUMNS)

    result = run_clean(companies, deals)

    row = result.clean.iloc[0]
    assert row["mrr_source"] == "imputed_from_deal"
    assert row["mrr_confidence"] == "medium"


def test_empresa_sin_resolucion_por_montos_ambiguos() -> None:
    """Dos montos distintos que no son multiplos de 12 dejan la empresa sin imputar."""
    companies = pd.DataFrame([_company("HS-200003", mrr="")], columns=COMPANIES_COLUMNS)
    deals = pd.DataFrame(
        [
            _deal("D90003", "HS-200003", "qualifiedtobuy", "4000"),
            _deal("D90004", "HS-200003", "qualifiedtobuy", "7000"),
        ],
        columns=DEALS_COLUMNS,
    )

    result = run_clean(companies, deals)

    row = result.clean.iloc[0]
    assert row["mrr_mxn"] == ""
    assert row["mrr_source"] == "unresolved"
    exception = result.exceptions[result.exceptions["source_id"] == "HS-200003"].iloc[0]
    assert exception["exception_code"] == "mrr_unresolved"
    assert exception["evidence_ref"] == "montos ambiguos"


def test_empresa_sin_resolucion_sin_deals() -> None:
    """Una empresa real con mrr nulo y sin ningun deal queda sin imputar y se reporta como unresolved."""
    companies = pd.DataFrame([_company("HS-200004", mrr="")], columns=COMPANIES_COLUMNS)
    deals = pd.DataFrame([], columns=DEALS_COLUMNS)

    result = run_clean(companies, deals)

    row = result.clean.iloc[0]
    assert row["mrr_source"] == "unresolved"
    exception = result.exceptions[result.exceptions["source_id"] == "HS-200004"].iloc[0]
    assert exception["exception_code"] == "mrr_unresolved"
    assert exception["evidence_ref"] == "sin deals"


def test_anualizacion_contada_como_correccion_propia() -> None:
    """Un monto que es 12 veces otro de la misma empresa se anualiza y produce su propia correccion."""
    companies = pd.DataFrame([_company("HS-200005", mrr="")], columns=COMPANIES_COLUMNS)
    deals = pd.DataFrame(
        [
            _deal("D90005", "HS-200005", "qualifiedtobuy", "1000"),
            _deal("D90006", "HS-200005", "qualifiedtobuy", "12000"),
        ],
        columns=DEALS_COLUMNS,
    )

    result = run_clean(companies, deals)

    row = result.clean.iloc[0]
    assert row["mrr_mxn"] == "1000.00"
    assert row["mrr_source"] == "imputed_from_deal"

    imputed = result.exceptions[
        (result.exceptions["source_id"] == "HS-200005")
        & (result.exceptions["exception_code"] == "mrr_imputed_from_deal")
    ].iloc[0]
    assert imputed["evidence_ref"] == "D90005"

    annualized = result.exceptions[result.exceptions["exception_code"] == "mrr_deal_annualized"]
    assert list(annualized["source_id"]) == ["D90006"]
    assert annualized.iloc[0]["evidence_ref"] == "HS-200005"


def test_clon_no_se_toca_por_impute() -> None:
    """`impute_mrr_from_deals` nunca procesa una fila `clone_excluded`, incluso si un deal apunta a ese hubspot_id."""
    companies = pd.DataFrame(
        [
            {
                "hubspot_id": "HS-900001",
                "mrr": "",
                "currency_original": "MXN",
                "mrr_source": "clone_excluded",
                "mrr_confidence": "none",
                "mrr_mxn": "",
            }
        ]
    )
    deals = pd.DataFrame([_deal("D90007", "HS-900001", "closedwon", "9999")], columns=DEALS_COLUMNS)

    result, corrections = impute_mrr_from_deals(companies, deals)

    assert result.at[0, "mrr_source"] == "clone_excluded"
    assert result.at[0, "mrr_mxn"] == ""
    assert corrections == []
