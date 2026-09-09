# Apply progress: `a6-cleaning-script`, PR1 (`feat/a6-pr1-clean-rules`) y PR2 (`feat/a6-pr2-clean-impute`)

## PR1: paquete `cleaning/`, las tres detecciones, el log y el comando `clean`

Work unit: `pr1-clean-rules`. Alcance: las 11 tareas de la seccion "PR1: paquete `cleaning/`, las tres detecciones, el log y el comando `clean`" de `tasks.md`.

### Estado de tareas

- [x] 1.1 `worky_engine/cleaning/__init__.py` (exporta `run_clean`, `CleanResult`, `format_cleaning_log`)
- [x] 1.2 `worky_engine/cleaning/rules.py` (`normalize_dates`, `convert_currency`, `detect_missing_mrr`)
- [x] 1.3 `worky_engine/cleaning/runner.py` (`run_clean`, `_passthrough_if_clean`)
- [x] 1.4 `worky_engine/quality/cleaning_contracts.py` (siete contratos sin imputacion)
- [x] 1.5 Escritor de la bitacora en `runner.py` (`cleaning_log.json`, `cleaning_log.md`, `cleaning_exceptions.csv`)
- [x] 1.6 `worky_engine/cli.py`: `_import_clean_dependencies`, `_locate_clean_data_dir`, `_resolve_clean_inputs`, `cmd_clean`, parser `clean`
- [x] 1.7 `scripts/clean_companies.py`
- [x] 1.8 `tests/test_cleaning_rules.py` (fixture minima propia)
- [x] 1.9 `tests/test_cleaning_dataset_numbers.py` (marca `dataset`, version parcial en su momento, completada en PR2)
- [x] 1.10 `tests/test_cleaning_idempotency.py` (version parcial en su momento, completada en PR2)
- [x] 1.11 Cierre de PR1: pruebas focalizadas, suite completa, `git status --short outputs` vacio, hash de los 20 archivos de `outputs/` sin cambio, commit convencional preparado

### Revision nativa y correccion (dcb188c)

La revision nativa de PR1 encontro diez hallazgos criticos: el paso de largo `_passthrough_if_clean` hacia tautologica la idempotencia (una fila ya "limpia" nunca se re-evaluaba, asi que una segunda corrida por CLI sobre `companies_clean.csv` no reproducia el mismo resultado que la primera pasada en memoria), y una moneda fuera de `{USD, MXN}` o un `mrr` con texto no numerico revenaban la corrida en vez de tolerarse de punta a punta. La correccion, en el commit `dcb188c` (`fix(cleaning): make idempotency converge by rule, tolerate unsupported currencies end to end and report non-numeric mrr apart`):

1. Elimino `_passthrough_if_clean`: las tres reglas de PR1 corren sobre todas las filas en cada corrida y son convergentes por construccion (D8 actualizado en `design.md`).
2. Una moneda no soportada ya no aborta: se captura, la fila queda intacta, se reporta `currency_unsupported` en cada corrida (reporte, no correccion) y el comando termina en 0.
3. Un `mrr` con texto no numerico (`"1,234"`, `"n/a"`) se distingue de una moneda no soportada: sale como `mrr_not_numeric`, nunca se copia a `mrr_mxn`, y no se confunde con el caso anterior.

Tras esa correccion, la revision quedo cerrada como no lograble por rechazo del proveedor (`unachievable_lens_slot` agotado); la entrega de PR1 siguio la politica ordinaria del repositorio con `size:exception` reconocido explicitamente (1,190 lineas de autoria contra el presupuesto de 800, ver seccion de presupuesto mas abajo). El estado final de PR1 (`dcb188c` en adelante) es el que consume PR2 como base.

### Work Unit Evidence (PR1)

| Evidencia | Valor |
|---|---|
| Comando de prueba focalizado y resultado exacto | `python -m pytest -q -m "not dataset" tests/test_cleaning_rules.py tests/test_cleaning_idempotency.py` (post-correccion, con las pruebas de tolerancia agregadas) |
| Arnes de runtime y resultado exacto | `python -m worky_engine clean --data-dir fundation-docs --out-dir <tmp1>` y `python scripts/clean_companies.py --data-dir fundation-docs --out-dir <tmp2>`: ambos exit 0, `diff -rq` identicos, sha256 identico |
| Frontera de rollback | Revertir `worky_engine/cli.py` al estado previo a este lote, y borrar `worky_engine/cleaning/`, `worky_engine/quality/cleaning_contracts.py`, `scripts/clean_companies.py` y los archivos nuevos de `tests/`. No toca `worky_engine/normalization/`, `worky_engine/sql/`, `worky_engine/quality/contracts.py` ni ningun archivo de `outputs/` |

### Presupuesto de lineas de autoria (PR1)

