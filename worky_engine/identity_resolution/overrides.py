"""Overrides de identidad: `identity_overrides.csv` fija manualmente un master_id (D14 a D17).

`load_overrides` lee y valida la forma del archivo (columnas, dominio de
`source_system`, campos obligatorios y fecha ISO), sin tocar el
crosswalk todavia. `apply_overrides` valida las referencias cruzadas
(que el `master_id` exista en `identity_crosswalk` y que el `source_id`
exista en su tabla cruda de origen) para TODAS las filas antes de
modificar cualquier salida de `resolve_identity`: una sola fila
invalida detiene la corrida sin escribir nada, tal como exige el
requisito "precedencia de overrides sobre la cascada" (spec
`identity-resolution`).

Este archivo es nuevo; no modifica ninguno de los modulos existentes de
`identity_resolution` (seccion 11 del diseno de `a4-warehouse-model`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from worky_engine.identity_resolution.cascade import RULESET_VERSION
from worky_engine.normalization import normalize_date

OVERRIDE_COLUMNS = ("source_system", "source_id", "master_id", "decided_by", "decided_at", "reason")
VALID_SOURCE_SYSTEMS = {"product_db", "vitally"}
OVERRIDE_TIER = "O"

# Misma tabla que `assert_source_id_in_origin_table` de `quality/contracts.py`,
# acotada a los dos sistemas que aceptan override (crm_hubspot no aplica: ahi
# el master_id se genera, no se vincula).
_ORIGIN_TABLE_BY_SOURCE_SYSTEM = {
    "product_db": ("raw_accounts", "account_id"),
    "vitally": ("raw_customers", "vitally_id"),
}
_CROSSWALK_COLUMN_BY_SOURCE_SYSTEM = {
    "product_db": ("account_id", "account_match_tier"),
    "vitally": ("vitally_id", "vitally_match_tier"),
}
# Fuerza de cada nivel para recalcular `confidence_tier`: 'O' pesa igual que
# 'T0' porque una decision humana es la evidencia mas fuerte disponible (D16).
_TIER_STRENGTH = {"T0": 0, "T1": 1, "T2": 2, "T3": 3, OVERRIDE_TIER: 0}


class OverrideError(Exception):
    """Una fila de `identity_overrides.csv` no paso validacion; el mensaje nombra la fila y el motivo."""


def load_overrides(path: str | Path) -> pd.DataFrame:
    """Lee `identity_overrides.csv` en UTF-8, como dato, y valida su forma.

    Valida las seis columnas exactas, que `source_system` sea
    `product_db` o `vitally`, que `decided_by`/`decided_at`/`reason` no
    vengan vacios, que `decided_at` sea una fecha ISO, y que el par
    `source_system`/`source_id` no se repita entre filas. No valida
    contra el crosswalk ni contra las tablas crudas: eso lo hace
    `apply_overrides`, que ya tiene esas referencias en memoria.
    """
    try:
        frame = pd.read_csv(Path(path), dtype=str, keep_default_na=False, encoding="utf-8")
    except pd.errors.EmptyDataError as error:
        raise OverrideError(f"identity_overrides: el archivo {path} esta vacio") from error
    except pd.errors.ParserError as error:
        raise OverrideError(
            f"identity_overrides: el archivo {path} no se pudo leer como CSV: {error}"
        ) from error

    columns = list(frame.columns)
    if columns != list(OVERRIDE_COLUMNS):
        raise OverrideError(
            f"identity_overrides: el archivo {path} debe traer las columnas "
            f"{list(OVERRIDE_COLUMNS)} y trae {columns}"
        )

    for position, row in frame.iterrows():
        row_number = position + 1
        source_system = row["source_system"]
        if source_system not in VALID_SOURCE_SYSTEMS:
            raise OverrideError(
                f"identity_overrides: fila {row_number} tiene source_system "
                f"'{source_system}' invalido, se esperaba 'product_db' o 'vitally'"
            )
        for column in ("decided_by", "decided_at", "reason"):
            if not row[column]:
                raise OverrideError(f"identity_overrides: fila {row_number} tiene '{column}' vacio")
        if not _is_iso_date(row["decided_at"]):
            raise OverrideError(
                f"identity_overrides: fila {row_number} tiene decided_at "
                f"'{row['decided_at']}' que no es una fecha ISO (YYYY-MM-DD)"
            )

    duplicated = frame.duplicated(subset=["source_system", "source_id"], keep="first")
    if duplicated.any():
        row_index = duplicated.index[duplicated][0]
        row_number = row_index + 1
        raise OverrideError(
            f"identity_overrides: fila {row_number} repite el source_id "
            f"'{frame.loc[row_index, 'source_id']}' de source_system "
            f"'{frame.loc[row_index, 'source_system']}', ya visto en una fila anterior"
        )

    return frame.reset_index(drop=True)


def apply_overrides(
    overrides: pd.DataFrame,
    identity_outputs: dict[str, pd.DataFrame],
    raw_tables: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Aplica overrides ya validados por `load_overrides` sobre las salidas de `resolve_identity`.

    Primero valida, para todas las filas, que el `master_id` exista en
    `identity_crosswalk` y que el `source_id` exista en la tabla cruda
    de su sistema; si una sola fila es invalida, lanza `OverrideError`
    antes de tocar cualquier salida. Despues, para cada fila valida:
    fija la columna del crosswalk que corresponde al sistema con nivel
    'O', recalcula `confidence_tier`, agrega una fila 'O' a
    `match_audit` con la evidencia del archivo, y marca
    `needs_review = false` con `superseded_by` en la fila que sustituye
    (D16). Devuelve un dict nuevo; no modifica `identity_outputs` en
    sitio.
    """
    crosswalk = identity_outputs["identity_crosswalk"]
    match_audit = identity_outputs["match_audit"]

    known_master_ids = set(crosswalk["master_id"])
    known_source_ids_by_system = {
        source_system: set(raw_tables[table_name][id_column].dropna())
        for source_system, (table_name, id_column) in _ORIGIN_TABLE_BY_SOURCE_SYSTEM.items()
    }

    for position, row in overrides.iterrows():
        row_number = position + 1
        if row["master_id"] not in known_master_ids:
            raise OverrideError(
                f"identity_overrides: fila {row_number} referencia master_id "
                f"'{row['master_id']}' que no existe en identity_crosswalk"
            )
        table_name, id_column = _ORIGIN_TABLE_BY_SOURCE_SYSTEM[row["source_system"]]
        if row["source_id"] not in known_source_ids_by_system[row["source_system"]]:
            raise OverrideError(
                f"identity_overrides: fila {row_number} referencia source_id "
                f"'{row['source_id']}' que no existe en {table_name}.{id_column}"
            )

    indexed_crosswalk = crosswalk.set_index("master_id", drop=False)
    match_audit_records = match_audit.to_dict("records")
    new_audit_rows: list[dict[str, Any]] = []

    for _, row in overrides.iterrows():
        source_system = row["source_system"]
        source_id = row["source_id"]
        master_id = row["master_id"]
        id_column, tier_column = _CROSSWALK_COLUMN_BY_SOURCE_SYSTEM[source_system]

        # Si la cascada (o un override anterior en este mismo archivo) ya
        # habia vinculado este source_id a otro master, hay que soltar ese
        # vinculo antes de crear el nuevo: si no, dos filas del crosswalk
        # terminan cargando el mismo account_id/vitally_id, una con tier
        # 'O' y la otra con su tier original, ya obsoleto.
        stale_mask = (indexed_crosswalk[id_column] == source_id) & (
            indexed_crosswalk["master_id"] != master_id
        )
        for stale_master_id in indexed_crosswalk.index[stale_mask]:
            indexed_crosswalk.at[stale_master_id, id_column] = None
            indexed_crosswalk.at[stale_master_id, tier_column] = None
            indexed_crosswalk.at[stale_master_id, "confidence_tier"] = _weakest_tier_with_override(
                indexed_crosswalk.at[stale_master_id, "account_match_tier"],
                indexed_crosswalk.at[stale_master_id, "vitally_match_tier"],
            )

        indexed_crosswalk.at[master_id, id_column] = source_id
        indexed_crosswalk.at[master_id, tier_column] = OVERRIDE_TIER
        indexed_crosswalk.at[master_id, "confidence_tier"] = _weakest_tier_with_override(
            indexed_crosswalk.at[master_id, "account_match_tier"],
            indexed_crosswalk.at[master_id, "vitally_match_tier"],
        )

        for record in match_audit_records:
            if record["source_system"] == source_system and record["source_id"] == source_id:
                evidence = json.loads(record["evidence_json"])
                evidence["superseded_by"] = {
                    "source": "identity_overrides",
                    "master_id": master_id,
                    "decided_by": row["decided_by"],
                    "decided_at": row["decided_at"],
                }
                record["evidence_json"] = json.dumps(
                    evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                )
                record["needs_review"] = False

        new_audit_rows.append(_override_audit_row(row))

    updated_match_audit = pd.DataFrame(
        match_audit_records + new_audit_rows, columns=list(match_audit.columns)
    )
    updated_match_audit = updated_match_audit.sort_values(
        ["source_system", "source_id"]
    ).reset_index(drop=True)

    updated_crosswalk = (
        indexed_crosswalk.reset_index(drop=True).sort_values("master_id").reset_index(drop=True)
    )

    return {
        **identity_outputs,
        "identity_crosswalk": updated_crosswalk,
        "match_audit": updated_match_audit,
    }


