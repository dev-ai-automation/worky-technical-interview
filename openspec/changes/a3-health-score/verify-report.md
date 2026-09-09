```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:e677b0acccfa7bc0214d884cf6a39ba667a921f86555fb3698247723f2601576
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 12/12
scenarios: 25/25
test_command: python -m pytest -q
test_exit_code: 0
test_output_hash: sha256:8cad9147ebb16eb451b3bc590daf6fd1021635735b744965031542efb66384b0
build_command: python -m worky_engine health --data-dir data/raw/sistemas --out-dir outputs/health (x2) && python -m worky_engine build --data-dir data/raw/sistemas --out-dir outputs && python -m worky_engine analyze --data-dir data/raw/sistemas --out-dir outputs/analysis && python -m worky_engine backtest --data-dir data/raw/sistemas --out-dir outputs
build_exit_code: 0
build_output_hash: sha256:d62c76f29ff25e7f1ea8f7c36826697baf0d1d4248f8f9d79573da2852495759
```

## Verification Report

**Change**: a3-health-score
**Capacidad**: health-score (comando `health`, cuatro subpuntajes ponderados del ADR-005, banda "sin historia", umbrales por capacidad de CSM y validacion medida contra `churn_date`)
**Mode**: Standard (Strict TDD no activo)
**Commit verificado**: 82353a2ca55c3f67632a1f6f67cc1bf3ece7b808 (rama feat/a3-pr3-health-validation, arbol limpio antes y despues de esta verificacion). `evidence_revision` es el sha256 de esta cadena de commit.
**Alcance de esta verificacion**: RERUN completo del cambio despues del blocker encontrado en la corrida anterior (verdict fail, commit 19b0d812, reporte previo commiteado en 2e19262). Entre esa corrida y esta, los commits fc19791 y 82353a2 agregaron `_acceptance_section` a `worky_engine/health/report.py`, cableada entre la seccion de metricas y la matriz de confusion, y corrigieron las rutas de referencia. Esta corrida vuelve a comprobar las doce capacidades del spec completo sobre el estado actual del repositorio, no solo el cambio incremental.

### Completeness

| Metrica | Valor |
|---|---|
| Tareas totales (tasks.md) | 28 |
| Tareas completas | 28 |
| Tareas incompletas | 0 |
| Requisitos totales | 12 |
| Requisitos cumplidos | 12 |
| Escenarios totales | 25 |
| Escenarios cumplidos | 25 |

Conteo verificado con grep sobre `openspec/changes/a3-health-score/specs/health-score/spec.md` bajo "## ADDED Requirements": 12 encabezados `### Requirement:` y 25 encabezados `#### Scenario:` (`grep -c "^### Requirement:"` = 12, `grep -c "^#### Scenario:"` = 25). `tasks.md` trae 28 casillas `- [x]` (PR 1: 1.1 a 1.12, PR 2: 2.1 a 2.8, PR 3: 3.1 a 3.8) y cero `- [ ]`.

### Ejecucion de pruebas

**Tests**: 213 passed / 0 failed / 0 skipped

```text
python -m pytest -q
........................................................................ [ 33%]
........................................................................ [ 67%]
.....................................................................    [100%]
213 passed in 109.47s (0:01:49)
```

213 pruebas, cuatro mas que las 209 del reporte anterior: los commits fc19791 y 82353a2 agregaron dos pruebas en `tests/test_health_report.py` (seccion de aceptacion presente con umbrales y veredicto, recomendacion de la mezcla medida cuando falla), una prueba adicional de guardia sin bajas en el mismo archivo, y una prueba en `tests/test_health_dataset_numbers.py` que fija el veredicto cumplido sobre el dataset real. El comando corrio sin `--data-dir` explicito adicional; `tests/conftest.py` resuelve la carpeta de datos por omision a `data/raw/sistemas`, asi que las pruebas marcadas `dataset` corrieron completas.

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
8c9b8058a1f6baf6c8a238ef8fc1dbd632c14bf51555413ee3339ba259c34684  validation.md
(mismo hash en las dos corridas)

