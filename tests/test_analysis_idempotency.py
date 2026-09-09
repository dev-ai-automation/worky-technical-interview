"""Idempotencia byte a byte de `analyze` (PR 1 y PR 2: A1.1 a A1.5), marca `dataset`.

Corre `python -m worky_engine analyze` dos veces en carpetas temporales
distintas y compara las cinco salidas disponibles hasta este PR entre si
y contra la copia commiteada en `outputs/analysis/`, y verifica que el
hash de los ocho archivos de `outputs/` (A0, de solo lectura para este
cambio) es el mismo antes y despues de correr `analyze` (decision D15
del diseno). `a1_03_cohort_retention.csv` y `a1_04_attribution.csv` se
agregan en el PR 2 (tarea 2.8; no listada en la tabla de lineas del PR 2
del diseno, ver "Brechas encontradas en el diseno" en tasks.md). Las
otras tres salidas (`a1_06_negative_hours.csv`, `analysis_exceptions.csv`
y `report.md`) se agregan en el PR 3, cuando sus archivos existen.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from worky_engine.cli import main

OUTPUT_NAMES = (
    "a1_01_active_mrr.csv",
    "a1_02_usage_drop.csv",
    "a1_03_cohort_retention.csv",
    "a1_04_attribution.csv",
    "a1_05_orphan_deals.csv",
)
GOLDEN_DIR = Path(__file__).resolve().parent.parent / "outputs" / "analysis"
A0_OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
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


def _run_analyze(data_dir: Path, out_dir: Path, db_path: Path) -> None:
    exit_code = main(
        ["analyze", "--data-dir", str(data_dir), "--out-dir", str(out_dir), "--db-path", str(db_path)]
    )
    assert exit_code == 0


def _read_bytes(out_dir: Path) -> dict[str, bytes]:
    return {name: (out_dir / name).read_bytes() for name in OUTPUT_NAMES}


def _hash_a0_outputs() -> dict[str, str]:
    return {name: hashlib.sha256((A0_OUTPUTS_DIR / name).read_bytes()).hexdigest() for name in A0_OUTPUT_NAMES}


@pytest.mark.dataset
def test_dos_corridas_de_analyze_son_identicas_entre_si_y_contra_el_golden(
    data_dir: Path, tmp_path: Path
) -> None:
    hashes_before = _hash_a0_outputs()

    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    _run_analyze(data_dir, first_dir, tmp_path / "first.duckdb")
    _run_analyze(data_dir, second_dir, tmp_path / "second.duckdb")

    first_bytes = _read_bytes(first_dir)
    second_bytes = _read_bytes(second_dir)
    assert first_bytes == second_bytes

    golden_bytes = {name: (GOLDEN_DIR / name).read_bytes() for name in OUTPUT_NAMES}
    assert first_bytes == golden_bytes

    hashes_after = _hash_a0_outputs()
    assert hashes_before == hashes_after
