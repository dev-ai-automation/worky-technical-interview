"""Pruebas unitarias e integracion de `worky_engine.cleaning` sobre una fixture minima propia.

Esta fixture no extiende `tests/fixtures/mini_dataset.py` (seccion 7
del diseno de `a6-cleaning-script`): agregar empresas ahi moveria los
conteos que ya fijan las pruebas de identidad y de imputacion de A0.
Cubre las tres reglas de PR1 (fechas, moneda, mrr nulo con exclusion
de clones), el comando `clean`, el wrapper y los codigos de salida.
"""

from __future__ import annotations

import builtins
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from worky_engine.cli import main as cli_main
from worky_engine.cleaning import run_clean
from worky_engine.cleaning.rules import convert_currency, detect_missing_mrr, normalize_dates
from worky_engine.quality.cleaning_contracts import run_cleaning_contracts

COMPANIES_COLUMNS = (
    "hubspot_id",
    "name",
    "domain",
    "segment",
    "industry",
    "mrr",
    "currency",
    "signup_date",
    "csm_owner",
    "plan",
    "state",
    "churn_date",
)
DEALS_COLUMNS = ("deal_id", "hubspot_id", "stage", "amount", "created_date", "close_date", "owner", "pipeline", "lead_source")


def _company(hubspot_id: str, mrr: str = "1000", currency: str = "MXN", signup_date: str = "2023-01-01", **overrides) -> dict:
    row = {
        "hubspot_id": hubspot_id,
        "name": f"Empresa {hubspot_id}",
        "domain": f"{hubspot_id.lower()}.com.mx",
        "segment": "SMB",
        "industry": "Tecnologia",
        "mrr": mrr,
        "currency": currency,
        "signup_date": signup_date,
        "csm_owner": "Ana Ruiz",
        "plan": "Basico",
        "state": "Jalisco",
        "churn_date": "",
    }
    row.update(overrides)
    return row


def fixture_companies() -> pd.DataFrame:
    """Siete filas: dos crm normales, una USD, una real sin mrr, un clon, dos fechas DD/MM/YYYY y una fecha imposible."""
    rows = [
        _company("HS-100001", mrr="5000", currency="MXN"),
        _company("HS-100002", mrr="1000", currency="USD"),
        _company("HS-100003", mrr="", currency="MXN"),
        _company("HS-900000", mrr="", currency="MXN", name="Clon"),
        _company("HS-100004", signup_date="25/12/2022"),
        _company("HS-100005", signup_date="05/06/2022"),
        _company("HS-100006", signup_date="31/02/2023"),
    ]
    return pd.DataFrame(rows, columns=COMPANIES_COLUMNS)


def fixture_deals() -> pd.DataFrame:
    rows = [
        {
            "deal_id": "D00001",
            "hubspot_id": "HS-100001",
            "stage": "closedwon",
            "amount": "5000",
            "created_date": "2023-01-15",
            "close_date": "2023-02-01",
            "owner": "Sales_Ana",
            "pipeline": "New Business",
            "lead_source": "Organic",
        }
    ]
    return pd.DataFrame(rows, columns=DEALS_COLUMNS)


def _write_fixture_files(tmp_path: Path) -> Path:
    data_dir = tmp_path / "sistemas"
    data_dir.mkdir()
    fixture_companies().to_csv(data_dir / "crm_hubspot__companies.csv", index=False)
    fixture_deals().to_csv(data_dir / "crm_hubspot__deals.csv", index=False)
    return data_dir


# --- comando y wrapper -------------------------------------------------------


def test_corrida_exitosa_desde_ambas_rutas(tmp_path: Path) -> None:
    """El subcomando y el wrapper generan las mismas salidas en outputs/clean/ y ambos terminan en 0."""
    data_dir = _write_fixture_files(tmp_path)
    out_dir_cmd = tmp_path / "out_cmd"
    out_dir_wrapper = tmp_path / "out_wrapper"

    exit_code = cli_main(["clean", "--data-dir", str(data_dir), "--out-dir", str(out_dir_cmd)])
    assert exit_code == 0

    repo_root = Path(__file__).resolve().parent.parent
    wrapper_result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "clean_companies.py"), "--data-dir", str(data_dir), "--out-dir", str(out_dir_wrapper)],
        capture_output=True,
        text=True,
    )
    assert wrapper_result.returncode == 0

    for name in ("companies_clean.csv", "cleaning_exceptions.csv", "cleaning_log.json", "cleaning_log.md"):
        assert (out_dir_cmd / name).read_bytes() == (out_dir_wrapper / name).read_bytes()