**Medido**: 1,190 lineas de autoria contra el presupuesto de 800 por PR de este repositorio (factor ~2.4x sobre el estimado de diseno de ~500, consistente con el factor historico ~2x que `tasks.md` ya anticipaba citando `cascade.py` de A0). `size:exception` reconocido: el corte en PR1/PR2 ya decidido de antemano (`auto-chain`, `stacked-to-main`) es la mitigacion estructural, y PR2 queda acotado a `impute.py`, sus contratos y los cuatro goldens sin repetir ninguna de las 1,190 lineas de este lote.

---

## PR2: imputación del ADR-002, `cleaning_exceptions.csv` completo y los goldens

Work unit: `pr2-clean-impute`. Alcance: las 10 tareas de la seccion "PR2: imputación del ADR-002, `cleaning_exceptions.csv` completo y los goldens" de `tasks.md`, sobre la base de `dcb188c` (PR1 corregido).

### Estado de tareas

- [x] 2.1 `worky_engine/cleaning/impute.py` (`impute_mrr_from_deals`, replica de `mart_mrr.sql` y `mart_deal_normalized.sql`)
- [x] 2.2 `worky_engine/cleaning/runner.py` conecta la imputacion; corrige dos bugs de idempotencia no anticipados (ver Desviaciones)
- [x] 2.3 `worky_engine/quality/cleaning_contracts.py`: `assert_no_null_mrr_after_imputation`, `assert_clone_deals_absent`
- [x] 2.4 `tests/test_cleaning_imputation.py` (6 pruebas: alta, media, montos ambiguos, sin deals, anualizacion, clon)
- [x] 2.5 `tests/test_cleaning_dataset_numbers.py` extendido (28 imputados, 3 anualizados, 112 filas totales)
- [x] 2.6 `tests/test_cleaning_equivalence.py` (marca `dataset`, coincidencia con `mart_mrr`)
- [x] 2.7 `tests/test_cleaning_idempotency.py`: los escenarios de comparacion byte a byte y de goldens intactos ya cubrian el caso con imputacion activa desde su forma de PR1; solo se actualizo el docstring de cabecera
- [x] 2.8 Cuatro goldens de `outputs/clean/` generados y verificados
- [x] 2.9 `README.md`: paso 7 de la ruta rapida y cuatro filas en la tabla de salidas
- [x] 2.10 Cierre de PR2: pruebas focalizadas, suite completa, `git status --short outputs`, hash de los 20 archivos, commit convencional preparado

21/21 tareas totales completas (11 PR1 + 10 PR2).

### Work Unit Evidence (PR2)

| Evidencia | Valor |
|---|---|
| Comando de prueba focalizado y resultado exacto | `python -m pytest -q -m "not dataset" tests/test_cleaning_rules.py tests/test_cleaning_imputation.py tests/test_cleaning_idempotency.py` → `29 passed, 2 deselected` |
| Comando de prueba focalizado (dataset) y resultado exacto | `python -m pytest -q -m dataset tests/test_cleaning_dataset_numbers.py tests/test_cleaning_equivalence.py tests/test_cleaning_idempotency.py` → `8 passed, 4 deselected` |
| Arnes de runtime y resultado exacto | `python -m worky_engine clean --data-dir fundation-docs --out-dir outputs/clean` corrido tres veces: `clean: 84 correcciones en 678 filas` cada vez, sha256 identico en los cuatro archivos entre las tres corridas; segunda corrida sobre `outputs/clean/companies_clean.csv` como `--companies`: exit 0, `clean: 0 correcciones en 678 filas`, exactamente 28 filas `clone_excluded` en `cleaning_exceptions.csv`, `companies_clean.csv` identico byte a byte al de la corrida original |
| Frontera de rollback | Eliminar `worky_engine/cleaning/impute.py`; revertir `worky_engine/cleaning/runner.py` y `worky_engine/cleaning/rules.py` al estado de `dcb188c`; revertir `worky_engine/quality/cleaning_contracts.py` quitando `assert_no_null_mrr_after_imputation` y `assert_clone_deals_absent`; borrar `tests/test_cleaning_imputation.py` y `tests/test_cleaning_equivalence.py`; revertir las extensiones de `tests/test_cleaning_dataset_numbers.py` y `tests/test_cleaning_idempotency.py`; borrar `outputs/clean/`; revertir el paso 7 y las cuatro filas nuevas de `README.md`. No toca `worky_engine/normalization/`, `worky_engine/sql/`, `worky_engine/quality/contracts.py`, ningun golden previo de `outputs/`, ni la tabla "Dónde está cada cosa" del README |

### Verificacion completa (PR2)

