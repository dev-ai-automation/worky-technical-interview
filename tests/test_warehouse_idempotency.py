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
from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset
from worky_engine.sources import load_raw_tables
from worky_engine.warehouse import open_warehouse_connection, run_warehouse

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

    # Conteos del perfil de schema y de la evidencia del PR 3: prueban que dim_company_open_bands sigue
    # llenando los cinco hechos. Son vistas sobre tablas en memoria, asi que se corre run_warehouse aqui mismo.
    expected_row_counts = {"dim_company": 650, "fact_usage_monthly": 9793, "fact_support_tickets": 1888, "fact_deals": 962,
                           "fact_revenue_monthly": 125, "fact_marketing_touches": 1635, "fact_health_score_monthly": 650}
    raw_tables = load_raw_tables(data_dir)
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    con = open_warehouse_connection(tmp_path / "counts.duckdb")
    try:
        assemble_master_dataset(con, raw_tables, identity_outputs)
        run_warehouse(con, overrides=None)
        for table_name, expected in expected_row_counts.items():
            where = "WHERE is_current" if table_name == "dim_company" else ""
            actual = con.execute(f"SELECT COUNT(*) FROM {table_name} {where}").fetchone()[0]
            assert actual == expected, f"{table_name}: se esperaban {expected} filas, se obtuvieron {actual}"
    finally:
        con.close()


@pytest.mark.dataset
def test_warehouse_deja_exactamente_los_dos_archivos_esperados(data_dir: Path, tmp_path: Path) -> None:
    """`--out-dir` queda con `dim_company.csv` y `map_source_identity.csv`, ni uno de mas ni uno de menos."""
    out_dir = tmp_path / "solo_archivos_esperados"
    _run_warehouse(data_dir, out_dir, tmp_path / "solo_archivos_esperados.duckdb")
    produced_names = {path.name for path in out_dir.iterdir() if path.is_file()}
    assert produced_names == set(OUTPUT_NAMES)
