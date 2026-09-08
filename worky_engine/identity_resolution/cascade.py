"""Cascada T0 a T3 con revision manual, y ensamblaje de las cuatro salidas de identidad.

`resolve_identity` es la unica funcion de todo el paquete
`identity_resolution` que importa pandas: convierte las tablas crudas en
listas de diccionarios para que `blocking.py`, `scoring.py`, `veto.py`,
`keys.py` y `quarantine.py` se queden puros, deterministas y faciles de
probar sin pandas, y vuelve a armar DataFrames solo al final para las
cuatro salidas de este PR. Esta es la decision de "modulos pequenos, sin
pandas salvo en la capa que arma las tablas de salida" que documenta el
diseno.
"""

from __future__ import annotations

import calendar
import itertools
import json
import math
from typing import Any

import pandas as pd

from worky_engine.identity_resolution import blocking, keys, quarantine, scoring, veto
from worky_engine.normalization import domain_label, normalize_company_name, normalize_date
from worky_engine.writers import format_money

RULESET_VERSION = "1.0.0"
DECIDED_BY = "worky_engine"
TIER_STRENGTH = {"T0": 0, "T1": 1, "T2": 2, "T3": 3}


def compute_dataset_asof(raw_tables: dict[str, pd.DataFrame]) -> str:
    """La fecha maxima presente en los datos, segun la seccion 7 del diseno.

    Considera `companies.signup_date`, `companies.churn_date`,
    `deals.created_date`, `deals.close_date`, `tickets.created_date` y el
    ultimo dia del ultimo mes de `product_usage`.
    """
    dates: list[str] = []
    date_sources = (
        ("raw_companies", "signup_date"),
        ("raw_companies", "churn_date"),
        ("raw_deals", "created_date"),
        ("raw_deals", "close_date"),
        ("raw_tickets", "created_date"),
    )
    for table_name, column in date_sources:
        frame = raw_tables.get(table_name)
        if frame is None or column not in frame.columns:
            continue
        for raw_value in frame[column].dropna():
            normalized = normalize_date(str(raw_value))
            if normalized:
                dates.append(normalized)

    usage = raw_tables.get("raw_product_usage")
    if usage is not None and not usage.empty:
        last_month = str(usage["month"].max())
        dates.append(_last_day_of_month(last_month))

    if not dates:
        raise ValueError("no se encontro ninguna fecha valida para calcular dataset_asof")
    return max(dates)


def _last_day_of_month(year_month: str) -> str:
    year, month = (int(part) for part in year_month.split("-"))
    last_day = calendar.monthrange(year, month)[1]
    return f"{year_month}-{last_day:02d}"


