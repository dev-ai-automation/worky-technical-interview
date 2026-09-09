# Apply progress: `a6-cleaning-script`, PR1 (`feat/a6-pr1-clean-rules`)

Work unit: `pr1-clean-rules`. Alcance: las 11 tareas de la seccion "PR1: paquete `cleaning/`, las tres detecciones, el log y el comando `clean`" de `tasks.md`. La imputacion del ADR-002, `impute.py`, los goldens de `outputs/clean/` y el paso 7 del README quedan para PR2 y no se tocaron en este lote.

## Estado de tareas

- [x] 1.1 `worky_engine/cleaning/__init__.py` (exporta `run_clean`, `CleanResult`, `format_cleaning_log`)
- [x] 1.2 `worky_engine/cleaning/rules.py` (`normalize_dates`, `convert_currency`, `detect_missing_mrr`)
- [x] 1.3 `worky_engine/cleaning/runner.py` (`run_clean`, `_passthrough_if_clean`)
- [x] 1.4 `worky_engine/quality/cleaning_contracts.py` (siete contratos sin imputacion)
- [x] 1.5 Escritor de la bitacora en `runner.py` (`cleaning_log.json`, `cleaning_log.md`, `cleaning_exceptions.csv`)
- [x] 1.6 `worky_engine/cli.py`: `_import_clean_dependencies`, `_locate_clean_data_dir`, `_resolve_clean_inputs`, `cmd_clean`, parser `clean`
- [x] 1.7 `scripts/clean_companies.py`
- [x] 1.8 `tests/test_cleaning_rules.py` (13 pruebas, fixture minima propia)
- [x] 1.9 `tests/test_cleaning_dataset_numbers.py` (5 pruebas, marca `dataset`, version parcial)
- [x] 1.10 `tests/test_cleaning_idempotency.py` (5 pruebas: 3 sin marca, 2 con marca `dataset`)
- [x] 1.11 Cierre de PR1: pruebas focalizadas, suite completa, `git status --short outputs` vacio, hash de los 20 archivos de `outputs/` sin cambio, commit convencional preparado

11/11 tareas de PR1 completas. 0/10 tareas de PR2 (fuera de este lote).

## Work Unit Evidence

| Evidencia | Valor |
|---|---|
| Comando de prueba focalizado y resultado exacto | `python -m pytest -q -m "not dataset" tests/test_cleaning_rules.py tests/test_cleaning_idempotency.py` → `16 passed, 2 deselected` |
| Comando de prueba focalizado (dataset) y resultado exacto | `python -m pytest -q -m dataset tests/test_cleaning_dataset_numbers.py tests/test_cleaning_idempotency.py` → `7 passed, 3 deselected` |
| Arnes de runtime y resultado exacto | `python -m worky_engine clean --data-dir fundation-docs --out-dir <tmp1>` y `python scripts/clean_companies.py --data-dir fundation-docs --out-dir <tmp2>`: ambos exit 0, `diff -rq` reporta identicos, sha256 identico en los cuatro archivos; resumen en espanol `56/28/22/31/12` confirmado en `cleaning_log.md`; `--data-dir` a una carpeta vacia termina en exit 2 con "clean: no se encontro companies.csv en ..." |
| Frontera de rollback | Revertir `worky_engine/cli.py` a la version anterior a este lote (elimina `_import_clean_dependencies`, `_locate_clean_data_dir`, `_resolve_clean_inputs`, `cmd_clean` y el subparser `clean`), y borrar `worky_engine/cleaning/`, `worky_engine/quality/cleaning_contracts.py`, `scripts/clean_companies.py` y los tres archivos nuevos de `tests/`. No toca `worky_engine/normalization/`, `worky_engine/sql/`, `worky_engine/quality/contracts.py` ni ningun archivo de `outputs/`. |

## Verificacion completa

