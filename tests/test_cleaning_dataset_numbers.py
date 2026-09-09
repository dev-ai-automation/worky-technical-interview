"""Pruebas de conteo exacto de `worky_engine.cleaning` sobre el dataset real (marca `dataset`).

Cubre los ocho conteos de la seccion 9 del diseno de
`a6-cleaning-script` sobre las 678 filas reales: 56 mrr nulo (28
clones, 28 imputados), 22 USD, 31 fechas normalizadas (12 ambiguas), 3
deals anualizados y las 112 filas totales de `cleaning_exceptions.csv`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from worky_engine.cleaning import run_clean

pytestmark = pytest.mark.dataset


def _read_real_csv(data_dir: Path, filename: str) -> pd.DataFrame:
    return pd.read_csv(data_dir / filename, dtype=str, keep_default_na=False, encoding="utf-8")


@pytest.fixture(scope="module")
def clean_result(data_dir: Path):
    companies = _read_real_csv(data_dir, "crm_hubspot__companies.csv")
    deals = _read_real_csv(data_dir, "crm_hubspot__deals.csv")
    return run_clean(companies, deals)


def test_conteo_exacto_sobre_el_dataset(clean_result) -> None:
    """56 filas con mrr nulo, de las cuales 28 son clones HS-9000xx y 28 quedan imputadas desde sus deals."""
    clean = clean_result.clean
    assert int((clean["mrr_source"] == "clone_excluded").sum()) == 28
    assert int((clean["mrr_source"] == "imputed_from_deal").sum()) == 28
    assert int((clean["mrr_source"] == "unresolved").sum()) == 0
    missing_mrr_rule = next(rule for rule in clean_result.counts["rules"] if rule["rule"] == "missing_mrr")
    assert missing_mrr_rule["detected"] == 56
    assert missing_mrr_rule["excluded_clones"] == 28
    assert missing_mrr_rule["corrected"] == 28


def test_conteo_exacto_de_usd(clean_result) -> None:
    """Exactamente 22 filas en USD sobre las 678 filas del dataset."""
    currency_rule = next(rule for rule in clean_result.counts["rules"] if rule["rule"] == "currency_to_mxn")
    assert currency_rule["detected"] == 22
    assert currency_rule["corrected"] == 22


def test_conteo_y_normalizacion_de_signup_date(clean_result) -> None:
    """31 fechas DD/MM/YYYY normalizadas a ISO, de las cuales 12 quedan marcadas como ambiguas."""
    date_rule = next(rule for rule in clean_result.counts["rules"] if rule["rule"] == "date_format")
    assert date_rule["corrected"] == 31
    assert date_rule["ambiguous"] == 12


def test_churn_date_sin_mezcla_de_formatos(clean_result) -> None:
    """churn_date no trae fechas mezcladas: la corrida de fechas no reporta correcciones sobre esa columna."""
    churn_corrections = clean_result.exceptions[
        (clean_result.exceptions["exception_code"] == "date_normalized")
        & (clean_result.exceptions["field_name"] == "churn_date")
    ]
    assert len(churn_corrections) == 0


def test_conteos_exactos_en_json_y_en_md(clean_result) -> None:
    """cleaning_log.json trae los conteos exactos 56, 28, 22, 31, 12 y 3 deals anualizados, con 112 filas de bitacora."""
    from worky_engine.cleaning import format_cleaning_log

    counts = clean_result.counts
    missing_mrr_rule = next(rule for rule in counts["rules"] if rule["rule"] == "missing_mrr")
    currency_rule = next(rule for rule in counts["rules"] if rule["rule"] == "currency_to_mxn")
    date_rule = next(rule for rule in counts["rules"] if rule["rule"] == "date_format")

    assert missing_mrr_rule["detected"] == 56
    assert missing_mrr_rule["excluded_clones"] == 28
    assert missing_mrr_rule["corrected"] == 28
    assert missing_mrr_rule["annualized_deals"] == 3
    assert missing_mrr_rule["unresolved"] == 0
    assert currency_rule["detected"] == 22
    assert date_rule["corrected"] == 31
    assert date_rule["ambiguous"] == 12
    assert counts["totals"]["exception_rows"] == 112

    markdown = format_cleaning_log(counts)
    assert "56" in markdown
    assert "28" in markdown
    assert "22" in markdown
    assert "31" in markdown
    assert "12" in markdown
    assert "3" in markdown
