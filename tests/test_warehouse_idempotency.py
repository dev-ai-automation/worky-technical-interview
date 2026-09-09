"""Idempotencia byte a byte de `outputs/warehouse/`, marca `dataset` (PR3 de `a4-warehouse-model`).

Corre `python -m worky_engine warehouse` dos veces en carpetas y bases temporales distintas
sobre el dataset real, y compara `dim_company.csv` y `map_source_identity.csv` entre si y
contra la copia commiteada en `outputs/warehouse/`, tal como fija el requisito "determinismo
de llaves surrogate y goldens byte-idénticos" (spec `warehouse-model`). Tambien verifica que
el hash de los dieciocho archivos ya versionados de `outputs/` (ocho de A0, ocho de A1, dos
de A3) es el mismo antes y despues, requisito "aislamiento respecto a los goldens de A0, A1
y A3", y que `--out-dir` queda con exactamente los dos archivos que `warehouse` produce.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from worky_engine.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = REPO_ROOT / "outputs" / "warehouse"
A0_OUTPUTS_DIR = REPO_ROOT / "outputs"
A1_OUTPUTS_DIR = REPO_ROOT / "outputs" / "analysis"
A3_OUTPUTS_DIR = REPO_ROOT / "outputs" / "health"

OUTPUT_NAMES = ("dim_company.csv", "map_source_identity.csv")

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
A3_OUTPUT_NAMES = ("health_scores.csv", "validation.md")


def _run_warehouse(data_dir: Path, out_dir: Path, db_path: Path) -> None:
    exit_code = main(
        ["warehouse", "--data-dir", str(data_dir), "--out-dir", str(out_dir), "--db-path", str(db_path)]
    )
    assert exit_code == 0


def _hash_files(directory: Path, names: tuple[str, ...]) -> dict[str, str]:
    return {name: hashlib.sha256((directory / name).read_bytes()).hexdigest() for name in names}


@pytest.mark.dataset
def test_dos_corridas_de_warehouse_son_identicas_entre_si_y_contra_el_golden(
    data_dir: Path, tmp_path: Path
) -> None:
    hashes_a0_before = _hash_files(A0_OUTPUTS_DIR, A0_OUTPUT_NAMES)
    hashes_a1_before = _hash_files(A1_OUTPUTS_DIR, A1_OUTPUT_NAMES)
    hashes_a3_before = _hash_files(A3_OUTPUTS_DIR, A3_OUTPUT_NAMES)

    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    _run_warehouse(data_dir, first_dir, tmp_path / "first.duckdb")
    _run_warehouse(data_dir, second_dir, tmp_path / "second.duckdb")

    for file_name in OUTPUT_NAMES:
        first_bytes = (first_dir / file_name).read_bytes()
        second_bytes = (second_dir / file_name).read_bytes()
        assert first_bytes == second_bytes, f"{file_name}: las dos corridas no son identicas"

        golden_bytes = (GOLDEN_DIR / file_name).read_bytes()
        assert first_bytes == golden_bytes, f"{file_name}: no coincide con el golden commiteado"

    assert _hash_files(A0_OUTPUTS_DIR, A0_OUTPUT_NAMES) == hashes_a0_before
    assert _hash_files(A1_OUTPUTS_DIR, A1_OUTPUT_NAMES) == hashes_a1_before
    assert _hash_files(A3_OUTPUTS_DIR, A3_OUTPUT_NAMES) == hashes_a3_before


@pytest.mark.dataset
def test_warehouse_deja_exactamente_los_dos_archivos_esperados(data_dir: Path, tmp_path: Path) -> None:
    """`--out-dir` queda con `dim_company.csv` y `map_source_identity.csv`, ni uno de mas ni uno de menos."""
    out_dir = tmp_path / "solo_archivos_esperados"
    _run_warehouse(data_dir, out_dir, tmp_path / "solo_archivos_esperados.duckdb")
    produced_names = {path.name for path in out_dir.iterdir() if path.is_file()}
    assert produced_names == set(OUTPUT_NAMES)