def _override_audit_row(row: pd.Series) -> dict[str, Any]:
    """Una fila `tier = 'O'` de `match_audit`, con la evidencia del archivo de overrides."""
    evidence = {"reason": row["reason"], "decided_by": row["decided_by"], "decided_at": row["decided_at"]}
    return {
        "source_system": row["source_system"],
        "source_id": row["source_id"],
        "master_id": row["master_id"],
        "tier": OVERRIDE_TIER,
        "score": "",
        "score_runner_up": "",
        "score_margin": "",
        "candidate_count": 1,
        "blocking_rule": "override",
        "evidence_json": json.dumps(evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        "veto_applied": False,
        "veto_reason": None,
        "needs_review": False,
        "ruleset_version": RULESET_VERSION,
        "decided_by": row["decided_by"],
        "decided_at": row["decided_at"],
    }


def _weakest_tier_with_override(*tiers: str | None) -> str | None:
    """Como `_weakest_tier` de `cascade.py`, pero 'O' pesa igual que 'T0' (D16).

    Un vinculo ausente llega aqui como `None` o como NaN de pandas
    (segun como se haya construido el DataFrame de origen): `pd.notna`
    filtra ambas formas, a diferencia de un `if tier` simple, que no
    descarta NaN porque `bool(float('nan'))` es `True`.
    """
    present = [tier for tier in tiers if pd.notna(tier)]
    if not present:
        return None
    return max(present, key=lambda tier: _TIER_STRENGTH[tier])


def _is_iso_date(value: str) -> bool:
    """`True` solo si `value` ya viene en formato ISO (`YYYY-MM-DD`) y es una fecha calendario real."""
    if len(value) != 10 or value[4] != "-" or value[7] != "-":
        return False
    return normalize_date(value) is not None
