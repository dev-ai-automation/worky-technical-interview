"""Pruebas de `coverage_report.md`, sobre la copia commiteada de `outputs/`.

Corre `mart_coverage.sql` en una conexion de DuckDB aparte, registrando
solo `match_audit`, `quarantine_companies` y `quarantine_deals` leidos de
los CSV commiteados (las tres tablas de las que depende ese mart), y
compara cada porcentaje del `coverage_report.md` resultante contra un
conteo recalculado de forma independiente con pandas puro, sin reusar el
SQL del mart. No requiere las tres bases SQLite: usa unicamente los
goldens de `outputs/`.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from worky_engine.quality import generate_coverage_report

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
MART_COVERAGE_SQL = (
    Path(__file__).resolve().parent.parent / "worky_engine" / "sql" / "marts" / "mart_coverage.sql"
).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def golden_frames() -> dict[str, pd.DataFrame]:
    names = (
        "identity_crosswalk", "match_audit", "quarantine_companies",
        "quarantine_deals", "master_dataset", "exceptions_log",
    )
    return {name: pd.read_csv(OUTPUTS_DIR / f"{name}.csv", encoding="utf-8") for name in names}


def _generate_report(match_audit: pd.DataFrame, golden_frames: dict[str, pd.DataFrame]) -> str:
    """Corre `mart_coverage.sql` sobre el `match_audit` dado y arma el texto del reporte.

    Se factoriza para poder correrla dos veces con un `match_audit`
    distinto entre corridas (requisito recalculo desde match_audit).
    """
    con = duckdb.connect()
    try:
        con.register("match_audit", match_audit)
        con.register("quarantine_companies", golden_frames["quarantine_companies"])
        con.register("quarantine_deals", golden_frames["quarantine_deals"])
        # mart_coverage.sql (secciones 7 y 9) lee `mart_master_dataset`:
        # registrar el golden bajo ese mismo nombre deja entrar la salida
        # ya materializada sin correr el resto del pipeline de marts.
        con.register("mart_master_dataset", golden_frames["master_dataset"])
        con.execute(MART_COVERAGE_SQL)
        coverage = {
            "coverage_by_system": con.execute("SELECT * FROM mart_coverage_by_system").df(),
            "coverage_by_tier": con.execute("SELECT * FROM mart_coverage_by_tier").df(),
            "coverage_manual_queue": con.execute("SELECT * FROM mart_coverage_manual_queue").df(),
            "coverage_quarantine": con.execute("SELECT * FROM mart_coverage_quarantine").df(),
            "coverage_trend": con.execute("SELECT * FROM mart_coverage_trend").df(),
            "coverage_trend_median": con.execute("SELECT * FROM mart_coverage_trend_median").df(),
            "coverage_channel": con.execute("SELECT * FROM mart_coverage_channel").df(),
            "coverage_revenue": con.execute("SELECT * FROM mart_coverage_revenue").df(),
        }
    finally:
        con.close()

    identity_outputs = {
        "identity_crosswalk": golden_frames["identity_crosswalk"],
        "match_audit": match_audit,
        "quarantine_companies": golden_frames["quarantine_companies"],
        "quarantine_deals": golden_frames["quarantine_deals"],
    }
    assembly_outputs = {
        "master_dataset": golden_frames["master_dataset"],
        "exceptions_log": golden_frames["exceptions_log"],
        **coverage,
    }
    return generate_coverage_report(identity_outputs, assembly_outputs)


@pytest.fixture(scope="module")
def report_and_frames(golden_frames: dict[str, pd.DataFrame]) -> tuple[str, dict[str, pd.DataFrame]]:
    report = _generate_report(golden_frames["match_audit"], golden_frames)
    return report, golden_frames


def test_el_reporte_cambia_cuando_match_audit_cambia_entre_corridas(
    golden_frames: dict[str, pd.DataFrame],
) -> None:
    """Requisito 'recalculo desde match_audit': un cambio en match_audit entre corridas cambia el reporte."""
    baseline_report = _generate_report(golden_frames["match_audit"], golden_frames)

    modified_match_audit = golden_frames["match_audit"].copy()
    t0_index = modified_match_audit.index[modified_match_audit["tier"] == "T0"][0]
    modified_match_audit.loc[t0_index, "tier"] = "M"
    modified_match_audit.loc[t0_index, "master_id"] = None
    modified_report = _generate_report(modified_match_audit, golden_frames)

    assert baseline_report != modified_report
    baseline_t0 = int((golden_frames["match_audit"]["tier"] == "T0").sum())
    baseline_m = int((golden_frames["match_audit"]["tier"] == "M").sum())
    assert f"| T0 | {baseline_t0} |" in baseline_report
    assert f"| T0 | {baseline_t0 - 1} |" in modified_report
    assert f"| M | {baseline_m} |" in baseline_report
    assert f"| M | {baseline_m + 1} |" in modified_report


def test_el_reporte_no_trae_nan_ni_none_literal(report_and_frames: tuple[str, dict]) -> None:
    report, _ = report_and_frames
    assert "nan" not in report
    assert "None" not in report


def test_cobertura_por_sistema_coincide_con_un_recalculo_independiente(
    report_and_frames: tuple[str, dict],
) -> None:
    report, frames = report_and_frames
    match_audit = frames["match_audit"]
    for system, group in match_audit.groupby("source_system"):
        expected_pct = 100.0 * group["master_id"].notna().sum() / len(group)
        assert f"| {system} | {len(group)} | {int(group['master_id'].notna().sum())} | {expected_pct:.2f}%" in report


def test_cobertura_por_nivel_coincide_con_un_recalculo_independiente(
    report_and_frames: tuple[str, dict],
) -> None:
    report, frames = report_and_frames
    match_audit = frames["match_audit"]
    tiered = match_audit[match_audit["tier"].isin(["T0", "T1", "T2", "T3", "M"])]
    total_tiered = len(tiered)
    for tier in ("T0", "T1", "T2", "T3", "M"):
        count = int((tiered["tier"] == tier).sum())
        expected_pct = 100.0 * count / total_tiered
        assert f"| {tier} | {count} | {expected_pct:.2f}%" in report


def test_cola_de_revision_manual_coincide_con_un_recalculo_independiente(
    report_and_frames: tuple[str, dict],
) -> None:
    report, frames = report_and_frames
    manual_count = int((frames["match_audit"]["tier"] == "M").sum())
    assert f"{manual_count} registros en el nivel M" in report


def test_totales_de_mrr_coinciden_con_un_recalculo_independiente(
    report_and_frames: tuple[str, dict],
) -> None:
    report, frames = report_and_frames
    master_dataset = frames["master_dataset"]
    total_crm = master_dataset.loc[master_dataset["mrr_source"] == "crm", "mrr_mxn"].sum()
    total_with_imputed = master_dataset.loc[
        master_dataset["mrr_source"].isin(["crm", "imputed_from_deal"]), "mrr_mxn"
    ].sum()
    expected_ratio = 100.0 * (total_with_imputed - total_crm) / total_with_imputed
    assert f"{total_crm:.2f}" in report
    assert f"{total_with_imputed:.2f}" in report
    assert f"{expected_ratio:.2f}%" in report


def test_conteos_de_cuarentena_coinciden_con_un_recalculo_independiente(
    report_and_frames: tuple[str, dict],
) -> None:
    report, frames = report_and_frames
    quarantine_deals = frames["quarantine_deals"]
    assert f"| Empresas clon (quarantine_companies) | {len(frames['quarantine_companies'])} |" in report
    assert f"| Deals huerfanos (quarantine_deals) | {len(quarantine_deals)} |" in report
    assert f"{quarantine_deals['amount'].sum():.2f}" in report


def test_excepciones_coinciden_con_un_recalculo_independiente(report_and_frames: tuple[str, dict]) -> None:
    report, frames = report_and_frames
    for code, count in frames["exceptions_log"]["exception_code"].value_counts().items():
        assert f"| {code} | {count} |" in report


def test_distribucion_de_trend_status_coincide_con_un_recalculo_independiente(
    report_and_frames: tuple[str, dict],
) -> None:
    report, frames = report_and_frames
    master_dataset = frames["master_dataset"]
    for status, count in master_dataset["trend_status"].value_counts().items():
        assert f"| {status} | {count} |" in report


def test_canal_de_adquisicion_y_revenue_coinciden_con_un_recalculo_independiente(
    report_and_frames: tuple[str, dict],
) -> None:
    report, frames = report_and_frames
    master_dataset = frames["master_dataset"]
    for channel, count in master_dataset["acquisition_channel"].value_counts().items():
        assert f"| {channel} | {count} |" in report
    expected_revenue = master_dataset["closed_revenue_mxn"].sum()
    assert f"{expected_revenue:.2f}" in report