| Comando | Resultado observado |
|---|---|
| `python -m pytest -q -m "not dataset" tests/test_cleaning_rules.py tests/test_cleaning_imputation.py tests/test_cleaning_idempotency.py` | `29 passed, 2 deselected` |
| `python -m pytest -q -m dataset tests/test_cleaning_dataset_numbers.py tests/test_cleaning_equivalence.py tests/test_cleaning_idempotency.py` | `8 passed, 4 deselected` |
| `python -m pytest -q` (suite completa, dataset real) | `289 passed in 966.69s (0:16:06)` |
| `python -m worky_engine clean --data-dir fundation-docs --out-dir outputs/clean` (x3, comparadas por sha256) | `clean: 84 correcciones en 678 filas` las tres veces; los cuatro archivos identicos byte a byte entre las tres corridas |
| `cleaning_log.json` / `cleaning_log.md` | `deals_in: 997`, `deals_matched: 962`; `missing_mrr`: detected 56, corrected 28, excluded_clones 28, annualized_deals 3, unresolved 0; `currency_to_mxn`: detected 22, corrected 22; `date_format`: detected 31, corrected 31, ambiguous 12; `totals.corrections: 84`, `exception_rows: 112` |
| `outputs/exceptions_log.csv` (oraculo) vs `cleaning_exceptions.csv` (PR2) | 28/28 filas `mrr_imputed_from_deal` coinciden en `applied_value` y `evidence_ref` por `source_id` (`tests/test_cleaning_equivalence.py`) |
| `outputs/master_dataset.csv` (oraculo) | Reparto de confianza de las 28 imputadas: 4 `high`, 24 `medium`, coincide exacto |
| Segunda corrida sobre `outputs/clean/companies_clean.csv` (`--companies`) | exit 0, `clean: 0 correcciones en 678 filas`, `cleaning_exceptions.csv` con exactamente 28 filas `clone_excluded` y ningun otro codigo, `companies_clean.csv` identico byte a byte al original |
| `git status --short outputs` | Solo `?? outputs/clean/`; ningun archivo de `outputs/analysis`, `outputs/health` u `outputs/warehouse` aparece |
| sha256 de los veinte archivos ya versionados de `outputs/` | Identico antes y despues de las tres corridas de `clean` |
| `git diff --numstat` (archivos de autoria) | `README.md` 10+0; `tests/test_cleaning_dataset_numbers.py` 14+9; `tests/test_cleaning_idempotency.py` 7+6; `worky_engine/cleaning/rules.py` 15+5; `worky_engine/cleaning/runner.py` 31+24; `worky_engine/quality/cleaning_contracts.py` 23+6; archivos nuevos por `wc -l`: `worky_engine/cleaning/impute.py` 119, `tests/test_cleaning_imputation.py` 146, `tests/test_cleaning_equivalence.py` 61 |

### Archivos cambiados

| Archivo | Accion | Que contiene |
|---|---|---|
| `worky_engine/cleaning/impute.py` | Nuevo | `impute_mrr_from_deals`: replica en pandas de `mart_mrr.sql` y `mart_deal_normalized.sql`, con anualizacion 12x, confianza `high`/`medium` y eleccion del deal de evidencia |
| `worky_engine/cleaning/runner.py` | Modificado | Conecta `impute_mrr_from_deals` despues de `detect_missing_mrr`; corrige el conteo de `corrected` para que cuente por excepcion de la corrida y no por estado final del marco |
| `worky_engine/cleaning/rules.py` | Modificado | `detect_missing_mrr` preserva `mrr_source == 'imputed_from_deal'` de una corrida anterior en vez de reclasificarlo como `crm` |
| `worky_engine/quality/cleaning_contracts.py` | Modificado | Agrega `assert_no_null_mrr_after_imputation` y `assert_clone_deals_absent`, wireados en `run_cleaning_contracts` |
| `tests/test_cleaning_imputation.py` | Nuevo | 6 pruebas: confianza alta, confianza media, montos ambiguos, sin deals, anualizacion, clon no tocado |
| `tests/test_cleaning_equivalence.py` | Nuevo | Prueba `dataset`: coincidencia de las 28 imputaciones con `outputs/exceptions_log.csv` y `outputs/master_dataset.csv` |
| `tests/test_cleaning_dataset_numbers.py` | Modificado | Conteos exactos completos: 28 imputados (no 28 "unresolved"), 3 anualizados, 112 filas totales |
| `tests/test_cleaning_idempotency.py` | Modificado | Docstring de cabecera actualizado (los escenarios de comparacion ya cubrian la imputacion activa desde su forma original) |
| `outputs/clean/companies_clean.csv`, `cleaning_exceptions.csv`, `cleaning_log.json`, `cleaning_log.md` | Nuevo (golden) | Generados con `python -m worky_engine clean --data-dir fundation-docs --out-dir outputs/clean`; fuera del conteo de autoria |
| `README.md` | Modificado | Paso 7 de la ruta rapida y cuatro filas en la tabla "Qué produce" |
| `openspec/changes/a6-cleaning-script/tasks.md` | Modificado | Tareas 2.1 a 2.10 marcadas `[x]` |

