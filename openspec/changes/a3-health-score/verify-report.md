```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:e592b90aa6d3406a739d9a0684d2aa8efa2e978dc746ea81fea547cb47d8da7e
verdict: fail
blockers: 1
critical_findings: 1
requirements: 11/12
scenarios: 24/25
test_command: python -m pytest -q
test_exit_code: 0
test_output_hash: sha256:a4907da518be33dd3e34351391c0fc21cb497b306d8fec19a073993b4e012072
build_command: python -m worky_engine health --data-dir data/raw/sistemas --out-dir outputs/health (x2) && python -m worky_engine build --data-dir data/raw/sistemas --out-dir outputs && python -m worky_engine analyze --data-dir data/raw/sistemas --out-dir outputs/analysis && python -m worky_engine backtest --data-dir data/raw/sistemas --out-dir outputs
build_exit_code: 0
build_output_hash: sha256:d62c76f29ff25e7f1ea8f7c36826697baf0d1d4248f8f9d79573da2852495759
```

## Verification Report

**Change**: a3-health-score
**Capacidad**: health-score (comando `health`, cuatro subpuntajes ponderados del ADR-005, banda "sin historia", umbrales por capacidad de CSM y validacion medida contra `churn_date`)
**Mode**: Standard (Strict TDD no activo)
**Commit verificado**: 19b0d812a3987271084f727884c1d57be48e12fe (rama feat/a3-pr3-health-validation, arbol limpio antes y despues de esta verificacion). `evidence_revision` es el sha256 de esta cadena de commit.
**Alcance de esta verificacion**: cierre del cambio completo (PR 1, PR 2 y PR 3, con recibo RDD approved y acknowledged en los tres segun `openspec/changes/a3-health-score/state.yaml`). Esta corrida vuelve a comprobar las doce capacidades del spec completo sobre el estado actual del repositorio, no solo lo nuevo del ultimo PR.

### Completeness

| Metrica | Valor |
|---|---|
| Tareas totales (tasks.md) | 28 |
| Tareas completas | 28 |
| Tareas incompletas | 0 |
| Requisitos totales | 12 |
| Requisitos cumplidos | 11 |
| Escenarios totales | 25 |
| Escenarios cumplidos | 24 |

Conteo verificado con grep sobre `openspec/changes/a3-health-score/specs/health-score/spec.md` bajo "## ADDED Requirements": 12 encabezados `### Requirement:` y 25 encabezados `#### Scenario:`. `tasks.md` trae 28 casillas `- [x]` (PR 1: 1.1 a 1.12, PR 2: 2.1 a 2.8, PR 3: 3.1 a 3.8) y cero `- [ ]`.

### Ejecucion de pruebas

**Tests**: 209 passed / 0 failed / 0 skipped

```text
python -m pytest -q
........................................................................ [ 34%]
........................................................................ [ 68%]
.................................................................        [100%]
209 passed in 115.69s (0:01:55)
```

El comando corrio sin `--data-dir` explicito adicional; `tests/conftest.py` resuelve la carpeta de datos por omision a `data/raw/sistemas`, que ya trae las tres bases SQLite del caso, asi que las pruebas marcadas `dataset` corrieron completas. El total coincide con las 209 que registra `apply-progress.md` al cierre del PR 3.

**Idempotencia de health**: Passed. Corrido dos veces seguidas directamente sobre `outputs/health/` (la carpeta que ya tiene los goldens comiteados):

```text
python -m worky_engine health --data-dir data/raw/sistemas --out-dir outputs/health
health: 650 empresas puntuadas en outputs\health
(segunda corrida, mismo comando)
health: 650 empresas puntuadas en outputs\health
```

```text
sha256sum outputs/health/health_scores.csv outputs/health/validation.md
7b56e0478bf19ed4dd4ec3e069c891a62e52f88a5780b502f318208a7c332bda  health_scores.csv
21ae626e46e2bc0d0afb46bb51441e28f603de04e75cc05e3e09aef0476edee7  validation.md
(mismo hash en las dos corridas)

git status --short outputs
(sin salida, antes y despues de las dos corridas)
```

