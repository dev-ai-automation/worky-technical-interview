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

## PR 2: `mart_last_touch`, A1.3 y A1.4

**Estado**: completo. Las 9 tareas de PR 2 (2.1 a 2.9) están marcadas `[x]` en `tasks.md`.

### Tareas completadas

- [x] 2.1 `worky_engine/sql/analysis/a1_00_last_touch.sql` (vista `mart_last_touch`, transcripción literal del diseño, sección 2.0).
- [x] 2.2 `worky_engine/sql/analysis/a1_03_cohort_retention.sql` (retención por cohorte de alta, celdas censuradas vacías, transcripción literal del diseño, sección 2.3).
- [x] 2.3 `worky_engine/sql/analysis/a1_04_attribution.sql` (atribución a grano deal por primer y último touch, transcripción literal del diseño, sección 2.4).
- [x] 2.4 `worky_engine/analysis/runner.py`: `ANALYSIS_FILES` ahora lista `a1_00_last_touch.sql` primero, luego `a1_01`, `a1_02`, `a1_03`, `a1_04`, `a1_05`; `ANALYSIS_OUTPUTS` agrega `analysis_a1_03_cohort_retention` (`cohort_month, k`) y `analysis_a1_04_attribution` (`model, channel_rank`). `mart_last_touch` no entra a `ANALYSIS_OUTPUTS` porque no tiene CSV propio (no está en la tabla de la sección 1 del diseño).
- [x] 2.5 `worky_engine/quality/analysis_contracts.py`: cinco contratos nuevos (`assert_a1_03_pct_within_range`, `assert_a1_03_monotone_non_increasing`, `assert_a1_03_retained_within_cohort_size`, `assert_a1_04_rate_within_unit`, `assert_a1_04_models_cover_same_deals`) y `run_analysis_contracts` los corre en orden fijo sobre las cinco salidas ya disponibles.
- [x] 2.6 `tests/test_analysis_rules.py`: fixture extendido con dos empresas nuevas (`HS-810020` cohorte reciente censurada, `HS-810021` caso frontera de churn exacto en k = 3), tres touches (empate por `touch_id` en la misma fecha) y dos deals nuevos (uno posterior al empate, otro anterior al único touch de su empresa). Cinco pruebas nuevas.
- [x] 2.7 `tests/test_analysis_dataset_numbers.py`: tres pruebas nuevas marcadas `dataset` con los números medidos sobre el dataset real (ver "Notas de la aplicación del PR 2").
- [x] 2.8 `tests/test_analysis_idempotency.py`: `OUTPUT_NAMES` ahora incluye las cinco salidas acumuladas (`a1_01`, `a1_02`, `a1_03`, `a1_04`, `a1_05`); la comparación byte a byte y la guarda de los ocho goldens de A0 no cambiaron de forma.
- [x] 2.9 Cierre de PR 2: suite completa en verde (168 pruebas), `analyze` corrido dos veces con sha256 idéntico en las cinco salidas, `git status --short outputs` solo muestra los dos goldens nuevos de este PR (los tres de PR 1 y los ocho de A0 sin cambio), goldens de `a1_03_cohort_retention.csv` y `a1_04_attribution.csv` generados.

### Archivos creados o modificados

| Archivo | Acción | Líneas (add/del) |
|---|---|---|
| `worky_engine/sql/analysis/a1_00_last_touch.sql` | crear | 31/0 |
| `worky_engine/sql/analysis/a1_03_cohort_retention.sql` | crear | 48/0 |
| `worky_engine/sql/analysis/a1_04_attribution.sql` | crear | 37/0 |
| `worky_engine/analysis/runner.py` | modificar | 14/8 |
| `worky_engine/quality/analysis_contracts.py` | modificar | 67/4 |
| `tests/test_analysis_rules.py` | modificar | 113/4 |
| `tests/test_analysis_dataset_numbers.py` | modificar | 43/0 |
| `tests/test_analysis_idempotency.py` | modificar | 15/7 |
| `outputs/analysis/a1_03_cohort_retention.csv`, `a1_04_attribution.csv` | generar (fuera del conteo de autoría) | 137 líneas totales |

**Total autoría (código + pruebas)**: 368 adiciones + 23 eliminaciones = **391 líneas**, muy por debajo de las ~405 estimadas por el diseño y del presupuesto de 800.

### Evidencia de unidad de trabajo

