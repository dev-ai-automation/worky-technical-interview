"""Equivalencia entre `worky_engine.cleaning.impute` y `mart_mrr` (D7), marca `dataset`.

Compara las 28 imputaciones de `clean` contra los goldens ya
versionados: `outputs/exceptions_log.csv` (filtrado a
`mrr_imputed_from_deal`, read-only) para el monto y el deal de
evidencia, y `outputs/master_dataset.csv` (read-only) para el reparto
de `mrr_confidence`. Correr los marts por DuckDB dentro de esta prueba
se descarto (D7): esos dos archivos ya se verifican byte a byte contra
los marts en `tests/test_build_idempotency.py`, asi que compararse con
ellos es compararse con `mart_mrr`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from worky_engine.cleaning import run_clean

pytestmark = pytest.mark.dataset

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read_real_csv(data_dir: Path, filename: str) -> pd.DataFrame:
    return pd.read_csv(data_dir / filename, dtype=str, keep_default_na=False, encoding="utf-8")


def test_coincidencia_con_mart_mrr(data_dir: Path) -> None:
    """Las 28 imputaciones de clean coinciden en monto, deal de evidencia y confianza con los goldens del motor."""
    companies = _read_real_csv(data_dir, "crm_hubspot__companies.csv")
    deals = _read_real_csv(data_dir, "crm_hubspot__deals.csv")
    result = run_clean(companies, deals)

    imputed = result.exceptions[result.exceptions["exception_code"] == "mrr_imputed_from_deal"]
    assert len(imputed) == 28
    by_id = {row["source_id"]: row for _, row in imputed.iterrows()}

    golden_exceptions = pd.read_csv(
        REPO_ROOT / "outputs" / "exceptions_log.csv", dtype=str, keep_default_na=False, encoding="utf-8"
    )
    golden_imputed = golden_exceptions[golden_exceptions["exception_code"] == "mrr_imputed_from_deal"]
    assert len(golden_imputed) == 28

    for _, golden_row in golden_imputed.iterrows():
        row = by_id[golden_row["source_id"]]
        assert row["applied_value"] == golden_row["applied_value"]
        assert row["evidence_ref"] == golden_row["evidence_ref"]

    master_dataset = pd.read_csv(
        REPO_ROOT / "outputs" / "master_dataset.csv", dtype=str, keep_default_na=False, encoding="utf-8"
    )
    confidence_by_id = dict(zip(master_dataset["hubspot_id"], master_dataset["mrr_confidence"]))
    high = sum(1 for source_id in by_id if confidence_by_id.get(source_id) == "high")
    medium = sum(1 for source_id in by_id if confidence_by_id.get(source_id) == "medium")
    assert high == 4
    assert medium == 24
    for source_id, row in by_id.items():
        assert row["confidence"] == confidence_by_id[source_id]