`health_scores.csv` (650 filas mas encabezado) y `validation.md` quedaron identicos, byte por byte, entre las dos corridas y contra la copia ya comiteada. `tests/test_health_idempotency.py::test_dos_corridas_de_health_son_identicas_entre_si_y_contra_el_golden` (marca `dataset`, dentro de los 209 casos en verde) cubre exactamente esta propiedad en cada corrida de la suite, corriendo `health` dos veces en carpetas temporales y comparando ademas el hash de los ocho archivos de `outputs/` (A0), los ocho de `outputs/analysis/` (A1) y `outputs/backtest_report.md`.

**A0 y A1 sin cambio (build, analyze, backtest)**: Passed. Se corrieron los tres comandos una vez cada uno, en este orden, despues de las dos corridas de `health`:

```text
python -m worky_engine build --data-dir data/raw/sistemas --out-dir outputs
build: 650 empresas ensambladas en outputs
git status --short outputs
(sin salida)

python -m worky_engine analyze --data-dir data/raw/sistemas --out-dir outputs/analysis
analyze: 6 consultas escritas en outputs\analysis
git status --short outputs
(sin salida)

python -m worky_engine backtest --data-dir data/raw/sistemas --out-dir outputs
backtest: reporte escrito en outputs\backtest_report.md
git status --short outputs
(sin salida)

git status --short
(sin salida, repositorio completo)
```

Los ocho goldens de A0, los ocho de A1 (incluido `backtest_report.md`) y los dos de `outputs/health/` quedaron identicos a la copia comiteada despues de las cinco corridas de esta sesion (health x2, build, analyze, backtest). El alias publico `auc = _auc` de `worky_engine/harness/backtest.py` (decision D4) es el unico toque a `worky_engine/harness/`, y `backtest_report.md` no cambio, confirmando que reusar el calculo de AUC no movio el golden del harness.

**Em dash**: la busqueda del caracter em dash sobre `worky_engine/health`, `worky_engine/sql/health`, `worky_engine/quality/health_contracts.py`, `outputs/health`, `README.md`, `docs/decisions/ADR-005-health-score-model.md` y `openspec/changes/a3-health-score/design.md` no encontro ninguna coincidencia. `tests/test_health_report.py::test_sin_em_dash_en_el_documento` fija esta regla como prueba automatizada sobre `validation.md`.

**Coverage**: no hay umbral de cobertura de linea configurado en `openspec/config.yaml` (`coverage_threshold: 0`); no aplica.

