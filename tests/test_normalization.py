"""Pruebas de las cuatro funciones puras de `worky_engine.normalization`.

Cubre la tabla de casos de fecha, dominio, nombre y moneda que exige la
seccion 6 del diseno, la idempotencia por registro y la ida y vuelta
UTF-8 con nombres acentuados.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worky_engine.normalization import (
    ConvertedAmount,
    domain_label,
    normalize_company_name,
    normalize_date,
    to_mxn,
)
from worky_engine.writers import write_csv

# --- fecha -----------------------------------------------------------------

DATE_CASES = [
    pytest.param("2023-05-14", "2023-05-14", id="date-ya-iso"),
    pytest.param("14/05/2023", "2023-05-14", id="date-dd-mm-yyyy"),
    pytest.param("2022-10-04", "2022-10-04", id="date-iso-otro-ejemplo"),
    pytest.param("04/10/2022", "2022-10-04", id="date-dmy-otro-ejemplo"),
    pytest.param("2023-13-01", None, id="date-mes-invalido"),
    pytest.param("31/02/2023", None, id="date-dia-invalido-para-febrero"),
    pytest.param("no-es-una-fecha", None, id="date-formato-desconocido"),
    pytest.param("2023/05/14", None, id="date-separador-incorrecto"),
    pytest.param("", None, id="date-cadena-vacia"),
    pytest.param(None, None, id="date-nulo"),
]


@pytest.mark.parametrize("raw, expected", DATE_CASES)
def test_normalize_date(raw: str | None, expected: str | None) -> None:
    assert normalize_date(raw) == expected


# --- dominio -----------------------------------------------------------------

DOMAIN_CASES = [
    pytest.param("app.cordero501.com.mx", "cordero501", id="domain-con-subdominio-app"),
    pytest.param("cordero501.mx", "cordero501", id="domain-sin-subdominio"),
    pytest.param("gaitán115.com.mx", "gaitan115", id="domain-con-acento"),
    pytest.param("www.example.org", "example", id="domain-subdominio-www-sufijo-org"),
    pytest.param("mail.portal.club226.com.mx", "club226", id="domain-dos-subdominios-conocidos"),
    pytest.param("", None, id="domain-cadena-vacia"),
    pytest.param(None, None, id="domain-nulo"),
]


@pytest.mark.parametrize("raw, expected", DOMAIN_CASES)
def test_domain_label(raw: str | None, expected: str | None) -> None:
    assert domain_label(raw) == expected


# --- nombre de empresa -------------------------------------------------------

NAME_CASES = [
    pytest.param("Sanches y Asociados SA de CV", "sanches", id="name-razon-social-simple"),
    pytest.param(
        "Gaitán y Asociados, S.A. de C.V.",
        "gaitan",
        id="name-acento-puntuacion-y-s-a-de-c-v",
    ),
    pytest.param("  Empresa   Uno  ", "empresa uno", id="name-espacios-repetidos"),
    pytest.param("Cuellar-Ceja e Hijos", "cuellar ceja", id="name-guion-y-e-hijos"),
    pytest.param("", None, id="name-cadena-vacia"),
    pytest.param(None, None, id="name-nulo"),
]


@pytest.mark.parametrize("raw, expected", NAME_CASES)
def test_normalize_company_name(raw: str | None, expected: str | None) -> None:
    assert normalize_company_name(raw) == expected


# --- moneda -------------------------------------------------------------------


def test_to_mxn_convierte_usd_al_tipo_de_cambio_fijo() -> None:
    result = to_mxn(1000, "USD")
    assert result == ConvertedAmount(mxn=18500.0, original_amount=1000, original_currency="USD")


def test_to_mxn_conserva_mxn_sin_cambio() -> None:
    result = to_mxn(5000, "MXN")
    assert result == ConvertedAmount(mxn=5000.0, original_amount=5000, original_currency="MXN")


def test_to_mxn_rechaza_moneda_no_soportada() -> None:
    with pytest.raises(ValueError):
        to_mxn(100, "EUR")


# --- idempotencia por registro -------------------------------------------------


@pytest.mark.parametrize(
    "normalizer, raw",
    [
        pytest.param(normalize_date, "14/05/2023", id="idempotencia-fecha"),
        pytest.param(domain_label, "app.cordero501.com.mx", id="idempotencia-dominio"),
        pytest.param(
            normalize_company_name,
            "Gaitán y Asociados, S.A. de C.V.",
            id="idempotencia-nombre",
        ),
    ],
)
def test_normalization_is_idempotent(normalizer, raw: str) -> None:
    once = normalizer(raw)
    twice = normalizer(once)
    assert once == twice


def test_to_mxn_es_idempotente_sobre_su_propia_salida() -> None:
    first = to_mxn(1000, "USD")
    second = to_mxn(first.mxn, "MXN")
    assert second.mxn == first.mxn


# --- ida y vuelta UTF-8 --------------------------------------------------------


def test_ida_y_vuelta_utf8_con_nombres_acentuados(tmp_path) -> None:
    frame = pd.DataFrame(
        {
            "company_name": ["Gaitán", "Sánchez"],
            "domain": ["gaitán115.com.mx", "sánchez201.com.mx"],
        }
    )
    output_path = tmp_path / "acentos.csv"

    write_csv(frame, output_path)
    round_tripped = pd.read_csv(output_path, encoding="utf-8", keep_default_na=False)

    assert list(round_tripped["company_name"]) == ["Gaitán", "Sánchez"]
    assert list(round_tripped["domain"]) == ["gaitán115.com.mx", "sánchez201.com.mx"]
    assert domain_label(round_tripped["domain"][0]) == "gaitan115"
    assert normalize_company_name(round_tripped["company_name"][0]) == "gaitan"
