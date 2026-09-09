"""Esquema en estrella ejecutable del warehouse (A4).

Expone `open_warehouse_connection` (conexion que persiste su archivo,
D2) y `run_warehouse` (orden fijo de `sql/warehouse/`, tablas
persistidas y `WarehouseResult`).
"""

from __future__ import annotations

from worky_engine.warehouse.db import open_warehouse_connection
from worky_engine.warehouse.runner import WAREHOUSE_FILES, WarehouseResult, run_warehouse

__all__ = ["open_warehouse_connection", "run_warehouse", "WAREHOUSE_FILES", "WarehouseResult"]