### Spec Compliance Matrix (health-score, 12 requisitos, 25 escenarios)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| comando health sin build previo | corrida sin build previo | Verificacion manual de esta sesion (dos corridas, exit 0, sin build previo) y tests/test_health_idempotency.py, que corre health en carpetas temporales sin build previo | COMPLIANT |
| comando health sin build previo | dos corridas identicas | tests/test_health_idempotency.py::test_dos_corridas_de_health_son_identicas_entre_si_y_contra_el_golden (marca dataset) y verificacion manual de esta sesion, hash identico en las dos corridas | COMPLIANT |
| comando health sin build previo | goldens de A0 y A1 sin cambio | Mismo test (compara el hash de los ocho archivos de A0, los ocho de A1 y backtest_report.md antes y despues de health) y verificacion manual de esta sesion con build, analyze y backtest corridos despues, git status --short outputs vacio en las cinco corridas | COMPLIANT |
| comando health sin build previo | falta una dependencia o una base de datos | Sin test que invoque el subcomando health con --data-dir inexistente o con DuckDB simulado ausente. cmd_health (worky_engine/cli.py:314-369) llama a las mismas funciones _resolve_data_dir y _exit_missing_dependency que cmd_build y cmd_analyze, y esa ruta si tiene pruebas dedicadas en tests/test_build_contracts.py. Ver WARNING 1 | COMPLIANT (evidencia indirecta, ver WARNING 1) |
| mes de corte igual para bajas y activas | mismo desplazamiento para las dos poblaciones | tests/test_health_rules.py::test_antiguedad_se_recorta_a_cero_para_una_empresa_dada_de_alta_despues_del_corte (empresa activa HS-810004, asof_month = 2024-06) y test_mes_de_uso_posterior_al_corte_queda_excluido (empresa con baja HS-810001, mismo asof_month = 2024-06), sobre el mismo fixture con health_params k_months=2, active_offset=2, mismo valor para las dos poblaciones | COMPLIANT |
| mes de corte igual para bajas y activas | ningun dato posterior al corte entra al subpuntaje | tests/test_health_rules.py::test_mes_de_uso_posterior_al_corte_queda_excluido (mes de uso posterior excluido de sig_momentum) y test_ticket_excluido_el_primer_dia_del_mes_siguiente_e_incluido_el_ultimo_dia_del_corte (ticket por dia, no por mes) | COMPLIANT |
| mes de corte igual para bajas y activas | lectura literal como sensibilidad | worky_engine/health/runner.py (SENSITIVITY_RUNS, corrida literal con active_offset=0) y outputs/health/validation.md, seccion Sensibilidades, fila Lectura literal, verificada en esta sesion sobre el archivo generado; tests/test_health_report.py verifica la seccion mas no el texto exacto de esa fila | COMPLIANT |
| los cuatro subpuntajes normalizados por percentil | subpuntaje de momentum en el mes de corte | tests/test_health_equivalence.py::test_caso_tipico_no_degenerado_coincide_con_el_harness y tests/test_health_rules.py::test_empates_en_el_rango_percentil_producen_el_mismo_subpuntaje | COMPLIANT |
| los cuatro subpuntajes normalizados por percentil | antiguedad con cobertura total | tests/test_health_rules.py::test_cuenta_de_dos_meses_cae_en_sin_historia_con_antiguedad_y_sin_subpuntajes_de_uso (score_tenure presente aun en sin historia) | COMPLIANT |
| senales medidas con peso cero | columnas de peso cero en el CSV | Inspeccion de outputs/health/health_scores.csv en esta sesion (encabezado trae tickets_window_total, tickets_window_urgent, csat_window_avg, activation_score) y worky_engine/health/runner.py _OUTPUT_COLUMNS | COMPLIANT |
| senales medidas con peso cero | AUC de las senales de peso cero | tests/test_health_report.py::test_soporte_presente_con_su_auc_y_su_peso_cero y outputs/health/validation.md, seccion AUC por senal, verificado en esta sesion (peso 0.00 para tickets, urgentes, CSAT y activacion) | COMPLIANT |
| score como suma ponderada de los subpuntajes del ADR-005 | suma ponderada verificable | tests/test_health_rules.py::test_suma_ponderada_recomputable_a_mano y contrato assert_health_score_matches_weights (worky_engine/quality/health_contracts.py:69-80), corrido dentro de run_health_contracts en cada corrida de health | COMPLIANT |
| banda sin historia para cuentas sin uso suficiente | cuenta nueva sin subpuntajes de uso | tests/test_health_rules.py::test_cuenta_de_dos_meses_cae_en_sin_historia_con_antiguedad_y_sin_subpuntajes_de_uso | COMPLIANT |
| banda sin historia para cuentas sin uso suficiente | contada en el recall como no detectable | tests/test_health_dataset_numbers.py::test_650_filas_89_bajas_22_no_detectables (marca dataset) y worky_engine/health/metrics.py::precision_recall (undetectable = denominator - detectable_denominator) | COMPLIANT |
| tasas de marcado por capacidad de CSM | 78 cuentas marcadas al 15 % | tests/test_health_dataset_numbers.py::test_marcadas_al_15_por_ciento_sobre_el_libro_activo (marca dataset: libro activo 518, marcadas 78, ~11.1 por CSM) | COMPLIANT |
| tasas de marcado por capacidad de CSM | corte fijo reportado aparte | worky_engine/health/metrics.py::fixed_cut_metrics y outputs/health/validation.md, tabla de metricas, fila corte fijo score menor a 40, verificada en esta sesion junto a las tres tasas | COMPLIANT |
| metricas de validacion contra churn_date | tabla de metricas a las tres tasas | tests/test_health_dataset_numbers.py::test_metricas_al_10_15_y_20_por_ciento (marca dataset) y outputs/health/validation.md, seccion Metricas de validacion | COMPLIANT |
| metricas de validacion contra churn_date | deteccion temprana definida sobre las marcadas en k = 2 | tests/test_health_dataset_numbers.py::test_deteccion_temprana_en_k3 (marca dataset: 56 elegibles, 0.929 de proporcion) | COMPLIANT |
| metricas de validacion contra churn_date | tabla de sensibilidad en k = 3 | outputs/health/validation.md, seccion Sensibilidades, fila k = 3, verificada en esta sesion (AUC 0.955, recall 0.607); tests/test_health_report.py verifica la presencia de la seccion, no el numero exacto | COMPLIANT |
| aceptacion del harness sobre los pesos del ADR-005 | los pesos por juicio pasan el harness | tests/test_health_dataset_numbers.py::test_regla_de_aceptacion_se_alcanza_sobre_las_bajas_detectables (marca dataset, llama metrics.acceptance_check y confirma passed is True, AUC 0.997, recall_detectable_20 1.000). outputs/health/validation.md muestra el AUC (0.997) y el recall detectable (1.000) en su tabla de metricas, pero nunca cita los umbrales 0.95 / 0.85 ni una frase que confirme explicitamente que se cumplieron. Ver WARNING 2 | COMPLIANT parcial, sin confirmacion explicita, ver WARNING 2 |
| aceptacion del harness sobre los pesos del ADR-005 | los pesos no pasan y se recomienda la mezcla medida | Sin ningun test, de fixture o de dataset. worky_engine/health/metrics.py::acceptance_check calcula el resultado pero ninguna funcion de worky_engine/health/report.py ni de worky_engine/cli.py lo invoca; no existe ninguna rama de codigo que muestre la mezcla medida (uso 70, antiguedad 15, activacion 15) en validation.md cuando el umbral no se alcanza. La comparacion equivalente si existe, pero vive en docs/decisions/ADR-005-health-score-model.md (Adenda 1), escrita a mano durante el PR 2, no generada por el comando. Ver CRITICAL 1 | FAILING, comportamiento ausente, CRITICAL 1 |
| respuesta narrativa de A3.4 en validation.md | narrativa de A3.4 presente | tests/test_health_report.py::test_seccion_a3_4_presente_con_costo_asimetrico y outputs/health/validation.md, seccion Respuesta a A3.4, verificada en esta sesion | COMPLIANT |
| contexto comercial fuera del score | canal y segmento en el CSV sin pesar en el score | tests/test_health_report.py::test_contexto_comercial_reporta_canal_y_segmento_fuera_del_score y worky_engine/health/scoring.py::_weighted_sum (no referencia acquisition_channel ni segment); inspeccion de health_scores.csv en esta sesion (columnas presentes) | COMPLIANT |
| pruebas por regla y sobre el dataset real | prueba de fixture por regla | tests/test_health_rules.py, diez pruebas sobre el fixture minimo propio (una por regla: exclusion por corte, denominadores degenerados, antiguedad recortada, empates, banda sin historia, suma ponderada, marcas anidadas, bandas contra umbrales) | COMPLIANT |
| pruebas por regla y sobre el dataset real | prueba marcada dataset con los numeros reales | tests/test_health_dataset_numbers.py, cinco pruebas con marca dataset que fijan 650 filas, 89 bajas, 22 no detectables (4 con cero meses de uso), 78 marcadas al 15 % sobre el libro activo de 518, y la regla de aceptacion sobre las detectables | COMPLIANT |