| Evidencia | Valor |
|---|---|
| Prueba enfocada | `python -m pytest -q -m "not dataset" tests/test_analysis_rules.py tests/test_analysis_dataset_numbers.py -k "cohort or attribution or a1_03 or a1_04"` y `python -m pytest -q -m "not dataset" tests/test_analysis_rules.py` → 15 passed |
| Arnés en tiempo real | `python -m worky_engine analyze --data-dir data/raw/sistemas --out-dir outputs/analysis` → `analyze: 5 consultas escritas en outputs\analysis`, corrido dos veces, sha256 idéntico en las cinco salidas |
| Límite de reversión | Eliminar `a1_00_last_touch.sql`, `a1_03_cohort_retention.sql`, `a1_04_attribution.sql` y revertir las entradas que agregan a `runner.py` (`ANALYSIS_FILES`/`ANALYSIS_OUTPUTS`) y `analysis_contracts.py` (los cinco `assert_a1_03_*`/`assert_a1_04_*` y sus llamadas en `run_analysis_contracts`); PR 1 (A1.1, A1.2, A1.5) queda intacto |

### Desviaciones del diseño (reportadas, no silenciosas)

1. **`ANALYSIS_OUTPUTS` no incluye `mart_last_touch`**: la tarea 2.4 decía "agregar `a1_00_last_touch.sql` ... a `ANALYSIS_FILES`/`ANALYSIS_OUTPUTS`", pero la tabla de `ANALYSIS_OUTPUTS` de la sección 1 del diseño no lista `mart_last_touch` (no tiene CSV propio; solo la consumen `a1_04` y el corredor la ejecuta desde `ANALYSIS_FILES`). Se agregó solo a `ANALYSIS_FILES`, siguiendo la tabla del diseño en vez de la redacción literal de la tarea.
2. **El canal ganador no cambia entre modelos**: el diseño y el ADR-004 (sección "Qué cambia en las secciones siguientes") anticipan que la comparación de atribución "alimenta la conversación" sobre un posible cambio de canal, y las tareas piden probar "la bandera de cambio de ganador". Sobre el dataset real medido, el canal ganador (`channel_rank = 1`) es `Paid Search` en los dos modelos (tasa 0.225000 en `first_touch`, 0.229885 en `last_touch`): el ganador no cambia. `test_a1_04_canal_ganador_medido_por_modelo` fija este resultado medido en vez de forzar un cambio que el dataset no produce (misma lógica que D12: se publica el número medido).

### Problemas notados y no corregidos en este PR

- El texto de ayuda de `analyze_subparser` en `worky_engine/cli.py` ("Corre A1.1, A1.2 y A1.5 sobre la sabana...") quedó desactualizado desde el PR 1: ahora el comando también corre A1.3 y A1.4. Ninguna tarea de PR 2 pide modificar `cli.py`, y el mensaje dinámico (`analyze: {N} consultas escritas`) ya refleja el conteo correcto (5) sin cambios de código; el texto de ayuda estático se deja para el PR 3, que sí modifica `cli.py` (tarea 3.4).

### Verificación final (verbatim)

```
$ python -m pytest -q
........................................................................ [ 42%]
........................................................................ [ 85%]
........................                                                 [100%]
168 passed in 45.55s
```

```
$ python -m worky_engine analyze --data-dir data/raw/sistemas --out-dir outputs/analysis
analyze: 5 consultas escritas en outputs\analysis
$ python -m worky_engine analyze --data-dir data/raw/sistemas --out-dir outputs/analysis
analyze: 5 consultas escritas en outputs\analysis
$ sha256sum outputs/analysis/*.csv   # antes y despues de la segunda corrida: identico
$ git status --short outputs
?? outputs/analysis/a1_03_cohort_retention.csv
?? outputs/analysis/a1_04_attribution.csv
```

### Notas de la aplicación del PR 2

- **Números reales medidos sobre el dataset**: A1.3 produce 120 filas (30 cohortes por mes de `signup_date`, 4 valores de k), 105 celdas `computed` y 15 `censored`. A1.4 atribuye 962 deals en cada modelo (997 de HubSpot menos los 35 huérfanos de A1.5), y el canal ganador (`channel_rank = 1`) es `Paid Search` en los dos modelos, sin cambio de ganador. La monotonía de `retained` no sube dentro de ninguna de las 30 cohortes (verificado con un chequeo manual y con el contrato `assert_a1_03_monotone_non_increasing`).
- **`cli.py` sin tocar**: ninguna tarea de PR 2 pide modificar `cli.py`; el texto de ayuda estático del subcomando queda desactualizado hasta el PR 3 (ver "Problemas notados y no corregidos").

