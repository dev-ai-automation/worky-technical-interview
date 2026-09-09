"""Interfaz de linea de comandos del motor: `build`, `resolve`, `backtest`, `analyze` y `health`.

`backtest` (PR 4b, seccion 5.3 del diseno) corre aparte de `build`: no
depende de `master_dataset.csv` ni de DuckDB, asi que puede reproducirse
sin haber corrido un build primero, y su golden (`backtest_report.md`)
se versiona por separado. `analyze` (A1, ADR-004) tampoco depende de
`build`: abre su propia conexion, resuelve identidad en memoria y nunca
lee `outputs/` (decisiones D1 y D3 del diseno de `sql-analysis`).
`resolve_identity`, `assemble_master_dataset` y `open_connection` se
importan de forma diferida, en el primer uso dentro de cada comando,
para poder capturar la falta de `rapidfuzz` o `duckdb` como un mensaje
claro en espanol en vez de un traceback al cargar el modulo (requisito
de mensajes claros de build-cli).
`resolve` y `build` aceptan `--overrides` (A4, D14 y D15 del diseno de
`a4-warehouse-model`): un CSV opcional que fija manualmente el
`master_id` de un registro despues de la cascada. Sin el archivo, sus
salidas quedan identicas a las de antes de este cambio.
`warehouse` (A4, ADR-006) tampoco depende de `build`: mismo orden que
`analyze` y `health` (D1), con su propia conexion persistida entre
corridas (D2, excepcion documentada a D6 de A0). Escribe
`map_source_identity.csv` y `dim_company.csv`, poblada por el
algoritmo de SCD2 (D4 a D8) y validada por `--run-date` contra el
`effective_from` vigente mas reciente ya persistido.
`clean` (A6, ADR-002) lee companies.csv y deals.csv en texto puro y
nunca las tres bases SQLite (D2, D3 del diseno de `a6-cleaning-script`):
`_locate_clean_data_dir` solo reutiliza la extraccion del zip de
`_resolve_data_dir` para ubicar la carpeta, nunca su lectura via
`sqlite3`. Corre las tres detecciones de este PR (fechas, moneda, mrr
nulo con exclusion de clones; la imputacion del ADR-002 se conecta en
PR2) y escribe companies_clean.csv, cleaning_exceptions.csv,
cleaning_log.json y cleaning_log.md en `--out-dir`.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

from worky_engine.quality import ContractViolation, generate_coverage_report, run_contracts
from worky_engine.sources import REQUIRED_DB_FILES, load_raw_tables
from worky_engine.writers import write_csv, write_markdown

ZIP_NAME = "dataset_caso_v3.zip"
DEFAULT_DB_PATH = Path(".build") / "worky.duckdb"
DEFAULT_ANALYSIS_DB_PATH = Path(".build") / "worky_analysis.duckdb"
DEFAULT_ANALYSIS_OUT_DIR = Path("outputs") / "analysis"
DEFAULT_HEALTH_DB_PATH = Path(".build") / "worky_health.duckdb"
DEFAULT_HEALTH_OUT_DIR = Path("outputs") / "health"
DEFAULT_OVERRIDES_PATH = Path("data") / "identity_overrides.csv"
DEFAULT_WAREHOUSE_DB_PATH = Path(".build") / "warehouse.duckdb"
DEFAULT_WAREHOUSE_OUT_DIR = Path("outputs") / "warehouse"
DEFAULT_CLEAN_DATA_DIR = Path("data") / "raw" / "sistemas"
DEFAULT_CLEAN_OUT_DIR = Path("outputs") / "clean"
CLEAN_COMPANIES_FILENAME = "crm_hubspot__companies.csv"
CLEAN_DEALS_FILENAME = "crm_hubspot__deals.csv"


def _exit_missing_dependency(error: ImportError) -> None:
    """Termina con codigo 2 y un mensaje en espanol que nombra la dependencia y como instalarla."""
    missing = error.name or "una dependencia"
    print(
        f"worky_engine: falta instalar la dependencia '{missing}'. Corre: pip install {missing}",
        file=sys.stderr,
    )
    raise SystemExit(2)


def _import_resolve_dependency():
    """Importa `resolve_identity` y los overrides en el primer uso; solo `resolve` y `build` los necesitan."""
    try:
        from worky_engine.identity_resolution import resolve_identity
        from worky_engine.identity_resolution.overrides import apply_overrides, load_overrides
    except ImportError as error:
        _exit_missing_dependency(error)
    return resolve_identity, load_overrides, apply_overrides


def _import_build_dependencies():
    """Importa `resolve_identity`, los overrides y las piezas de DuckDB en el primer uso, solo para `build`."""
    try:
        from worky_engine.identity_resolution import resolve_identity
        from worky_engine.identity_resolution.overrides import apply_overrides, load_overrides
        from worky_engine.master_dataset import assemble_master_dataset, open_connection
    except ImportError as error:
        _exit_missing_dependency(error)
    return resolve_identity, load_overrides, apply_overrides, assemble_master_dataset, open_connection


def _import_backtest_dependencies():
    """Importa el harness en el primer uso; solo `backtest` lo necesita."""
    try:
        from worky_engine.harness import format_report, run_backtest
    except ImportError as error:
        _exit_missing_dependency(error)
    return run_backtest, format_report


def _import_analyze_dependencies():
    """Importa las piezas de `analyze` en el primer uso: DuckDB, el corredor de A1, `report.py` y sus contratos."""
    try:
        from worky_engine.analysis.report import format_report
        from worky_engine.analysis.runner import ANALYSIS_OUTPUTS, run_analysis
        from worky_engine.identity_resolution import resolve_identity
        from worky_engine.master_dataset import assemble_master_dataset, open_connection
        from worky_engine.quality.analysis_contracts import run_analysis_contracts
    except ImportError as error:
        _exit_missing_dependency(error)
    return (
        resolve_identity,
        assemble_master_dataset,
        open_connection,
        run_analysis,
        run_analysis_contracts,
        ANALYSIS_OUTPUTS,
        format_report,
    )


def _import_health_dependencies():
    """Importa las piezas de `health` en el primer uso: DuckDB, el corredor de A3, `report.py` y sus contratos."""
    try:
        from worky_engine.health.report import format_validation
        from worky_engine.health.runner import run_health
        from worky_engine.identity_resolution import resolve_identity
        from worky_engine.master_dataset import assemble_master_dataset, open_connection
        from worky_engine.quality.health_contracts import run_health_contracts
    except ImportError as error:
        _exit_missing_dependency(error)
    return resolve_identity, assemble_master_dataset, open_connection, run_health, run_health_contracts, format_validation


def _import_warehouse_dependencies():
    """Importa las piezas de `warehouse` en el primer uso: DuckDB, overrides, el corredor de A4 y sus contratos."""
    try:
        from worky_engine.identity_resolution import resolve_identity
        from worky_engine.identity_resolution.overrides import apply_overrides, load_overrides
        from worky_engine.master_dataset import assemble_master_dataset
        from worky_engine.quality.warehouse_contracts import run_warehouse_contracts
        from worky_engine.warehouse import open_warehouse_connection, run_warehouse
    except ImportError as error:
        _exit_missing_dependency(error)
    return (
        resolve_identity,
        load_overrides,
        apply_overrides,
        assemble_master_dataset,
        open_warehouse_connection,
        run_warehouse,
        run_warehouse_contracts,
    )


def _import_clean_dependencies():
    """Importa el paquete `cleaning` y sus contratos en el primer uso; solo `clean` los necesita."""
    try:
        from worky_engine.cleaning import format_cleaning_log, run_clean
        from worky_engine.quality.cleaning_contracts import run_cleaning_contracts
    except ImportError as error:
        _exit_missing_dependency(error)
    return run_clean, run_cleaning_contracts, format_cleaning_log


def _reconfigure_streams_to_utf8() -> None:
    """Reconfigura `stdout`/`stderr` a UTF-8 antes de imprimir cualquier cosa.

    La consola de Windows abre en cp1252 por omision, y un nombre real
    del dataset con acento tiraria el proceso al escribirlo sin este
    ajuste, segun la seccion 3.1 del diseno.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def _resolve_data_dir(data_dir: Path) -> Path:
    """Devuelve la carpeta con las tres bases SQLite, extrayendo el zip si hace falta."""
    if all((data_dir / name).is_file() for name in REQUIRED_DB_FILES):
        return data_dir

    zip_path = data_dir / ZIP_NAME
    if zip_path.is_file():
        extract_dir = Path(".build") / "dataset"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)
        # el zip guarda sus tres bases dentro de una carpeta "sistemas/"
        nested = extract_dir / "sistemas"
        if all((nested / name).is_file() for name in REQUIRED_DB_FILES):
            return nested
        if all((extract_dir / name).is_file() for name in REQUIRED_DB_FILES):
            return extract_dir

    print(
        f"no se encontraron las tres bases SQLite en {data_dir} ni un {ZIP_NAME} para extraer",
        file=sys.stderr,
    )
    raise SystemExit(2)