**Compliance summary**: 24/25 escenarios compliant (dos con evidencia indirecta o parcial documentada en WARNING 1 y WARNING 2), 1/25 escenario FAILING por comportamiento ausente (CRITICAL 1).

### Correctness (Static Evidence)

| Elemento | Estado | Notas |
|---|---|---|
| HEALTH_FILES con h1_company_asof.sql primero y h6_asof_inputs.sql al final | Implementado | worky_engine/health/runner.py:25-32; h6 une h1 a h5 |
| SENSITIVITY_RUNS con las tres corridas (primaria 2/2, k3 3/3, literal 2/0) | Implementado | worky_engine/health/runner.py:37-41 |
| health_params de una sola fila creada antes de cada corrida de HEALTH_FILES | Implementado | worky_engine/health/runner.py:85-93 (_run_once), consumida por CROSS JOIN health_params p en h1_company_asof.sql |
| Los doce contratos de health_contracts.py | Implementados y corridos | worky_engine/quality/health_contracts.py, run_health_contracts en orden fijo (incluye assert_health_bands_match_thresholds, agregado en la correccion R3-risk-band-thresholds-unproved del PR 1, no contado como los doce en el diseno ni en apply-progress.md) |
| report.py no abre conexion ni lee archivos | Implementado | worky_engine/health/report.py, sin import duckdb ni open(); recibe HealthResult ya materializado |
| mart_support_asof fuera de mart_support.sql | Implementado | worky_engine/sql/health/h4_support_asof.sql; worky_engine/sql/marts/mart_support.sql sin cambio de este cambio |
| Alias publico auc = _auc en el harness | Implementado | worky_engine/harness/backtest.py:127-129, reexportado en worky_engine/harness/__init__.py; worky_engine/health/metrics.py lo importa como harness_auc |
| cmd_health corre los contratos de A0 antes que los de A3 | Implementado | worky_engine/cli.py:344-361 |
| activation_raw, promedio de las cuatro columnas de actividad temprana | Implementado, decision de implementacion documentada | worky_engine/sql/health/h5_activation.sql:27-28; el diseno no fijaba la formula exacta, apply-progress.md documenta la eleccion |
| Apendice de SQL como decimotercera seccion de validation.md | Implementado, desviacion documentada | worky_engine/health/report.py:381-386 (_sql_appendix_section); el diseno seccion 7 lista doce secciones fijas y ninguna es un apendice de SQL; apply-progress.md documenta la brecha |
| Regla de aceptacion (acceptance_check) calculada pero no surfaceada en validation.md ni en cmd_health | Implementado solo a nivel de funcion, sin invocacion en produccion | worky_engine/health/metrics.py:254-275; ninguna llamada a acceptance_check en worky_engine/health/report.py ni worky_engine/cli.py (ver CRITICAL 1) |
| Referencias a los ADR en validation.md con ruta de archivo incorrecta | Implementado con error | worky_engine/health/report.py:369-378 (_references_section): cita docs/decisions con acento y sin la e final, carpeta que no existe; la carpeta real es docs/decisions (ver WARNING 3) |

