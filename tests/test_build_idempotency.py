"""Idempotencia byte a byte de `build`, marca `dataset`.

Corre `python -m worky_engine build` dos veces en carpetas temporales
distintas y compara las salidas de este PR (`master_dataset.csv`,
`exceptions_log.csv` y, desde el PR 3b, `coverage_report.md`) entre si y
contra la copia commiteada en `outputs/`, tal como fija el requisito de
idempotencia byte a byte de `build-cli`. `coverage_report.md` no lleva
hora de reloj (seccion 2 del diseno), asi que tambien debe salir
identico entre las dos corridas.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from worky_engine.cli import main

OUTPUT_NAMES = ("master_dataset.csv", "exceptions_log.csv", "coverage_report.md")
GOLDEN_DIR = Path(__file__).resolve().parent.parent / "outputs"

# Requisito comando unico de construccion (build-cli): outputs/ trae
# exactamente estos siete archivos tras un build, ni uno de mas ni uno
# de menos (identidad, ensamblaje y el reporte de cobertura).
EXPECTED_BUILD_OUTPUT_NAMES = frozenset(
    {
        "identity_crosswalk.csv",
        "match_audit.csv",
        "quarantine_companies.csv",
        "quarantine_deals.csv",
        "master_dataset.csv",
        "exceptions_log.csv",
        "coverage_report.md",
    }
)


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


@pytest.mark.dataset
def test_build_deja_exactamente_los_siete_archivos_esperados(data_dir: Path, tmp_path: Path) -> None:
    """Comando unico de construccion: `outputs/` trae las siete salidas, sin archivos de mas ni de menos."""
    out_dir = tmp_path / "solo_archivos_esperados"
    _run_build(data_dir, out_dir, tmp_path / "solo_archivos_esperados.duckdb")
    produced_names = {path.name for path in out_dir.iterdir() if path.is_file()}
    assert produced_names == EXPECTED_BUILD_OUTPUT_NAMES
