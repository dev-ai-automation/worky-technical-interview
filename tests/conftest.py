"""Configuracion compartida de pytest para el motor del dataset maestro.

Resuelve la carpeta con las tres bases SQLite reales en este orden: la
opcion `--data-dir`, la variable de entorno `WORKY_DATA_DIR` y, al
final, `data/raw/sistemas`. Esa ultima ruta es la que deja la extraccion
de `fundation-docs/dataset_caso_v3.zip` (tarea 1.1 del PR 1): el zip
guarda sus tres bases dentro de una carpeta `sistemas/`, por eso la ruta
final no es `fundation-docs/dataset_caso_v3` tal como la nombra la
seccion 6 del diseno, sino esta carpeta ya extraida. Cuando ninguna de
las tres opciones resuelve, las pruebas marcadas `dataset` se saltan con
un motivo que nombra la ruta que falto.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "raw" / "sistemas"
REQUIRED_DB_FILES = ("crm_hubspot.db", "product_db.db", "vitally_support.db")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--data-dir",
        action="store",
        default=None,
        help="Carpeta con las tres bases SQLite reales del caso.",
    )


def _has_required_dbs(path: Path) -> bool:
    return path.is_dir() and all((path / name).is_file() for name in REQUIRED_DB_FILES)


def _resolve_data_dir(config: pytest.Config) -> Path | None:
    candidates = (
        config.getoption("--data-dir"),
        os.environ.get("WORKY_DATA_DIR"),
        str(DEFAULT_DATA_DIR),
    )
    for candidate in candidates:
        if not candidate:
            continue
        candidate_path = Path(candidate)
        if _has_required_dbs(candidate_path):
            return candidate_path
    return None


@pytest.fixture(scope="session")
def data_dir(request: pytest.FixtureRequest) -> Path | None:
    """Entrega la carpeta con las tres bases SQLite reales, o None si falta."""
    return _resolve_data_dir(request.config)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _resolve_data_dir(config) is not None:
        return
    reason = (
        "requiere el dataset real: no se encontro en --data-dir, "
        f"WORKY_DATA_DIR ni en {DEFAULT_DATA_DIR}"
    )
    skip_dataset = pytest.mark.skip(reason=reason)
    for item in items:
        if "dataset" in item.keywords:
            item.add_marker(skip_dataset)
