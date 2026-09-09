# Progreso de aplicación: `a1-sql-queries`

## PR 1: corredor de análisis, subcomando `analyze`, A1.1, A1.2 y A1.5

**Estado**: completo. Las 11 tareas de PR 1 (1.1 a 1.11) están marcadas `[x]` en `tasks.md`.

### Tareas completadas

- [x] 1.1 `worky_engine/analysis/__init__.py` (expone `run_analysis`; `format_report` se agrega en PR 3, ver nota de desviación).
- [x] 1.2 `worky_engine/analysis/runner.py` con `ANALYSIS_FILES`, `ANALYSIS_OUTPUTS` y `run_analysis` (alcance de PR 1: solo A1.1, A1.2, A1.5; ver nota de desviación).
- [x] 1.3 `worky_engine/sql/analysis/a1_01_active_mrr.sql`.
- [x] 1.4 `worky_engine/sql/analysis/a1_02_usage_drop.sql`.
- [x] 1.5 `worky_engine/sql/analysis/a1_05_orphan_deals.sql`.
- [x] 1.6 `worky_engine/quality/analysis_contracts.py` con los seis contratos de PR 1 y `run_analysis_contracts`.
- [x] 1.7 `worky_engine/cli.py`: `cmd_analyze`, `_import_analyze_dependencies`, parser `analyze`.
- [x] 1.8 `tests/test_analysis_rules.py` (fixture propio, 9 pruebas).
- [x] 1.9 `tests/test_analysis_dataset_numbers.py` (marca `dataset`, 3 pruebas; cifra de `windows_overlap` corregida a 33, ver nota de desviación).
- [x] 1.10 `tests/test_analysis_idempotency.py` (marca `dataset`, 1 prueba).
- [x] 1.11 Cierre de PR 1: suite completa en verde, `analyze` corrido dos veces, `git status --short outputs` sin cambios en los ocho goldens de A0, goldens de `outputs/analysis/` generados.

### Archivos creados o modificados

| Archivo | Acción | Líneas (add/del) |
|---|---|---|
| `worky_engine/analysis/__init__.py` | crear | 13/0 |
| `worky_engine/analysis/runner.py` | crear | 79/0 |
| `worky_engine/sql/analysis/a1_01_active_mrr.sql` | crear | 33/0 |
| `worky_engine/sql/analysis/a1_02_usage_drop.sql` | crear | 54/0 |
| `worky_engine/sql/analysis/a1_05_orphan_deals.sql` | crear | 22/0 |
| `worky_engine/quality/analysis_contracts.py` | crear | 105/0 |
| `worky_engine/cli.py` | modificar (`cmd_analyze` y su parser) | 96/6 |
| `tests/test_analysis_rules.py` | crear | 199/0 |
| `tests/test_analysis_dataset_numbers.py` | crear | 73/0 |
| `tests/test_analysis_idempotency.py` | crear | 71/0 |
| `outputs/analysis/a1_01_active_mrr.csv`, `a1_02_usage_drop.csv`, `a1_05_orphan_deals.csv` | generar (fuera del conteo de autoría) | 164 líneas totales |

**Total autoría (código + pruebas)**: 745 adiciones + 6 eliminaciones = **751 líneas**, dentro del presupuesto de 800 y sin necesidad de mover A1.5 al PR 3.

### Evidencia de unidad de trabajo

| Evidencia | Valor |
|---|---|
| Prueba enfocada | `python -m pytest -q -m "not dataset" tests/test_analysis_rules.py tests/test_analysis_dataset_numbers.py tests/test_analysis_idempotency.py` → 9 passed (las de marca `dataset` se saltan sin `--data-dir`) |
| Arnés en tiempo real | `python -m worky_engine analyze --data-dir data/raw/sistemas --out-dir outputs/analysis` → `analyze: 3 consultas escritas en outputs\analysis`, corrido dos veces, salidas byte-identicas |
| Límite de reversión | Eliminar `worky_engine/analysis/`, `worky_engine/sql/analysis/`, el comando `analyze` de `cli.py` (bloque `cmd_analyze` + su parser + `_import_analyze_dependencies` + las dos constantes `DEFAULT_ANALYSIS_*`), `worky_engine/quality/analysis_contracts.py`, los tres archivos `tests/test_analysis_*.py` y `outputs/analysis/`; `build`, `resolve` y `backtest` quedan intactos |

### Desviaciones del diseño (reportadas, no silenciosas)

1. **`ANALYSIS_FILES`/`ANALYSIS_OUTPUTS` acotado al PR 1**: la tarea 1.2 describía el orden final completo con `a1_00_last_touch.sql` primero. Ese archivo no existe hasta el PR 2; incluirlo en el PR 1 haría fallar `run_sql_files` (`FileNotFoundError`). El PR 1 declara ambas listas solo con las tres consultas que existen; el PR 2 las extiende.
2. **`__init__.py` sin `format_report`**: la tarea 1.1 pedía exponer `run_analysis` y `format_report`, pero `format_report` vive en `report.py`, que se crea en el PR 3. El PR 1 expone solo `run_analysis`.
3. **`windows_overlap` mide 33, no 30**: sobre el dataset real, A1.2 entrega las 89 filas esperadas, pero exactamente 33 cuentas tienen menos de seis meses de uso (no 30, como cita el ADR-004 y la sección 2.2 del diseño). La consulta es una transcripción literal y verificada del SQL del diseño; la discrepancia es entre la cifra citada en el ADR-004/diseño y el resultado medido de esa misma fórmula sobre el dataset real, no un error de transcripción. Se documentó en `tasks.md` bajo "Notas de la aplicación del PR 1" con el desglose exacto (3 cuentas con 0 meses, 1 con 2, 6 con 3, 12 con 4, 11 con 5) y queda pendiente una adenda al ADR-004.

### Problemas notados y no corregidos en este PR

- Ninguno bloqueante. La discrepancia de `windows_overlap` (33 vs 30) queda documentada como pendiente de adenda al ADR-004; no se tocó ni el ADR ni el SQL para forzar el número citado, siguiendo la instrucción explícita del diseño de publicar el número medido.

### Verificación final (verbatim)

```
$ python -m pytest -q
........................................................................ [ 45%]
........................................................................ [ 90%]
...............                                                          [100%]
159 passed in 44.03s
```

```
$ python -m worky_engine analyze --data-dir data/raw/sistemas --out-dir outputs/analysis
analyze: 3 consultas escritas en outputs\analysis
$ python -m worky_engine analyze --data-dir data/raw/sistemas --out-dir outputs/analysis
analyze: 3 consultas escritas en outputs\analysis
$ git status --short outputs
?? outputs/analysis/
```

### Próximos pasos

- `next_recommended`: `sdd-verify` para el PR 1.
- PR 2 (`mart_last_touch`, A1.3, A1.4) y PR 3 (A1.6, `analysis_exceptions.csv`, A1.7, `report.md`) siguen pendientes, fuera del alcance de este work unit.
