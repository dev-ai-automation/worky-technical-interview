"""Pruebas del algoritmo de SCD2 de `dim_company` y de la foto de `fact_health_score_monthly`
(PR3 de `a4-warehouse-model`, seccion 3 del diseno).

Fixture minimo propio, sin extender `tests/fixtures/mini_dataset.py`, misma forma que usa
`tests/test_identity_overrides.py` (companias mas tablas secundarias vacias pero con sus
columnas correctas). Cubre los escenarios de la tarea 3.5: "el archivo sobrevive a la
segunda corrida", "primera corrida abre una fila vigente por empresa", "corrida sin cambios
no agrega filas", "un cambio de plan cierra la fila anterior y abre una nueva", "una empresa
que desaparece de las fuentes conserva su fila", "cada corrida de health agrega un
snapshot", "snapshot idempotente para la misma fecha", mas el caso de tipo 1 (un atributo no
rastreado cambia sin abrir banda) y el reemplazo de banda del mismo dia, ambos de la seccion
3 del diseno.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset
from worky_engine.warehouse import WarehouseResult, open_warehouse_connection, run_warehouse


def _company(
    hubspot_id: str, name: str, domain: str, plan: str, csm_owner: str, signup_date: str, state: str = "CDMX"
) -> dict:
    return {
        "hubspot_id": hubspot_id, "name": name, "domain": domain, "segment": "SMB",
        "industry": "Retail", "mrr": 1000.0, "currency": "MXN", "signup_date": signup_date,
        "csm_owner": csm_owner, "plan": plan, "state": state, "churn_date": None,
    }


def _empty_secondary_tables() -> dict[str, pd.DataFrame]:
    """Las cinco tablas crudas que estas pruebas no ejercitan, vacias pero con sus columnas reales."""
    return {
        "raw_accounts": pd.DataFrame(columns=["account_id", "hubspot_id", "account_name", "created_at"]),
        "raw_customers": pd.DataFrame(columns=["vitally_id", "domain", "company_name", "csm_email"]),
        "raw_deals": pd.DataFrame(
            columns=["deal_id", "hubspot_id", "stage", "amount", "created_date", "close_date", "pipeline", "lead_source"]
        ),
        "raw_marketing_touches": pd.DataFrame(
            columns=["touch_id", "hubspot_id", "channel", "touch_date", "campaign"]
        ),
        "raw_product_usage": pd.DataFrame(
            columns=["account_id", "month", "active_users", "logins", "payroll_runs_completed", "features_used", "api_calls"]
        ),
        "raw_tickets": pd.DataFrame(
            columns=["ticket_id", "vitally_id", "created_date", "priority", "status", "category", "resolution_hours", "csat_score"]
        ),
    }


def _raw_tables(companies: list[dict]) -> dict[str, pd.DataFrame]:
    tables = _empty_secondary_tables()
    tables["raw_companies"] = pd.DataFrame(companies)
    return tables


def _identity_outputs(raw_tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)


def _master_id_for(crosswalk: pd.DataFrame, hubspot_id: str) -> str:
    return crosswalk.loc[crosswalk["hubspot_id"] == hubspot_id, "master_id"].iloc[0]


def _run(con, companies: list[dict], run_date: str) -> tuple[WarehouseResult, dict[str, pd.DataFrame]]:
    """Ensambla el fixture de `companies` sobre `con` y corre `run_warehouse` con `run_date`."""
    raw_tables = _raw_tables(companies)
    identity_outputs = _identity_outputs(raw_tables)
    assemble_master_dataset(con, raw_tables, identity_outputs)
    return run_warehouse(con, overrides=None, run_date=run_date), identity_outputs


def _run_raw(con, raw_tables: dict[str, pd.DataFrame], run_date: str) -> tuple[WarehouseResult, dict[str, pd.DataFrame]]:
    """Igual que `_run`, pero recibe `raw_tables` ya armado (con hechos), en vez de una lista de companies."""
    identity_outputs = _identity_outputs(raw_tables)
    assemble_master_dataset(con, raw_tables, identity_outputs)
    return run_warehouse(con, overrides=None, run_date=run_date), identity_outputs


def _raw_tables_con_hechos(plan: str) -> dict[str, pd.DataFrame]:
    """Una empresa mas un hecho de cada fuente antes de su primera banda y uno despues de un cambio de plan."""
    companies = [_company("HS-9301", "Rho SCD SA de CV", "rhoscd.com.mx", plan, "Ana", "2022-01-01")]
    tables = _raw_tables(companies)
    tables["raw_accounts"] = pd.DataFrame([{"account_id": "ACC-9301", "hubspot_id": "HS-9301", "account_name": "Rho", "created_at": "2022-01-01"}])
    tables["raw_customers"] = pd.DataFrame([{"vitally_id": "cus_9301", "domain": "rhoscd.com.mx", "company_name": "Rho SCD SA de CV", "csm_email": "ana@worky.mx"}])
    tables["raw_tickets"] = pd.DataFrame(
        [
            # Antes de la primera banda (2022-06-01): debe unirse con ella via join_effective_from.
            {"ticket_id": "TK-9301A", "vitally_id": "cus_9301", "created_date": "2021-01-01",
             "priority": "Urgent", "status": "closed", "category": "bug", "resolution_hours": 2, "csat_score": 4},
            # Despues del cambio de plan (2023-06-01): debe unirse con la segunda banda.
            {"ticket_id": "TK-9301B", "vitally_id": "cus_9301", "created_date": "2023-07-01",
             "priority": "Low", "status": "open", "category": "billing", "resolution_hours": None, "csat_score": None},
        ]
    )
    tables["raw_deals"] = pd.DataFrame([{"deal_id": "D-9301A", "hubspot_id": "HS-9301", "stage": "closedwon", "amount": 1000.0,
                                        "created_date": "2020-12-01", "close_date": "2021-01-15", "pipeline": "New Business", "lead_source": "Web"}])
    tables["raw_marketing_touches"] = pd.DataFrame(
        [{"touch_id": "MT-9301A", "hubspot_id": "HS-9301", "channel": "Organic", "touch_date": "2021-01-01", "campaign": "spring"}]
    )
    tables["raw_product_usage"] = pd.DataFrame([{"account_id": "ACC-9301", "month": "2021-01", "active_users": 5, "logins": 20,
                                                "payroll_runs_completed": 1, "features_used": 2, "api_calls": 100}])
    return tables


def test_el_archivo_sobrevive_a_la_segunda_corrida(tmp_path: Path) -> None:
    """El mismo `.duckdb` se reutiliza en una segunda conexion y conserva la fila cerrada de la primera."""
    db_path = tmp_path / "warehouse.duckdb"
    companies_v1 = [_company("HS-9201", "Alfa SCD SA de CV", "alfascd.com.mx", "Pro", "Ana", "2022-01-01")]

    con = open_warehouse_connection(db_path)
    _run(con, companies_v1, "2022-06-01")
    con.close()

    companies_v2 = [_company("HS-9201", "Alfa SCD SA de CV", "alfascd.com.mx", "Pro", "Carla", "2022-01-01")]
    con = open_warehouse_connection(db_path)
    try:
        _run(con, companies_v2, "2024-01-01")
        rows = con.execute("SELECT csm_owner, is_current FROM dim_company ORDER BY effective_from").df()
    finally:
        con.close()

    assert list(rows["csm_owner"]) == ["Ana", "Carla"]
    assert list(rows["is_current"]) == [False, True]


def test_primera_corrida_abre_una_fila_vigente_por_empresa(tmp_path: Path) -> None:
    companies = [
        _company("HS-9202", "Beta SCD SA de CV", "betascd.com.mx", "Pro", "Ana", "2022-01-01"),
        _company("HS-9203", "Gama SCD SA de CV", "gamascd.com.mx", "Basico", "Luis", "2022-02-01"),
    ]
    con = open_warehouse_connection(tmp_path / "warehouse.duckdb")
    try:
        result, _identity = _run(con, companies, "2022-06-01")
    finally:
        con.close()

    assert len(result.dim_company) == 2
    assert result.dim_company["is_current"].all()
    assert result.dim_company["effective_to"].isna().all()


def test_corrida_sin_cambios_no_agrega_filas(tmp_path: Path) -> None:
    companies = [_company("HS-9204", "Delta SCD SA de CV", "deltascd.com.mx", "Pro", "Ana", "2022-01-01")]
    con = open_warehouse_connection(tmp_path / "warehouse.duckdb")
    try:
        _run(con, companies, "2022-06-01")
        result, _identity = _run(con, companies, "2023-06-01")
    finally:
        con.close()

    assert len(result.dim_company) == 1
    assert bool(result.dim_company.iloc[0]["is_current"])


def test_cambio_de_plan_cierra_la_fila_anterior_y_abre_una_nueva(tmp_path: Path) -> None:
    companies_v1 = [_company("HS-9205", "Epsilon SCD SA de CV", "epsilonscd.com.mx", "Basico", "Ana", "2022-01-01")]
    companies_v2 = [_company("HS-9205", "Epsilon SCD SA de CV", "epsilonscd.com.mx", "Pro", "Ana", "2022-01-01")]
    con = open_warehouse_connection(tmp_path / "warehouse.duckdb")
    try:
        _run(con, companies_v1, "2022-06-01")
        result, identity = _run(con, companies_v2, "2023-06-01")
    finally:
        con.close()

    master_id = _master_id_for(identity["identity_crosswalk"], "HS-9205")
    rows = result.dim_company[result.dim_company["master_id"] == master_id].sort_values("effective_from")
    assert list(rows["plan"]) == ["Basico", "Pro"]
    assert list(rows["is_current"]) == [False, True]
    assert str(rows.iloc[0]["effective_to"])[:10] == "2023-06-01"
    assert pd.isna(rows.iloc[1]["effective_to"])


def test_empresa_que_desaparece_conserva_su_fila(tmp_path: Path) -> None:
    companies_v1 = [
        _company("HS-9206", "Zeta SCD SA de CV", "zetascd.com.mx", "Pro", "Ana", "2022-01-01"),
        _company("HS-9207", "Eta SCD SA de CV", "etascd.com.mx", "Basico", "Luis", "2022-02-01"),
    ]
    con = open_warehouse_connection(tmp_path / "warehouse.duckdb")
    try:
        _, identity_v1 = _run(con, companies_v1, "2022-06-01")
        master_id_9207 = _master_id_for(identity_v1["identity_crosswalk"], "HS-9207")

        companies_v2 = [companies_v1[0]]  # HS-9207 ya no llega en esta corrida
        result, _identity_v2 = _run(con, companies_v2, "2023-06-01")
    finally:
        con.close()

    row = result.dim_company[result.dim_company["master_id"] == master_id_9207].iloc[0]
    assert bool(row["is_current"])
    assert pd.isna(row["effective_to"])


def test_cada_corrida_de_health_agrega_un_snapshot(tmp_path: Path) -> None:
    companies = [_company("HS-9208", "Theta SCD SA de CV", "thetascd.com.mx", "Pro", "Ana", "2022-01-01")]
    con = open_warehouse_connection(tmp_path / "warehouse.duckdb")
    try:
        result1, _identity = _run(con, companies, "2022-06-01")
        result2, _identity = _run(con, companies, "2023-06-01")
    finally:
        con.close()

    assert len(result1.fact_health_score_monthly) == 1
    assert len(result2.fact_health_score_monthly) == 2
    run_dates = set(result2.fact_health_score_monthly["run_date"].astype(str).str[:10])
    assert run_dates == {"2022-06-01", "2023-06-01"}


def test_snapshot_idempotente_para_la_misma_fecha(tmp_path: Path) -> None:
    companies = [_company("HS-9209", "Iota SCD SA de CV", "iotascd.com.mx", "Pro", "Ana", "2022-01-01")]
    con = open_warehouse_connection(tmp_path / "warehouse.duckdb")
    try:
        _run(con, companies, "2022-06-01")
        result, _identity = _run(con, companies, "2022-06-01")
    finally:
        con.close()

    assert len(result.fact_health_score_monthly) == 1


def test_cambio_de_atributo_no_rastreado_actualiza_en_sitio(tmp_path: Path) -> None:
    """`state` no esta en la lista de atributos del SCD2 (D5): un cambio se sobrescribe en la
    misma fila (tipo 1), sin cerrar la banda ni abrir una nueva."""
    companies_v1 = [_company("HS-9210", "Kappa SCD SA de CV", "kappascd.com.mx", "Pro", "Ana", "2022-01-01", state="CDMX")]
    companies_v2 = [_company("HS-9210", "Kappa SCD SA de CV", "kappascd.com.mx", "Pro", "Ana", "2022-01-01", state="Jalisco")]
    con = open_warehouse_connection(tmp_path / "warehouse.duckdb")
    try:
        _run(con, companies_v1, "2022-06-01")
        result, identity = _run(con, companies_v2, "2023-06-01")
    finally:
        con.close()

    master_id = _master_id_for(identity["identity_crosswalk"], "HS-9210")
    rows = result.dim_company[result.dim_company["master_id"] == master_id]
    assert len(rows) == 1
    assert rows.iloc[0]["state"] == "Jalisco"
    assert bool(rows.iloc[0]["is_current"])
    assert pd.isna(rows.iloc[0]["effective_to"])


def test_llaves_no_dependen_del_orden_de_ejecucion(tmp_path: Path) -> None:
    """El mismo conjunto de empresas, en dos ordenes de fila distintos dentro de `raw_companies`,
    genera el mismo `company_sk` por empresa: el hash depende de `master_id` y `run_date` (D6),
    nunca de la posicion en la que DuckDB proceso la fila."""
    companies = [
        _company("HS-9212", "Mu SCD SA de CV", "muscd.com.mx", "Pro", "Ana", "2022-01-01"),
        _company("HS-9213", "Nu SCD SA de CV", "nuscd.com.mx", "Basico", "Luis", "2022-02-01"),
    ]

    con_a = open_warehouse_connection(tmp_path / "orden_a.duckdb")
    try:
        result_a, identity_a = _run(con_a, companies, "2022-06-01")
    finally:
        con_a.close()

    con_b = open_warehouse_connection(tmp_path / "orden_b.duckdb")
    try:
        result_b, identity_b = _run(con_b, list(reversed(companies)), "2022-06-01")
    finally:
        con_b.close()

    keys_a = result_a.dim_company.set_index("master_id")["company_sk"].to_dict()
    keys_b = result_b.dim_company.set_index("master_id")["company_sk"].to_dict()
    assert keys_a == keys_b
    assert len(keys_a) == 2


def test_reemplazo_de_banda_del_mismo_dia(tmp_path: Path) -> None:
    """Dos corridas con la misma `run_date` y un cambio real de por medio reemplazan la banda
    en vez de duplicarla (paso 1 del algoritmo, seccion 3 del diseno)."""
    companies_v1 = [_company("HS-9211", "Lambda SCD SA de CV", "lambdascd.com.mx", "Basico", "Ana", "2022-01-01")]
    companies_v2 = [_company("HS-9211", "Lambda SCD SA de CV", "lambdascd.com.mx", "Pro", "Ana", "2022-01-01")]
    con = open_warehouse_connection(tmp_path / "warehouse.duckdb")
    try:
        _run(con, companies_v1, "2022-06-01")
        result, identity = _run(con, companies_v2, "2022-06-01")
    finally:
        con.close()

    master_id = _master_id_for(identity["identity_crosswalk"], "HS-9211")
    rows = result.dim_company[result.dim_company["master_id"] == master_id]
    assert len(rows) == 1
    assert rows.iloc[0]["plan"] == "Pro"
    assert bool(rows.iloc[0]["is_current"])
    assert pd.isna(rows.iloc[0]["effective_to"])


def test_hecho_anterior_a_la_primera_banda_se_une_con_ella(tmp_path: Path) -> None:
    """La banda mas vieja se abre hacia atras (dim_company_open_bands): los hechos anteriores a ella se unen
    con ella y los posteriores a un cambio real de plan con la banda nueva; sin el CASE quedarian en cero."""
    con = open_warehouse_connection(tmp_path / "warehouse.duckdb")
    try:
        raw_v1 = _raw_tables_con_hechos("Basico")
        _result1, identity = _run_raw(con, raw_v1, "2022-06-01")

        raw_v2 = _raw_tables_con_hechos("Pro")
        _run_raw(con, raw_v2, "2023-06-01")

        master_id = _master_id_for(identity["identity_crosswalk"], "HS-9301")
        bands = con.execute(
            "SELECT company_sk FROM dim_company WHERE master_id = ? ORDER BY effective_from", [master_id]
        ).df()["company_sk"].tolist()
        band1_sk, band2_sk = bands  # exactamente dos bandas: la original y la abierta por el cambio de plan

        tickets = con.execute("SELECT ticket_id, company_sk FROM fact_support_tickets ORDER BY ticket_id").df()
        assert tickets["ticket_id"].is_unique
        assert tickets.set_index("ticket_id")["company_sk"].to_dict() == {"TK-9301A": band1_sk, "TK-9301B": band2_sk}

        deals = con.execute("SELECT deal_id, company_sk FROM fact_deals").df()
        assert deals.set_index("deal_id")["company_sk"].to_dict() == {"D-9301A": band1_sk}

        touches = con.execute("SELECT touch_id, company_sk FROM fact_marketing_touches").df()
        assert touches.set_index("touch_id")["company_sk"].to_dict() == {"MT-9301A": band1_sk}

        usage = con.execute("SELECT month, company_sk FROM fact_usage_monthly").df()
        assert usage.set_index("month")["company_sk"].to_dict() == {"2021-01": band1_sk}

        revenue = con.execute("SELECT revenue_month, company_sk FROM fact_revenue_monthly").df()
        assert revenue.set_index("revenue_month")["company_sk"].to_dict() == {"2021-01": band1_sk}
    finally:
        con.close()
