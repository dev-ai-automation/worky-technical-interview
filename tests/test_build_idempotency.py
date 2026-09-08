"""Idempotencia byte a byte de `build`, marca `dataset`.

Corre `python -m worky_engine build` dos veces en carpetas temporales
distintas y compara las salidas de este PR (`master_dataset.csv`,
`exceptions_log.csv`) entre si y contra la copia commiteada en
`outputs/`, tal como fija el requisito de idempotencia byte a byte de
`build-cli`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from worky_engine.cli import main

OUTPUT_NAMES = ("master_dataset.csv", "exceptions_log.csv")
GOLDEN_DIR = Path(__file__).resolve().parent.parent / "outputs"


def _run_build(data_dir: Path, out_dir: Path, db_path: Path) -> None:
    exit_code = main(
        ["build", "--data-dir", str(data_dir), "--out-dir", str(out_dir), "--db-path", str(db_path)]
    )
    assert exit_code == 0


def _read_bytes(out_dir: Path) -> dict[str, bytes]:
    return {name: (out_dir / name).read_bytes() for name in OUTPUT_NAMES}


@pytest.mark.dataset
def test_dos_corridas_de_build_son_identicas_entre_si_y_contra_outputs(
    data_dir: Path, tmp_path: Path
) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    _run_build(data_dir, first_dir, tmp_path / "first.duckdb")
    _run_build(data_dir, second_dir, tmp_path / "second.duckdb")

    first_bytes = _read_bytes(first_dir)
    second_bytes = _read_bytes(second_dir)
    assert first_bytes == second_bytes

    golden_bytes = {name: (GOLDEN_DIR / name).read_bytes() for name in OUTPUT_NAMES}
    assert first_bytes == golden_bytes