### Desviaciones del diseño

Ninguna en el comportamiento observable exigido por la especificacion. Dos correcciones necesarias y no anticipadas por `tasks.md`, descubiertas al probar la idempotencia end-to-end sobre el dataset real:

1. **`detect_missing_mrr` no preservaba `mrr_source == 'imputed_from_deal'`.** La funcion (de PR1) reiniciaba `mrr_source` a `'crm'` para toda fila con `mrr` no vacio, sin distinguir un valor del CRM de un valor ya imputado en una corrida anterior. En la segunda corrida sobre `companies_clean.csv`, esto reclasificaba las 28 empresas imputadas como `'crm'`, perdiendo la procedencia y rompiendo el byte a byte. Se agrego la guarda que el propio D8 del diseño ya anticipaba en su prosa ("un `mrr_source` ya resuelto no produce corrección") pero que ninguna tarea de PR1 o PR2 implementaba todavia.
2. **`_build_counts` contaba `corrected` por estado final del marco, no por excepcion de la corrida.** `mrr_corrected = int((clean["mrr_source"] == "imputed_from_deal").sum())` cuenta TODAS las filas ya imputadas, incluidas las preservadas de corridas anteriores; el contrato `assert_clean_is_idempotent` exige que la segunda pasada reporte 0 correcciones, y una imputacion preservada (sin excepcion nueva) inflaba ese conteo a 28. Se cambio a `_count(corrections, "mrr_imputed_from_deal")`, consistente con como `assert_counts_match_exceptions` ya esperaba ese campo (cuenta de filas de `cleaning_exceptions.csv`, no del `DataFrame` final).

Ambas correcciones se verificaron con una segunda corrida real sobre el dataset completo: `corrections: 0`, `companies_clean.csv` identico byte a byte, contratos en verde.

### Problemas encontrados

Ninguno mas alla de los dos ya descritos en Desviaciones.

### Presupuesto de lineas de autoria (PR2)

**Medido, no estimado**: `git diff --numstat` sobre los archivos modificados suma 251 lineas (README.md 10, tests/test_cleaning_dataset_numbers.py 23, tests/test_cleaning_idempotency.py 13, worky_engine/cleaning/rules.py 20, worky_engine/cleaning/runner.py 55, worky_engine/quality/cleaning_contracts.py 29, tasks.md excluido por ser bitácora de proceso, igual que en PR1); los tres archivos nuevos suman 326 lineas por `wc -l` (impute.py 119, test_cleaning_imputation.py 146, test_cleaning_equivalence.py 61). Total autoria de PR2: **476 lineas**, dentro del presupuesto de 800 por PR y por debajo del estimado de diseño de ~400 con el factor historico de este repositorio (~1.2x, no ~2x: PR2 no repitió el patrón de subestimación de PR1). Los cuatro archivos de `outputs/clean/` quedan fuera de este conteo por ser goldens generados, tal como fija `tasks.md`. No se recorto ninguna prueba, docstring ni codigo de excepcion para llegar a este numero: 476 es la suma real del trabajo asignado.

**Recomendacion**: entrega directa, sin `size:exception`. PR2 cierra la rebanada de `tasks.md` (`auto-chain`, `stacked-to-main`, PR2 apuntando a `feat/a6-pr1-clean-rules`) dentro del presupuesto.

### Commit convencional preparado (no ejecutado)

```
feat(cleaning): connect ADR-002 MRR imputation into the clean pipeline

Add worky_engine.cleaning.impute (impute_mrr_from_deals), a pandas
replica of mart_mrr.sql and mart_deal_normalized.sql: resolves the 28
real companies with null mrr from their deals, annualizes deal
amounts that are exactly 12x another deal of the same company, and
assigns high/medium confidence. Wire it into runner.run_clean right
after detect_missing_mrr, add the imputation contracts
(assert_no_null_mrr_after_imputation, assert_clone_deals_absent), and
fix two idempotency bugs surfaced by a real second pass over the
golden output: detect_missing_mrr now preserves an already-imputed
mrr_source instead of resetting it to crm, and the corrected count in
cleaning_log.json is now derived from this run's exceptions instead
of the final dataframe state.

Add tests/test_cleaning_imputation.py (confidence tiers, ambiguous
amounts, no deals, annualization, clone untouched),
tests/test_cleaning_equivalence.py (28/28 match against the engine's
own exceptions_log.csv and master_dataset.csv goldens), extend the
dataset-number and idempotency suites for the completed pipeline, and
commit the four outputs/clean/ goldens. Add the clean command's step
to the README quick path and its four output rows.
```
