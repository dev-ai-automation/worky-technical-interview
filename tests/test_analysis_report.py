"""Pruebas de estructura de `report.md`, capa unitaria (D13, seccion 6 del diseno).

Reusa `_minimal_raw_tables` de `tests/test_analysis_rules.py` en vez de
duplicar el mismo fixture minimo: estas pruebas no ejercen ninguna regla
de negocio, solo la forma del reporte (secciones, SQL insertado
verbatim, la regla de tabla completa contra encabezado mas conteo, la
matriz pivotada de A1.3 y la ausencia de em dash y de hora de reloj), y
el dataset minimo que ya cubre A1.1 a A1.6 en `test_analysis_rules.py`
alcanza para eso.
"""

from __future__ import annotations

import re

import pytest

from test_analysis_rules import _minimal_raw_tables
from worky_engine.analysis import format_report, run_analysis
from worky_engine.identity_resolution import resolve_identity
from worky_engine.master_dataset import assemble_master_dataset, open_connection
from worky_engine.master_dataset.assemble import SQL_DIR

_SQL_FILES = (
    "analysis/a1_01_active_mrr.sql",
    "analysis/a1_02_usage_drop.sql",
    "analysis/a1_03_cohort_retention.sql",
    "analysis/a1_04_attribution.sql",
    "analysis/a1_05_orphan_deals.sql",
    "analysis/a1_06_negative_hours.sql",
)


@pytest.fixture(scope="module")
def report_text(tmp_path_factory) -> str:
    raw_tables = _minimal_raw_tables()
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)
    db_path = tmp_path_factory.mktemp("analysis_report") / "worky.duckdb"
    con = open_connection(db_path)
    try:
        assemble_master_dataset(con, raw_tables, identity_outputs)
        result = run_analysis(con)
    finally:
        con.close()
    return format_report(result)


def test_una_seccion_por_item_de_a1_1_a_a1_7(report_text: str) -> None:
    for heading in ("## A1.1.", "## A1.2.", "## A1.3.", "## A1.4.", "## A1.5.", "## A1.6.", "## A1.7."):
        assert heading in report_text


def test_bloque_sql_igual_al_archivo_caracter_por_caracter(report_text: str) -> None:
    for relative_path in _SQL_FILES:
        file_text = (SQL_DIR / relative_path).read_text(encoding="utf-8").rstrip()
        assert f"```sql\n{file_text}\n```" in report_text


def test_regla_de_tabla_completa_contra_encabezado_mas_conteo(report_text: str) -> None:
    # A1.2 y A1.6 muestran encabezado mas conteo ("Total: N filas."); A1.1,
    # A1.3, A1.4 y A1.5 muestran la tabla completa, sin esa linea.
    bounds = {
        heading: report_text.index(f"## {heading}.")
        for heading in ("A1.1", "A1.2", "A1.3", "A1.4", "A1.5", "A1.6", "A1.7")
    }
    ordered = sorted(bounds.items(), key=lambda item: item[1])
    sections = {}
    for index, (heading, start) in enumerate(ordered):
        end = ordered[index + 1][1] if index + 1 < len(ordered) else len(report_text)
        sections[heading] = report_text[start:end]

    assert re.search(r"Total: \d+ filas\.", sections["A1.2"])
    assert re.search(r"Total: \d+ filas\.", sections["A1.6"])
    for heading in ("A1.1", "A1.3", "A1.4", "A1.5"):
        assert "Total: " not in sections[heading]


def test_a1_03_matriz_pivotada_con_celdas_censuradas_vacias(report_text: str) -> None:
    # HS-810020 (cohorte 2024-07) solo cumple k = 1 en el fixture minimo;
    # las celdas de k = 3, 6 y 12 deben quedar vacias en la matriz.
    line = next(line for line in report_text.splitlines() if line.startswith("| 2024-07 "))
    cells = [cell.strip() for cell in line.strip("|").split("|")]
    assert cells[2] == "100.00"
    assert cells[3] == "" and cells[4] == "" and cells[5] == ""


def test_a1_06_justificacion_presente_en_tres_a_cuatro_lineas(report_text: str) -> None:
    start = report_text.index("**Justificación:**")
    end = report_text.index("## A1.7.")
    block = report_text[start:end]
    quote = block.split("> ", 1)[1].strip()
    sentences = [sentence for sentence in quote.split(". ") if sentence.strip()]
    assert 3 <= len(sentences) <= 4


def test_sin_hora_de_reloj_en_el_documento(report_text: str) -> None:
    assert re.search(r"\b\d{1,2}:\d{2}(:\d{2})?\b", report_text) is None


def test_sin_em_dash_en_el_documento(report_text: str) -> None:
    assert "—" not in report_text