def _locate_clean_data_dir(data_dir: Path) -> Path:
    """Ubica la carpeta con companies.csv y deals.csv para `clean`, extrayendo el zip si data_dir solo lo trae.

    A diferencia de `_resolve_data_dir`, nunca exige las tres bases
    SQLite (D2 del diseno de `a6-cleaning-script`): solo revisa que la
    carpeta candidata tenga los dos CSV. Si ninguna candidata los trae,
    devuelve `data_dir` sin cambios para que `_resolve_clean_inputs`
    nombre el archivo que falta sobre esa misma ruta.
    """
    candidates = [data_dir]
    zip_path = data_dir / ZIP_NAME
    if zip_path.is_file():
        extract_dir = Path(".build") / "dataset"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)
        candidates.append(extract_dir / "sistemas")
        candidates.append(extract_dir)
    for candidate in candidates:
        if (candidate / CLEAN_COMPANIES_FILENAME).is_file() and (candidate / CLEAN_DEALS_FILENAME).is_file():
            return candidate
    return data_dir


def _resolve_clean_inputs(args: argparse.Namespace) -> tuple[Path, Path]:
    """Resuelve companies.csv y deals.csv: `--companies`/`--deals` sueltos, o dentro de `--data-dir` (D2).

    Sin el archivo, termina en 2 nombrando cual de los dos falta, sin
    escribir ninguna salida parcial (requisito "entradas requeridas
    companies.csv y deals.csv").
    """
    data_dir = _locate_clean_data_dir(Path(args.data_dir))
    companies_path = Path(args.companies) if args.companies else data_dir / CLEAN_COMPANIES_FILENAME
    deals_path = Path(args.deals) if args.deals else data_dir / CLEAN_DEALS_FILENAME
    if not companies_path.is_file():
        print(f"clean: no se encontro companies.csv en '{companies_path}'", file=sys.stderr)
        raise SystemExit(2)
    if not deals_path.is_file():
        print(f"clean: no se encontro deals.csv en '{deals_path}'", file=sys.stderr)
        raise SystemExit(2)
    return companies_path, deals_path


