"""Reglas de blocking del ADR-001, segun la seccion 3.3 del diseno.

Cada funcion limita con que candidatos se compara un registro antes de
calcular puntajes. A 650 por 650 comparaciones el costo es trivial, asi
que el blocking existe sobre todo para dejar escrita la evidencia que
justifica cada vinculo, y de paso mantiene el trabajo pequeno.
"""

from __future__ import annotations

from typing import Any


def index_by(records: list[dict[str, Any]], key: str) -> dict[Any, list[dict[str, Any]]]:
    """Agrupa `records` por el valor de `key`, ignorando los valores nulos."""
    index: dict[Any, list[dict[str, Any]]] = {}
    for record in records:
        value = record.get(key)
        if value is None:
            continue
        index.setdefault(value, []).append(record)
    return index


def index_by_hubspot_id(companies: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Bloque de T0: igualdad exacta de `hubspot_id` contra companies ya deduplicada."""
    return {company["hubspot_id"]: company for company in companies if company.get("hubspot_id")}


def index_by_domain(companies: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Bloque de T1: igualdad exacta de la etiqueta de dominio registrable."""
    return index_by(companies, "domain_label")


def index_by_signup_date(companies: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Bloque de T2: `accounts.created_at` igual a `companies.signup_date`."""
    return index_by(companies, "signup_date")
