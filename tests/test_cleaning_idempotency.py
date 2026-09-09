"""Idempotencia de `worky_engine.cleaning`, version parcial (sin imputacion, seccion 7 del diseno de A6).

Los dos primeros escenarios corren sobre la fixture minima de
`tests/test_cleaning_rules.py`, sin marca `dataset`. Los otros dos
corren sobre el dataset real y confirman que `clean` nunca toca los
veinte archivos ya versionados bajo `outputs/` (`git ls-files outputs/`
en este repositorio). La comparacion byte a byte de los cuatro archivos
de `outputs/clean/` sobre el dataset real, con la imputacion activa, se
completa en PR2 (task 2.7): este PR ya la corre sin imputacion.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from tests.test_cleaning_rules import fixture_companies, fixture_deals
from worky_engine.cleaning import run_clean
from worky_engine.cli import main as cli_main

REPO_ROOT = Path(__file__).resolve().parent.parent
TRACKED_OUTPUT_FILES = (
    "outputs/analysis/a1_01_active_mrr.csv",
    "outputs/analysis/a1_02_usage_drop.csv",
    "outputs/analysis/a1_03_cohort_retention.csv",
    "outputs/analysis/a1_04_attribution.csv",
    "outputs/analysis/a1_05_orphan_deals.csv",
    "outputs/analysis/a1_06_negative_hours.csv",
    "outputs/analysis/analysis_exceptions.csv",
    "outputs/analysis/report.md",
    "outputs/backtest_report.md",
    "outputs/coverage_report.md",
    "outputs/exceptions_log.csv",
    "outputs/health/health_scores.csv",
    "outputs/health/validation.md",
    "outputs/identity_crosswalk.csv",
    "outputs/master_dataset.csv",
    "outputs/match_audit.csv",
    "outputs/quarantine_companies.csv",
    "outputs/quarantine_deals.csv",
    "outputs/warehouse/dim_company.csv",
    "outputs/warehouse/map_source_identity.csv",
)


def _hash_tracked_outputs() -> dict[str, str]:
    return {
        name: hashlib.sha256((REPO_ROOT / name).read_bytes()).hexdigest()
        for name in TRACKED_OUTPUT_FILES
    }


# --- fixture minima, sin marca dataset ---------------------------------------


def test_orden_determinista() -> None:
    """Dos corridas seguidas sobre la misma fixture dejan cleaning_exceptions.csv en el mismo orden."""
    companies = fixture_companies()
    deals = fixture_deals()
    first = run_clean(companies, deals)
    second = run_clean(companies, deals)
    assert list(first.exceptions["exception_id"]) == list(second.exceptions["exception_id"])


def test_cero_correcciones_sobre_la_salida_propia() -> None:
    """Correr clean usando companies_clean.csv como entrada reporta cero correcciones en cada regla."""
    first = run_clean(fixture_companies(), fixture_deals())
    second = run_clean(first.clean, fixture_deals())
    assert second.counts["totals"]["corrections"] == 0
    for rule in second.counts["rules"]:
        assert rule["corrected"] == 0


def test_salidas_identicas_entre_corridas_fixture() -> None:
    """Dos corridas seguidas sobre la misma fixture producen companies_clean.csv identico byte a byte."""
    companies = fixture_companies()
    deals = fixture_deals()
    first = run_clean(companies, deals)
    second = run_clean(companies, deals)
    assert first.clean.to_csv(index=False) == second.clean.to_csv(index=False)
    assert first.exceptions.to_csv(index=False) == second.exceptions.to_csv(index=False)


# --- dataset real -------------------------------------------------------------


@pytest.mark.dataset
def test_salidas_identicas_entre_corridas_dataset(data_dir: Path, tmp_path: Path) -> None:
    """Dos corridas de clean sobre el dataset real producen companies_clean.csv identico byte a byte."""
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    exit_first = cli_main(["clean", "--data-dir", str(data_dir), "--out-dir", str(first_dir)])
    exit_second = cli_main(["clean", "--data-dir", str(data_dir), "--out-dir", str(second_dir)])
    assert exit_first == 0
    assert exit_second == 0

    for name in ("companies_clean.csv", "cleaning_exceptions.csv", "cleaning_log.json", "cleaning_log.md"):
        assert (first_dir / name).read_bytes() == (second_dir / name).read_bytes()

    companies = pd.read_csv(data_dir / "crm_hubspot__companies.csv", dtype=str, keep_default_na=False, encoding="utf-8")
    deals = pd.read_csv(data_dir / "crm_hubspot__deals.csv", dtype=str, keep_default_na=False, encoding="utf-8")
    clean_output = pd.read_csv(first_dir / "companies_clean.csv", dtype=str, keep_default_na=False, encoding="utf-8")
    third_pass = run_clean(clean_output, deals)
    assert third_pass.counts["totals"]["corrections"] == 0


@pytest.mark.dataset
def test_ningun_golden_previo_cambia(data_dir: Path, tmp_path: Path) -> None:
    """Correr clean sobre el dataset real no toca ningun archivo ya versionado bajo outputs/."""
    before = _hash_tracked_outputs()
    exit_code = cli_main(["clean", "--data-dir", str(data_dir), "--out-dir", str(tmp_path / "out")])
    assert exit_code == 0
    after = _hash_tracked_outputs()
    assert before == after