### Coherence (Design)

| Decision | Seguida? | Notas |
|---|---|---|
| D1, health con su propia conexion, espejo de analyze | Si | cmd_health no llama a cmd_build ni a cmd_analyze; corrida sin build previo verificada en esta sesion |
| D2, paquete nuevo worky_engine/health/ | Si | scoring.py, metrics.py, runner.py, report.py, __init__.py |
| D3, SQL calcula agregados ventanados, pandas calcula percentiles y metricas | Si | Las seis vistas SQL solo agregan; scoring.py y metrics.py hacen todo el resto en pandas |
| D4, alias publico auc en vez de copiar el calculo | Si | worky_engine/harness/backtest.py:127-129; tests/test_harness_regression.py verifica identidad del objeto |
| D5, SQL es produccion, _features es referencia, prueba de equivalencia entre los dos | Si | tests/test_health_equivalence.py, tres pruebas, con los tres casos degenerados exceptuados de forma explicita |
| D6, mes de referencia derivado de churn_date o dataset_asof, nunca constante | Si | h1_company_asof.sql:30-31, sin ningun literal de fecha |
| D7, mes de corte con el mismo desplazamiento para bajas y activas en la corrida principal | Si | health_params k_months=2, active_offset=2 en la corrida primaria; confirmado en tests/test_health_rules.py |
| D8, sensibilidades como corridas adicionales, no como CSV separado | Si | SENSITIVITY_RUNS alimenta solo validation.md; health_scores.csv publica solo la corrida principal |
| D9, health_params de una fila con CROSS JOIN, sin interpolar texto | Si | worky_engine/health/runner.py:85-93; las seis vistas SQL leen health_params con CROSS JOIN |
| D10, todo el SQL nuevo bajo worky_engine/sql/health/, incluida mart_support_asof | Si | worky_engine/sql/health/h4_support_asof.sql; ningun archivo en worky_engine/sql/marts/ para este cambio |
| D11, resguardo de fuga en tres filtros | Si | u.month menor o igual a a.asof_month en h2, ventana por dia en tickets en h4, tercer mes de activacion menor o igual a asof_month en h5 |
| D12, normalizacion por rango percentil, empates promediados | Si | worky_engine/health/scoring.py:44-52 (percentile_score, rank pct=True method=average) |
| D13, una sola poblacion de normalizacion, bajas y activas juntas | Si | percentile_score no filtra por churned |
| D14, redondeo a dos decimales antes de sumar y ordenar | Si | worky_engine/health/scoring.py:52,70; _order_rows ordena sobre el valor ya redondeado |
| D15, denominadores degenerados en 0.0, no nulos | Si | h2_usage_signals.sql:64-72; tests/test_health_rules.py::test_tres_denominadores_degenerados_valen_cero |
| D16, umbral operativo del libro activo con interpolation lower, aplicado a activas y bajas por igual | Si | worky_engine/health/scoring.py:117-124 |
| D17, denominador del recall incluye a las no detectables sin excepcion | Si | worky_engine/health/metrics.py:67-95 (precision_recall, denominator = churned.sum() sin filtrar por historia) |
| D18, regla de aceptacion restablecida en la Adenda 1 sobre las bajas detectables | Si en el calculo; No en la superficie de validation.md | worky_engine/health/metrics.py:254-275 calcula correctamente sobre recall_detectable; pero validation.md no expone el veredicto ni la alternativa de mezcla medida cuando falla (ver CRITICAL 1) |
| D19, bandas alto/medio/bajo/sin historia, alto es el 15 % marcado | Si | worky_engine/health/scoring.py:73-87 (_risk_band); contrato assert_health_bands_match_thresholds |
| D20, sin bandera de corrida, SENSITIVITY_RUNS es una constante | Si | health no acepta --k ni bandera de sensibilidad en su parser (worky_engine/cli.py:418-425) |
| D21, numeros reales solo en pruebas dataset, nunca en contratos | Si | worky_engine/quality/health_contracts.py no trae ningun literal 89/22/78/650; los doce contratos son invariantes |

