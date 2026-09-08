"""Registro de tablas en DuckDB y ejecucion del SQL de staging y marts.

Expone `open_connection` y `assemble_master_dataset`, el punto exacto
donde el motor le entrega el control a SQL (seccion 1 del diseno).
"""

from __future__ import annotations

from worky_engine.master_dataset.assemble import assemble_master_dataset, open_connection

__all__ = ["assemble_master_dataset", "open_connection"]
