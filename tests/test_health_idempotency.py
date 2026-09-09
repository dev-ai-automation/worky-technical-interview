"""Idempotencia byte a byte de `health_scores.csv` y `validation.md`, marca `dataset`.

Corre `python -m worky_engine health` dos veces en carpetas temporales
distintas y compara las dos salidas entre si y contra la copia
commiteada en `outputs/health/`, y verifica que el hash de los ocho
archivos de `outputs/` (A0) y de los ocho de `outputs/analysis/` (A1),
incluido `backtest_report.md`, es el mismo antes y despues de correr
`health` (requirement "comando health sin build previo", escenario
"goldens de A0 y A1 sin cambio").
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from worky_engine.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = REPO_ROOT / "outputs" / "health"
A0_OUTPUTS_DIR = REPO_ROOT / "outputs"
A1_OUTPUTS_DIR = REPO_ROOT / "outputs" / "analysis"
A0_OUTPUT_NAMES = (
    "identity_crosswalk.csv",
    "match_audit.csv",
    "quarantine_companies.csv",
    "quarantine_deals.csv",
    "master_dataset.csv",
    "exceptions_log.csv",
    "coverage_report.md",
    "backtest_report.md",
)
A1_OUTPUT_NAMES = (
    "a1_01_active_mrr.csv",
    "a1_02_usage_drop.csv",
    "a1_03_cohort_retention.csv",
    "a1_04_attribution.csv",
    "a1_05_orphan_deals.csv",
    "a1_06_negative_hours.csv",
    "analysis_exceptions.csv",
    "report.md",
)


def _run_health(data_dir: Path, out_dir: Path, db_path: Path) -> None:
    exit_code = main(["health", "--data-dir", str(data_dir), "--out-dir", str(out_dir), "--db-path", str(db_path)])
    assert exit_code == 0


def _hash_files(directory: Path, names: tuple[str, ...]) -> dict[str, str]:
    return {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in names}


@pytest.mark.dataset
def test_dos_corridas_de_health_son_identicas_entre_si_y_contra_el_golden(data_dir: Path, tmp_path: Path) -> None:
    hashes_a0_before = _hash_files(A0_OUTPUTS_DIR, A0_OUTPUT_NAMES)
    hashes_a1_before = _hash_files(A1_OUTPUTS_DIR, A1_OUTPUT_NAMES)

    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    _run_health(data_dir, first_dir, tmp_path / "first.duckdb")
    _run_health(data_dir, second_dir, tmp_path / "second.duckdb")

    for file_name in ("health_scores.csv", "validation.md"):
        first_bytes = (first_dir / file_name).read_bytes()
        second_bytes = (second_dir / file_name).read_bytes()
        assert first_bytes == second_bytes, f"{file_name}: las dos corridas no son identicas"

        golden_bytes = (GOLDEN_DIR / file_name).read_bytes()
        assert first_bytes == golden_bytes, f"{file_name}: no coincide con el golden commiteado"

    assert _hash_files(A0_OUTPUTS_DIR, A0_OUTPUT_NAMES) == hashes_a0_before
    assert _hash_files(A1_OUTPUTS_DIR, A1_OUTPUT_NAMES) == hashes_a1_before
