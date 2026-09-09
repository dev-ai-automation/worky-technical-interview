"""Pruebas de estructura de `validation.md`, capa unitaria (seccion 9 del diseno de A3).

Fixture propio, distinto del de `test_health_rules.py`: cuatro
empresas (dos bajas, dos activas), dos segmentos y dos canales de
adquisicion via `raw_marketing_touches`, y una baja con menos de tres
meses de uso al corte (banda "sin historia"). Esa combinacion es la
minima que ejercita las doce secciones sin depender del dataset real:
con solo tres empresas (como el fixture de `test_health_rules.py`) el
conteo de no detectables siempre da cero y la matriz de confusion
nunca muestra un falso negativo no detectable.
"""

from __future__ import annotations

import re

import pandas as pd
import pytest

from worky_engine.health import format_validation, run_health
from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset, open_connection
from worky_engine.master_dataset.assemble import SQL_DIR

_HEALTH_SQL_FILES = (
    "health/h1_company_asof.sql",
    "health/h2_usage_signals.sql",
    "health/h3_tenure.sql",
    "health/h4_support_asof.sql",
    "health/h5_activation.sql",
    "health/h6_asof_inputs.sql",
)

_SECTION_HEADINGS = (
    "## Encabezado",
    "## Fórmula y pesos",
    "## AUC por señal",
    "## Métricas de validación",
    "## Regla de aceptación del ADR-005",
    "## Matriz de confusión",
    "## Empresas no detectables",
    "## Detección temprana",
    "## Sensibilidades",
    "## Capacidad por CSM",
    "## Respuesta a A3.4",
    "## Contexto comercial",
    "## Referencias",
)

_EMPTY_DEALS = pd.DataFrame(
    columns=["deal_id", "hubspot_id", "stage", "amount", "created_date", "close_date", "pipeline", "lead_source"]
)
_EMPTY_TICKETS = pd.DataFrame(
    columns=["ticket_id", "vitally_id", "created_date", "priority", "status", "category", "resolution_hours", "csat_score"]
)
_EMPTY_CUSTOMERS = pd.DataFrame(columns=["vitally_id", "domain", "company_name", "csm_email"])


def _company(hubspot_id: str, name: str, domain: str, segment: str, churn_date: str | None = None) -> dict:
    return {
        "hubspot_id": hubspot_id, "name": name, "domain": domain, "segment": segment,
        "industry": "Retail", "mrr": 1000.0, "currency": "MXN", "signup_date": "2022-01-01",
        "csm_owner": "X", "plan": "Basico", "state": "CDMX", "churn_date": churn_date,
    }


def _usage_rows(account_id: str, months_users: list[tuple[str, int]]) -> list[dict]:
    return [
        {
            "account_id": account_id, "month": month, "active_users": users, "logins": users * 2,
            "payroll_runs_completed": 1, "features_used": 3, "api_calls": users * 5,
        }
        for month, users in months_users
    ]


def _touch(hubspot_id: str, channel: str) -> dict:
    return {"touch_id": f"TCH-{hubspot_id}", "hubspot_id": hubspot_id, "channel": channel, "touch_date": "2022-01-01", "campaign": "camp"}


