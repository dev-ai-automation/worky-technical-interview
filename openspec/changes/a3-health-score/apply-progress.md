# Progreso de aplicacion: `a3-health-score`, PR 1 y PR 2

## Hecho

Tareas 1.1 a 1.12 completas y marcadas `[x]` en `tasks.md`.

- `worky_engine/sql/health/h1_company_asof.sql` (43 lineas): vista `health_company_asof`, identidad, mes de referencia y mes de corte, parametrizada por `health_params` (D6, D7, D9).
- `worky_engine/sql/health/h2_usage_signals.sql` (74 lineas): vista `health_usage_signals`, `sig_momentum`/`sig_mom`/`sig_drawdown` con resguardo de fuga y denominadores degenerados en 0.0 (D11, D15).
- `worky_engine/sql/health/h3_tenure.sql` (15 lineas): vista `health_tenure`, `sig_tenure` recortado a cero.
- `worky_engine/sql/health/h4_support_asof.sql` (28 lineas): vista `mart_support_asof`, ventana de soporte de 3 meses (D10, D11); `mart_support.sql` intacta.
- `worky_engine/sql/health/h5_activation.sql` (39 lineas): vista `health_activation`, `activation_raw` de los primeros 3 meses de uso.
- `worky_engine/sql/health/h6_asof_inputs.sql` (20 lineas): vista `health_asof_inputs`, une h1 a h5 (D9).
- `worky_engine/health/__init__.py` (6 lineas) y `worky_engine/health/scoring.py` (118 lineas): `percentile_score`, `WEIGHTS`, `compute_scores` con banda "sin historia", suma ponderada y las tres marcas de capacidad (D12 a D19).
- `worky_engine/harness/backtest.py` y `worky_engine/harness/__init__.py`: alias publico `auc = _auc`, reexportado (D4).
- `worky_engine/quality/health_contracts.py` (110 lineas): ocho contratos de forma y banda calculables en memoria.
- `tests/test_health_rules.py` (233 lineas, 8 pruebas): una por regla del ADR-005, fixture minimo propio via DuckDB para las reglas de SQL y DataFrame sintetico para las de `scoring.py`.
- `tests/test_health_equivalence.py` (95 lineas, 3 pruebas): equivalencia SQL contra `_features` del harness, aislando `h2_usage_signals.sql`.
- `tests/test_harness_regression.py`: prueba de identidad del alias `auc`.

## Diferido (fuera de este PR)

- `runner.py`, `metrics.py`, `cmd_health`, el resto de los contratos (`assert_health_asof_before_reference`, `assert_health_recall_denominator`, `assert_health_row_order`), `run_health_contracts`, pruebas `dataset` e idempotencia parcial: PR 2, tareas 2.1 a 2.8.
- `report.py`, `validation.md`, README, cierre de documentacion: PR 3, tareas 3.1 a 3.8.
- Razon: el corte en tres PR encadenados ya esta fijado en la seccion 10 del diseno y en `tasks.md`; PR 1 es exactamente el alcance de "SQL de subpuntajes, `scoring.py`, alias `auc` y contratos de forma y banda".

## Desviaciones

- **Reduccion del presupuesto de revision (no es un cambio de alcance)**: la primera implementacion honesta de las tareas 1.1 a 1.11 llego a 991 lineas de autoria, sobre el presupuesto de 800 de este repositorio. Se aplico una reduccion en tres pasos, documentada en la seccion "Brechas encontradas en el diseño" de `tasks.md`, sin borrar pruebas, comentarios ni documentacion: (1) las reglas de `scoring.py` (empates, "sin historia", suma ponderada, marcas anidadas) se probaron con un DataFrame sintetico llamando `compute_scores` directo, en vez de repetir el ensamblaje completo por cada una; (2) `h2_usage_signals.sql` se reescribio con funciones de ventana en un solo paso de agregacion; (3) `test_health_equivalence.py` aisla `h2_usage_signals.sql` (solo `health_company_asof` y `stg_product_usage` minimas) en vez de correr el pipeline completo. Conteo final: 798 lineas de autoria (`git diff --numstat`).
- **`activation_raw`, formula propia**: el diseno (tarea 1.5) no fija la formula exacta de `activation_raw`, solo que viene de los primeros 3 meses de uso. Se eligio el promedio de las cuatro columnas de actividad temprana que measurements.md ya midio (`payroll_runs_completed`, `logins`, `features_used`, `active_users`), normalizado despues por percentil en `scoring.py` igual que las otras senales (misma direccion, sin invertir). Es una decision de implementacion razonable dentro de un hueco del diseno, no una desviacion de una regla ya fijada.
- **`test_health_rules.py` con dos fixtures, no una**: el diseno (seccion 9) describe un solo fixture minimo por archivo de prueba. Aqui se uso un fixture via DuckDB (tres empresas, para las reglas de SQL) y un DataFrame sintetico directo (para las reglas de `scoring.py`), documentado en el docstring del modulo. Es una separacion por capa, consistente con la tabla de modulos de la seccion 1 del diseno, no una desviacion de una regla del ADR-005.