### Desviaciones conocidas y aceptadas

- activation_raw es el promedio de las cuatro columnas de actividad temprana (payroll_runs_completed, logins, features_used, active_users); el diseno (tarea 1.5) no fijaba la formula exacta. Documentado en apply-progress.md como decision de implementacion dentro de un hueco del diseno.
- HealthResult gana dataset_asof y ruleset_version sobre lo que describia la seccion 1 del diseno original, mismo patron que AnalysisResult de A1: report.py no abre conexion ni lee archivos (D13) y necesita esos dos valores para el encabezado de validation.md. Documentado en apply-progress.md (PR 3).
- El apendice de SQL de validation.md es una decimotercera seccion que la seccion 7 del diseno no lista (esta describe doce secciones fijas). Documentado en apply-progress.md como brecha del diseno, resuelta siguiendo el patron de analysis/report.py de A1.
- La mezcla de pesos medida (uso 70 por ciento, antiguedad 15 por ciento, activacion 15 por ciento) se probo en la tarea 2.6 siguiendo la redaccion original de D18, no ayudo (AUC bajo a 0.992, recall general se quedo en 0.753) y se descarto; la Adenda 1 del ADR-005 documenta la medicion completa y la decision del usuario de conservar los pesos originales. Documentado en apply-progress.md y en el ADR.
- assert_health_bands_match_thresholds es un contrato agregado en una correccion de revision (R3-risk-band-thresholds-unproved, PR 1) que ni el diseno ni la tabla original de apply-progress.md contaban; el total real de contratos es doce, no once. No es una tarea sin marcar: los doce corren en run_health_contracts.
- Las rutas de referencia a los ADR en la seccion de Referencias de validation.md tienen un error tipografico en el nombre de la carpeta (la carpeta real del repositorio es docs/decisions, sin acentos). Ningun test verifica el contenido de esa seccion mas alla de que exista el encabezado. Ver WARNING 3.