def resolve_identity(
    raw_tables: dict[str, pd.DataFrame],
    existing_crosswalk: pd.DataFrame | None,
    reuse_crosswalk: bool = True,
) -> dict[str, pd.DataFrame]:
    """Corre la cascada T0 a T3 sobre las tres fuentes y arma las cuatro salidas de este PR."""
    decided_at = compute_dataset_asof(raw_tables)

    companies = _prepare_companies(raw_tables["raw_companies"])
    all_company_hubspot_ids = {company["hubspot_id"] for company in companies}
    accounts = _clean_records(raw_tables["raw_accounts"].to_dict("records"))
    customers = _clean_records(raw_tables["raw_customers"].to_dict("records"))
    deals = _clean_records(raw_tables["raw_deals"].to_dict("records"))
    for deal in deals:
        deal["created_date"] = normalize_date(deal.get("created_date"))
        deal["close_date"] = normalize_date(deal.get("close_date"))

    referenced_ids = {row["hubspot_id"] for row in accounts if row.get("hubspot_id")}
    survivors, clone_rows = quarantine.deduplicate_companies(companies, referenced_ids)

    existing_lookup = (
        _crosswalk_lookup(existing_crosswalk)
        if reuse_crosswalk and existing_crosswalk is not None
        else {}
    )
    for company in survivors:
        company["master_id"] = keys.resolve_master_id(
            company["hubspot_id"], company["domain_label"], company["name_norm"], existing_lookup
        )
    keys.assert_unique_master_ids(survivors)

    survivor_master_id_by_hubspot = {c["hubspot_id"]: c["master_id"] for c in survivors}
    for row in clone_rows:
        row["survivor_master_id"] = survivor_master_id_by_hubspot[row["survivor_hubspot_id"]]
        row["decided_at"] = decided_at

    vetoed_ids = _detect_domain_veto_pairs(survivors)

    audit_rows: list[dict[str, Any]] = []
    crosswalk_rows: dict[str, dict[str, Any]] = {}
    for company in survivors:
        audit_rows.append(
            _company_audit_row(company, decided_at, company["hubspot_id"] in vetoed_ids)
        )
        crosswalk_rows[company["master_id"]] = {
            "master_id": company["master_id"],
            "hubspot_id": company["hubspot_id"],
            "account_id": None,
            "vitally_id": None,
            "account_match_tier": None,
            "vitally_match_tier": None,
            "resolved_at": decided_at,
        }
    for row in clone_rows:
        audit_rows.append(
            _decision(
                "crm_hubspot", row["hubspot_id"], None, "Q", "none", 1,
                None, None, None, row["evidence"], decided_at,
            )
        )

    companies_by_hubspot = blocking.index_by_hubspot_id(survivors)
    companies_by_domain = blocking.index_by_domain(survivors)
    companies_by_signup = blocking.index_by_signup_date(survivors)

    for account in accounts:
        decision = _resolve_account(account, companies_by_hubspot, companies_by_signup, survivors, decided_at)
        audit_rows.append(decision)
        if decision["master_id"]:
            entry = crosswalk_rows[decision["master_id"]]
            entry["account_id"] = account["account_id"]
            entry["account_match_tier"] = decision["tier"]

    for customer in customers:
        decision = _resolve_customer(customer, companies_by_domain, survivors, decided_at)
        audit_rows.append(decision)
        if decision["master_id"]:
            entry = crosswalk_rows[decision["master_id"]]
            entry["vitally_id"] = customer["vitally_id"]
            entry["vitally_match_tier"] = decision["tier"]

    quarantine_deal_rows = quarantine.quarantine_orphan_deals(deals, all_company_hubspot_ids)
    for row in quarantine_deal_rows:
        row["decided_at"] = decided_at

    return {
        "identity_crosswalk": _to_identity_crosswalk_frame(crosswalk_rows),
        "match_audit": _to_match_audit_frame(audit_rows),
        "quarantine_companies": _to_quarantine_companies_frame(clone_rows),
        "quarantine_deals": _to_quarantine_deals_frame(quarantine_deal_rows),
    }


def _resolve_account(
    account: dict[str, Any],
    companies_by_hubspot: dict[str, dict[str, Any]],
    companies_by_signup: dict[str, list[dict[str, Any]]],
    all_companies: list[dict[str, Any]],
    decided_at: str,
) -> dict[str, Any]:
    """T0 por `hubspot_id`, T2 por bloque de fecha, y el resguardo global T3/M."""
    account_id = account["account_id"]
    hubspot_id = account.get("hubspot_id")
    account_norm = normalize_company_name(account.get("account_name"))
    created_at = normalize_date(account.get("created_at"))

    if hubspot_id and hubspot_id in companies_by_hubspot:
        company = companies_by_hubspot[hubspot_id]
        return _decision(
            "product_db", account_id, company, "T0", "hubspot_id", 1,
            None, None, None, {"hubspot_id": hubspot_id}, decided_at,
        )

    date_candidates = companies_by_signup.get(created_at, [])
    scored = sorted(
        ((c, scoring.partial_ratio(account_norm, c["name_norm"])) for c in date_candidates),
        key=lambda item: -item[1],
    )
    passing = [item for item in scored if item[1] >= 90]
    if len(passing) == 1:
        company, score = passing[0]
        evidence = {"created_at": created_at, "name_norm": account_norm, "partial_ratio": score}
        return _decision(
            "product_db", account_id, company, "T2", "signup_date", len(date_candidates),
            score, None, None, evidence, decided_at,
        )

    return _global_fallback(
        "product_db", account_id, account_norm, all_companies, decided_at,
        len(date_candidates), "signup_date",
    )


