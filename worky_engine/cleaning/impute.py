"""Imputacion de `mrr` desde deals (ADR-002, adenda 1), replica en pandas de `mart_mrr.sql`
y `mart_deal_normalized.sql` (D6, D7; tabla linea por linea en la seccion 3 del diseno).

Solo procesa filas que `detect_missing_mrr` ya marco como `unresolved`
con `mrr` vacio: las empresas reales sin `mrr`, sin sus 28 clones
`HS-9000xx` (esos quedan en `clone_excluded` y nunca llegan aqui) y sin
las filas `unresolved` por moneda o texto no numerico (esas ya traen
`mrr` con texto, no vacio). Una fila ya resuelta en una corrida
anterior (`mrr_source == 'imputed_from_deal'`, D8) no se reprocesa:
`detect_missing_mrr` la preserva antes de que esta funcion la vea.
"""

from __future__ import annotations

import pandas as pd

from worky_engine.cleaning.rules import Correction, parse_finite_amount
from worky_engine.normalization.currency import to_mxn
from worky_engine.writers import format_money


def impute_mrr_from_deals(companies: pd.DataFrame, deals: pd.DataFrame) -> tuple[pd.DataFrame, list[Correction]]:
    """Imputa `mrr_mxn` desde el monto unico de los deals de cada empresa candidata.

    Une por `hubspot_id` crudo (los deals huerfanos caen solos, D6
    punto 2). Un monto que es exactamente 12 veces el minimo de la
    misma empresa se anualiza a ese minimo y produce su propia
    correccion `mrr_deal_annualized`. `mrr_confidence` es `high` con un
    deal `closedwon` y `medium` en cualquier otro caso. Una empresa sin
    deals o con montos que no convergen a un unico valor queda
    `unresolved` y se reporta en cada corrida (reporte, no correccion).

    Un deal con `amount` vacio, no numerico o no finito (`nan`, `inf`)
    se salta y se reporta como `deal_amount_not_numeric` (reporte,
    nunca correccion); la empresa se imputa igual con sus deals
    restantes, o queda `unresolved` si ninguno trae un monto valido.

    Los montos se acumulan por fila de deal, no por `deal_id`, igual
    que el `GROUP BY` de `mart_mrr.sql` sobre todas las filas: dos
    filas con el mismo `deal_id` y montos distintos dejan a la empresa
    `unresolved` en vez de colapsarse en silencio a la ultima.
    """
    result = companies.copy()
    corrections: list[Correction] = []

    candidates = result.index[(result["mrr_source"] == "unresolved") & (result["mrr"] == "")]
    for index in candidates:
        hubspot_id = result.at[index, "hubspot_id"]
        currency = result.at[index, "currency_original"] or "MXN"
        company_deals = deals[deals["hubspot_id"] == hubspot_id]

        if company_deals.empty:
            corrections.append(
                Correction(
                    exception_code="mrr_unresolved",
                    source_system="crm_hubspot",
                    source_id=hubspot_id,
                    field_name="mrr_mxn",
                    original_value="",
                    applied_value="",
                    evidence_ref="sin deals",
                )
            )
            continue

        amounts_mxn: list[tuple[str, float]] = []
        valid_rows: list[int] = []
        for position, (deal_id, amount) in enumerate(zip(company_deals["deal_id"], company_deals["amount"])):
            try:
                amounts_mxn.append((deal_id, round(to_mxn(parse_finite_amount(amount), currency).mxn, 2)))
                valid_rows.append(position)
            except ValueError:
                corrections.append(
                    Correction(
                        exception_code="deal_amount_not_numeric",
                        source_system="crm_hubspot",
                        source_id=deal_id,
                        field_name="amount",
                        original_value=amount,
                        applied_value="",
                        evidence_ref=hubspot_id,
                    )
                )

        if not amounts_mxn:
            corrections.append(
                Correction(
                    exception_code="mrr_unresolved",
                    source_system="crm_hubspot",
                    source_id=hubspot_id,
                    field_name="mrr_mxn",
                    original_value="",
                    applied_value="",
                    evidence_ref="sin deals numericos",
                )
            )
            continue

        min_amount = min(amount for _deal_id, amount in amounts_mxn)
        normalized: list[tuple[str, float]] = []
        annualized: list[tuple[str, float]] = []
        for deal_id, amount in amounts_mxn:
            if min_amount > 0 and round(amount, 2) == round(min_amount * 12, 2):
                normalized.append((deal_id, min_amount))
                annualized.append((deal_id, amount))
            else:
                normalized.append((deal_id, amount))

        if len({round(amount, 2) for _deal_id, amount in normalized}) != 1:
            corrections.append(
                Correction(
                    exception_code="mrr_unresolved",
                    source_system="crm_hubspot",
                    source_id=hubspot_id,
                    field_name="mrr_mxn",
                    original_value="",
                    applied_value="",
                    evidence_ref="montos ambiguos",
                )
            )
            continue

        candidate_mrr = min_amount
        valid_deals = company_deals.iloc[valid_rows]
        has_closedwon = (valid_deals["stage"] == "closedwon").any()
        confidence = "high" if has_closedwon else "medium"
        evidence_deal_id = min(amounts_mxn, key=lambda item: (item[1] != candidate_mrr, item[0]))[0]

        result.at[index, "mrr"] = format_money(candidate_mrr)
        result.at[index, "mrr_mxn"] = format_money(candidate_mrr)
        result.at[index, "mrr_source"] = "imputed_from_deal"
        result.at[index, "mrr_confidence"] = confidence

        corrections.append(
            Correction(
                exception_code="mrr_imputed_from_deal",
                source_system="crm_hubspot",
                source_id=hubspot_id,
                field_name="mrr_mxn",
                original_value="",
                applied_value=format_money(candidate_mrr),
                evidence_ref=evidence_deal_id,
                confidence=confidence,
            )
        )
        for deal_id, amount in annualized:
            corrections.append(
                Correction(
                    exception_code="mrr_deal_annualized",
                    source_system="crm_hubspot",
                    source_id=deal_id,
                    field_name="amount",
                    original_value=format_money(amount),
                    applied_value=format_money(min_amount),
                    evidence_ref=hubspot_id,
                )
            )

    return result, corrections
