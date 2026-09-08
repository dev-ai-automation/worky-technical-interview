"""master_id determinista e idempotente, segun la seccion 3.6 del diseno."""

from __future__ import annotations

import hashlib
from typing import Any

MASTER_ID_LENGTH = 12


def compute_master_id(domain_label: str, normalized_name: str) -> str:
    """sha256(domain_label|normalized_name), truncado a 12 caracteres hex.

    La barra vertical es parte de la llave para que el par `("ab", "c")`
    y el par `("a", "bc")` nunca produzcan el mismo id.
    """
    key = f"{domain_label}|{normalized_name}".encode("utf-8")
    return hashlib.sha256(key).hexdigest()[:MASTER_ID_LENGTH]


def resolve_master_id(
    hubspot_id: str,
    domain_label: str,
    normalized_name: str,
    existing_master_id_by_hubspot: dict[str, str],
) -> str:
    """Reutiliza el master_id ya asignado en el crosswalk, o genera uno nuevo."""
    existing = existing_master_id_by_hubspot.get(hubspot_id)
    if existing:
        return existing
    return compute_master_id(domain_label, normalized_name)


class IdentityCollisionError(ValueError):
    """Dos ids de la misma fuente resolvieron al mismo master_id del crosswalk.

    El crosswalk guarda una sola fila por company (`account_id` y
    `vitally_id` son columnas escalares), asi que un segundo id que
    resuelva al mismo `master_id` no tiene donde escribirse sin borrar
    al primero; se aborta en vez de sobrescribir en silencio.
    """


def assert_unique_master_ids(companies: list[dict[str, Any]]) -> None:
    """Aborta con un mensaje claro si dos empresas distintas generan el mismo master_id.

    Dos empresas reales con el mismo dominio y el mismo nombre normalizado
    serian indistinguibles con la evidencia disponible; detener la corrida
    convierte una fusion silenciosa en una pregunta explicita, tal como
    fija la seccion 3.6 del diseno.
    """
    seen_hubspot_id_by_master_id: dict[str, str] = {}
    for company in companies:
        master_id = company["master_id"]
        hubspot_id = company["hubspot_id"]
        previous = seen_hubspot_id_by_master_id.get(master_id)
        if previous is not None and previous != hubspot_id:
            raise ValueError(
                f"colision de master_id entre {previous!r} y {hubspot_id!r}: "
                f"ambos producen {master_id!r}"
            )
        seen_hubspot_id_by_master_id[master_id] = hubspot_id