## Verificacion (verbatim)

```
$ python -m pytest -q -m "not dataset" tests/test_health_rules.py tests/test_health_equivalence.py tests/test_harness_regression.py
............
12 passed, 4 deselected in 4.68s

$ python -m pytest -q
191 passed in 53.51s

$ python -m worky_engine build --data-dir data/raw/sistemas --out-dir outputs
build: 650 empresas ensambladas en outputs

$ python -m worky_engine backtest --data-dir data/raw/sistemas --out-dir outputs
backtest: reporte escrito en outputs\backtest_report.md

$ git status --short outputs
(vacio)

$ grep -rln "—" worky_engine tests --include="*.py" --include="*.sql"
tests/test_analysis_report.py   (preexistente de A1, cadena literal de una aserción "not in", no autoría de este PR)
```

## Presupuesto de revision

- Autoria total (`git diff --numstat`, suma de adiciones + eliminaciones): 798 lineas, bajo el presupuesto de 800.
- No hay goldens generados en este PR (empiezan en `outputs/health/` a partir del PR 2).

## Estado (PR 1)

12/12 tareas de PR 1 completas.

---

# Progreso de aplicacion: PR 2

## Hecho

Tareas 2.1 a 2.8 completas y marcadas `[x]` en `tasks.md`.

- `worky_engine/health/runner.py` (106 lineas): `HEALTH_FILES`, `SENSITIVITY_RUNS` (primaria k=2/2, k3 3/3, literal 2/0), `_run_once` crea `health_params` con parametros y corre `HEALTH_FILES`, `_order_rows` ordena `health_score` ascendente con vacios al final y `master_id` de desempate (`mergesort`), `_format_for_csv` selecciona las 22 columnas de salida y formatea los subpuntajes a texto de 2 decimales con `writers.format_money`. `run_health(con)` regresa `HealthResult` (scores numericos, formato CSV, sensibilidades k3/literal, texto SQL).
- `worky_engine/health/metrics.py` (179 lineas): `auc_by_signal` (usa el alias `worky_engine.harness.auc`, con inversion de direccion para las senales "mas alto es riesgo" como tickets), `precision_recall`, `mrr_weighted_recall`, `rate_metrics` (10/15/20 %), `confusion_matrix_15`, `fixed_cut_metrics` (score < 40), `capacity_by_csm` (7 CSM), `early_detection_k3`, `sensitivity_summary`, `acceptance_check` (AUC >= 0.95, recall >= 0.85 al 20 %, D18).
- `worky_engine/quality/health_contracts.py` (+62/-5 lineas): tres contratos nuevos (`assert_health_asof_before_reference`, `assert_health_recall_denominator`, `assert_health_row_order` sobre el archivo ya formateado a texto con `pd.to_numeric` como guarda de CAST) y `run_health_contracts` que corre los doce contratos en orden fijo. `assert_health_score_matches_weights` se actualizo para incluir el termino de `activation_score` (ver desviaciones).
- `worky_engine/cli.py` (+78 lineas): `cmd_health` (mismo orden que `cmd_analyze`: importacion diferida, `_resolve_data_dir`, `load_raw_tables`, `resolve_identity` en memoria, `open_connection` propio, `assemble_master_dataset`, `run_contracts` de A0, `run_health`, `run_health_contracts`, `write_csv`) y su parser (`--data-dir`, `--out-dir` por omision `outputs/health`, `--db-path` por omision `.build/worky_health.duckdb`). Solo escribe `health_scores.csv` en este PR; `validation.md` llega en el PR 3.
- `worky_engine/health/__init__.py` (+6/-1 lineas): expone `HealthResult` y `run_health`.
- `worky_engine/health/scoring.py`: `WEIGHTS` con los cuatro pesos originales del ADR-005 (momentum 0.35 / mom 0.20 / caida 0.15 / antiguedad 0.30) y `_weighted_sum` con la suma de cuatro terminos (ver "Decision del usuario" abajo).
- `tests/test_health_dataset_numbers.py` (5 pruebas, marca `dataset`): 650 filas, 89 bajas, 22 no detectables en k=2, 78 marcadas al 15 % sobre el libro activo de 518, metricas al 10/15/20 % con los pesos originales, deteccion temprana en k=3, regla de aceptacion restablecida sobre el recall detectable (alcanzada).
- `tests/test_health_idempotency.py` (marca `dataset`, 1 prueba): dos corridas de `health` en carpetas temporales distintas, `health_scores.csv` identico byte a byte entre si y contra el golden commiteado, hash de los ocho archivos de A0 y los ocho de A1 (incluido `backtest_report.md`) sin cambio.
- `tests/test_health_rules.py`: revertido a la version de PR 1 (cuatro pesos, sin `activation_raw` en los fixtures sinteticos), porque `WEIGHTS` ya no tiene termino de activacion.
- `worky_engine/quality/health_contracts.py`: `assert_health_score_matches_weights` revertido a la formula de cuatro terminos.
- `worky_engine/health/metrics.py`: `precision_recall` agrega `recall_detectable` (denominador = bajas con `health_score`) y `undetectable` junto al recall general; `acceptance_check` decide sobre `recall_detectable_20`.
- `docs/decisions/ADR-005-health-score-model.md`: "Adenda 1" reescrita (ver "Decision del usuario" abajo).
- `outputs/health/health_scores.csv` (650 filas + encabezado, generado, fuera del conteo de autoria): golden de la corrida principal, regenerado con los pesos originales.

