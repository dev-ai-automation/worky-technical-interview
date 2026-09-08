"""Interfaz de linea de comandos del motor: `build`, `resolve` y `backtest`.

Este PR agrega `build`; `backtest` llega en el PR 4, segun la seccion
5.3 del diseno. `resolve_identity`, `assemble_master_dataset` y
`open_connection` se importan de forma diferida, en el primer uso dentro
de cada comando, para poder capturar la falta de `rapidfuzz` o `duckdb`
como un mensaje claro en espanol en vez de un traceback al cargar el
modulo (requisito de mensajes claros de build-cli).
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import pandas as pd

from worky_engine.quality import ContractViolation, generate_coverage_report, run_contracts
from worky_engine.sources import REQUIRED_DB_FILES, load_raw_tables
from worky_engine.writers import write_csv, write_markdown

ZIP_NAME = "dataset_caso_v3.zip"
DEFAULT_DB_PATH = Path(".build") / "worky.duckdb"


def _exit_missing_dependency(error: ImportError) -> None:
    """Termina con codigo 2 y un mensaje en espanol que nombra la dependencia y como instalarla."""
    missing = error.name or "una dependencia"
    print(
        f"worky_engine: falta instalar la dependencia '{missing}'. Corre: pip install {missing}",
        file=sys.stderr,
    )
    raise SystemExit(2)


def _import_resolve_dependency():
    """Importa `resolve_identity` en el primer uso; solo `resolve` y `build` lo necesitan."""
    try:
        from worky_engine.identity_resolution import resolve_identity
    except ImportError as error:
        _exit_missing_dependency(error)
    return resolve_identity


def _import_build_dependencies():
    """Importa `resolve_identity` y las piezas de DuckDB en el primer uso, solo para `build`."""
    try:
        from worky_engine.identity_resolution import resolve_identity
        from worky_engine.master_dataset import assemble_master_dataset, open_connection
    except ImportError as error:
        _exit_missing_dependency(error)
    return resolve_identity, assemble_master_dataset, open_connection


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


def _load_existing_crosswalk(out_dir: Path) -> pd.DataFrame | None:
    path = out_dir / "identity_crosswalk.csv"
    if path.is_file():
        return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""], encoding="utf-8")
    return None


def cmd_resolve(args: argparse.Namespace) -> int:
    """Corre solo la capa de identidad y escribe sus cuatro salidas en `--out-dir`."""
    resolve_identity = _import_resolve_dependency()
    data_dir = _resolve_data_dir(Path(args.data_dir))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_tables = load_raw_tables(data_dir)
    existing_crosswalk = _load_existing_crosswalk(out_dir)
    outputs = resolve_identity(
        raw_tables, existing_crosswalk, reuse_crosswalk=not args.no_reuse_crosswalk
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
    mismas salidas ya materializadas.
    """
    resolve_identity, assemble_master_dataset, open_connection = _import_build_dependencies()
    data_dir = _resolve_data_dir(Path(args.data_dir))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_tables = load_raw_tables(data_dir)
    existing_crosswalk = _load_existing_crosswalk(out_dir)
    identity_outputs = resolve_identity(
        raw_tables, existing_crosswalk, reuse_crosswalk=not args.no_reuse_crosswalk
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
    build_subparser.set_defaults(func=cmd_build)

    return parser


def main(argv: list[str] | None = None) -> int:
    _reconfigure_streams_to_utf8()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
