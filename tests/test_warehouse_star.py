"""Pruebas de `worky_engine.warehouse` y `cmd_warehouse` (PR2 de `a4-warehouse-model`).

Fixture minimo propio (tres empresas, un producto con dos meses de uso
y cuatro deals), la misma forma que usa
`tests/test_support_commercial.py`, sin extender
`tests/fixtures/mini_dataset.py`. Cubre los escenarios de PR2 de la
tarea 2.10: "corrida sin build previo", "falta una dependencia o una
base de datos", "dimensiones derivadas sin duplicar logica", "hechos
al grano correcto", "marts y staging sin cambios", "agregacion por mes
de cierre", "no es una serie de mrr_mxn", "un hecho se une contra la
version vigente en su fecha", "dos hechos de fechas distintas ven CSM
distinto", "tabla con las columnas del contrato" y "override reflejado
en map_source_identity".

`dim_company` todavia no la puebla ningun algoritmo (el SCD2 llega en
el PR3): las pruebas que necesitan una banda de vigencia la siembran a
mano, directo sobre la tabla vacia que ya crea `run_warehouse`, para
ejercitar el JOIN historico de `w5_facts.sql` sin depender de ese
algoritmo todavia ausente.

`fact_support_tickets` y `fact_marketing_touches` se restauraron
despues del cierre original de este PR (decision del usuario, con
`size:exception` aceptado; ver apply-progress.md de este PR). El
fixture trae dos tickets del mismo `vitally_id` y dos touches del
mismo `hubspot_id`, uno de cada par antes del corte de banda de
`dim_company` (2024-06-01) y otro despues, para reusar el mismo patron
de "dos hechos de fechas distintas ven CSM distinto" que ya cubre
`fact_deals`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from worky_engine.cli import main as cli_main
from worky_engine.identity_resolution import resolve_identity
from worky_engine.identity_resolution.overrides import apply_overrides, load_overrides
from worky_engine.master_dataset import assemble_master_dataset
from worky_engine.warehouse import open_warehouse_connection, run_warehouse

REPO_ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = REPO_ROOT / "worky_engine" / "sql"


def _company(hubspot_id: str, name: str, domain: str, plan: str, csm_owner: str, signup_date: str) -> dict:
    return {
        "hubspot_id": hubspot_id, "name": name, "domain": domain, "segment": "SMB",
        "industry": "Retail", "mrr": 1500.0, "currency": "MXN", "signup_date": signup_date,
        "csm_owner": csm_owner, "plan": plan, "state": "CDMX", "churn_date": None,
    }


def _raw_tables() -> dict[str, pd.DataFrame]:
    companies = [
        _company("HS-8001", "Alfa Warehouse SA de CV", "alfa800.com.mx", "Pro", "Ana", "2022-01-01"),
        _company("HS-8002", "Beta Warehouse SA de CV", "beta800.com.mx", "Basico", "Luis", "2022-02-01"),
        # Mismo plan y csm_owner que HS-8001: dim_plan y dim_csm deben
        # reportar dos valores distintos, no tres, aunque haya tres empresas.
        _company("HS-8003", "Gama Warehouse SA de CV", "gama800.com.mx", "Pro", "Ana", "2022-03-01"),
    ]
    accounts = [
        {"account_id": "ACC-8001", "hubspot_id": "HS-8001", "account_name": "Alfa Warehouse", "created_at": "2022-01-01"},
        # Sin hubspot_id y sin nombre parecido a ninguna empresa: cae en
        # revision manual (tier M), el punto de partida del override.
        {"account_id": "ACC-8004", "hubspot_id": None, "account_name": "Consultoria Ajena Total", "created_at": "2023-06-01"},
    ]
    customers = [
        {"vitally_id": "cus_8001", "domain": "alfa800.com.mx", "company_name": "Alfa Warehouse SA de CV", "csm_email": "ana@worky.mx"},
    ]
    usage = [
        {"account_id": "ACC-8001", "month": "2024-01", "active_users": 10, "logins": 40,
         "payroll_runs_completed": 1, "features_used": 3, "api_calls": 500},
        {"account_id": "ACC-8001", "month": "2024-02", "active_users": 12, "logins": 44,
         "payroll_runs_completed": 1, "features_used": 3, "api_calls": 520},
    ]
    deals = [
        # Dos deals closedwon en el mismo mes (2024-05), antes del cambio
        # de CSM sembrado en dim_company (2024-06-01): caen en la banda
        # 'Ana' y fact_revenue_monthly debe sumarlos en una sola fila.
        {"deal_id": "D-8001A", "hubspot_id": "HS-8001", "stage": "closedwon", "amount": 1000.0,
         "created_date": "2024-04-01", "close_date": "2024-05-15", "pipeline": "New Business", "lead_source": "Web"},
        {"deal_id": "D-8001B", "hubspot_id": "HS-8001", "stage": "closedwon", "amount": 2000.0,
         "created_date": "2024-04-10", "close_date": "2024-05-20", "pipeline": "New Business", "lead_source": "Web"},
        # Un tercer deal closedwon en 2024-06, ya dentro de la banda
        # 'Carla': fila aparte, no se suma con la de mayo.
        {"deal_id": "D-8001C", "hubspot_id": "HS-8001", "stage": "closedwon", "amount": 500.0,
         "created_date": "2024-05-01", "close_date": "2024-06-10", "pipeline": "Renewal", "lead_source": "Web"},
        # Deal abierto: nunca debe entrar a fact_revenue_monthly ni a
        # fact_deals via el grano cerrado (queda en fact_deals, pero no
        # aporta a la agregacion de revenue).
        {"deal_id": "D-8001D", "hubspot_id": "HS-8001", "stage": "qualifiedtobuy", "amount": 999.0,
         "created_date": "2024-06-01", "close_date": None, "pipeline": "New Business", "lead_source": "Web"},
    ]
    return {
        "raw_companies": pd.DataFrame(companies),
        "raw_accounts": pd.DataFrame(accounts),
        "raw_customers": pd.DataFrame(customers),
        "raw_product_usage": pd.DataFrame(usage),
        "raw_tickets": pd.DataFrame(
            [
                # Antes del corte de banda (2024-06-01): cae en 'Ana'.
                {"ticket_id": "TK-8001A", "vitally_id": "cus_8001", "created_date": "2023-05-01",
                 "priority": "Urgent", "status": "closed", "category": "bug", "resolution_hours": 2, "csat_score": 4},
                # Despues del corte: cae en 'Carla'.
                {"ticket_id": "TK-8001B", "vitally_id": "cus_8001", "created_date": "2024-07-01",
                 "priority": "Low", "status": "open", "category": "billing", "resolution_hours": None, "csat_score": None},
            ]
        ),
        "raw_deals": pd.DataFrame(deals),
        "raw_marketing_touches": pd.DataFrame(
            [
                {"touch_id": "MT-8001A", "hubspot_id": "HS-8001", "channel": "Organic",
                 "touch_date": "2023-05-01", "campaign": "spring"},
                {"touch_id": "MT-8001B", "hubspot_id": "HS-8001", "channel": "Paid Search",
                 "touch_date": "2024-07-01", "campaign": "summer"},
            ]
        ),
    }


def _identity_outputs(raw_tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    return resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)


def _master_id_for(crosswalk: pd.DataFrame, hubspot_id: str) -> str:
    return crosswalk.loc[crosswalk["hubspot_id"] == hubspot_id, "master_id"].iloc[0]


def _open_assembled_connection(
    tmp_path: Path, raw_tables: dict[str, pd.DataFrame], identity_outputs: dict[str, pd.DataFrame]
) -> duckdb.DuckDBPyConnection:
    """Abre una conexion de warehouse y corre el ensamblaje de A0, igual que hace `cmd_warehouse`."""
    con = open_warehouse_connection(tmp_path / "warehouse.duckdb")
    assemble_master_dataset(con, raw_tables, identity_outputs)
    return con


def _seed_dim_company_bands(con: duckdb.DuckDBPyConnection, master_id: str) -> None:
    """Siembra a mano dos bandas de vigencia para `master_id`, simulando lo que hara el SCD2 del PR3.

    Banda 1 ('Ana'): 2022-01-01 a 2024-06-01 (exclusivo). Banda 2
    ('Carla'), vigente: desde 2024-06-01, sin cierre. `run_warehouse`
    ya debe haber corrido antes (crea la tabla vacia); esta funcion solo
    inserta filas encima, con las columnas que las pruebas necesitan.
    """
    con.execute(
        "INSERT INTO dim_company (company_sk, master_id, csm_owner, effective_from, effective_to, is_current) "
        "VALUES ('CSK-8001-B1', ?, 'Ana', DATE '2022-01-01', DATE '2024-06-01', false), "
        "('CSK-8001-B2', ?, 'Carla', DATE '2024-06-01', NULL, true)",
        [master_id, master_id],
    )


@pytest.fixture()
def warehouse_setup(tmp_path: Path):
    """Ensambla el fixture, corre `run_warehouse` y siembra las dos bandas de `dim_company`."""
    raw_tables = _raw_tables()
    identity_outputs = _identity_outputs(raw_tables)
    con = _open_assembled_connection(tmp_path, raw_tables, identity_outputs)
    try:
        result = run_warehouse(con, overrides=None)
        master_id_8001 = _master_id_for(identity_outputs["identity_crosswalk"], "HS-8001")
        _seed_dim_company_bands(con, master_id_8001)
        yield con, identity_outputs, raw_tables, result, master_id_8001
    finally:
        con.close()


def test_corrida_sin_build_previo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Con un data-dir valido, `warehouse` termina en 0 y deja su `.duckdb` bajo `--db-path`, sin `build` antes."""
    raw_tables = _raw_tables()
    identity_outputs = _identity_outputs(raw_tables)
    out_dir = tmp_path / "out"
    db_path = tmp_path / "warehouse.duckdb"

    def _fake_load_raw_tables(_data_dir):
        return raw_tables

    def _fake_resolve_identity(_raw, existing_crosswalk=None, reuse_crosswalk=True):
        return identity_outputs

    monkeypatch.setattr("worky_engine.cli.load_raw_tables", _fake_load_raw_tables)
    monkeypatch.setattr("worky_engine.cli._resolve_data_dir", lambda data_dir: data_dir)
    monkeypatch.setattr("worky_engine.identity_resolution.resolve_identity", _fake_resolve_identity)

    exit_code = cli_main(
        ["warehouse", "--data-dir", str(tmp_path), "--out-dir", str(out_dir), "--db-path", str(db_path)]
    )
    assert exit_code == 0
    assert db_path.is_file()
    assert (out_dir / "map_source_identity.csv").is_file()