| Comando | Resultado observado |
|---|---|
| `python -m pytest -q -m "not dataset" tests/test_cleaning_rules.py` | `13 passed` |
| `python -m pytest -q -m dataset tests/test_cleaning_dataset_numbers.py` | `5 passed` |
| `python -m pytest -q -m "not dataset" tests/test_cleaning_idempotency.py` | `3 passed, 2 deselected` |
| `python -m pytest -q -m dataset tests/test_cleaning_idempotency.py` | `2 passed, 3 deselected` |
| `python -m pytest -q` (suite completa) | `275 passed in 1002.38s` (baseline 252 + 23 pruebas nuevas de este PR) |
| `python -m worky_engine clean --data-dir fundation-docs --out-dir <tmp1>` | exit 0, `clean: 53 correcciones en 678 filas` |
| `python scripts/clean_companies.py --data-dir fundation-docs --out-dir <tmp2>` | exit 0, mismo mensaje |
| `diff -rq <tmp1> <tmp2>` | sin diferencias |
| `sha256sum <tmp1>/* <tmp2>/*` | los cuatro pares de hash coinciden |
| `python -m worky_engine clean --data-dir <carpeta-vacia> --out-dir <tmp>` | exit 2, `clean: no se encontro companies.csv en '<ruta>'` |
| `git status --short outputs` | vacio (sin salida) |
| `git diff --stat outputs/` | vacio (sin salida): los 20 archivos ya versionados de `outputs/` no cambiaron |
| `git diff --stat worky_engine/cli.py` | `120 insertions(+)`, 0 borrados |

## Archivos cambiados

| Archivo | Accion | Que contiene |
|---|---|---|
| `worky_engine/cleaning/__init__.py` | Nuevo | Exporta `run_clean`, `CleanResult`, `format_cleaning_log` |
| `worky_engine/cleaning/rules.py` | Nuevo | `normalize_dates`, `convert_currency`, `detect_missing_mrr`, `Correction` |
| `worky_engine/cleaning/runner.py` | Nuevo | `run_clean`, `CleanResult`, `_passthrough_if_clean`, `format_cleaning_log`, armado de `cleaning_log.json`/`cleaning_exceptions.csv` |
| `worky_engine/quality/cleaning_contracts.py` | Nuevo | Siete contratos disponibles sin imputacion, `run_cleaning_contracts` |
| `scripts/clean_companies.py` | Nuevo | Wrapper delgado sobre `main(["clean", ...])` |
| `worky_engine/cli.py` | Modificado | `_import_clean_dependencies`, `_locate_clean_data_dir`, `_resolve_clean_inputs`, `cmd_clean`, subparser `clean`, constantes `DEFAULT_CLEAN_*` |
| `tests/test_cleaning_rules.py` | Nuevo | 13 pruebas: CLI, wrapper, ambas rutas, archivos faltantes, dependencia faltante, reglas puras |
| `tests/test_cleaning_dataset_numbers.py` | Nuevo | 5 pruebas, marca `dataset`, conteos exactos sobre el dataset real |
| `tests/test_cleaning_idempotency.py` | Nuevo | 5 pruebas: 3 sobre fixture, 2 sobre dataset real (marca `dataset`) |
| `openspec/changes/a6-cleaning-script/tasks.md` | Modificado | Tareas 1.1 a 1.11 marcadas `[x]` |

## Desviaciones del diseno

Ninguna en el comportamiento observable exigido por la especificacion. Tres decisiones de implementacion llenan huecos que el diseno dejo abiertos a proposito (no contradicen ninguna decision D1-D12):

1. **`_locate_clean_data_dir` en `cli.py`.** El diseno (D2) solo dice "sin CSV, termina en 2 nombrando el archivo que falto" y rechaza explicitamente reutilizar `_resolve_data_dir` para *leer via SQLite*. No dice como `--data-dir` debe ubicar los CSV cuando la carpeta solo trae el zip (`fundation-docs/dataset_caso_v3.zip`, el caso real de la verificacion de este lote). Se agrego un resolutor propio, `_locate_clean_data_dir`, que reutiliza la extraccion de zip ya existente pero nunca lee tablas por `sqlite3`, y que reporta el nombre exacto del CSV faltante (no "bases SQLite") cuando ninguna carpeta candidata trae ambos archivos, para cumplir literalmente los escenarios "falta companies.csv" y "falta deals.csv" de la especificacion.
2. **`mrr_source = "unresolved"` en PR1 sin la excepcion `mrr_unresolved`.** El diseno fija el dominio final de `mrr_source` (`crm`, `imputed_from_deal`, `unresolved`, `clone_excluded`) pero no describe el estado intermedio de una empresa real con `mrr` nulo antes de que `impute.py` exista (PR2). Se uso `unresolved` para esa celda (es el valor de dominio mas honesto: "no se le resolvio ningun monto todavia"), pero el campo `unresolved` de `cleaning_log.json` y la excepcion `mrr_unresolved` se dejaron en cero en este PR, porque ese campo describe un intento de imputacion que fallo, y en PR1 no se intenta imputar. Esto evita una contradiccion real que se detecto en pruebas manuales: `assert_counts_match_exceptions` fallaba si el conteo de "unresolved" en el log no correspondia a ninguna fila de la bitacora.
3. **`format_cleaning_log` exportado desde `worky_engine.cleaning`.** La tarea 1.1 solo pide exportar `run_clean` y `CleanResult`; se agrego tambien `format_cleaning_log` porque `cmd_clean` lo necesita para escribir `cleaning_log.md` y el paquete no debe filtrar su implementacion interna (`runner.py`) al CLI.

