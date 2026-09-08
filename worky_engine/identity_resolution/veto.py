"""Regla de veto del ADR-001, segun la seccion 3.4 del diseno.

Protege el caso donde dos empresas reales comparten dominio: si ademas
son poco similares en nombre, tienen fechas de alta distintas y ambas
cobran MRR, el sistema las trata como empresas distintas de forma
explicita, en lugar de dejar que la coincidencia de dominio las
confunda con una sola. El ADR-001 dice "similitud de nombre por debajo
de 70" sin nombrar la metrica; este modulo supone `token_set_ratio`, la
misma que usa T1, para que el veto y el nivel que anula se midan con la
misma vara.
"""

from __future__ import annotations

VETO_REASON = "shared_domain_distinct_company"
NAME_SIMILARITY_THRESHOLD = 70


def is_vetoed_pair(
    *,
    domain_shared: bool,
    name_similarity: float,
    signup_date_a: str | None,
    signup_date_b: str | None,
    mrr_a: float | None,
    mrr_b: float | None,
) -> bool:
    """True cuando las cuatro condiciones del veto se cumplen a la vez."""
    return (
        domain_shared
        and name_similarity < NAME_SIMILARITY_THRESHOLD
        and signup_date_a != signup_date_b
        and mrr_a is not None
        and mrr_b is not None
    )
