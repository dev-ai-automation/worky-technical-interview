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

from worky_engine.cleaning.rules import Correction
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

    Un deal con `amount` vacio o no numerico se salta y se reporta como
    `deal_amount_not_numeric` (reporte, nunca correccion); la empresa
    se imputa igual con sus deals restantes, o queda `unresolved` si
    ninguno trae un monto numerico.
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

        amounts_mxn: dict[str, float] = {}
        for deal_id, amount in zip(company_deals["deal_id"], company_deals["amount"]):
            try:
                amounts_mxn[deal_id] = round(to_mxn(float(amount), currency).mxn, 2)
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

        min_amount = min(amounts_mxn.values())
        normalized = {}
        annualized_deal_ids = []
        for deal_id, amount in amounts_mxn.items():
            if min_amount > 0 and round(amount, 2) == round(min_amount * 12, 2):
                normalized[deal_id] = min_amount
                annualized_deal_ids.append(deal_id)
            else:
                normalized[deal_id] = amount

        if len({round(v, 2) for v in normalized.values()}) != 1:
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
        valid_deals = company_deals[company_deals["deal_id"].isin(amounts_mxn)]
        has_closedwon = (valid_deals["stage"] == "closedwon").any()
        confidence = "high" if has_closedwon else "medium"
        evidence_deal_id = min(normalized, key=lambda deal_id: (amounts_mxn[deal_id] != candidate_mrr, deal_id))

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
        for deal_id in annualized_deal_ids:
            corrections.append(
                Correction(
                    exception_code="mrr_deal_annualized",
                    source_system="crm_hubspot",
                    source_id=deal_id,
                    field_name="amount",
                    original_value=format_money(amounts_mxn[deal_id]),
                    applied_value=format_money(min_amount),
                    evidence_ref=hubspot_id,
                )
            )

    return result, corrections