def _minimal_raw_tables() -> dict[str, pd.DataFrame]:
    """Dos bajas (una con historia suficiente, una sin historia) y dos activas, en dos segmentos y dos canales."""
    companies = [
        _company("HS-9001", "Detectable Baja SA", "det9001.com.mx", "SMB", "2024-08-15"),
        _company("HS-9002", "No Detectable Baja SA", "nodet9002.com.mx", "Enterprise", "2024-08-20"),
        _company("HS-9003", "Activa Uno SA", "act9003.com.mx", "SMB"),
        _company("HS-9004", "Activa Dos SA", "act9004.com.mx", "Enterprise"),
    ]
    accounts = [
        {"account_id": "ACC-9001", "hubspot_id": "HS-9001", "account_name": "Detectable Baja", "created_at": "2022-01-01"},
        {"account_id": "ACC-9002", "hubspot_id": "HS-9002", "account_name": "No Detectable Baja", "created_at": "2022-01-01"},
        {"account_id": "ACC-9003", "hubspot_id": "HS-9003", "account_name": "Activa Uno", "created_at": "2022-01-01"},
        {"account_id": "ACC-9004", "hubspot_id": "HS-9004", "account_name": "Activa Dos", "created_at": "2022-01-01"},
    ]
    usage = (
        _usage_rows("ACC-9001", [("2024-02", 40), ("2024-03", 45), ("2024-04", 50), ("2024-05", 55), ("2024-06", 60)])
        + _usage_rows("ACC-9002", [("2024-06", 10)])
        + _usage_rows("ACC-9003", [(m, 30 + i) for i, m in enumerate(
            ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"]
        )])
        + _usage_rows("ACC-9004", [(m, 20 + i) for i, m in enumerate(
            ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06"]
        )])
    )
    touches = [
        _touch("HS-9001", "Organic"),
        _touch("HS-9002", "Outbound SDR"),
        _touch("HS-9003", "Organic"),
        _touch("HS-9004", "Outbound SDR"),
    ]
    return {
        "raw_companies": pd.DataFrame(companies),
        "raw_accounts": pd.DataFrame(accounts),
        "raw_product_usage": pd.DataFrame(usage),
        "raw_deals": _EMPTY_DEALS,
        "raw_marketing_touches": pd.DataFrame(touches),
        "raw_customers": _EMPTY_CUSTOMERS,
        "raw_tickets": _EMPTY_TICKETS,
    }


@pytest.fixture(scope="module")
def report_context(tmp_path_factory):
    raw_tables = _minimal_raw_tables()
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    db_path = tmp_path_factory.mktemp("health_report") / "worky_health.duckdb"
    con = open_connection(db_path)
    try:
        assemble_master_dataset(con, raw_tables, identity_outputs)
        result = run_health(con)
    finally:
        con.close()
    return result, format_validation(result)


@pytest.fixture(scope="module")
def report_text(report_context) -> str:
    return report_context[1]


def test_las_doce_secciones_en_orden(report_text: str) -> None:
    positions = [report_text.index(heading) for heading in _SECTION_HEADINGS]
    assert positions == sorted(positions), "las doce secciones deben aparecer en el orden del diseno"


def test_apendice_con_el_sql_de_las_seis_vistas_insertado_tal_cual(report_text: str) -> None:
    for relative_path in _HEALTH_SQL_FILES:
        file_text = (SQL_DIR / relative_path).read_text(encoding="utf-8").rstrip()
        assert f"```sql\n{file_text}\n```" in report_text, f"{relative_path} no esta insertado tal cual"


def test_cada_cifra_dice_en_este_dataset(report_text: str) -> None:
    for heading in (
        "## Encabezado", "## AUC por señal", "## Métricas de validación", "## Matriz de confusión",
        "## Empresas no detectables", "## Detección temprana", "## Sensibilidades", "## Capacidad por CSM",
    ):
        start = report_text.index(heading)
        end = report_text.index("##", start + len(heading))
        assert "en este dataset" in report_text[start:end], f"'{heading}' no dice 'en este dataset'"


def test_soporte_presente_con_su_auc_y_su_peso_cero(report_text: str) -> None:
    start = report_text.index("## AUC por señal")
    end = report_text.index("## Métricas de validación")
    block = report_text[start:end]
    for label in ("Tickets totales", "Tickets urgentes", "CSAT promedio", "Activacion en los primeros"):
        assert label in block
    assert "| 0.00 |" in block, "las senales de soporte y activacion deben declarar peso 0.00"


def test_conteo_de_no_detectables_dentro_de_la_matriz_de_confusion(report_text: str) -> None:
    start = report_text.index("## Matriz de confusión")
    end = report_text.index("## Empresas no detectables")
    block = report_text[start:end]
    assert re.search(r"Falsos negativos.*\(de los cuales \d+ son no detectables", block)
    assert "de los cuales 1 son no detectables" in block


def test_seccion_a3_4_presente_con_costo_asimetrico(report_text: str) -> None:
    start = report_text.index("## Respuesta a A3.4")
    end = report_text.index("## Contexto comercial")
    block = report_text[start:end]
    assert "falso positivo" in block
    assert "falso negativo" in block
    assert "recall ponderado por MRR" in block
    assert "onboarding" in block.lower()


