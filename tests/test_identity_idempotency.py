"""Idempotencia de `resolve_identity`, sobre el fixture sintetico.

Corre la resolucion dos veces: una reutilizando el `identity_crosswalk`
que dejo la primera corrida, y otra con `--no-reuse-crosswalk`
simulado (`reuse_crosswalk=False`). Las cuatro salidas deben quedar
identicas byte a byte en los tres casos, porque `master_id` es una
funcion pura de `domain_label` y del nombre normalizado, tal como fija
la seccion 3.6 del diseno. No lleva marca `dataset`: usa el fixture
sintetico para correr en cada invocacion de pytest.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tests.fixtures.mini_dataset import build_mini_dataset
from worky_engine.identity_resolution import resolve_identity
from worky_engine.writers import write_csv

OUTPUT_NAMES = (
    "identity_crosswalk.csv",
    "match_audit.csv",
    "quarantine_companies.csv",
    "quarantine_deals.csv",
)


def _write_outputs(outputs: dict[str, pd.DataFrame], out_dir: Path) -> None:
    for name in OUTPUT_NAMES:
        key = name.removesuffix(".csv")
        write_csv(outputs[key], out_dir / name)


def _read_bytes(out_dir: Path) -> dict[str, bytes]:
    return {name: (out_dir / name).read_bytes() for name in OUTPUT_NAMES}


def test_dos_corridas_reutilizando_el_crosswalk_son_identicas(tmp_path: Path) -> None:
    raw_tables = build_mini_dataset()

    first_dir = tmp_path / "first"
    first_dir.mkdir()
    first_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    _write_outputs(first_outputs, first_dir)

    existing_crosswalk = pd.read_csv(first_dir / "identity_crosswalk.csv", dtype=str, keep_default_na=False, na_values=[""], encoding="utf-8")

    second_dir = tmp_path / "second"
    second_dir.mkdir()
    second_outputs = resolve_identity(raw_tables, existing_crosswalk=existing_crosswalk, reuse_crosswalk=True)
    _write_outputs(second_outputs, second_dir)

    assert _read_bytes(first_dir) == _read_bytes(second_dir)


def test_correr_sin_reutilizar_el_crosswalk_produce_las_mismas_salidas(tmp_path: Path) -> None:
    raw_tables = build_mini_dataset()

    reused_dir = tmp_path / "reused"
    reused_dir.mkdir()
    reused_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    _write_outputs(reused_outputs, reused_dir)

    existing_crosswalk = pd.read_csv(reused_dir / "identity_crosswalk.csv", dtype=str, keep_default_na=False, na_values=[""], encoding="utf-8")

    no_reuse_dir = tmp_path / "no_reuse"
    no_reuse_dir.mkdir()
    no_reuse_outputs = resolve_identity(raw_tables, existing_crosswalk=existing_crosswalk, reuse_crosswalk=False)
    _write_outputs(no_reuse_outputs, no_reuse_dir)

    assert _read_bytes(reused_dir) == _read_bytes(no_reuse_dir)