def _resolve_customer(
    customer: dict[str, Any],
    companies_by_domain: dict[str, list[dict[str, Any]]],
    all_companies: list[dict[str, Any]],
    decided_at: str,
) -> dict[str, Any]:
    """T1 por dominio compartido, y el resguardo global T3/M."""
    vitally_id = customer["vitally_id"]
    customer_norm = normalize_company_name(customer.get("company_name"))
    label = domain_label(customer.get("domain"))
    candidates = companies_by_domain.get(label, [])
    scored = sorted(
        ((c, scoring.token_set_ratio(customer_norm, c["name_norm"])) for c in candidates),
        key=lambda item: -item[1],
    )
    passing = [item for item in scored if item[1] >= 90]
    if len(passing) == 1:
        company, score = passing[0]
        evidence = {"domain_label": label, "name_norm": customer_norm, "token_set_ratio": score}
        return _decision(
            "vitally", vitally_id, company, "T1", "domain_label", len(candidates),
            score, None, None, evidence, decided_at,
        )

    return _global_fallback(
        "vitally", vitally_id, customer_norm, all_companies, decided_at,
        len(candidates), "domain_label",
    )


def _global_fallback(
    source_system: str,
    source_id: str,
    name_norm: str,
    all_companies: list[dict[str, Any]],
    decided_at: str,
    blocked_candidate_count: int,
    blocked_rule: str,
) -> dict[str, Any]:
    """T3 por `WRatio` global con margen, o M cuando ni eso resuelve un unico candidato."""
    scored = sorted(
        ((c, scoring.weighted_ratio(name_norm, c["name_norm"])) for c in all_companies),
        key=lambda item: -item[1],
    )
    top_company, top_score = scored[0]
    runner_up_score = scored[1][1] if len(scored) > 1 else 0.0
    margin = top_score - runner_up_score

    if top_score >= 94 and margin >= 10:
        evidence = {"name_norm": name_norm, "wratio": top_score}
        return _decision(
            source_system, source_id, top_company, "T3", "global", len(all_companies),
            top_score, runner_up_score, margin, evidence, decided_at,
        )

    candidate_count = blocked_candidate_count if blocked_candidate_count else len(all_companies)
    rule = blocked_rule if blocked_candidate_count else "global"
    evidence = {
        "name_norm": name_norm,
        "wratio": top_score,
        "wratio_runner_up": runner_up_score,
        "blocked_candidate_count": blocked_candidate_count,
    }
    return _decision(
        source_system, source_id, None, "M", rule, candidate_count,
        top_score, runner_up_score, margin, evidence, decided_at, needs_review=True,
    )


def _company_audit_row(company: dict[str, Any], decided_at: str, vetoed: bool) -> dict[str, Any]:
    """Fila `tier = 'S'` del propio registro dorado, con el veto ya evaluado."""
    evidence = {"domain_label": company["domain_label"], "name_norm": company["name_norm"]}
    return _decision(
        "crm_hubspot", company["hubspot_id"], company, "S", "none", 1,
        None, None, None, evidence, decided_at,
        veto_applied=vetoed, veto_reason=veto.VETO_REASON if vetoed else None,
    )