git status --short outputs
(sin salida, antes y despues de las dos corridas)
```

`health_scores.csv` (650 filas mas encabezado) y `validation.md` quedaron identicos, byte por byte, entre las dos corridas y contra la copia ya comiteada. El hash de `validation.md` (8c9b8058...) es distinto del que registraba el reporte anterior (21ae626e...), consistente con las diez lineas nuevas que fc19791 y 82353a2 agregaron al documento (la seccion de aceptacion): la copia comiteada de `outputs/health/validation.md` en este commit ya trae esa seccion, asi que el hash coincide contra el golden actual, no contra el de la corrida verificada anteriormente. `tests/test_health_idempotency.py::test_dos_corridas_de_health_son_identicas_entre_si_y_contra_el_golden` (marca `dataset`, dentro de los 213 casos en verde) cubre exactamente esta propiedad en cada corrida de la suite, corriendo `health` dos veces en carpetas temporales y comparando ademas el hash de los ocho archivos de `outputs/` (A0), los ocho de `outputs/analysis/` (A1) y `outputs/backtest_report.md`.

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

Los ocho goldens de A0, los ocho de A1 (incluido `backtest_report.md`) y los dos de `outputs/health/` quedaron identicos a la copia comiteada despues de las cinco corridas de esta sesion (health x2, build, analyze, backtest). `build_output_hash` (d62c76f2...) coincide exactamente con el del reporte anterior: los mensajes de consola de los cinco comandos son deterministas y no cambiaron entre las dos verificaciones.

**Em dash**: la busqueda del caracter em dash sobre `worky_engine/health`, `worky_engine/sql/health`, `worky_engine/quality/health_contracts.py`, `outputs/health`, `README.md`, `docs/decisions/ADR-005-health-score-model.md` y `openspec/changes/a3-health-score/design.md` no encontro ninguna coincidencia. `tests/test_health_report.py::test_sin_em_dash_en_el_documento` fija esta regla como prueba automatizada sobre `validation.md`, incluida la nueva seccion de aceptacion.

**Coverage**: no hay umbral de cobertura de linea configurado en `openspec/config.yaml` (`coverage_threshold: 0`); no aplica.

### Spec Compliance Matrix (health-score, 12 requisitos, 25 escenarios)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| comando health sin build previo | corrida sin build previo | Verificacion manual de esta sesion (dos corridas, exit 0, sin build previo) y tests/test_health_idempotency.py, que corre health en carpetas temporales sin build previo | COMPLIANT |
| comando health sin build previo | dos corridas identicas | tests/test_health_idempotency.py::test_dos_corridas_de_health_son_identicas_entre_si_y_contra_el_golden (marca dataset) y verificacion manual de esta sesion, hash identico en las dos corridas | COMPLIANT |
| comando health sin build previo | goldens de A0 y A1 sin cambio | Mismo test (compara el hash de los ocho archivos de A0, los ocho de A1 y backtest_report.md antes y despues de health) y verificacion manual de esta sesion con build, analyze y backtest corridos despues, git status --short outputs vacio en las cinco corridas | COMPLIANT |
| comando health sin build previo | falta una dependencia o una base de datos | Sin test que invoque el subcomando health con --data-dir inexistente o con DuckDB simulado ausente. cmd_health (worky_engine/cli.py) llama a las mismas funciones _resolve_data_dir y _exit_missing_dependency que cmd_build y cmd_analyze, y esa ruta si tiene pruebas dedicadas en tests/test_build_contracts.py. Sin cambio desde el reporte anterior. Ver WARNING 1 | COMPLIANT (evidencia indirecta, ver WARNING 1) |
| mes de corte igual para bajas y activas | mismo desplazamiento para las dos poblaciones | tests/test_health_rules.py::test_antiguedad_se_recorta_a_cero_para_una_empresa_dada_de_alta_despues_del_corte y test_mes_de_uso_posterior_al_corte_queda_excluido, sobre el mismo fixture con health_params k_months=2, active_offset=2, mismo valor para las dos poblaciones | COMPLIANT |
| mes de corte igual para bajas y activas | ningun dato posterior al corte entra al subpuntaje | tests/test_health_rules.py::test_mes_de_uso_posterior_al_corte_queda_excluido y test_ticket_excluido_el_primer_dia_del_mes_siguiente_e_incluido_el_ultimo_dia_del_corte | COMPLIANT |
| mes de corte igual para bajas y activas | lectura literal como sensibilidad | worky_engine/health/runner.py (SENSITIVITY_RUNS, corrida literal con active_offset=0) y outputs/health/validation.md, seccion Sensibilidades, fila Lectura literal, verificada en esta sesion | COMPLIANT |
| los cuatro subpuntajes normalizados por percentil | subpuntaje de momentum en el mes de corte | tests/test_health_equivalence.py::test_caso_tipico_no_degenerado_coincide_con_el_harness y tests/test_health_rules.py::test_empates_en_el_rango_percentil_producen_el_mismo_subpuntaje | COMPLIANT |
| los cuatro subpuntajes normalizados por percentil | antiguedad con cobertura total | tests/test_health_rules.py::test_cuenta_de_dos_meses_cae_en_sin_historia_con_antiguedad_y_sin_subpuntajes_de_uso (score_tenure presente aun en sin historia) | COMPLIANT |
| senales medidas con peso cero | columnas de peso cero en el CSV | Inspeccion de outputs/health/health_scores.csv en esta sesion (encabezado trae tickets_window_total, tickets_window_urgent, csat_window_avg, activation_score) y worky_engine/health/runner.py _OUTPUT_COLUMNS | COMPLIANT |
| senales medidas con peso cero | AUC de las senales de peso cero | tests/test_health_report.py::test_soporte_presente_con_su_auc_y_su_peso_cero y outputs/health/validation.md, seccion AUC por senal, verificado en esta sesion (peso 0.00 para tickets, urgentes, CSAT y activacion) | COMPLIANT |
| score como suma ponderada de los subpuntajes del ADR-005 | suma ponderada verificable | tests/test_health_rules.py::test_suma_ponderada_recomputable_a_mano y contrato assert_health_score_matches_weights, corrido dentro de run_health_contracts en cada corrida de health | COMPLIANT |
| banda sin historia para cuentas sin uso suficiente | cuenta nueva sin subpuntajes de uso | tests/test_health_rules.py::test_cuenta_de_dos_meses_cae_en_sin_historia_con_antiguedad_y_sin_subpuntajes_de_uso | COMPLIANT |
| banda sin historia para cuentas sin uso suficiente | contada en el recall como no detectable | tests/test_health_dataset_numbers.py::test_650_filas_89_bajas_22_no_detectables (marca dataset) y worky_engine/health/metrics.py::precision_recall (undetectable = denominator - detectable_denominator) | COMPLIANT |
| tasas de marcado por capacidad de CSM | 78 cuentas marcadas al 15 % | tests/test_health_dataset_numbers.py::test_marcadas_al_15_por_ciento_sobre_el_libro_activo (marca dataset: libro activo 518, marcadas 78, ~11.1 por CSM) | COMPLIANT |
| tasas de marcado por capacidad de CSM | corte fijo reportado aparte | worky_engine/health/metrics.py::fixed_cut_metrics y outputs/health/validation.md, tabla de metricas, fila corte fijo score menor a 40, verificada en esta sesion junto a las tres tasas | COMPLIANT |
| metricas de validacion contra churn_date | tabla de metricas a las tres tasas | tests/test_health_dataset_numbers.py::test_metricas_al_10_15_y_20_por_ciento (marca dataset) y outputs/health/validation.md, seccion Metricas de validacion | COMPLIANT |
| metricas de validacion contra churn_date | deteccion temprana definida sobre las marcadas en k = 2 | tests/test_health_dataset_numbers.py::test_deteccion_temprana_en_k3 (marca dataset: 56 elegibles, 0.929 de proporcion) | COMPLIANT |
| metricas de validacion contra churn_date | tabla de sensibilidad en k = 3 | outputs/health/validation.md, seccion Sensibilidades, fila k = 3, verificada en esta sesion (AUC 0.955, recall 0.607); tests/test_health_report.py verifica la presencia de la seccion, no el numero exacto de esa fila | COMPLIANT |
| aceptacion del harness sobre los pesos del ADR-005 | los pesos por juicio pasan el harness | tests/test_health_dataset_numbers.py::test_regla_de_aceptacion_se_alcanza_sobre_las_bajas_detectables (AUC 0.997, recall_detectable_20 1.000, passed True) y test_validation_md_declara_la_regla_cumplida_en_el_dataset_real (marca dataset, verifica el texto exacto "Regla cumplida." sin "mezcla medida" en la seccion). outputs/health/validation.md, seccion "Regla de aceptacion del ADR-005", verificada en esta sesion: cita los umbrales 0.95 y 0.85 de forma explicita, el AUC medido (0.997), el recall detectable (1.000), el recall general (0.753) con 22 no detectables, y el veredicto "Regla cumplida." | COMPLIANT, resuelve WARNING 2 del reporte anterior |
| aceptacion del harness sobre los pesos del ADR-005 | los pesos no pasan y se recomienda la mezcla medida | tests/test_health_report.py::test_seccion_de_aceptacion_recomienda_la_mezcla_medida_cuando_falla (llama directo a _acceptance_section con un score sintetico que no separa, confirma "Regla no cumplida.", la mezcla medida completa con sus seis cifras, la mencion a WEIGHTS y la frase "no cambia los pesos por su cuenta") y test_seccion_de_aceptacion_presente_con_umbrales_y_veredicto (verifica la exclusividad: cumplida sin mezcla medida, o no cumplida con mezcla medida, nunca las dos cosas). worky_engine/health/report.py::_acceptance_section, cableada en format_validation entre _metrics_section y _confusion_section. Antes ausente (CRITICAL 1 del reporte anterior), ahora implementada y probada | COMPLIANT, resuelve CRITICAL 1 del reporte anterior |
| respuesta narrativa de A3.4 en validation.md | narrativa de A3.4 presente | tests/test_health_report.py::test_seccion_a3_4_presente_con_costo_asimetrico y outputs/health/validation.md, seccion Respuesta a A3.4, verificada en esta sesion | COMPLIANT |
| contexto comercial fuera del score | canal y segmento en el CSV sin pesar en el score | tests/test_health_report.py::test_contexto_comercial_reporta_canal_y_segmento_fuera_del_score y worky_engine/health/scoring.py::_weighted_sum (no referencia acquisition_channel ni segment); inspeccion de health_scores.csv en esta sesion (columnas presentes) | COMPLIANT |
| pruebas por regla y sobre el dataset real | prueba de fixture por regla | tests/test_health_rules.py, diez pruebas sobre el fixture minimo propio (una por regla: exclusion por corte, denominadores degenerados, antiguedad recortada, empates, banda sin historia, suma ponderada, marcas anidadas, bandas contra umbrales) | COMPLIANT |
| pruebas por regla y sobre el dataset real | prueba marcada dataset con los numeros reales | tests/test_health_dataset_numbers.py, siete pruebas con marca dataset que fijan 650 filas, 89 bajas, 22 no detectables (4 con cero meses de uso), 78 marcadas al 15 % sobre el libro activo de 518, y la regla de aceptacion sobre las detectables, incluido el veredicto cumplido explicito | COMPLIANT |

**Compliance summary**: 25/25 escenarios compliant. El unico escenario que el reporte anterior marcaba FAILING (CRITICAL 1) ahora tiene implementacion y prueba; el escenario con evidencia parcial (WARNING 2) ahora cita los umbrales y el veredicto de forma explicita en validation.md.

### Correctness (Static Evidence)

| Elemento | Estado | Notas |
|---|---|---|
| HEALTH_FILES con h1_company_asof.sql primero y h6_asof_inputs.sql al final | Implementado | worky_engine/health/runner.py; h6 une h1 a h5 |
| SENSITIVITY_RUNS con las tres corridas (primaria 2/2, k3 3/3, literal 2/0) | Implementado | worky_engine/health/runner.py |
| health_params de una sola fila creada antes de cada corrida de HEALTH_FILES | Implementado | worky_engine/health/runner.py (_run_once), consumida por CROSS JOIN health_params p en h1_company_asof.sql |
| Los doce contratos de health_contracts.py | Implementados y corridos | worky_engine/quality/health_contracts.py, run_health_contracts en orden fijo, sin cambio en esta sesion |
| report.py no abre conexion ni lee archivos | Implementado | worky_engine/health/report.py, sin import duckdb ni open(); recibe HealthResult ya materializado; _acceptance_section nueva sigue el mismo patron, solo calcula sobre el DataFrame de scores |
| mart_support_asof fuera de mart_support.sql | Implementado | worky_engine/sql/health/h4_support_asof.sql; worky_engine/sql/marts/mart_support.sql sin cambio de este cambio |
| Alias publico auc = _auc en el harness | Implementado | worky_engine/harness/backtest.py, reexportado en worky_engine/harness/__init__.py |
| cmd_health corre los contratos de A0 antes que los de A3 | Implementado | worky_engine/cli.py |
| _acceptance_section cableada entre metricas y matriz de confusion, con guardia sin bajas | Implementado, resuelve CRITICAL 1 anterior | worky_engine/health/report.py, funcion _acceptance_section (lineas 369-403), invocada en format_validation entre _metrics_section y _confusion_section; devuelve texto de "sin evaluar" cuando no hay bajas (mismo patron de guardia que _undetectable_section ya tenia, correccion R3-acceptance-section-no-empty-churn-guard) |
| Referencias a los ADR en validation.md con ruta de carpeta correcta | Implementado con error corregido | worky_engine/health/report.py::_references_section: ahora cita docs/decisions/ADR-003-usage-trend-and-leakage-guard.md, docs/decisions/ADR-004-sql-analysis-definitions.md y docs/decisions/ADR-005-health-score-model.md; los tres archivos existen en esa ruta exacta (verificado con ls docs/decisions/ en esta sesion). Resuelve WARNING 3 del reporte anterior |
| Apendice de SQL como decimotercera seccion de validation.md | Implementado, desviacion documentada, sin cambio | worky_engine/health/report.py::_sql_appendix_section; el diseno seccion 7 lista doce secciones fijas mas la seccion de aceptacion nueva y el apendice, dos huecos del diseno ya documentados en apply-progress.md |

### Coherence (Design)

| Decision | Seguida? | Notas |
|---|---|---|
| D1 a D17, D19 a D21 | Si | Sin cambio de codigo en esta sesion respecto al reporte anterior; misma evidencia que ya verifico esa corrida |
| D18, regla de aceptacion restablecida en la Adenda 1 sobre las bajas detectables | Si, en el calculo y en la superficie de validation.md | worky_engine/health/metrics.py::acceptance_check calcula sobre recall_detectable (sin cambio); worky_engine/health/report.py::_acceptance_section ahora expone el veredicto y, cuando falla, la mezcla medida como alternativa, resolviendo la brecha que el reporte anterior marcaba como CRITICAL 1 |

### Desviaciones conocidas y aceptadas

- Las desviaciones documentadas en el reporte anterior (activation_raw como promedio de cuatro columnas, HealthResult con dataset_asof y ruleset_version, apendice de SQL como decimotercera seccion, la mezcla de pesos medida descartada, assert_health_bands_match_thresholds como contrato agregado en correccion de revision) siguen vigentes sin cambio: ningun archivo que las produce se toco en los commits fc19791 y 82353a2.
- La seccion de aceptacion es ahora una seccion adicional de validation.md, sumada a las doce fijas de la seccion 7 del diseno y al apendice de SQL. No es una desviacion de una regla del ADR-005: la seccion 6 del diseno ya exigia publicar la regla de aceptacion "verificada en validation.md y fijada por prueba dataset", y esta correccion cierra exactamente esa exigencia que antes solo vivia en el calculo.

### Issues Found

**CRITICAL**: Ninguno.

**WARNING**:

1. La ruta de error de health para "falta una dependencia o una base de datos" (requisito comando health sin build previo) no tiene una prueba que invoque el subcomando health con --data-dir inexistente o con DuckDB no instalado. cmd_health reusa exactamente las mismas funciones (_resolve_data_dir, _exit_missing_dependency) que cmd_build y cmd_analyze, y esa ruta si tiene pruebas dedicadas en tests/test_build_contracts.py, pero ninguna prueba ejercita el codigo de salida 2 a traves del subcomando health. Sin cambio desde el reporte anterior: mismo patron ya documentado como WARNING en el verify-report de a1-sql-queries. Riesgo bajo, mismo codigo y mismo mensaje.

**SUGGESTION**:

1. apply-progress.md (PR 1) describe "los ocho contratos de forma y banda calculables en memoria" y no menciona el noveno contrato (assert_health_bands_match_thresholds) que la correccion de revision R3-risk-band-thresholds-unproved agrego al mismo PR; el docstring de health_contracts.py si dice "doce" en su version actual, pero la nota de progreso del PR 1 quedo desactualizada. Sin cambio desde el reporte anterior.
2. Ninguna prueba automatizada verifica el texto exacto de la fila "Lectura literal" ni de la fila "k = 3" en la seccion de sensibilidades de validation.md; tests/test_health_report.py solo confirma que la seccion existe y que dice "en este dataset". Sin cambio desde el reporte anterior.
3. La tabla "Metricas medidas" de apply-progress.md (PR 2) no incluye el "Recall detectable" que si aparece en la tabla real de validation.md y en metrics.rate_metrics; no es un error, solo una nota de progreso escrita antes de que esa columna se agregara a la funcion. Sin cambio desde el reporte anterior.

### Verdict

**PASS WITH WARNINGS**

Las 28 tareas de tasks.md (12 del PR 1, 8 del PR 2, 8 del PR 3) estan completas, y las 213 pruebas de python -m pytest -q pasan (exit 0). El comando health corrio dos veces seguidas sobre outputs/health/ sin diferencia byte a byte (git status --short outputs vacio en las dos corridas), y build, analyze y backtest, corridos despues, no tocaron ninguno de los ocho goldens de A0, los ocho de A1 ni backtest_report.md (git status --short outputs y git status --short del repositorio completo vacios en las cinco corridas de esta sesion). Ningun archivo generado ni la prosa de README.md o validation.md contiene el caracter em dash.

De los 25 escenarios del spec, los 25 tienen ahora evidencia de cumplimiento con prueba automatizada o inspeccion directa del archivo generado en esta sesion. El escenario que el reporte anterior marcaba FAILING ("los pesos no pasan y se recomienda la mezcla medida") tiene implementacion en worky_engine/health/report.py::_acceptance_section, cableada en format_validation entre las metricas y la matriz de confusion, y dos pruebas dedicadas que cubren la rama de exito y la rama de falla, ademas de la guardia sin bajas. Los dos WARNING del reporte anterior sobre esta misma area (falta de confirmacion explicita de los umbrales, rutas de referencia incorrectas) tambien quedaron resueltos: validation.md ahora cita los umbrales 0.95 y 0.85 de forma literal junto con el veredicto, y las tres referencias a los ADR apuntan a la carpeta real del repositorio.

Queda abierto un WARNING de bajo riesgo, sin cambio desde la corrida anterior (falta de prueba dedicada para el codigo de salida 2 de health cuando falta una dependencia o una base de datos), que no bloquea el archivado porque el codigo que ejecuta esa ruta ya tiene cobertura indirecta a traves de las pruebas de build y analyze que comparten la misma funcion. El cambio queda listo para sdd-archive.
