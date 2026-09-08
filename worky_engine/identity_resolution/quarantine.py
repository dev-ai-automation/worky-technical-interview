"""Deduplicacion de companies y cuarentena de deals huerfanos.

Implementa las secciones 3.2 y 3.8 del diseno. Trabaja sobre listas de
diccionarios, nunca sobre DataFrames, para quedarse fuera de la capa que
toca pandas (ver el docstring de `cascade.py`, que es esa capa).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

CLONE_REASON = "duplicate_company_clone"
ORPHAN_DEAL_REASON = "orphan_deal_missing_company"


def deduplicate_companies(
    companies: list[dict[str, Any]],
    referenced_hubspot_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separa las filas clon de las empresas reales, por evidencia y no por prefijo de id.

    Una fila es clon cuando su nombre normalizado y su etiqueta de
    dominio coinciden con los de otra fila, su `mrr` viene en nulo y
    ningun `accounts.hubspot_id` la referencia. La fila sobreviviente es
    la que no cumple esa condicion. Si un grupo no produce exactamente
    un sobreviviente, todas sus filas se conservan como reales, para no
    perder datos ante una forma que el diseno no anticipo.
    """
    groups: dict[tuple[Any, Any], list[dict[str, Any]]] = defaultdict(list)
    for row in companies:
        groups[(row["name_norm"], row["domain_label"])].append(row)

    survivors: list[dict[str, Any]] = []
    quarantine_rows: list[dict[str, Any]] = []
    for group in groups.values():
        if len(group) == 1:
            survivors.append(group[0])
            continue

        is_clone = [
            row.get("mrr") is None and row["hubspot_id"] not in referenced_hubspot_ids
            for row in group
        ]
        clones = [row for row, flag in zip(group, is_clone) if flag]
        group_survivors = [row for row, flag in zip(group, is_clone) if not flag]

        if len(group_survivors) != 1:
            survivors.extend(group)
            continue

        survivor = group_survivors[0]
        survivors.append(survivor)
        for clone in clones:
            quarantine_rows.append(
                {
                    "hubspot_id": clone["hubspot_id"],
                    "company_name": clone.get("name"),
                    "domain": clone.get("domain"),
                    "mrr": clone.get("mrr"),
                    "currency": clone.get("currency"),
                    "signup_date": clone.get("signup_date"),
                    "churn_date": clone.get("churn_date"),
                    "reason_code": CLONE_REASON,
                    "survivor_hubspot_id": survivor["hubspot_id"],
                    "evidence": {
                        "mrr_is_null": clone.get("mrr") is None,
                        "name_norm_equal": True,
                        "referenced_by_accounts": clone["hubspot_id"] in referenced_hubspot_ids,
                    },
                }
            )

    return survivors, quarantine_rows


def quarantine_orphan_deals(
    deals: list[dict[str, Any]],
    all_company_hubspot_ids: set[str],
) -> list[dict[str, Any]]:
    """Deals cuyo `hubspot_id` no existe en `companies`, ni real ni clon."""
    orphans: list[dict[str, Any]] = []
    for deal in deals:
        hubspot_id = deal.get("hubspot_id")
        if hubspot_id in all_company_hubspot_ids:
            continue
        orphans.append(
            {
                "deal_id": deal["deal_id"],
                "hubspot_id": hubspot_id,
                "stage": deal.get("stage"),
                "amount": deal.get("amount"),
                "created_date": deal.get("created_date"),
                "close_date": deal.get("close_date"),
                "pipeline": deal.get("pipeline"),
                "lead_source": deal.get("lead_source"),
                "reason_code": ORPHAN_DEAL_REASON,
            }
        )
    return orphans