def test_falta_una_base_de_datos_termina_con_codigo_2(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Sin las tres bases SQLite en `--data-dir`, `warehouse` termina en 2 con un mensaje en espanol."""
    with pytest.raises(SystemExit) as exit_info:
        cli_main(
            [
                "warehouse",
                "--data-dir", str(tmp_path / "no-existe"),
                "--out-dir", str(tmp_path / "out"),
            ]
        )
    assert exit_info.value.code == 2
    assert "no se encontraron las tres bases SQLite" in capsys.readouterr().err


def test_dimensiones_derivadas_sin_duplicar_logica(warehouse_setup) -> None:
    con, *_ = warehouse_setup
    plans = con.execute("SELECT plan FROM dim_plan ORDER BY plan").df()["plan"].tolist()
    csms = con.execute("SELECT csm_owner FROM dim_csm ORDER BY csm_owner").df()["csm_owner"].tolist()
    assert plans == ["Basico", "Pro"]
    assert csms == ["Ana", "Luis"]


def test_hechos_al_grano_correcto(warehouse_setup) -> None:
    con, _identity, _raw, _result, master_id = warehouse_setup

    usage = con.execute(
        "SELECT * FROM fact_usage_monthly WHERE master_id = ? ORDER BY month", [master_id]
    ).df()
    assert list(usage["month"]) == ["2024-01", "2024-02"]

    deals = con.execute(
        "SELECT * FROM fact_deals WHERE master_id = ? ORDER BY deal_id", [master_id]
    ).df()
    # Los cuatro deals del fixture aportan una fila cada uno, incluido el
    # abierto: fact_deals es al grano de un deal, no solo de los cerrados.
    assert list(deals["deal_id"]) == ["D-8001A", "D-8001B", "D-8001C", "D-8001D"]


def test_fact_support_tickets_al_grano_correcto(warehouse_setup) -> None:
    """Cada ticket del fixture aparece exactamente una vez, atribuido a la misma empresa que mart_support."""
    con, _identity, raw, _result, master_id = warehouse_setup
    tickets = con.execute(
        "SELECT ticket_id, master_id FROM fact_support_tickets ORDER BY ticket_id"
    ).df()
    assert list(tickets["ticket_id"]) == ["TK-8001A", "TK-8001B"]
    assert tickets["ticket_id"].is_unique
    assert len(tickets) == len(raw["raw_tickets"])
    assert set(tickets["master_id"]) == {master_id}

    # El join a la empresa usa vitally_id, la misma llave que mart_support
    # (seccion 4.5 del diseno): el conteo debe coincidir con tickets_total.
    tickets_total = con.execute(
        "SELECT tickets_total FROM mart_support WHERE master_id = ?", [master_id]
    ).df()["tickets_total"].iloc[0]
    assert int(tickets_total) == len(tickets)


def test_fact_marketing_touches_al_grano_correcto(warehouse_setup) -> None:
    """Cada touch del fixture aparece exactamente una vez, con el master_id que ya resuelve stg_marketing_touches."""
    con, _identity, raw, _result, master_id = warehouse_setup
    touches = con.execute(
        "SELECT touch_id, master_id FROM fact_marketing_touches ORDER BY touch_id"
    ).df()
    assert list(touches["touch_id"]) == ["MT-8001A", "MT-8001B"]
    assert touches["touch_id"].is_unique
    assert len(touches) == len(raw["raw_marketing_touches"])
    assert set(touches["master_id"]) == {master_id}


def test_ticket_y_touch_de_fechas_distintas_ven_csm_distinto(warehouse_setup) -> None:
    """Mismo patron que test_dos_hechos_de_fechas_distintas_ven_csm_distinto, para los dos hechos restaurados."""
    con, _identity, _raw, _result, master_id = warehouse_setup
    tickets = con.execute(
        "SELECT f.ticket_id, d.csm_owner FROM fact_support_tickets f "
        "JOIN dim_company d ON d.company_sk = f.company_sk ORDER BY f.ticket_id"
    ).df()
    assert tickets.set_index("ticket_id")["csm_owner"].to_dict() == {
        "TK-8001A": "Ana", "TK-8001B": "Carla",
    }

    touches = con.execute(
        "SELECT f.touch_id, d.csm_owner FROM fact_marketing_touches f "
        "JOIN dim_company d ON d.company_sk = f.company_sk ORDER BY f.touch_id"
    ).df()
    assert touches.set_index("touch_id")["csm_owner"].to_dict() == {
        "MT-8001A": "Ana", "MT-8001B": "Carla",
    }


def test_marts_y_staging_sin_cambios(tmp_path: Path) -> None:
    """Ningun archivo de `sql/staging/` ni de `sql/marts/` cambia una linea al correr `warehouse`.

    Los hashes se toman antes de ensamblar y correr el warehouse, y se
    vuelven a tomar despues; la corrida ocurre en medio, dentro de la
    propia prueba, para que la comparacion pueda fallar de verdad.
    """
    staging_files = sorted((SQL_DIR / "staging").glob("*.sql"))
    mart_files = sorted((SQL_DIR / "marts").glob("*.sql"))
    assert staging_files, "se esperaban archivos de staging"
    assert mart_files, "se esperaban archivos de marts"
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in staging_files + mart_files}

    raw_tables = _raw_tables()
    identity_outputs = _identity_outputs(raw_tables)
    con = _open_assembled_connection(tmp_path, raw_tables, identity_outputs)
    try:
        result = run_warehouse(con, overrides=None)
    finally:
        con.close()
    assert result is not None

    after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in staging_files + mart_files}
    assert before == after


def test_agregacion_por_mes_de_cierre(warehouse_setup) -> None:
    con, _identity, _raw, _result, master_id = warehouse_setup
    revenue = con.execute(
        "SELECT revenue_month, revenue_mxn FROM fact_revenue_monthly WHERE master_id = ? ORDER BY revenue_month",
        [master_id],
    ).df()
    assert list(revenue["revenue_month"]) == ["2024-05", "2024-06"]
    assert float(revenue.loc[revenue["revenue_month"] == "2024-05", "revenue_mxn"].iloc[0]) == 3000.0
    assert float(revenue.loc[revenue["revenue_month"] == "2024-06", "revenue_mxn"].iloc[0]) == 500.0


def test_no_es_una_serie_de_mrr_mxn(warehouse_setup) -> None:
    """`fact_revenue_monthly` no repite `mrr_mxn`: son montos de deals cerrados, distintos mes a mes."""
    con, _identity, _raw, _result, master_id = warehouse_setup
    revenue = con.execute(
        "SELECT revenue_mxn FROM fact_revenue_monthly WHERE master_id = ? ORDER BY revenue_month", [master_id]
    ).df()["revenue_mxn"].tolist()
    assert revenue == [3000.0, 500.0]
    assert len(set(revenue)) > 1


def test_dos_hechos_de_fechas_distintas_ven_csm_distinto(warehouse_setup) -> None:
    """Cubre a la vez "un hecho se une contra la version vigente en su fecha" (D-8001A, banda 'Ana') y
    "dos hechos de fechas distintas ven CSM distinto" (banda 'Ana' antes del corte, 'Carla' despues)."""
    con, _identity, _raw, _result, master_id = warehouse_setup
    csms = con.execute(
        "SELECT f.deal_id, d.csm_owner FROM fact_deals f "
        "JOIN dim_company d ON d.company_sk = f.company_sk ORDER BY f.deal_id"
    ).df()
    assert csms.set_index("deal_id")["csm_owner"].to_dict() == {
        "D-8001A": "Ana", "D-8001B": "Ana", "D-8001C": "Carla", "D-8001D": "Carla",
    }


def test_tabla_con_las_columnas_del_contrato(warehouse_setup) -> None:
    con, *_ = warehouse_setup
    columns = con.execute("SELECT * FROM identity_overrides LIMIT 0").df().columns.tolist()
    assert columns == ["source_system", "source_id", "master_id", "decided_by", "decided_at", "reason"]


def test_override_reflejado_en_map_source_identity(tmp_path: Path) -> None:
    raw_tables = _raw_tables()
    identity_outputs = _identity_outputs(raw_tables)
    master_id = _master_id_for(identity_outputs["identity_crosswalk"], "HS-8002")

    overrides_path = tmp_path / "identity_overrides.csv"
    overrides_path.write_text(
        "source_system,source_id,master_id,decided_by,decided_at,reason\n"
        f"product_db,ACC-8004,{master_id},ana.reyes,2024-08-15,cuenta confirmada por el CSM\n",
        encoding="utf-8",
    )
    overrides = load_overrides(overrides_path)
    identity_outputs = apply_overrides(overrides, identity_outputs, raw_tables)

    con = _open_assembled_connection(tmp_path, raw_tables, identity_outputs)
    try:
        result = run_warehouse(con, overrides=overrides)
    finally:
        con.close()

    row = result.map_source_identity[
        (result.map_source_identity["source_system"] == "product_db")
        & (result.map_source_identity["source_id"] == "ACC-8004")
    ].iloc[0]
    assert row["link_source"] == "override"
    assert row["master_id"] == master_id
    assert row["decided_by"] == "ana.reyes"