### Issues Found

**CRITICAL**:

1. Requisito "aceptacion del harness sobre los pesos del ADR-005", escenario "los pesos no pasan y se recomienda la mezcla medida": el comportamiento que el spec exige con MUST (validation.md debe reportarlo y debe recomendar la mezcla medida cuando el score no alcanza AUC mayor o igual a 0.95 o recall mayor o igual a 0.85 al 20 por ciento entre las bajas detectables) no existe en ningun archivo de produccion. worky_engine/health/metrics.py::acceptance_check calcula correctamente el veredicto, probado por tests/test_health_dataset_numbers.py::test_regla_de_aceptacion_se_alcanza_sobre_las_bajas_detectables (marca dataset), pero ninguna funcion de worky_engine/health/report.py ni worky_engine/cli.py::cmd_health la invoca. No hay ninguna rama condicional que, si acceptance_check devolviera el resultado negativo, escribiera la mezcla medida (uso 70, antiguedad 15, activacion 15) en validation.md. Confirmado con una busqueda de acceptance_check en todo worky_engine y tests (solo aparece la definicion y la prueba de dataset) y con inspeccion linea por linea de report.py (sin ninguna mencion a la mezcla ni a los umbrales 0.95 o 0.85). Con el dataset del caso el veredicto real es positivo (AUC 0.997, recall detectable 1.000), asi que esta rama nunca se ejecuta con los datos actuales, pero el codigo tampoco la ejecutaria si el dataset cambiara y el umbral dejara de alcanzarse: la unica evidencia de la mezcla medida que se probo en la tarea 2.6 vive en docs/decisions/ADR-005-health-score-model.md (Adenda 1), escrita a mano durante el PR 2, no generada por el comando health. Esto bloquea el archivado hasta que se implemente la rama condicional en report.py, o se decida y documente explicitamente que el spec queda satisfecho solo por el proceso manual de PR 2, lo cual requeriria ajustar la redaccion del escenario en una revision del spec, no dejarlo sin resolver.

**WARNING**:

1. La ruta de error de health para "falta una dependencia o una base de datos" (requisito comando health sin build previo) no tiene una prueba que invoque el subcomando health con --data-dir inexistente o con DuckDB no instalado. cmd_health reusa exactamente las mismas funciones (_resolve_data_dir, _exit_missing_dependency) que cmd_build y cmd_analyze, y esa ruta si tiene pruebas dedicadas en tests/test_build_contracts.py, pero ninguna prueba ejercita el codigo de salida 2 a traves del subcomando health. Mismo patron ya documentado como WARNING en el verify-report de a1-sql-queries. Riesgo bajo, mismo codigo y mismo mensaje.
2. La regla de aceptacion (AUC mayor o igual a 0.95, recall detectable mayor o igual a 0.85 al 20 por ciento) se calcula correctamente y se prueba a nivel de funcion (tests/test_health_dataset_numbers.py::test_regla_de_aceptacion_se_alcanza_sobre_las_bajas_detectables), y sus dos cifras (AUC 0.997, recall detectable 1.000) aparecen en la tabla de metricas de validation.md, pero el documento nunca cita los umbrales 0.95 o 0.85 ni afirma explicitamente que se cumplieron: quien lo lea tiene que comparar las cifras el mismo contra los umbrales que solo aparecen en el ADR-005 y en el spec, no en validation.md. Relacionado con CRITICAL 1: si se implementa la rama condicional para el caso en que no pasa, conviene que la misma rama declare explicitamente el caso en que si pasa.
3. worky_engine/health/report.py, funcion _references_section (lineas 369 a 378), cita las tres referencias del ADR con una ruta de carpeta que no existe en el repositorio, un error de tecleo en el nombre de la carpeta real docs/decisions. Ningun test verifica el contenido de la seccion de referencias mas alla de que el encabezado exista en el orden correcto (tests/test_health_report.py::test_las_doce_secciones_en_orden). Un lector que siga ese enlace desde validation.md no encontrara el archivo.