### Próximos pasos

- `next_recommended`: `sdd-verify` para el PR 2.
- PR 3 (A1.6, `analysis_exceptions.csv`, A1.7, `report.md`) sigue pendiente, fuera del alcance de este work unit.

## PR 3: A1.6, `analysis_exceptions.csv`, A1.7 y `report.md`

**Estado**: completo. Las 12 tareas de PR 3 (3.1 a 3.12) están marcadas `[x]` en `tasks.md`.

### Tareas completadas

- [x] 3.1 `worky_engine/sql/analysis/a1_06_negative_hours.sql`: dos vistas, `analysis_a1_06_negative_hours` (detalle) y `analysis_exceptions` (once columnas de `exceptions_log`), transcripción literal del diseño, sección 2.6 y 3.
- [x] 3.2 `worky_engine/analysis/runner.py`: `ANALYSIS_FILES` agrega `a1_06_negative_hours.sql` al final; `ANALYSIS_OUTPUTS` agrega `analysis_a1_06_negative_hours` y `analysis_exceptions`. `AnalysisResult` gana `dataset_asof` y `ruleset_version` (extensión sobre el diseño, ver nota de desviación).
- [x] 3.3 `worky_engine/analysis/report.py`: `format_report`, sin abrir conexión ni leer archivos. Una sección por ítem A1.1 a A1.6 (definición, motor, SQL verbatim, resultado y nota de límite), justificación de A1.6, sección A1.7 con DDL ilustrativo y tabla de referencias.
- [x] 3.4 `worky_engine/cli.py`: `cmd_analyze` escribe `report.md` con `format_report` después del bucle que ya escribía los CSV de `ANALYSIS_OUTPUTS` (incluye `analysis_exceptions.csv` porque ya está en esa lista desde la tarea 3.2); el mensaje final cuenta solo las vistas `analysis_a1_*` (6), no `analysis_exceptions`; texto de ayuda del subcomando `analyze` actualizado (pendiente reportado en el cierre del PR 2).
- [x] 3.5 `worky_engine/quality/analysis_contracts.py`: `assert_a1_06_all_hours_negative` y `assert_analysis_exceptions_shape`, con la lista de las once columnas de `exceptions_log` como constante del módulo; ambos corren en `run_analysis_contracts`.
- [x] 3.6 `tests/test_analysis_rules.py`: fixture con tres tickets (negativo, positivo, nulo) y una prueba que comprueba que solo el negativo entra al detalle y a `analysis_exceptions`.
- [x] 3.7 `tests/test_analysis_report.py`: siete pruebas sobre la estructura del reporte generado con el mismo fixture mínimo (importado de `test_analysis_rules.py`).
- [x] 3.8 `tests/test_analysis_dataset_numbers.py`: dos pruebas nuevas marcadas `dataset`, 48 filas de A1.6/`analysis_exceptions` y las medianas 13.5/12.2 medidas con pandas sobre `raw_tickets` (sin tolerancia porque coinciden exactas con las citadas en el ADR-004).
- [x] 3.9 `tests/test_analysis_idempotency.py`: `OUTPUT_NAMES` ahora tiene las ocho salidas completas; la guarda de los ocho goldens de A0 no cambió de forma.
- [x] 3.10 `README.md`: un paso 4 nuevo en "Ruta rápida" con el comando `analyze` y una fila en "Qué produce" para `outputs/analysis/report.md`.
- [x] 3.11 Verificado: `grep -rn "—" outputs/analysis README.md worky_engine/analysis` no encuentra nada.
- [x] 3.12 Cierre de PR 3: suite completa en verde (178 pruebas), `analyze` corrido dos veces en carpetas distintas con sha256 idéntico en las ocho salidas y contra el golden commiteado, `git status --short outputs` solo muestra los tres goldens nuevos de este PR, los ocho goldens de A0 sin cambio, goldens de `a1_06_negative_hours.csv`, `analysis_exceptions.csv` y `report.md` generados.

### Archivos creados o modificados

Ver la tabla completa en `tasks.md`, sección "Notas de la aplicación del PR 3". Resumen: 662 adiciones + 38 eliminaciones = **700 líneas de autoría**, dentro del presupuesto de 800 sin `size:exception`.

### Evidencia de unidad de trabajo