def test_falta_companies_csv_termina_con_codigo_2(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Sin companies.csv en el directorio de datos, clean termina en 2 nombrando el archivo faltante."""
    data_dir = tmp_path / "sistemas"
    data_dir.mkdir()
    fixture_deals().to_csv(data_dir / "crm_hubspot__deals.csv", index=False)

    with pytest.raises(SystemExit) as exit_info:
        cli_main(["clean", "--data-dir", str(data_dir), "--out-dir", str(tmp_path / "out")])
    assert exit_info.value.code == 2
    assert "companies.csv" in capsys.readouterr().err


def test_falta_deals_csv_termina_con_codigo_2_sin_salida_parcial(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Sin deals.csv, clean termina en 2 nombrando deals.csv y no escribe companies_clean.csv."""
    data_dir = tmp_path / "sistemas"
    data_dir.mkdir()
    fixture_companies().to_csv(data_dir / "crm_hubspot__companies.csv", index=False)
    out_dir = tmp_path / "out"

    with pytest.raises(SystemExit) as exit_info:
        cli_main(["clean", "--data-dir", str(data_dir), "--out-dir", str(out_dir)])
    assert exit_info.value.code == 2
    assert "deals.csv" in capsys.readouterr().err
    assert not (out_dir / "companies_clean.csv").exists()


def test_ambos_archivos_presentes_corre_las_tres_detecciones(tmp_path: Path) -> None:
    """Con companies.csv y deals.csv presentes, clean lee ambos y corre las tres detecciones."""
    data_dir = _write_fixture_files(tmp_path)
    out_dir = tmp_path / "out"

    exit_code = cli_main(["clean", "--data-dir", str(data_dir), "--out-dir", str(out_dir)])
    assert exit_code == 0
    counts = out_dir / "cleaning_log.json"
    assert counts.is_file()
    assert (out_dir / "companies_clean.csv").is_file()


def test_falta_una_dependencia_termina_con_codigo_2(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Si `worky_engine.cleaning` no se puede importar, clean termina en 2 nombrando la dependencia."""
    real_import = builtins.__import__

    def _fake_import(name: str, *args, **kwargs):
        if name == "worky_engine.cleaning":
            raise ImportError(name="worky_engine.cleaning")
        return real_import(name, *args, **kwargs)

    for cached in ("worky_engine.cleaning",):
        monkeypatch.delitem(sys.modules, cached, raising=False)
    monkeypatch.setattr(builtins, "__import__", _fake_import)

    with pytest.raises(SystemExit) as exit_info:
        cli_main(["clean", "--data-dir", str(tmp_path), "--out-dir", str(tmp_path / "out")])
    assert exit_info.value.code == 2
    assert "worky_engine.cleaning" in capsys.readouterr().err


# --- reglas puras ------------------------------------------------------------


def test_un_clon_no_se_imputa() -> None:
    """Una fila clon HS-9000xx con mrr nulo queda sin imputar y se reporta como excluida por cuarentena."""
    companies = fixture_companies()
    result = run_clean(companies, fixture_deals())
    clone_row = result.clean[result.clean["hubspot_id"] == "HS-900000"].iloc[0]
    assert clone_row["mrr_source"] == "clone_excluded"
    assert clone_row["mrr_mxn"] == ""
    clone_exception = result.exceptions[result.exceptions["source_id"] == "HS-900000"]
    assert len(clone_exception) == 1
    assert (clone_exception["exception_code"] == "clone_excluded").all()


def test_fecha_calendario_imposible_conserva_el_original() -> None:
    """Una fecha invalida como 31/02/2023 no se normaliza, la fila sale como date_unresolved y la corrida no aborta."""
    companies = pd.DataFrame([_company("HS-100006", signup_date="31/02/2023")], columns=COMPANIES_COLUMNS)
    result, corrections = normalize_dates(companies)
    assert result.at[0, "signup_date"] == "31/02/2023"
    assert len(corrections) == 1
    assert corrections[0].exception_code == "date_unresolved"


def test_monto_en_usd_se_convierte_a_mxn() -> None:
    """Un monto de 1000 USD queda en mrr_mxn = 18500, mrr_original = 1000 y currency_original = USD."""
    companies = pd.DataFrame([_company("HS-100002", mrr="1000", currency="USD")], columns=COMPANIES_COLUMNS)
    result = run_clean(companies, fixture_deals())
    row = result.clean.iloc[0]
    assert row["mrr_mxn"] == "18500.00"
    assert row["mrr_original"] == "1000.00"
    assert row["currency_original"] == "USD"


def test_monto_ya_en_mxn_no_cambia_de_valor() -> None:
    """Un monto de 5000 MXN sale con mrr_mxn igual a mrr_original y currency_original en MXN."""
    companies = pd.DataFrame([_company("HS-100001", mrr="5000", currency="MXN")], columns=COMPANIES_COLUMNS)
    result = run_clean(companies, fixture_deals())
    row = result.clean.iloc[0]
    assert row["mrr_mxn"] == row["mrr_original"] == "5000.00"
    assert row["currency_original"] == "MXN"


def test_mismas_filas_y_mismo_orden() -> None:
    """companies_clean.csv trae las mismas filas de companies.csv, en el mismo orden."""
    companies = fixture_companies()
    result = run_clean(companies, fixture_deals())
    assert len(result.clean) == len(companies)
    assert list(result.clean["hubspot_id"]) == list(companies["hubspot_id"])


def test_columnas_originales_mas_las_nuevas() -> None:
    """El encabezado de companies_clean.csv conserva las columnas originales y agrega las cinco de auditoria."""
    result = run_clean(fixture_companies(), fixture_deals())
    expected = list(COMPANIES_COLUMNS) + ["mrr_mxn", "mrr_original", "currency_original", "mrr_source", "mrr_confidence"]
    assert list(result.clean.columns) == expected


def test_detect_missing_mrr_deja_las_filas_con_valor_como_crm() -> None:
    """Una fila con mrr no vacio queda con mrr_source = 'crm', sin correccion."""
    companies = pd.DataFrame([_company("HS-100001", mrr="5000")], columns=COMPANIES_COLUMNS)
    result, corrections = detect_missing_mrr(companies)
    assert result.at[0, "mrr_source"] == "crm"
    assert corrections == []


def test_detect_missing_mrr_sin_mrr_confidence_previa_no_revienta() -> None:
    """Un frame con mrr_source de una corrida previa pero sin la columna mrr_confidence no revienta (R2-01)."""
    companies = pd.DataFrame(
        [_company("HS-100012", mrr="4000", mrr_source="imputed_from_deal")],
        columns=list(COMPANIES_COLUMNS) + ["mrr_source"],
    )
    result, corrections = detect_missing_mrr(companies)
    assert result.at[0, "mrr_source"] == "imputed_from_deal"
    assert result.at[0, "mrr_confidence"] == "none"
    assert corrections == []


def test_convert_currency_no_revienta_con_moneda_no_soportada() -> None:
    """Una moneda fuera de {USD, MXN} no revienta la corrida: la fila queda intacta y sale como currency_unsupported."""
    companies = pd.DataFrame([_company("HS-100007", mrr="100", currency="EUR")], columns=COMPANIES_COLUMNS)
    result, corrections = convert_currency(companies)
    assert result.at[0, "mrr"] == "100"
    assert len(corrections) == 1
    assert corrections[0].exception_code == "currency_unsupported"


# --- moneda no soportada, tolerante de punta a punta -------------------------


def test_moneda_no_soportada_no_aborta_la_corrida_end_to_end() -> None:
    """Una fila en EUR llega intacta a run_clean, pasa los contratos y escribe las cuatro salidas via cmd_clean."""
    companies = pd.DataFrame([_company("HS-100007", mrr="300", currency="EUR")], columns=COMPANIES_COLUMNS)
    deals = fixture_deals()
    result = run_clean(companies, deals)

    run_cleaning_contracts(result.clean, companies, result.exceptions, result.counts, run_clean, deals)

    row = result.clean.iloc[0]
    assert row["currency"] == "EUR"
    assert row["currency_original"] == "EUR"
    assert row["mrr_mxn"] == ""
    assert row["mrr_source"] == "unresolved"

    exception = result.exceptions[result.exceptions["source_id"] == "HS-100007"].iloc[0]
    assert exception["exception_code"] == "currency_unsupported"
    assert exception["original_value"] == "EUR"


def test_moneda_no_soportada_via_cmd_clean(tmp_path: Path) -> None:
    """El comando clean termina en 0 y escribe las cuatro salidas aunque una fila traiga una moneda no soportada."""
    companies = pd.DataFrame([_company("HS-100007", mrr="300", currency="EUR")], columns=COMPANIES_COLUMNS)
    data_dir = tmp_path / "sistemas"
    data_dir.mkdir()
    companies.to_csv(data_dir / "crm_hubspot__companies.csv", index=False)
    fixture_deals().to_csv(data_dir / "crm_hubspot__deals.csv", index=False)
    out_dir = tmp_path / "out"

    exit_code = cli_main(["clean", "--data-dir", str(data_dir), "--out-dir", str(out_dir)])

    assert exit_code == 0
    for name in ("companies_clean.csv", "cleaning_exceptions.csv", "cleaning_log.json", "cleaning_log.md"):
        assert (out_dir / name).is_file()


# --- mrr no numerico, distinto de moneda no soportada -------------------------


@pytest.mark.parametrize(
    ("hubspot_id", "raw_mrr", "currency"),
    [
        ("HS-100008", "1,234", "MXN"),
        ("HS-100009", "1,234", "USD"),
        ("HS-100010", "n/a", "MXN"),
        ("HS-100011", "n/a", "USD"),
    ],
)
def test_mrr_no_numerico_no_se_confunde_con_moneda_no_soportada(hubspot_id: str, raw_mrr: str, currency: str) -> None:
    """Un mrr no numerico sale como mrr_not_numeric, nunca como currency_unsupported, y mrr_mxn se queda vacio."""
    companies = pd.DataFrame([_company(hubspot_id, mrr=raw_mrr, currency=currency)], columns=COMPANIES_COLUMNS)
    deals = fixture_deals()
    result = run_clean(companies, deals)

    run_cleaning_contracts(result.clean, companies, result.exceptions, result.counts, run_clean, deals)

    row = result.clean.iloc[0]
    assert row["mrr"] == raw_mrr
    assert row["mrr_mxn"] == ""
    assert row["mrr_source"] == "unresolved"
    assert row["currency"] == "MXN"

    exception = result.exceptions[result.exceptions["source_id"] == hubspot_id].iloc[0]
    assert exception["exception_code"] == "mrr_not_numeric"
    assert exception["original_value"] == raw_mrr

    not_numeric_rule = next(rule for rule in result.counts["rules"] if rule["rule"] == "missing_mrr")
    assert not_numeric_rule["not_numeric"] == 1


def test_mrr_no_numerico_se_reemite_en_cada_corrida() -> None:
    """mrr_not_numeric es un reporte, no una correccion: la segunda corrida sobre la salida limpia lo repite igual."""
    companies = pd.DataFrame([_company("HS-100008", mrr="1,234", currency="MXN")], columns=COMPANIES_COLUMNS)
    deals = fixture_deals()

    first = run_clean(companies, deals)
    second = run_clean(first.clean, deals)

    for result in (first, second):
        exception = result.exceptions[result.exceptions["source_id"] == "HS-100008"]
        assert len(exception) == 1 and exception.iloc[0]["exception_code"] == "mrr_not_numeric"

    assert second.counts["totals"]["corrections"] == 0
    assert second.clean.equals(first.clean)
    assert second.exceptions.equals(first.exceptions)


def test_companies_csv_vacio_termina_con_codigo_2_sin_salida(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Un companies.csv de 0 bytes termina en 2 con un mensaje que lo nombra, sin escribir salidas."""
    data_dir = tmp_path / "sistemas"
    data_dir.mkdir()
    (data_dir / "crm_hubspot__companies.csv").write_bytes(b"")
    fixture_deals().to_csv(data_dir / "crm_hubspot__deals.csv", index=False)
    out_dir = tmp_path / "out"

    with pytest.raises(SystemExit) as exit_info:
        cli_main(["clean", "--data-dir", str(data_dir), "--out-dir", str(out_dir)])
    assert exit_info.value.code == 2
    err = capsys.readouterr().err
    assert "companies.csv" in err and "vacio" in err
    assert list(out_dir.glob("*")) == []


def test_companies_csv_no_utf8_termina_con_codigo_2_sin_salida(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Un companies.csv con un byte Windows-1252 en un nombre termina en 2 con un mensaje que lo nombra."""
    data_dir = tmp_path / "sistemas"
    data_dir.mkdir()
    csv_bytes = fixture_companies().to_csv(index=False).encode("utf-8").replace(b"Empresa HS-100001", b"Empresa HS-100001 \xf1")
    (data_dir / "crm_hubspot__companies.csv").write_bytes(csv_bytes)
    fixture_deals().to_csv(data_dir / "crm_hubspot__deals.csv", index=False)
    out_dir = tmp_path / "out"

    with pytest.raises(SystemExit) as exit_info:
        cli_main(["clean", "--data-dir", str(data_dir), "--out-dir", str(out_dir)])
    assert exit_info.value.code == 2
    err = capsys.readouterr().err
    assert "companies.csv" in err and "UTF-8" in err
    assert list(out_dir.glob("*")) == []


@pytest.mark.parametrize("raw_mrr", ["nan", "inf", "-inf"])
def test_mrr_no_finito_se_reporta_como_no_numerico(raw_mrr: str) -> None:
    """`float` acepta nan e inf sin error; para un monto cuentan como texto no numerico y nunca llegan a mrr_mxn."""
    companies = pd.DataFrame([_company("HS-100009", mrr=raw_mrr, currency="USD")], columns=COMPANIES_COLUMNS)
    deals = fixture_deals()
    result = run_clean(companies, deals)

    run_cleaning_contracts(result.clean, companies, result.exceptions, result.counts, run_clean, deals)

    row = result.clean.iloc[0]
    assert row["mrr"] == raw_mrr
    assert row["mrr_mxn"] == ""
    assert row["mrr_source"] == "unresolved"
    exception = result.exceptions[result.exceptions["source_id"] == "HS-100009"]
    assert len(exception) == 1 and exception.iloc[0]["exception_code"] == "mrr_not_numeric"