## Problemas encontrados

Uno, ya corregido antes de terminar este lote: el wrapper `scripts/clean_companies.py`, al correrse como `python scripts/clean_companies.py` (no via `-m`), pone el directorio `scripts/` en `sys.path[0]` en vez de la raiz del repositorio, y el paquete `worky_engine` no esta instalado en modo editable en este entorno. Sin insertar la raiz del repositorio en `sys.path` antes del import, el wrapper fallaba con `ModuleNotFoundError`. Se agrego una insercion de dos lineas al inicio del wrapper (`sys.path.insert(0, ...)`) que solo repara esa resolucion de import, sin agregar ninguna regla de negocio; se confirmo con `diff -rq` y sha256 que las dos rutas siguen produciendo salidas identicas.

## Presupuesto de lineas de autoria

**Medido, no estimado**: `git diff --numstat worky_engine/cli.py` reporta 120 inserciones, 0 borrados; los ocho archivos nuevos suman 1070 lineas (`wc -l` de `worky_engine/cleaning/__init__.py`, `rules.py`, `runner.py`, `worky_engine/quality/cleaning_contracts.py`, `scripts/clean_companies.py` y las tres pruebas). Total autoria de PR1: **1190 lineas**, sobre el presupuesto de 800 lineas por PR de este repositorio, y por encima del estimado de diseno de ~500 (factor ~2.4x, consistente con el factor historico ~2x que `tasks.md` ya anticipaba citando `cascade.py` de A0).

La palanca declarada en `tasks.md` ("mover `cleaning_log.md` a PR2") se evaluo y no alcanza por si sola: el escritor de Markdown y sus aserciones de prueba suman entre 40 y 50 lineas, muy por debajo de las ~390 lineas que faltarian para bajar de 1190 a 800. Aplicar esa palanca de forma aislada solo reduciria el numero sin resolver el problema real, y quitar `cleaning_log.md` de este PR tambien contradice la tarea 1.5 tal como esta escrita ("MUST escribir cleaning_log.md"). Siguiendo la regla de "nunca recortar pruebas ni docstrings para encajar en el presupuesto" y de "reportar el conteo final en vez de iterar intentando llegar al numero", no se recorto nada: las 23 pruebas nuevas, los docstrings y los tres codigos de excepcion generales (`date_unresolved`, `currency_unsupported`, ademas de los tres que si emite este PR) se mantuvieron completos.

**Recomendacion**: `size:exception` para PR1, ya reconocido desde `tasks.md` como riesgo "Medium" con el corte en dos PR ya decidido de antemano (`auto-chain`, `stacked-to-main`). El propio corte en PR1/PR2 ya es la mitigacion estructural: PR2 queda acotado a `impute.py`, sus contratos y los cuatro goldens, sin repetir ninguna de las 1190 lineas de este lote.

## Commit convencional preparado (no ejecutado)

```
feat(cleaning): add clean subcommand with date, currency and missing-mrr detection

Add the worky_engine.cleaning package (rules, runner, passthrough
idempotency), its contracts, the `clean` CLI subcommand and wrapper
script, and unit/dataset tests covering the three PR1 detections
(signup_date/churn_date normalization, USD-to-MXN conversion, null-mrr
detection with clone exclusion) plus the cleaning log writer. MRR
imputation from the ADR-002 rule lands in a follow-up PR.
```
