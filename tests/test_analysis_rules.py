"""Pruebas de fixture minimo para las consultas de A1 disponibles en este PR.

Construye su propio fixture, con la forma de `_minimal_raw_tables` de
`tests/test_support_commercial.py`, y no extiende
`tests/fixtures/mini_dataset.py` (decision del diseno, seccion 6):
agregar empresas ahi moveria los conteos que ya fijan las pruebas de
identidad y de imputacion. El fixture ejercita, a proposito: dos
empresas activas en segmentos distintos para A1.1; cuatro cuentas con
churn para A1.2 (mes de baja excluido, windows_overlap en una cuenta de
tres meses, drop_status 'no_usage' y 'final_window_empty'); un deal
huerfano mas un deal de un clon en cuarentena para A1.5; dos touches con
la misma fecha (empate por touch_id en los dos extremos) y un deal
creado antes del primer touch de su empresa para A1.4; una cohorte de
alta reciente que fuerza celdas censuradas mas el caso frontera de una
empresa que hace churn exactamente en el mes k para A1.3; y tres
tickets para A1.6, con resolution_hours negativo, positivo y nulo, para
comprobar que la vista de detalle solo lista el negativo.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worky_engine.analysis import run_analysis
from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset, open_connection
from worky_engine.quality.analysis_contracts import run_analysis_contracts

_EMPTY_CUSTOMERS = pd.DataFrame(columns=["vitally_id", "domain", "company_name", "csm_email"])


def _ticket(ticket_id: str, vitally_id: str, resolution_hours, status: str, csat_score=3.0) -> dict:
    return {
        "ticket_id": ticket_id, "vitally_id": vitally_id, "created_date": "2024-01-15",
        "priority": "medium", "status": status, "category": "billing",
        "resolution_hours": resolution_hours, "csat_score": csat_score,
    }


def _company(hubspot_id: str, name: str, domain: str, segment: str, industry: str, mrr, churn_date=None) -> dict:
    return {
        "hubspot_id": hubspot_id, "name": name, "domain": domain, "segment": segment,
        "industry": industry, "mrr": mrr, "currency": "MXN", "signup_date": "2022-01-01",
        "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": churn_date,
    }


def _touch(touch_id: str, hubspot_id: str, channel: str, touch_date: str) -> dict:
    return {"touch_id": touch_id, "hubspot_id": hubspot_id, "channel": channel, "touch_date": touch_date, "campaign": "camp"}


def _usage(account_id: str, month: str, active_users: int) -> dict:
    return {
        "account_id": account_id, "month": month, "active_users": active_users,
        "logins": active_users * 2, "payroll_runs_completed": 1, "features_used": 3, "api_calls": 100,
    }


def _minimal_raw_tables() -> dict[str, pd.DataFrame]:
    companies = [
        _company("HS-810001", "Activa Uno SA de CV", "activa810uno.com.mx", "SMB", "Retail", 1000.0),
        _company("HS-810002", "Activa Dos SA de CV", "activa810dos.com.mx", "Enterprise", "Tech", 5000.0),
        _company("HS-810003", "Superviviente SA de CV", "survivor810.com.mx", "SMB", "Retail", 300.0),
        # Clon del sobreviviente anterior: mismo nombre y dominio
        # normalizados, sin mrr y sin ningun account que lo referencie
        # (patron de tests/test_deal_remap_clone.py).
        {
            "hubspot_id": "HS-900081", "name": "SUPERVIVIENTE, S.A. DE C.V.", "domain": "survivor810.com.mx",
            "segment": "SMB", "industry": "Retail", "mrr": None, "currency": "MXN", "signup_date": "2022-01-01",
            "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": None,
        },
        # ACC-8110: 8 meses de uso, churn en 2024-08; el mes de baja trae
        # un pico de uso que debe quedar fuera de la ventana final.
        _company("HS-810010", "Excluye Mes Baja SA de CV", "excl810.com.mx", "SMB", "Retail", 1000.0, "2024-08-15"),
        # ACC-8111: exactamente 3 meses de uso; ventana inicial y final
        # comparten los mismos tres meses (windows_overlap).
        _company("HS-810011", "Ventana Tres SA de CV", "vtres810.com.mx", "SMB", "Retail", 1000.0, "2024-04-15"),
        # ACC-8112: sin ninguna fila de uso -> drop_status = 'no_usage'.
        _company("HS-810012", "Sin Uso SA de CV", "sinuso810.com.mx", "SMB", "Retail", 1000.0, "2024-06-15"),
        # ACC-8113: uso solo en 2021, muy antes del churn -> ventana final vacia.
        _company("HS-810013", "Ventana Vacia SA de CV", "vvacia810.com.mx", "SMB", "Retail", 1000.0, "2024-06-15"),
        # ACC-8114 y ACC-8115: el uso sube antes de la baja, asi que la
        # caida relativa es negativa; fijan el orden numerico descendente.
        _company("HS-810014", "Sube Mucho SA de CV", "submucho810.com.mx", "SMB", "Retail", 1000.0, "2024-06-15"),
        _company("HS-810015", "Sube Poco SA de CV", "subpoco810.com.mx", "SMB", "Retail", 1000.0, "2024-06-15"),
        # HS-810020: alta el mes calendario anterior al cierre de los
        # datos (que en este fixture cae en 2024-08 por el mes de baja y
        # el uso de ACC-8110); su cohorte 2024-07 solo cumple k = 1 y
        # queda censorada en k = 3, 6 y 12. mrr None para no mover el
        # total de A1.1 (queda 'unresolved', aporta cero pesos).
        {
            "hubspot_id": "HS-810020", "name": "Cohorte Reciente SA de CV", "domain": "cohortereciente810.com.mx",
            "segment": "SMB", "industry": "Retail", "mrr": None, "currency": "MXN", "signup_date": "2024-07-01",
            "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": None,
        },
        # HS-810021: caso frontera, hace churn exactamente 3 meses
        # despues de su alta (months_to_churn = 3). Debe seguir activa en
        # k = 1 y dejar de contar como activa justo en k = 3, 6 y 12.
        {
            "hubspot_id": "HS-810021", "name": "Frontera Churn SA de CV", "domain": "fronterachurn810.com.mx",
            "segment": "SMB", "industry": "Retail", "mrr": None, "currency": "MXN", "signup_date": "2023-01-01",
            "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": "2023-04-01",
        },
    ]
    accounts = [
        {"account_id": "ACC-8110", "hubspot_id": "HS-810010", "account_name": "Excluye Mes Baja", "created_at": "2022-01-01"},
        {"account_id": "ACC-8111", "hubspot_id": "HS-810011", "account_name": "Ventana Tres", "created_at": "2022-01-01"},
        {"account_id": "ACC-8112", "hubspot_id": "HS-810012", "account_name": "Sin Uso", "created_at": "2022-01-01"},
        {"account_id": "ACC-8113", "hubspot_id": "HS-810013", "account_name": "Ventana Vacia", "created_at": "2022-01-01"},
        {"account_id": "ACC-8114", "hubspot_id": "HS-810014", "account_name": "Sube Mucho", "created_at": "2022-01-01"},
        {"account_id": "ACC-8115", "hubspot_id": "HS-810015", "account_name": "Sube Poco", "created_at": "2022-01-01"},
    ]
    usage = [
        *[
            _usage("ACC-8110", month, users)
            for month, users in zip(
                ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06", "2024-07"],
                [20, 18, 16, 12, 10, 8, 6],
            )
        ],
        _usage("ACC-8110", "2024-08", 999),  # mes de baja: no debe entrar al promedio final
        _usage("ACC-8111", "2024-01", 100),
        _usage("ACC-8111", "2024-02", 50),
        _usage("ACC-8111", "2024-03", 25),
        _usage("ACC-8113", "2021-01", 10),
        _usage("ACC-8113", "2021-02", 10),
        _usage("ACC-8113", "2021-03", 10),
        # ACC-8114: primeros 3 meses 10; ventana final (2024-03 a 2024-05) 10, 20, 60 -> caida -2.0
        _usage("ACC-8114", "2024-01", 10), _usage("ACC-8114", "2024-02", 10), _usage("ACC-8114", "2024-03", 10),
        _usage("ACC-8114", "2024-04", 20), _usage("ACC-8114", "2024-05", 60),
        # ACC-8115: primeros 3 meses 10; ventana final 10, 10, 15 -> caida -0.166667
        _usage("ACC-8115", "2024-01", 10), _usage("ACC-8115", "2024-02", 10), _usage("ACC-8115", "2024-03", 10),
        _usage("ACC-8115", "2024-04", 10), _usage("ACC-8115", "2024-05", 15),
    ]
    deals = [
        # Deal huerfano: hubspot_id sin ninguna empresa real ni clon.
        {"deal_id": "D-819999", "hubspot_id": "HS-819999", "stage": "closedwon", "amount": 500.0,
         "created_date": "2022-01-01", "close_date": "2022-01-10", "pipeline": "New Business", "lead_source": "Web"},
        # Deal sobre el clon HS-900081: se remapea al sobreviviente
        # HS-810003 y no debe aparecer como huerfano.
        {"deal_id": "D-810081", "hubspot_id": "HS-900081", "stage": "closedwon", "amount": 300.0,
         "created_date": "2022-02-01", "close_date": "2022-02-10", "pipeline": "New Business", "lead_source": "Web"},
        # D-8110401: creado despues de los dos touches empatados por
        # fecha de HS-810001. mart_first_touch (grano empresa, sin
        # filtro de fecha) rompe el empate por touch_id ascendente,
        # mart_last_touch (grano deal, touch_date < created_date) lo
        # rompe por touch_id descendente: los dos extremos del mismo
        # empate deben dar canales distintos.
        {"deal_id": "D-8110401", "hubspot_id": "HS-810001", "stage": "open", "amount": 1000.0,
         "created_date": "2022-02-01", "close_date": "2022-03-01", "pipeline": "New Business", "lead_source": "Web"},
        # D-8110402: creado antes del unico touch de HS-810002. El
        # primer touch de la empresa si existe (mart_first_touch no
        # filtra por fecha), pero el ultimo touch anterior al deal no,
        # asi que el modelo de ultimo touch debe etiquetarlo
        # 'no_prior_touch' en vez de 'unknown'.
        {"deal_id": "D-8110402", "hubspot_id": "HS-810002", "stage": "open", "amount": 800.0,
         "created_date": "2022-01-01", "close_date": "2022-02-01", "pipeline": "New Business", "lead_source": "Web"},
    ]
    touches = [
        _touch("T-8110301", "HS-810001", "Organic", "2022-01-05"),
        _touch("T-8110302", "HS-810001", "Paid Search", "2022-01-05"),
        _touch("T-8110303", "HS-810002", "Webinar", "2022-06-01"),
    ]
    tickets = [
        # TK-8110601: resolution_hours negativo, el unico que debe aparecer
        # en analysis_a1_06_negative_hours y en analysis_exceptions.
        _ticket("TK-8110601", "cus_810601", -6.5, "Closed"),
        # TK-8110602: positivo, no debe aparecer en la vista de A1.6.
        _ticket("TK-8110602", "cus_810602", 6.5, "Closed"),
        # TK-8110603: resolution_hours nulo (ticket sin resolver), tampoco
        # debe aparecer; comprueba que el filtro es "< 0" y no "no positivo".
        _ticket("TK-8110603", "cus_810603", None, "Open"),
    ]
    return {
        "raw_companies": pd.DataFrame(companies),
        "raw_accounts": pd.DataFrame(accounts),
        "raw_product_usage": pd.DataFrame(usage),
        "raw_deals": pd.DataFrame(deals),
        "raw_marketing_touches": pd.DataFrame(touches),
        "raw_customers": _EMPTY_CUSTOMERS,
        "raw_tickets": pd.DataFrame(tickets),
    }


@pytest.fixture(scope="module")
def analysis_fixture(tmp_path_factory):
    raw_tables = _minimal_raw_tables()
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    assert len(identity_outputs["quarantine_companies"]) == 1
    db_path = tmp_path_factory.mktemp("analysis_rules") / "worky.duckdb"
    con = open_connection(db_path)
    try:
        assembly_outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
        result = run_analysis(con)
    finally:
        con.close()
    return result, assembly_outputs, identity_outputs


def test_a1_01_dos_columnas_mrr_y_fila_de_totales(analysis_fixture) -> None:
    result, _, _ = analysis_fixture
    active_mrr = result.outputs["analysis_a1_01_active_mrr"]
    total = active_mrr.loc[active_mrr["row_type"] == "total"].iloc[0]
    assert total["mrr_crm_mxn"] == "6300.00"
    assert total["mrr_total_mxn"] == "6300.00"
    segments = active_mrr.loc[active_mrr["row_type"] == "segment"]
    assert set(zip(segments["segment"], segments["industry"])) == {("SMB", "Retail"), ("Enterprise", "Tech")}


def test_a1_01_total_coincide_con_master_dataset(analysis_fixture) -> None:
    result, assembly_outputs, _ = analysis_fixture
    active_mrr = result.outputs["analysis_a1_01_active_mrr"]
    total = active_mrr.loc[active_mrr["row_type"] == "total"].iloc[0]
    master_dataset = assembly_outputs["master_dataset"]
    active = master_dataset.loc[master_dataset["churn_status"] == "active", "mrr_mxn"]
    expected = round(pd.to_numeric(active, errors="coerce").fillna(0).sum(), 2)
    assert round(float(total["mrr_total_mxn"]), 2) == expected


def test_a1_02_mes_de_baja_excluido_de_la_ventana(analysis_fixture) -> None:
    result, _, _ = analysis_fixture
    usage_drop = result.outputs["analysis_a1_02_usage_drop"].set_index("hubspot_id")
    row = usage_drop.loc["HS-810010"]
    assert row["avg_users_last_3_before_churn"] == "8.00"
    assert bool(row["windows_overlap"]) is False
    assert row["drop_status"] == "computed"


def test_a1_02_windows_overlap_en_cuenta_de_tres_meses(analysis_fixture) -> None:
    result, _, _ = analysis_fixture
    usage_drop = result.outputs["analysis_a1_02_usage_drop"].set_index("hubspot_id")
    row = usage_drop.loc["HS-810011"]
    assert bool(row["windows_overlap"]) is True
    assert row["drop_status"] == "computed"
    assert row["drop_relative"] == "0.000000"


def test_a1_02_drop_status_sin_uso(analysis_fixture) -> None:
    result, _, _ = analysis_fixture
    usage_drop = result.outputs["analysis_a1_02_usage_drop"].set_index("hubspot_id")
    row = usage_drop.loc["HS-810012"]
    assert row["drop_status"] == "no_usage"
    assert pd.isna(row["drop_relative"])


def test_a1_02_drop_status_ventana_final_vacia(analysis_fixture) -> None:
    result, _, _ = analysis_fixture
    usage_drop = result.outputs["analysis_a1_02_usage_drop"].set_index("hubspot_id")
    row = usage_drop.loc["HS-810013"]
    assert row["drop_status"] == "final_window_empty"
    assert row["avg_users_first_3"] == "10.00"
    assert pd.isna(row["drop_relative"])


def test_a1_05_deal_huerfano_detectado(analysis_fixture) -> None:
    result, _, identity_outputs = analysis_fixture
    orphan_deals = result.outputs["analysis_a1_05_orphan_deals"]
    assert set(orphan_deals["deal_id"]) == set(identity_outputs["quarantine_deals"]["deal_id"])
    assert "D-819999" in set(orphan_deals["deal_id"])


def test_a1_05_deal_de_clon_remapeado_no_es_huerfano(analysis_fixture) -> None:
    result, _, _ = analysis_fixture
    orphan_deals = result.outputs["analysis_a1_05_orphan_deals"]
    assert "D-810081" not in set(orphan_deals["deal_id"])


def test_analysis_contracts_pasan_sobre_el_fixture(analysis_fixture) -> None:
    result, assembly_outputs, identity_outputs = analysis_fixture
    run_analysis_contracts(
        result.outputs, assembly_outputs["master_dataset"], identity_outputs["quarantine_deals"]
    )


def test_a1_02_orden_numerico_descendente_con_negativos(analysis_fixture) -> None:
    # R3-a1-02: drop_relative es texto, pero el orden debe ser numerico:
    # los negativos van al final de las filas calculadas, del menos al mas negativo.
    result, _, _ = analysis_fixture
    usage_drop = result.outputs["analysis_a1_02_usage_drop"]
    computed = usage_drop[usage_drop["drop_status"] == "computed"]
    values = [float(v) for v in computed["drop_relative"]]
    assert values == sorted(values, reverse=True)
    assert values[-1] == -2.0
    assert computed.iloc[-1]["hubspot_id"] == "HS-810014"
    assert computed.iloc[-2]["hubspot_id"] == "HS-810015"
    first_uncomputed = usage_drop.index[usage_drop["drop_status"] != "computed"].min()
    assert first_uncomputed > computed.index.max()


def test_a1_03_celda_censurada_vacia_en_cohorte_reciente(analysis_fixture) -> None:
    result, _, _ = analysis_fixture
    cohort_retention = result.outputs["analysis_a1_03_cohort_retention"]
    recent = cohort_retention.loc[cohort_retention["cohort_month"] == "2024-07"].set_index("k")
    assert recent.loc[1, "cell_status"] == "computed"
    assert recent.loc[1, "retention_pct"] == "100.00"
    for k in (3, 6, 12):
        assert recent.loc[k, "cell_status"] == "censored"
        assert pd.isna(recent.loc[k, "retained"])
        assert pd.isna(recent.loc[k, "retention_pct"])


def test_a1_03_caso_frontera_churn_exacto_en_mes_k(analysis_fixture) -> None:
    # HS-810021 hace churn a exactamente 3 meses de su alta: sigue activa
    # en k = 1 (3 > 1) y deja de contar como activa justo en k = 3, 6 y
    # 12 (3 > k es falso en los tres), sin quedar censorada porque su
    # cohorte ya acumulo mas de 12 meses desde el alta.
    result, _, _ = analysis_fixture
    cohort_retention = result.outputs["analysis_a1_03_cohort_retention"]
    frontera = cohort_retention.loc[cohort_retention["cohort_month"] == "2023-01"].set_index("k")
    assert frontera.loc[1, "cell_status"] == "computed"
    assert int(frontera.loc[1, "retained"]) == 1
    for k in (3, 6, 12):
        assert frontera.loc[k, "cell_status"] == "computed"
        assert int(frontera.loc[k, "retained"]) == 0
        assert frontera.loc[k, "retention_pct"] == "0.00"


def test_a1_04_empate_por_touch_id_en_los_dos_extremos(analysis_fixture) -> None:
    # Los mismos dos touches de HS-810001 (misma fecha, distinto
    # touch_id) resuelven a canales distintos en cada modelo: el primer
    # touch se queda con el touch_id mas chico (Organic), el ultimo
    # touch con el mas grande (Paid Search), porque cada vista rompe el
    # empate en el extremo que le corresponde.
    result, _, _ = analysis_fixture
    attribution = result.outputs["analysis_a1_04_attribution"]
    first_touch = attribution.loc[attribution["model"] == "first_touch"].set_index("channel")
    last_touch = attribution.loc[attribution["model"] == "last_touch"].set_index("channel")
    assert int(first_touch.loc["Organic", "deals_attributed"]) == 1
    assert int(last_touch.loc["Paid Search", "deals_attributed"]) == 1


def test_a1_04_deal_creado_antes_del_primer_touch_es_no_prior_touch(analysis_fixture) -> None:
    # D-8110402 se creo antes del unico touch de HS-810002: el primer
    # touch de la empresa si existe (Webinar), pero ningun touch queda
    # antes del deal, asi que el ultimo touch lo etiqueta
    # 'no_prior_touch' en vez de 'unknown'. El deal del clon
    # remapeado (D-810081, sin ningun touch) tambien cae en
    # 'no_prior_touch', asi que el canal suma dos deals atribuidos.
    result, _, _ = analysis_fixture
    attribution = result.outputs["analysis_a1_04_attribution"]
    first_touch = attribution.loc[attribution["model"] == "first_touch"].set_index("channel")
    last_touch = attribution.loc[attribution["model"] == "last_touch"].set_index("channel")
    assert int(first_touch.loc["Webinar", "deals_attributed"]) == 1
    assert int(last_touch.loc["no_prior_touch", "deals_attributed"]) == 2


def test_a1_04_modelos_cubren_los_mismos_deals(analysis_fixture) -> None:
    result, _, _ = analysis_fixture
    attribution = result.outputs["analysis_a1_04_attribution"]
    totals = attribution.groupby("model")["deals_attributed"].sum()
    assert totals["first_touch"] == totals["last_touch"] == 3


def test_a1_06_ticket_negativo_en_detalle_y_su_fila_de_excepcion(analysis_fixture) -> None:
    # Solo TK-8110601 (resolution_hours = -6.5) debe listarse: el positivo
    # y el nulo quedan fuera de la vista y de las excepciones.
    result, _, _ = analysis_fixture
    negative_hours = result.outputs["analysis_a1_06_negative_hours"]
    assert set(negative_hours["ticket_id"]) == {"TK-8110601"}
    row = negative_hours.set_index("ticket_id").loc["TK-8110601"]
    assert row["resolution_hours"] == "-6.50"
    assert row["resolution_hours_abs"] == "6.50"

    exceptions = result.outputs["analysis_exceptions"]
    assert len(exceptions) == 1
    exception_row = exceptions.iloc[0]
    assert exception_row["exception_code"] == "negative_resolution_hours"
    assert exception_row["source_system"] == "vitally"
    assert exception_row["source_id"] == "TK-8110601"
    assert exception_row["field_name"] == "resolution_hours"
    assert exception_row["original_value"] == "-6.50"
    assert exception_row["applied_value"] == "null"