def _detect_domain_veto_pairs(companies: list[dict[str, Any]]) -> set[str]:
    """Ids de empresas que comparten dominio con otra y cumplen las cuatro condiciones del veto.

    Se evalua antes de aceptar cualquier vinculo T1 sobre ese dominio,
    segun la seccion 3.4 del diseno.
    """
    vetoed: set[str] = set()
    for group in blocking.index_by_domain(companies).values():
        if len(group) < 2:
            continue
        for company_a, company_b in itertools.combinations(group, 2):
            score = scoring.token_set_ratio(company_a["name_norm"], company_b["name_norm"])
            if veto.is_vetoed_pair(
                domain_shared=True,
                name_similarity=score,
                signup_date_a=company_a["signup_date"],
                signup_date_b=company_b["signup_date"],
                mrr_a=company_a.get("mrr"),
                mrr_b=company_b.get("mrr"),
            ):
                vetoed.add(company_a["hubspot_id"])
                vetoed.add(company_b["hubspot_id"])
    return vetoed


def _decision(
    source_system: str,
    source_id: str,
    company: dict[str, Any] | None,
    tier: str,
    blocking_rule: str,
    candidate_count: int,
    score: float | None,
    score_runner_up: float | None,
    score_margin: float | None,
    evidence: dict[str, Any],
    decided_at: str,
    *,
    veto_applied: bool = False,
    veto_reason: str | None = None,
    needs_review: bool = False,
) -> dict[str, Any]:
    """Una fila de `match_audit`, con el `evidence_json` ya serializado de forma determinista."""
    return {
        "source_system": source_system,
        "source_id": source_id,
        "master_id": company["master_id"] if company else None,
        "tier": tier,
        "score": score,
        "score_runner_up": score_runner_up,
        "score_margin": score_margin,
        "candidate_count": candidate_count,
        "blocking_rule": blocking_rule,
        "evidence_json": json.dumps(evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        "veto_applied": veto_applied,
        "veto_reason": veto_reason,
        "needs_review": needs_review,
        "ruleset_version": RULESET_VERSION,
        "decided_by": DECIDED_BY,
        "decided_at": decided_at,
    }


def _weakest_tier(*tiers: str | None) -> str | None:
    """El nivel mas debil entre los vinculos que forman una fila de crosswalk."""
    present = [tier for tier in tiers if tier]
    if not present:
        return None
    return max(present, key=lambda tier: TIER_STRENGTH[tier])


def _prepare_companies(companies_df: pd.DataFrame) -> list[dict[str, Any]]:
    records = _clean_records(companies_df.to_dict("records"))
    for row in records:
        row["signup_date"] = normalize_date(row.get("signup_date"))
        row["churn_date"] = normalize_date(row.get("churn_date"))
        row["name_norm"] = normalize_company_name(row.get("name"))
        row["domain_label"] = domain_label(row.get("domain"))
    return records


def _clean_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convierte cualquier NaN de pandas a None para que el resto del paquete solo revise `is None`."""
    cleaned: list[dict[str, Any]] = []
    for record in records:
        cleaned.append(
            {
                key: (None if isinstance(value, float) and math.isnan(value) else value)
                for key, value in record.items()
            }
        )
    return cleaned


def _crosswalk_lookup(existing_crosswalk: pd.DataFrame) -> dict[str, str]:
    return dict(zip(existing_crosswalk["hubspot_id"], existing_crosswalk["master_id"]))


def _to_identity_crosswalk_frame(crosswalk_rows: dict[str, dict[str, Any]]) -> pd.DataFrame:
    records = []
    for row in crosswalk_rows.values():
        records.append(
            {
                **row,
                "confidence_tier": _weakest_tier(row["account_match_tier"], row["vitally_match_tier"]),
                "ruleset_version": RULESET_VERSION,
            }
        )
    columns = [
        "master_id", "hubspot_id", "account_id", "vitally_id",
        "account_match_tier", "vitally_match_tier", "confidence_tier",
        "resolved_at", "ruleset_version",
    ]
    frame = pd.DataFrame(records, columns=columns)
    return frame.sort_values("master_id").reset_index(drop=True)


def _to_match_audit_frame(audit_rows: list[dict[str, Any]]) -> pd.DataFrame:
    columns = [
        "source_system", "source_id", "master_id", "tier", "score",
        "score_runner_up", "score_margin", "candidate_count", "blocking_rule",
        "evidence_json", "veto_applied", "veto_reason", "needs_review",
        "ruleset_version", "decided_by", "decided_at",
    ]
    frame = pd.DataFrame(audit_rows, columns=columns)
    for column in ("score", "score_runner_up", "score_margin"):
        # pandas convierte la columna a float64 cuando mezcla None con
        # numeros, y ese None se vuelve NaN; format_money solo reconoce
        # None, asi que hay que revertir el NaN antes de formatear.
        frame[column] = frame[column].apply(lambda value: format_money(None if pd.isna(value) else value))
    return frame.sort_values(["source_system", "source_id"]).reset_index(drop=True)


_QUARANTINE_COMPANIES_COLUMNS = [
    "hubspot_id", "company_name", "domain", "mrr", "currency", "signup_date",
    "churn_date", "reason_code", "survivor_hubspot_id", "survivor_master_id",
    "evidence_json", "ruleset_version", "decided_at",
]

_QUARANTINE_DEALS_COLUMNS = [
    "deal_id", "hubspot_id", "stage", "amount", "created_date", "close_date",
    "pipeline", "lead_source", "reason_code", "ruleset_version", "decided_at",
]


def _to_quarantine_companies_frame(clone_rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Siempre entrega las 13 columnas del contrato, con cero filas si no hay clones.

    Un `pd.DataFrame([])` sin columnas rechaza el `con.register()` de
    DuckDB ("Need a DataFrame with at least one column") en cuanto no
    hay ningun clon: hallazgo del PR 4a, tarea 4.15. El esquema fijo
    evita ese caso sin depender de que siempre haya al menos una fila.
    """
    if not clone_rows:
        return pd.DataFrame(columns=_QUARANTINE_COMPANIES_COLUMNS)
    records = []
    for row in clone_rows:
        records.append(
            {
                "hubspot_id": row["hubspot_id"],
                "company_name": row["company_name"],
                "domain": row["domain"],
                "mrr": format_money(row["mrr"]),
                "currency": row["currency"],
                "signup_date": row["signup_date"],
                "churn_date": row["churn_date"],
                "reason_code": row["reason_code"],
                "survivor_hubspot_id": row["survivor_hubspot_id"],
                "survivor_master_id": row["survivor_master_id"],
                "evidence_json": json.dumps(
                    row["evidence"], sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ),
                "ruleset_version": RULESET_VERSION,
                "decided_at": row["decided_at"],
            }
        )
    frame = pd.DataFrame(records, columns=_QUARANTINE_COMPANIES_COLUMNS)
    return frame.sort_values("hubspot_id").reset_index(drop=True)


def _to_quarantine_deals_frame(orphan_rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Siempre entrega las 11 columnas del contrato, con cero filas si no hay huerfanos (tarea 4.15)."""
    if not orphan_rows:
        return pd.DataFrame(columns=_QUARANTINE_DEALS_COLUMNS)
    records = []
    for row in orphan_rows:
        records.append(
            {
                "deal_id": row["deal_id"],
                "hubspot_id": row["hubspot_id"],
                "stage": row["stage"],
                "amount": format_money(row["amount"]),
                "created_date": row["created_date"],
                "close_date": row["close_date"],
                "pipeline": row["pipeline"],
                "lead_source": row["lead_source"],
                "reason_code": row["reason_code"],
                "ruleset_version": RULESET_VERSION,
                "decided_at": row["decided_at"],
            }
        )
    frame = pd.DataFrame(records, columns=_QUARANTINE_DEALS_COLUMNS)
    return frame.sort_values("deal_id").reset_index(drop=True)
