"""Permite `python -m worky_engine`, que reenvia a `cli.main`."""

from __future__ import annotations

from worky_engine.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
