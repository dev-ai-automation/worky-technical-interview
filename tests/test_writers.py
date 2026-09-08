"""Pruebas de `worky_engine.writers`: formato exacto de CSV y Markdown.

Confirma codificacion UTF-8 sin BOM, salto de linea `\n`, ausencia de
columna de indice, nulo escrito como campo vacio, y el formato de dos y
seis decimales que exige la seccion 7 del diseno.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worky_engine.writers import format_money, format_ratio, write_csv, write_markdown


def test_write_csv_usa_utf8_sin_bom(tmp_path) -> None:
    frame = pd.DataFrame({"company_name": ["Gaitán"]})
    output_path = tmp_path / "salida.csv"

    write_csv(frame, output_path)

    raw_bytes = output_path.read_bytes()
    assert not raw_bytes.startswith(b"\xef\xbb\xbf")
    assert "Gaitán".encode("utf-8") in raw_bytes


def test_write_csv_usa_salto_de_linea_unix(tmp_path) -> None:
    frame = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    output_path = tmp_path / "salida.csv"

    write_csv(frame, output_path)

    raw_bytes = output_path.read_bytes()
    assert b"\r\n" not in raw_bytes
    assert b"\n" in raw_bytes


def test_write_csv_no_incluye_columna_de_indice(tmp_path) -> None:
    frame = pd.DataFrame({"a": [1, 2]})
    output_path = tmp_path / "salida.csv"

    write_csv(frame, output_path)

    first_line = output_path.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "a"


def test_write_csv_escribe_nulo_como_campo_vacio(tmp_path) -> None:
    import csv

    frame = pd.DataFrame({"a": [1, 2], "b": [3.0, None]})
    output_path = tmp_path / "salida.csv"

    write_csv(frame, output_path)

    with open(output_path, encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["a", "b"]
    assert rows[2] == ["2", ""]


def test_write_markdown_usa_utf8_y_salto_unix(tmp_path) -> None:
    output_path = tmp_path / "reporte.md"

    write_markdown("# Título\n\nCon acentos: canción\n", output_path)

    raw_bytes = output_path.read_bytes()
    assert not raw_bytes.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in raw_bytes
    assert "Título".encode("utf-8") in raw_bytes


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(1234.5, "1234.50", id="money-un-decimal"),
        pytest.param(0, "0.00", id="money-cero"),
        pytest.param(None, "", id="money-nulo"),
        pytest.param(float("nan"), "", id="money-nan-de-pandas"),
        pytest.param(pd.NA, "", id="money-pd-na"),
    ],
)
def test_format_money_usa_dos_decimales(value, expected: str) -> None:
    assert format_money(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(0.4123, "0.412300", id="ratio-cuatro-decimales"),
        pytest.param(0, "0.000000", id="ratio-cero"),
        pytest.param(None, "", id="ratio-nulo"),
        pytest.param(float("nan"), "", id="ratio-nan-de-pandas"),
        pytest.param(pd.NA, "", id="ratio-pd-na"),
    ],
)
def test_format_ratio_usa_seis_decimales(value, expected: str) -> None:
    assert format_ratio(value) == expected