def _load_existing_crosswalk(out_dir: Path) -> pd.DataFrame | None:
    path = out_dir / "identity_crosswalk.csv"
    if path.is_file():
        return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], encoding="utf-8")
    return None


def _apply_overrides_if_present(
    load_overrides,
    apply_overrides,
    overrides_path: Path,
    identity_outputs: dict[str, pd.DataFrame],
    raw_tables: dict[str, pd.DataFrame],
    command_name: str,
) -> dict[str, pd.DataFrame]:
    """Aplica `identity_overrides.csv` sobre `identity_outputs` justo despues de la cascada, si el archivo existe.

    Sin archivo, `identity_outputs` regresa sin tocar (D14): las salidas
    de `resolve`, `build` y `warehouse` quedan identicas a las de antes
    de este cambio. Una fila invalida termina el comando con codigo de
    salida 1 y un mensaje que nombra la fila y el motivo, sin escribir
    nada (requisito "precedencia de overrides sobre la cascada").
    """
    if not overrides_path.is_file():
        return identity_outputs

    from worky_engine.identity_resolution.overrides import OverrideError

    try:
        overrides = load_overrides(overrides_path)
        return apply_overrides(overrides, identity_outputs, raw_tables)
    except OverrideError as error:
        print(f"{command_name}: {error}", file=sys.stderr)
        raise SystemExit(1) from error


