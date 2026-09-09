"""Wrapper delgado sobre `python -m worky_engine clean` (D12): solo reenvia sys.argv, sin logica propia.

Sin instalacion editable del paquete, `python scripts/clean_companies.py`
pone `scripts/` en `sys.path[0]` en vez de la raiz del repositorio; la
insercion de abajo solo repara esa resolucion de import, no agrega
ninguna regla de negocio.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from worky_engine.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["clean", *sys.argv[1:]]))