**SUGGESTION**:

1. apply-progress.md (PR 1) describe "los ocho contratos de forma y banda calculables en memoria" y no menciona el noveno contrato (assert_health_bands_match_thresholds) que la correccion de revision R3-risk-band-thresholds-unproved agrego al mismo PR; el docstring de health_contracts.py si dice "doce" en su version actual, pero la nota de progreso del PR 1 quedo desactualizada. Vale la pena corregirla antes o durante el archivado.
2. Ninguna prueba automatizada verifica el texto exacto de la fila "Lectura literal" ni de la fila "k = 3" en la seccion de sensibilidades de validation.md; tests/test_health_report.py solo confirma que la seccion existe y que dice "en este dataset". Vale la pena que un cambio futuro agregue una asercion sobre el contenido de esas filas, no solo sobre el encabezado de la seccion.
3. La tabla "Metricas medidas" de apply-progress.md (PR 2) no incluye el "Recall detectable" que si aparece en la tabla real de validation.md y en metrics.rate_metrics; no es un error, solo una nota de progreso escrita antes de que esa columna se agregara a la funcion.

### Verdict

**FAIL**

Las 28 tareas de tasks.md (12 del PR 1, 8 del PR 2, 8 del PR 3) estan completas, y las 209 pruebas de python -m pytest -q pasan (exit 0). El comando health corrio dos veces seguidas sobre outputs/health/ sin diferencia byte a byte (git status --short outputs vacio en las dos corridas), y build, analyze y backtest, corridos despues, no tocaron ninguno de los ocho goldens de A0, los ocho de A1 ni backtest_report.md (git status --short outputs y git status --short del repositorio completo vacios en las cinco corridas de esta sesion). Ningun archivo generado ni la prosa de README.md o validation.md contiene el caracter em dash. Las veintiuna decisiones de diseno D1 a D21 se verificaron contra el codigo: veinte coinciden sin reserva, y D18 coincide en el calculo (acceptance_check, probado y correcto) pero no en la superficie del documento, porque validation.md nunca expone el veredicto ni la alternativa de mezcla medida.

De los 25 escenarios del spec, 24 tienen evidencia de cumplimiento con prueba automatizada o inspeccion directa del archivo generado en esta sesion, y 1 escenario (requisito "aceptacion del harness sobre los pesos del ADR-005", "los pesos no pasan y se recomienda la mezcla medida") no tiene ninguna prueba ni ninguna implementacion: el comportamiento que el spec exige con MUST esta completamente ausente del codigo de produccion (CRITICAL 1). Esto no es un defecto que el dataset actual exponga, porque el score si pasa la regla de aceptacion con margen, pero es una brecha real entre lo que el spec promete y lo que el comando health puede hacer si algun dia el umbral no se alcanza. El cambio no esta listo para sdd-archive hasta que se resuelva CRITICAL 1, ya sea implementando la rama condicional en report.py o ajustando el spec de forma explicita y documentada para reflejar que ese escenario se resuelve por proceso humano, como ya ocurrio en la tarea 2.6, y no por el comando.