def cmd_resolve(args: argparse.Namespace) -> int:
    """Corre solo la capa de identidad y escribe sus cuatro salidas en `--out-dir`.

    Aplica `--overrides` justo despues de la cascada y antes de escribir,
    solo si el archivo existe (D14, D15).
    """
    resolve_identity, load_overrides, apply_overrides = _import_resolve_dependency()
    data_dir = _resolve_data_dir(Path(args.data_dir))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_tables = load_raw_tables(data_dir)
    existing_crosswalk = _load_existing_crosswalk(out_dir)
    outputs = resolve_identity(
        raw_tables, existing_crosswalk, reuse_crosswalk=not args.no_reuse_crosswalk
    )
    outputs = _apply_overrides_if_present(
        load_overrides, apply_overrides, Path(args.overrides), outputs, raw_tables, "resolve"
    )

    write_csv(outputs["identity_crosswalk"], out_dir / "identity_crosswalk.csv")
    write_csv(outputs["match_audit"], out_dir / "match_audit.csv")
    write_csv(outputs["quarantine_companies"], out_dir / "quarantine_companies.csv")
    write_csv(outputs["quarantine_deals"], out_dir / "quarantine_deals.csv")

    print(f"resolve: {len(outputs['identity_crosswalk'])} empresas resueltas en {out_dir}")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    """Corre `resolve` y despues el ensamblaje: escribe las salidas de identidad mas este PR.

    `master_dataset.csv` y `exceptions_log.csv` solo se escriben cuando
    los contratos de `worky_engine.quality.contracts` pasan; una
    violacion detiene el build con codigo de salida 1 y nombra el
    contrato en el mensaje, segun el requisito de mensajes claros de
    `build-cli`. `coverage_report.md` se genera al final, a partir de las
    mismas salidas ya materializadas. Aplica `--overrides` justo despues
    de la cascada y antes de escribir, solo si el archivo existe (D14, D15).
    """
    resolve_identity, load_overrides, apply_overrides, assemble_master_dataset, open_connection = (
        _import_build_dependencies()
    )
    data_dir = _resolve_data_dir(Path(args.data_dir))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_tables = load_raw_tables(data_dir)
    existing_crosswalk = _load_existing_crosswalk(out_dir)
    identity_outputs = resolve_identity(
        raw_tables, existing_crosswalk, reuse_crosswalk=not args.no_reuse_crosswalk
    )
    identity_outputs = _apply_overrides_if_present(
        load_overrides, apply_overrides, Path(args.overrides), identity_outputs, raw_tables, "build"
    )
    for name, frame in identity_outputs.items():
        write_csv(frame, out_dir / f"{name}.csv")

    con = open_connection(args.db_path)
    try:
        assembly_outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
    finally:
        con.close()

    try:
        run_contracts(
            assembly_outputs["master_dataset"],
            identity_outputs["identity_crosswalk"],
            assembly_outputs["exceptions_log"],
            identity_outputs["match_audit"],
            raw_tables,
            identity_outputs["quarantine_companies"],
        )
    except ContractViolation as error:
        print(f"build: {error}", file=sys.stderr)
        return 1

    write_csv(assembly_outputs["master_dataset"], out_dir / "master_dataset.csv")
    write_csv(assembly_outputs["exceptions_log"], out_dir / "exceptions_log.csv")

    report_text = generate_coverage_report(identity_outputs, assembly_outputs)
    write_markdown(report_text, out_dir / "coverage_report.md")

    print(f"build: {len(assembly_outputs['master_dataset'])} empresas ensambladas en {out_dir}")
    return 0