def test_contexto_comercial_reporta_canal_y_segmento_fuera_del_score(report_text: str) -> None:
    start = report_text.index("## Contexto comercial")
    end = report_text.index("## Referencias")
    block = report_text[start:end]
    assert "acquisition_channel" in block
    assert "segment" in block
    assert "no entran a la fórmula" in block


def test_sin_hora_de_reloj_en_el_documento(report_text: str) -> None:
    assert re.search(r"\b\d{1,2}:\d{2}(:\d{2})?\b", report_text) is None


def test_sin_em_dash_en_el_documento(report_text: str) -> None:
    assert "—" not in report_text


def test_seccion_de_no_detectables_sin_bajas_no_divide_entre_cero() -> None:
    # R3-undetectable-zero-division: un dataset sin churn debe producir la
    # seccion con una oracion, no un ZeroDivisionError.
    from worky_engine.health.report import _undetectable_section

    scores = pd.DataFrame(
        [
            {"master_id": "A", "churned": False, "usage_months_asof": 5, "health_score": 50.0, "risk_band": "riesgo bajo"},
            {"master_id": "B", "churned": False, "usage_months_asof": 1, "health_score": None, "risk_band": "sin historia"},
        ]
    )
    text = _undetectable_section(scores)
    assert text.startswith("## Empresas no detectables")
    assert "no tiene bajas" in text


def test_seccion_de_aceptacion_presente_con_umbrales_y_veredicto(report_text: str) -> None:
    # Verificacion de A3: el reporte debe decir la regla, lo medido y si se cumplio.
    assert "## Regla de aceptación del ADR-005" in report_text
    start = report_text.index("## Regla de aceptación del ADR-005")
    assert "## Matriz de confusión" in report_text[start:], "la seccion de aceptacion debe ir antes de la matriz"
    section = report_text[start : report_text.index("## Matriz de confusión", start)]
    assert "0.95" in section and "0.85" in section
    # El veredicto y la recomendacion son excluyentes: cumplida sin mezcla medida,
    # no cumplida con mezcla medida. Asi una recomendacion incondicional no pasa.
    if "Regla cumplida." in section:
        assert "mezcla medida" not in section
    else:
        assert "Regla no cumplida." in section and "mezcla medida" in section


def test_seccion_de_aceptacion_recomienda_la_mezcla_medida_cuando_falla() -> None:
    # Con un score que no separa, la regla falla y el reporte debe recomendar
    # la mezcla medida y la adenda, sin cambiar los pesos por su cuenta.
    from worky_engine.health.report import _acceptance_section

    rows = []
    for index in range(20):
        churned = index % 2 == 0
        rows.append(
            {
                "master_id": f"X{index:02d}", "churned": churned, "usage_months_asof": 6,
                "health_score": float(index), "flagged_20": index < 4, "mrr_mxn": 1000.0,
                "risk_band": "riesgo alto" if index < 3 else "riesgo bajo",
            }
        )
    text = _acceptance_section(pd.DataFrame(rows))
    assert "Regla no cumplida." in text
    assert "mezcla medida" in text and "WEIGHTS" in text
    for piece in ("uso 70 %", "momentum 0.35", "cambio mes a mes 0.20", "caída 0.15", "antigüedad 15 %", "activación 15 %"):
        assert piece in text
    assert "no cambia los pesos por su cuenta" in text


def test_seccion_de_aceptacion_sin_bajas_queda_sin_evaluar() -> None:
    # R3-acceptance-section-no-empty-churn-guard: sin clase positiva no hay
    # AUC ni recall; la seccion lo dice en vez de tronar o imprimir NaN.
    from worky_engine.health.report import _acceptance_section

    scores = pd.DataFrame(
        [
            {"master_id": "A", "churned": False, "usage_months_asof": 5, "health_score": 50.0, "flagged_20": False, "mrr_mxn": 100.0, "risk_band": "riesgo bajo"},
            {"master_id": "B", "churned": False, "usage_months_asof": 5, "health_score": 20.0, "flagged_20": True, "mrr_mxn": 100.0, "risk_band": "riesgo alto"},
        ]
    )
    text = _acceptance_section(scores)
    assert text.startswith("## Regla de aceptación del ADR-005")
    assert "no tiene bajas" in text and "queda sin evaluar" in text
    assert "NaN" not in text and "nan" not in text