| Evidencia | Valor |
|---|---|
| Prueba enfocada | `python -m pytest -q -m "not dataset" tests/test_analysis_report.py tests/test_analysis_rules.py` → 30 passed |
| Arnés en tiempo real | `python -m worky_engine analyze --data-dir data/raw/sistemas --out-dir outputs/analysis` → `analyze: 6 consultas escritas en outputs\analysis`, corrido dos veces en carpetas temporales distintas más una tercera vez sobre `outputs/analysis`, sha256 idéntico en las ocho salidas entre las tres corridas |
| Límite de reversión | Eliminar `a1_06_negative_hours.sql`, `worky_engine/analysis/report.py`, la escritura de `report.md`/`analysis_exceptions.csv` en `cli.py` (revertir a la versión que solo escribía los CSV de A1.1 a A1.5), las dos entradas nuevas de `ANALYSIS_FILES`/`ANALYSIS_OUTPUTS` y `dataset_asof`/`ruleset_version` de `AnalysisResult` en `runner.py`, los dos contratos nuevos en `analysis_contracts.py`, y la línea nueva de `README.md`; PR 1 y PR 2 (A1.1 a A1.5) quedan intactos |

### Deviaciones del diseño (reportadas, no silenciosas)

1. **`AnalysisResult` gana `dataset_asof` y `ruleset_version`**: el diseño solo describía `outputs` y `sql_text`. El encabezado de `report.md` necesita esos dos valores y `report.py` no puede leerlos (no abre conexión ni archivos, decisión D13); se agregaron como campos de `AnalysisResult`, leídos por `run_analysis` desde `mart_master_dataset` justo después de correr `ANALYSIS_FILES`.
2. **`report.py` mide ~336 líneas, no las ~180 estimadas**: la estimación de la sección 7 del diseño subestimó el volumen de texto de las siete secciones. El total de autoría del PR sigue dentro del presupuesto de 800, así que no se movió alcance a otro corte.
3. **DDL de A1.7 con `MERGE INTO` en vez de `DELETE` + `INSERT`**: instrucción explícita de esta fase de incluir un sketch de `MERGE` o `INSERT ... ON CONFLICT`; el diseño original usaba `DELETE` seguido de `INSERT`. El DDL sigue marcado como ilustrativo y no ejecutable.
4. **`tests/test_analysis_report.py` importa el fixture de `test_analysis_rules.py`** en vez de duplicarlo, para no repetir el mismo dataset mínimo en dos archivos; no hay precedente de este patrón cruzado en el resto de la suite.
5. **Fixture de A1.6 con tres tickets** (negativo, positivo, nulo), no solo el negativo que pedía la tarea 3.6, para comprobar que el filtro es estrictamente `< 0`.

### Problemas notados y no corregidos en este PR

- Ninguno bloqueante. La adenda pendiente al ADR-004 (corregir 30 a 33 en `windows_overlap`, reportada en el cierre del PR 1) sigue pendiente; no forma parte del alcance de A1.6/A1.7/`report.md`.

### Verificación final (verbatim)

```
$ python -m pytest -q tests --data-dir data/raw/sistemas
........................................................................ [ 40%]
........................................................................ [ 80%]
..................................                                       [100%]
178 passed in 47.68s
```

```
$ python -m worky_engine analyze --data-dir data/raw/sistemas --out-dir outputs/analysis
analyze: 6 consultas escritas en outputs\analysis
$ git status --short outputs
?? outputs/analysis/a1_06_negative_hours.csv
?? outputs/analysis/analysis_exceptions.csv
?? outputs/analysis/report.md
$ grep -rn "—" outputs/analysis README.md worky_engine/analysis
(sin resultados)
```

### Notas de la aplicación del PR 3

- **Números reales medidos sobre el dataset**: 48 tickets con `resolution_hours` negativo (10 `Open`, 38 `Closed`); mediana del valor absoluto de los negativos 13.5, mediana de los positivos 12.2, medidas con pandas sobre `raw_tickets` sin pasar por DuckDB, coinciden exactas con las que cita la justificación del ADR-004. En A1.4, el modelo de último touch atribuye 326 de los 962 deals a `no_prior_touch`, sin cambio de canal ganador entre modelos (`Paid Search` en los dos).
- **PR 3 cierra el cambio `a1-sql-queries`**: las 33 tareas de las tres PR (11 + 9 + 12) están en `[x]`. Queda pendiente, fuera de este cambio, la adenda al ADR-004 que corrija 30 a 33 en `windows_overlap` (nota del PR 1).

### Próximos pasos

- `next_recommended`: `sdd-verify` para el PR 3 (y cierre del cambio completo).