def cmd_backtest(args: argparse.Namespace) -> int:
    """Corre el harness del ADR-003 y escribe `backtest_report.md` en `--out-dir`.

    No corre `build`: lee las tres bases directo con `load_raw_tables`,
    tal como fija la seccion 5.3 del diseno.
    """
    run_backtest, format_report = _import_backtest_dependencies()
    data_dir = _resolve_data_dir(Path(args.data_dir))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_tables = load_raw_tables(data_dir)
    k_values = tuple(int(part) for part in args.k.split(","))
    metrics = run_backtest(raw_tables, k_values=k_values, flag_rate=args.flag_rate)
    report_text = format_report(metrics, k_values)
    write_markdown(report_text, out_dir / "backtest_report.md")

    print(f"backtest: reporte escrito en {out_dir / 'backtest_report.md'}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    """Corre identidad, ensamblaje y las siete consultas de A1, sin `build` previo.

    Abre su propia conexion de DuckDB, corre `resolve_identity` en
    memoria y nunca lee `outputs/` (decisiones D1 y D3 del diseno de
    `sql-analysis`). Corre los contratos de A0 sobre el dataset que
    acaba de ensamblar antes de correr los propios de A1 (decision
    D14), escribe un CSV por salida de `ANALYSIS_OUTPUTS` (incluye
    `analysis_exceptions.csv`) mas `report.md`, y termina con los
    mismos codigos de salida que `build`.
    """
    (
        resolve_identity,
        assemble_master_dataset,
        open_connection,
        run_analysis,
        run_analysis_contracts,
        analysis_outputs,
        format_report,
    ) = _import_analyze_dependencies()
    data_dir = _resolve_data_dir(Path(args.data_dir))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_tables = load_raw_tables(data_dir)
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)

    con = open_connection(args.db_path)
    try:
        assembly_outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
        try:
            run_contracts(
                assembly_outputs["master_dataset"],
                identity_outputs["identity_crosswalk"],
                assembly_outputs["exceptions_log"],
                identity_outputs["match_audit"],
                raw_tables,
                identity_outputs["quarantine_companies"],
            )
        except ContractViolation as error:
            print(f"analyze: {error}", file=sys.stderr)
            return 1

        result = run_analysis(con)
        try:
            run_analysis_contracts(
                result.outputs, assembly_outputs["master_dataset"], identity_outputs["quarantine_deals"]
            )
        except ContractViolation as error:
            print(f"analyze: {error}", file=sys.stderr)
            return 1
    finally:
        con.close()

    for item in analysis_outputs:
        write_csv(result.outputs[item.view], out_dir / item.file_name)

    report_text = format_report(result)
    write_markdown(report_text, out_dir / "report.md")

    queries_written = sum(1 for item in analysis_outputs if item.view.startswith("analysis_a1_"))
    print(f"analyze: {queries_written} consultas escritas en {out_dir}")
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    """Corre identidad, ensamblaje y las tres corridas de A3 (ADR-005), sin `build` previo.

    Mismo orden que `cmd_analyze`: importacion diferida, `_resolve_data_dir`,
    `load_raw_tables`, `resolve_identity` en memoria, `open_connection`
    propio, `assemble_master_dataset`, `run_contracts` de A0 sobre el
    dataset recien ensamblado, `run_health`, `run_health_contracts`,
    `write_csv` y `write_markdown`. Escribe `health_scores.csv` y
    `validation.md` en `--out-dir`. Mismos codigos de salida que
    `build` y `analyze`.
    """
    (
        resolve_identity,
        assemble_master_dataset,
        open_connection,
        run_health,
        run_health_contracts,
        format_validation,
    ) = _import_health_dependencies()
    data_dir = _resolve_data_dir(Path(args.data_dir))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_tables = load_raw_tables(data_dir)
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)

    con = open_connection(args.db_path)
    try:
        assembly_outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
        try:
            run_contracts(
                assembly_outputs["master_dataset"],
                identity_outputs["identity_crosswalk"],
                assembly_outputs["exceptions_log"],
                identity_outputs["match_audit"],
                raw_tables,
                identity_outputs["quarantine_companies"],
            )
        except ContractViolation as error:
            print(f"health: {error}", file=sys.stderr)
            return 1

        result = run_health(con)
        try:
            run_health_contracts(result.scores, result.formatted, assembly_outputs["master_dataset"])
        except ContractViolation as error:
            print(f"health: {error}", file=sys.stderr)
            return 1
    finally:
        con.close()

    write_csv(result.formatted, out_dir / "health_scores.csv")
    write_markdown(format_validation(result), out_dir / "validation.md")

    print(f"health: {len(result.formatted)} empresas puntuadas en {out_dir}")
    return 0


def cmd_warehouse(args: argparse.Namespace) -> int:
    """Corre identidad, ensamblaje y el esquema en estrella de A4, sin `build` previo.

    Mismo orden que `cmd_analyze` y `cmd_health` (D1): importacion
    diferida, `_resolve_data_dir`, `load_raw_tables`, `resolve_identity`
    en memoria, `apply_overrides` si `--overrides` existe (D15,
    reutiliza `overrides.py` del PR1), conexion propia que no borra su
    archivo entre corridas (`open_warehouse_connection`, D2), validacion
    de `--run-date` (PR3, seccion 2 del diseno: formato ISO y nunca
    anterior al `effective_from` vigente mas reciente ya persistido),
    `assemble_master_dataset`, `run_contracts` de A0 sobre el dataset
    recien ensamblado, `run_warehouse` (que ahora corre el algoritmo de
    SCD2 de `dim_company` y la foto de `fact_health_score_monthly`,
    PR3), `run_warehouse_contracts` y dos `write_csv`. Mismos codigos
    de salida que `build`, `analyze` y `health`; un `--run-date`
    invalido tambien termina en 1.
    """
    (
        resolve_identity,
        load_overrides,
        apply_overrides,
        assemble_master_dataset,
        open_warehouse_connection,
        run_warehouse,
        run_warehouse_contracts,
    ) = _import_warehouse_dependencies()
    data_dir = _resolve_data_dir(Path(args.data_dir))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_tables = load_raw_tables(data_dir)
    identity_outputs = resolve_identity(raw_tables, existing_crosswalk=None, reuse_crosswalk=True)

    overrides_path = Path(args.overrides)
    overrides_frame = None
    if overrides_path.is_file():
        from worky_engine.identity_resolution.overrides import OverrideError

        try:
            overrides_frame = load_overrides(overrides_path)
            identity_outputs = apply_overrides(overrides_frame, identity_outputs, raw_tables)
        except OverrideError as error:
            print(f"warehouse: {error}", file=sys.stderr)
            return 1

    con = open_warehouse_connection(args.db_path)
    try:
        run_date = args.run_date
        if run_date is not None:
            try:
                date.fromisoformat(run_date)
            except ValueError:
                print(f"warehouse: --run-date '{run_date}' no tiene formato ISO (YYYY-MM-DD)", file=sys.stderr)
                return 1
            dim_company_exists = con.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'dim_company'"
            ).fetchone()[0]
            max_effective_from = (
                con.execute("SELECT MAX(effective_from) FROM dim_company WHERE is_current").fetchone()[0]
                if dim_company_exists
                else None
            )
            if max_effective_from is not None and run_date < str(max_effective_from):
                print(
                    f"warehouse: --run-date '{run_date}' es anterior al effective_from vigente mas "
                    f"reciente ({max_effective_from})",
                    file=sys.stderr,
                )
                return 1

        assembly_outputs = assemble_master_dataset(con, raw_tables, identity_outputs)
        try:
            run_contracts(
                assembly_outputs["master_dataset"],
                identity_outputs["identity_crosswalk"],
                assembly_outputs["exceptions_log"],
                identity_outputs["match_audit"],
                raw_tables,
                identity_outputs["quarantine_companies"],
            )
        except ContractViolation as error:
            print(f"warehouse: {error}", file=sys.stderr)
            return 1

        result = run_warehouse(con, overrides_frame, run_date)
        try:
            run_warehouse_contracts(
                result.map_source_identity,
                result.overrides,
                result.dim_company,
                result.fact_health_score_monthly,
            )
        except ContractViolation as error:
            print(f"warehouse: {error}", file=sys.stderr)
            return 1
    finally:
        con.close()

    write_csv(result.map_source_identity, out_dir / "map_source_identity.csv")
    write_csv(result.dim_company, out_dir / "dim_company.csv")

    current_companies = int(result.dim_company["is_current"].sum())
    print(
        f"warehouse: {current_companies} empresas vigentes y {len(result.map_source_identity)} "
        f"vinculos en {out_dir}"
    )
    return 0


def _read_clean_csv(path: Path) -> pd.DataFrame:
    """Lee un CSV de `clean` en texto puro; un archivo vacio o que no sea UTF-8 termina en 2 sin traceback."""
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    except pd.errors.EmptyDataError:
        print(f"clean: '{path}' esta vacio, no se puede leer como CSV", file=sys.stderr)
        raise SystemExit(2)
    except UnicodeDecodeError:
        print(f"clean: '{path}' no esta en UTF-8", file=sys.stderr)
        raise SystemExit(2)


def cmd_clean(args: argparse.Namespace) -> int:
    """Corre las tres detecciones de A6 sobre companies.csv y deals.csv, sin build previo.

    Lee ambos CSV en texto puro (`dtype=str, keep_default_na=False`,
    D3), corre `run_clean` en el orden fijo de `worky_engine.cleaning`
    (fechas, moneda, deteccion de mrr nulo; la imputacion del ADR-002
    se conecta en PR2), corre los contratos de forma, moneda, fecha,
    unicidad e idempotencia disponibles en este PR y escribe las
    cuatro salidas en `--out-dir`. Mismos codigos de salida que los
    otros cinco comandos: 2 cuando falta un archivo, esta vacio, no
    esta en UTF-8 o falta una dependencia; 1 cuando un contrato se viola.
    """
    run_clean, run_cleaning_contracts, format_cleaning_log = _import_clean_dependencies()
    companies_path, deals_path = _resolve_clean_inputs(args)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    companies = _read_clean_csv(companies_path)
    deals = _read_clean_csv(deals_path)

    result = run_clean(companies, deals, companies_path.name, deals_path.name)

    try:
        run_cleaning_contracts(result.clean, companies, result.exceptions, result.counts, run_clean, deals)
    except ContractViolation as error:
        print(f"clean: {error}", file=sys.stderr)
        return 1

    write_csv(result.clean, out_dir / "companies_clean.csv")
    write_csv(result.exceptions, out_dir / "cleaning_exceptions.csv")
    with open(out_dir / "cleaning_log.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(result.counts, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    write_markdown(format_cleaning_log(result.counts), out_dir / "cleaning_log.md")

    total_corrections = result.counts["totals"]["corrections"]
    print(f"clean: {total_corrections} correcciones en {len(result.clean)} filas, salidas en {out_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="worky_engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve_parser = subparsers.add_parser("resolve", help="Resuelve identidad entre los tres sistemas.")
    resolve_parser.add_argument("--data-dir", required=True)
    resolve_parser.add_argument("--out-dir", required=True)
    resolve_parser.add_argument(
        "--no-reuse-crosswalk",
        action="store_true",
        help="Ignora el identity_crosswalk.csv existente y regenera todos los master_id por hash.",
    )
    resolve_parser.add_argument(
        "--overrides",
        default=str(DEFAULT_OVERRIDES_PATH),
        help="CSV de identity_overrides; se aplica solo si el archivo existe (por omision: data/identity_overrides.csv).",
    )
    resolve_parser.set_defaults(func=cmd_resolve)

    build_subparser = subparsers.add_parser("build", help="Corre resolve y el ensamblaje del dataset maestro.")
    build_subparser.add_argument("--data-dir", required=True)
    build_subparser.add_argument("--out-dir", required=True)
    build_subparser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    build_subparser.add_argument(
        "--no-reuse-crosswalk",
        action="store_true",
        help="Ignora el identity_crosswalk.csv existente y regenera todos los master_id por hash.",
    )
    build_subparser.add_argument(
        "--overrides",
        default=str(DEFAULT_OVERRIDES_PATH),
        help="CSV de identity_overrides; se aplica solo si el archivo existe (por omision: data/identity_overrides.csv).",
    )
    build_subparser.set_defaults(func=cmd_build)

    backtest_subparser = subparsers.add_parser(
        "backtest", help="Corre el harness del ADR-003 y escribe backtest_report.md."
    )
    backtest_subparser.add_argument("--data-dir", required=True)
    backtest_subparser.add_argument("--out-dir", required=True)
    backtest_subparser.add_argument(
        "--k", default="0,2,3", help="Valores de k separados por coma (por omision: 0,2,3)."
    )
    backtest_subparser.add_argument(
        "--flag-rate", type=float, default=0.20, help="Tasa de marcado para precision/recall (por omision: 0.20)."
    )
    backtest_subparser.set_defaults(func=cmd_backtest)

    analyze_subparser = subparsers.add_parser(
        "analyze", help="Corre A1.1 a A1.6 y escribe report.md sobre la sabana (ADR-004), sin build previo."
    )
    analyze_subparser.add_argument("--data-dir", required=True)
    analyze_subparser.add_argument("--out-dir", default=str(DEFAULT_ANALYSIS_OUT_DIR))
    analyze_subparser.add_argument("--db-path", default=str(DEFAULT_ANALYSIS_DB_PATH))
    analyze_subparser.set_defaults(func=cmd_analyze)

    health_subparser = subparsers.add_parser(
        "health",
        help="Corre el health score de A3 (ADR-005) y escribe health_scores.csv y validation.md, sin build previo.",
    )
    health_subparser.add_argument("--data-dir", required=True)
    health_subparser.add_argument("--out-dir", default=str(DEFAULT_HEALTH_OUT_DIR))
    health_subparser.add_argument("--db-path", default=str(DEFAULT_HEALTH_DB_PATH))
    health_subparser.set_defaults(func=cmd_health)

    warehouse_subparser = subparsers.add_parser(
        "warehouse",
        help="Corre el esquema en estrella de A4 (ADR-006) y escribe map_source_identity.csv, sin build previo.",
    )
    warehouse_subparser.add_argument("--data-dir", required=True)
    warehouse_subparser.add_argument("--out-dir", default=str(DEFAULT_WAREHOUSE_OUT_DIR))
    warehouse_subparser.add_argument("--db-path", default=str(DEFAULT_WAREHOUSE_DB_PATH))
    warehouse_subparser.add_argument(
        "--run-date",
        default=None,
        help=(
            "Fecha de corrida en formato YYYY-MM-DD; por omision, dataset_asof (D3). Nunca puede ser "
            "anterior al effective_from vigente mas reciente ya persistido."
        ),
    )
    warehouse_subparser.add_argument(
        "--overrides",
        default=str(DEFAULT_OVERRIDES_PATH),
        help="CSV de identity_overrides; se aplica solo si el archivo existe (por omision: data/identity_overrides.csv).",
    )
    warehouse_subparser.set_defaults(func=cmd_warehouse)

    clean_subparser = subparsers.add_parser(
        "clean",
        help="Corre las tres detecciones de A6 (fechas, moneda, mrr nulo) sobre companies.csv, sin build previo.",
    )
    clean_subparser.add_argument("--data-dir", default=str(DEFAULT_CLEAN_DATA_DIR))
    clean_subparser.add_argument("--out-dir", default=str(DEFAULT_CLEAN_OUT_DIR))
    clean_subparser.add_argument(
        "--companies", default=None, help="Ruta directa a companies.csv; por omision, <data-dir>/crm_hubspot__companies.csv."
    )
    clean_subparser.add_argument(
        "--deals", default=None, help="Ruta directa a deals.csv; por omision, <data-dir>/crm_hubspot__deals.csv."
    )
    clean_subparser.set_defaults(func=cmd_clean)

    return parser


def main(argv: list[str] | None = None) -> int:
    _reconfigure_streams_to_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