## Decision del usuario (post PR 2, revierte la tarea 2.6)

La tarea 2.6 habia cambiado `WEIGHTS` a la mezcla medida (uso 70 %, antiguedad 15 %, activacion 15 %) siguiendo al pie de la letra la redaccion original de D18. Al revisar el resultado, el usuario decidio: (1) mantener la banda "sin historia" tal cual, (2) revertir `WEIGHTS` a los pesos originales del ADR-005, porque la mezcla medida no mejoraba el recall (se quedaba en el mismo 0.753) y si bajaba el AUC (0.992 contra 0.997), (3) restablecer la regla de aceptacion como AUC >= 0.95 y recall entre las bajas detectables >= 0.85 al 20 % (en vez de sobre el recall general), que con los pesos originales si se cumple (AUC 0.997, recall detectable 1.000), (4) seguir reportando el recall general con su techo estructural de 22 no detectables como hallazgo de onboarding para la Parte B, y (5) corregir la cifra "10 de 89" de la ruta rapida del ADR-005 (era el conteo de bajas con cero meses de uso, no el de bajas sin historia suficiente; el conteo correcto es 22 de 89, de las cuales 4 no tienen ningun mes de uso). La Adenda 1 del ADR-005 quedo reescrita con esta decision completa. Las tareas de PR 2 en `tasks.md` se mantienen marcadas `[x]`; la tarea 2.6 documenta esta decision en su propia nota.

## Verificacion (verbatim, con los pesos originales del ADR-005)

```
$ python -m worky_engine health --data-dir data/raw/sistemas --out-dir outputs/health
health: 650 empresas puntuadas, health_scores.csv en outputs\health (validation.md llega en el PR 3)
$ sha256sum outputs/health/health_scores.csv
7b56e0478bf19ed4dd4ec3e069c891a62e52f88a5780b502f318208a7c332bda outputs/health/health_scores.csv

$ python -m worky_engine health --data-dir data/raw/sistemas --out-dir outputs/health
health: 650 empresas puntuadas, health_scores.csv en outputs\health (validation.md llega en el PR 3)
$ sha256sum outputs/health/health_scores.csv
7b56e0478bf19ed4dd4ec3e069c891a62e52f88a5780b502f318208a7c332bda outputs/health/health_scores.csv
(identico entre las dos corridas)

$ python -m pytest -q
199 passed in 105.22s

$ git status --short outputs
?? outputs/health/
(sin cambios en los goldens de A0 ni A1)
```

## Metricas medidas (corrida principal, pesos originales del ADR-005)

| Tasa | Marcadas (total) | Marcadas (libro activo, 518) | Precision | Recall general | Recall detectable | Recall ponderado por MRR |
|---|---|---|---|---|---|---|
| 10 % | 119 | 52 | 0.563 | 0.753 | 1.000 | 0.608 |
| 15 % | 145 | 78 | 0.462 | 0.753 | 1.000 | 0.608 |
| 20 % | 171 | 104 | 0.392 | 0.753 | 1.000 | 0.608 |

AUC del `health_score`: 0.997. No detectables: 22 de 89 (4 con cero meses de uso, 6 con uno, 12 con dos). Deteccion temprana en k=3: 52 de 56 elegibles (0.929). Regla de aceptacion (AUC >= 0.95, recall detectable >= 0.85 al 20 %): alcanzada.

## Presupuesto de revision

- Archivos modificados (`git diff --numstat`, adiciones + eliminaciones): `worky_engine/cli.py` 78, `worky_engine/health/__init__.py` 7, `worky_engine/health/scoring.py` 26, `worky_engine/quality/health_contracts.py` 66. Subtotal: 177. `tests/test_health_rules.py` volvio a la version commiteada de PR 1 (sin diferencia).
- Archivos nuevos (`wc -l`): `tests/test_health_dataset_numbers.py` 144, `tests/test_health_idempotency.py` 75, `worky_engine/health/metrics.py` 207, `worky_engine/health/runner.py` 106. Subtotal: 532.
- Total de autoria: 709 lineas, bajo el presupuesto de 800.
- `outputs/health/health_scores.csv` (651 lineas con encabezado) queda fuera del conteo de autoria, como golden generado.

## Estado (PR 2)

8/8 tareas de PR 2 completas. Listo para `sdd-verify`.
