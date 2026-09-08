"""Prueba de regresion de la calibracion del ADR-001, marca `dataset`.

Oculta el `hubspot_id` de los pares que T0 ya confirmo y corre el
puntaje solo por nombre, tal como describe la seccion 3.9 del diseno.
Compara contra `tests/fixtures/calibration_expectations.json`: si una
actualizacion de rapidfuzz mueve un puntaje, esta prueba debe fallar,
porque la respuesta correcta es subir `ruleset_version`, actualizar el
archivo de expectativas y revisar el ADR-001 en su propio cambio, nunca
ajustar el umbral en silencio.

Los valores del archivo de expectativas se midieron en la primera
corrida de este PR con rapidfuzz 3.14.6 y la normalizacion real del
motor: 590 de 596 aciertos en primer lugar (99.0%). El ADR-001, el spec
de `identity-resolution` y la seccion 3.9 del diseno ya se corrigieron
a este mismo numero, que es la linea base de `ruleset_version` 1.0.0;
la version no sube porque ningun umbral cambio, solo la medicion con la
normalizacion real en lugar de la calibracion previa. Los 6 pares que
`WRatio` no puede desempatar por nombre son casos genuinamente
ambiguos: dos empresas reales se llaman `Galindo S. R.L. de C.V.`, y
`Rangel S.A. de C.V.` queda identico a `Rangel y Asociados` despues de
quitar la razon social. El desglose por nivel (596/650/54/0/0) si
reproduce exactamente la lista de verificacion del ADR-001.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from worky_engine.identity_resolution import resolve_identity
from worky_engine.identity_resolution import scoring
from worky_engine.normalization import normalize_company_name
from worky_engine.sources import load_raw_tables

EXPECTATIONS_PATH = Path(__file__).parent / "fixtures" / "calibration_expectations.json"


@pytest.fixture(scope="module")
def expectations() -> dict[str, Any]:
    with open(EXPECTATIONS_PATH, encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def real_result(data_dir) -> dict[str, Any]:
    raw_tables = load_raw_tables(data_dir)
    result = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    return {"raw_tables": raw_tables, **result}


@pytest.mark.dataset
def test_wratio_elige_el_cruce_correcto_en_primer_lugar(real_result, expectations) -> None:
    audit = real_result["match_audit"]
    accounts_by_id = {
        row["account_id"]: row["account_name"]
        for row in real_result["raw_tables"]["raw_accounts"].to_dict("records")
    }
    company_names = {
        row["source_id"]: json.loads(row["evidence_json"])["name_norm"]
        for row in audit[audit["tier"] == "S"].to_dict("records")
    }
    labeled_pairs = [
        (row["source_id"], json.loads(row["evidence_json"])["hubspot_id"])
        for row in audit[audit["tier"] == "T0"].to_dict("records")
    ]

    correct = 0
    for account_id, true_hubspot_id in labeled_pairs:
        account_norm = normalize_company_name(accounts_by_id[account_id])
        best_hubspot_id = max(
            company_names, key=lambda candidate: scoring.weighted_ratio(account_norm, company_names[candidate])
        )
        if best_hubspot_id == true_hubspot_id:
            correct += 1

    assert len(labeled_pairs) == expectations["labeled_pairs"]
    assert correct == expectations["top1_correct_with_wratio"]


@pytest.mark.dataset
def test_desglose_por_nivel_reproduce_la_lista_de_verificacion(real_result, expectations) -> None:
    tier_counts = real_result["match_audit"]["tier"].value_counts().to_dict()
    for tier, expected_count in expectations["coverage_by_tier"].items():
        assert tier_counts.get(tier, 0) == expected_count, f"tier {tier}: se esperaban {expected_count} filas"


@pytest.mark.dataset
def test_match_audit_tiene_una_fila_por_registro_origen(real_result) -> None:
    # 678 companies (650 S + 28 Q) + 650 accounts (596 T0 + 54 T2) + 650
    # customers (650 T1) = 1978, tal como fija la seccion 2 del diseno.
    tier_counts = real_result["match_audit"]["tier"].value_counts().to_dict()

    assert tier_counts.get("S", 0) == 650
    assert tier_counts.get("Q", 0) == 28
    assert tier_counts.get("T0", 0) == 596
    assert tier_counts.get("T2", 0) == 54
    assert tier_counts.get("T1", 0) == 650
    assert sum(tier_counts.values()) == 1978
