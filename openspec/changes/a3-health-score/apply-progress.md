# Progreso de aplicacion: `a3-health-score`, PR 1

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

## Estado

12/12 tareas de PR 1 completas. Listo para `sdd-verify`.
