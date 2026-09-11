```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:33e4c98541c45352a9503804bdf5827cec4e05e6b89e1780afd7fdca2f5a3534
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 11/11
scenarios: 31/31
test_command: python -m pytest -q
test_exit_code: 0
test_output_hash: sha256:4178a43ca66112da937eaeb0e0e73235ef24ddc699fb11cb584fe322f47b6606
build_command: python -m worky_engine clean --data-dir fundation-docs --out-dir outputs/clean (x2) && python scripts/clean_companies.py --data-dir fundation-docs --out-dir outputs/clean
build_exit_code: 0
build_output_hash: sha256:69b5176c2e3c7f2c2cc9a449c4239da3af258bed13a50bd0fde68498cd539d1a
```

## Verification Report

**Change**: a6-cleaning-script
**Capacidad**: data-cleaning (comando clean y wrapper scripts/clean_companies.py: deteccion y correccion de fechas DD/MM/YYYY, montos en USD y mrr nulo, imputacion del ADR-002 desde deals.csv con anualizacion 12x, log auditable de correcciones)
**Mode**: Standard (Strict TDD no activo, strict_tdd: false en openspec/config.yaml)
**Commit verificado**: 9ca349c9b7a4743abaf55eaed174fdb6a975ee28 (rama feat/a6-pr2-clean-impute, que apila PR1 feat/a6-pr1-clean-rules y PR2 sobre main; arbol de git limpio antes y despues de esta verificacion, salvo deliverables.zip y deliverables/ sin trackear, ajenos a este cambio). evidence_revision es el sha256 de este commit.
**Alcance de esta verificacion**: primera corrida de sdd-verify sobre el cambio completo (21/21 tareas, dos PR apilados). La revision nativa de ambos PR no obtuvo un recibo terminal (rechazo del proveedor del modelo en los cuatro lentes); esta verificacion es el chequeo independiente de ejecucion de facto, junto con un verificador en contexto fresco corriendo en paralelo sobre un worktree separado.

### Completeness

| Metrica | Valor |
|---|---|
| Tareas totales (tasks.md) | 21 |
| Tareas completas | 21 |
| Tareas incompletas | 0 |
| Requisitos totales | 11 |
| Requisitos cumplidos | 11 |
| Escenarios totales | 31 |
| Escenarios cumplidos | 31 |

Conteo verificado con lectura directa de openspec/changes/a6-cleaning-script/specs/data-cleaning/spec.md: 11 encabezados de Requirement y 31 encabezados de Scenario bajo ADDED Requirements. tasks.md trae 21 casillas marcadas (PR1: 1.1 a 1.11, PR2: 2.1 a 2.10) y cero casillas sin marcar.

### Ejecucion de pruebas

**Tests**: 295 passed / 0 failed / 0 skipped

```text
python -m pytest -q
........................................................................ [ 24%]
........................................................................ [ 48%]
........................................................................ [ 73%]
........................................................................ [ 97%]
.......                                                                  [100%]
295 passed in 1034.86s (0:17:14)
```

295 pruebas, 6 mas que las 289 que cita apply-progress.md al cerrar PR2 (tarea 2.10), diferencia explicada por dos commits de correccion posteriores al cierre de esa tarea: 7b23e6a (tres advertencias del verificador independiente de PR1, pruebas nuevas en tests/test_cleaning_rules.py) y 0fa82cb (tolerancia de montos de deal vacios o no numericos, tres pruebas nuevas en tests/test_cleaning_imputation.py y tests/test_cleaning_rules.py); 289 + 3 + 3 = 295, cifra que coincide exactamente con la medicion de esta sesion (ver SUGGESTION 1). Cero fallas, cero errores, cero pruebas saltadas.

**Determinismo e aislamiento sobre el dataset real (fundation-docs)**: Passed. Se calculo el sha256 de los veinte archivos ya versionados de outputs/ (ocho de A0, ocho de A1, dos de A3, dos de A4) y de los cuatro goldens de outputs/clean/ antes de correr nada; se corrio python -m worky_engine clean --data-dir fundation-docs --out-dir outputs/clean dos veces seguidas y despues python scripts/clean_companies.py --data-dir fundation-docs --out-dir outputs/clean una tercera vez:

```text
clean: 84 correcciones en 678 filas, salidas en outputs\clean
(segunda corrida, mismo comando)
clean: 84 correcciones en 678 filas, salidas en outputs\clean
(wrapper, tercera corrida)
clean: 84 correcciones en 678 filas, salidas en outputs\clean
```

El sha256 de los cuatro archivos de outputs/clean/ salio identico byte a byte en las tres corridas y contra la version ya comiteada. El sha256 de los veinte archivos versionados de outputs/analysis, outputs/health, outputs/warehouse y los sueltos en outputs/ salio identico antes y despues de las tres corridas. git status --short outputs salio vacio en cada verificacion.

**Subcomando y wrapper equivalentes**: Passed. Se corrio python -m worky_engine clean --data-dir fundation-docs --out-dir tmp_a y python scripts/clean_companies.py --data-dir fundation-docs --out-dir tmp_b sobre directorios temporales aislados; diff -rq tmp_a tmp_b no reporto diferencias (los cuatro archivos identicos).

**Segunda corrida sobre la propia salida (--companies)**: Passed. python scripts/clean_companies.py --companies tmp_a/companies_clean.csv --deals .build/dataset/sistemas/crm_hubspot__deals.csv --out-dir tmp_c: exit 0, clean: 0 correcciones en 678 filas, cleaning_exceptions.csv con exactamente 28 filas clone_excluded y ningun otro codigo, companies_clean.csv identico byte a byte al de la primera corrida.

**Rutas de error del CLI**: Passed, las seis probadas en esta sesion.

| Caso | Comando | Resultado observado |
|---|---|---|
| Falta companies.csv | clean --companies (no existe) --deals (real) | exit 2, mensaje en espanol nombrando la ruta faltante |
| Falta deals.csv | clean --companies (real) --deals (no existe) | exit 2, mensaje en espanol nombrando la ruta faltante |
| companies.csv de cero bytes | clean --companies (vacio) --deals (real) | exit 2, mensaje nombrando el archivo y "esta vacio, no se puede leer como CSV", sin escribir salida |
| companies.csv con bytes fuera de UTF-8 | clean --companies (bytes 0xFF 0xFE) --deals (real) | exit 2, mensaje nombrando el archivo y "no esta en UTF-8", sin escribir salida |
| Contrato violado (assert_clone_deals_absent) | clean con un deals.csv con una fila para HS-900001 | exit 1, mensaje nombrando el contrato y el clon, directorio de salida vacio |
| Moneda EUR, mrr no numerico, fecha imposible y deal sin monto en una sola corrida | clean sobre companies/deals modificados con las cuatro condiciones | exit 0; currency_unsupported (HS-100001), date_unresolved (HS-100003), mrr_not_numeric (HS-100002), deal_amount_not_numeric x3 y mrr_unresolved (HS-100012, deals vaciados) |

Una segunda corrida sobre el mismo companies/deals modificados repitio exactamente mrr_not_numeric para HS-100002 (reporte, no correccion: totals.corrections se mantuvo en 83 en ambas corridas) y companies_clean.csv salio identico byte a byte entre las dos corridas.

**Conteos del log sobre el dataset real** (outputs/clean/cleaning_log.json, verificado por lectura directa y por conteo independiente de filas en cleaning_exceptions.csv): rows_in 678, deals_in 997, deals_matched 962; missing_mrr detected 56 / corrected 28 / excluded_clones 28 / annualized_deals 3 / unresolved 0; currency_to_mxn detected 22 / corrected 22; date_format detected 31 / corrected 31 / ambiguous 12; totals.corrections 84, exception_rows 112 (28 clone_excluded + 22 currency_converted_to_mxn + 31 date_normalized + 3 mrr_deal_annualized + 28 mrr_imputed_from_deal = 112, contado por columna en el CSV). cleaning_log.md resume los mismos numeros en espanol.

**Coincidencia con mart_mrr**: Passed, verificado tambien de forma independiente fuera de pytest: las 28 filas mrr_imputed_from_deal de cleaning_exceptions.csv coinciden una a una por source_id con las 28 filas de outputs/exceptions_log.csv en applied_value y evidence_ref (0 discrepancias), y el reparto de confianza de esas 28 empresas coincide exacto contra outputs/master_dataset.csv: 4 high, 24 medium, en ambos goldens.

**Aislamiento respecto a A0 a A4**: Passed. git diff --stat main..HEAD sobre worky_engine/normalization/, worky_engine/sql/, worky_engine/quality/contracts.py, outputs/analysis, outputs/health, outputs/warehouse, outputs/backtest_report.md, outputs/coverage_report.md, outputs/exceptions_log.csv, outputs/identity_crosswalk.csv, outputs/master_dataset.csv, outputs/match_audit.csv, outputs/quarantine_companies.csv y outputs/quarantine_deals.csv no produjo ninguna salida.

**Coverage**: no hay umbral de cobertura de linea configurado en openspec/config.yaml (coverage_threshold: 0); no aplica.

### Spec Compliance Matrix - data-cleaning (11 requisitos, 31 escenarios)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| comando clean y wrapper equivalentes | corrida exitosa desde ambas rutas | test_cleaning_rules.py::test_corrida_exitosa_desde_ambas_rutas; verificacion manual (diff -rq identico entre subcomando y wrapper sobre el dataset real) | COMPLIANT |
| comando clean y wrapper equivalentes | falta companies.csv | test_cleaning_rules.py::test_falta_companies_csv_termina_con_codigo_2; probe manual (exit 2, mensaje nombra la ruta) | COMPLIANT |
| comando clean y wrapper equivalentes | falta una dependencia | test_cleaning_rules.py::test_falta_una_dependencia_termina_con_codigo_2 | COMPLIANT |
| entradas requeridas companies.csv y deals.csv | ambos archivos presentes | test_cleaning_rules.py::test_ambos_archivos_presentes_corre_las_tres_detecciones | COMPLIANT |
| entradas requeridas companies.csv y deals.csv | falta deals.csv | test_cleaning_rules.py::test_falta_deals_csv_termina_con_codigo_2_sin_salida_parcial; probe manual (exit 2, sin salida) | COMPLIANT |
| entradas requeridas companies.csv y deals.csv | archivo vacio o con bytes fuera de UTF-8 | test_cleaning_rules.py::test_companies_csv_vacio_termina_con_codigo_2_sin_salida, test_companies_csv_no_utf8_termina_con_codigo_2_sin_salida; probe manual (exit 2 en ambos casos) | COMPLIANT |
| deteccion de mrr nulo con exclusion de clones | conteo exacto sobre el dataset | test_cleaning_dataset_numbers.py::test_conteo_exacto_sobre_el_dataset (marca dataset); cleaning_log.json (56/28/28) | COMPLIANT |
| deteccion de mrr nulo con exclusion de clones | un clon no se imputa | test_cleaning_rules.py::test_un_clon_no_se_imputa, test_cleaning_imputation.py::test_clon_no_se_toca_por_impute; probe manual (28 filas clone_excluded, ningun otro codigo, en la segunda corrida) | COMPLIANT |
| deteccion de moneda USD | conteo exacto de USD | test_cleaning_dataset_numbers.py::test_conteo_exacto_de_usd (marca dataset); cleaning_log.json (22/22) | COMPLIANT |
| deteccion y normalizacion de signup_date | conteo y normalizacion de signup_date | test_cleaning_dataset_numbers.py::test_conteo_y_normalizacion_de_signup_date (marca dataset); cleaning_log.json (31/31, 12 ambiguas) | COMPLIANT |
| deteccion y normalizacion de signup_date | fecha calendario imposible | test_cleaning_rules.py::test_fecha_calendario_imposible_conserva_el_original; probe manual (31/02/2023 en HS-100003, date_unresolved, la corrida no aborta) | COMPLIANT |
| deteccion y normalizacion de signup_date | churn_date sin mezcla de formatos | test_cleaning_dataset_numbers.py::test_churn_date_sin_mezcla_de_formatos (marca dataset) | COMPLIANT |
| conversion de moneda USD a MXN | monto en USD | test_cleaning_rules.py::test_monto_en_usd_se_convierte_a_mxn | COMPLIANT |
| conversion de moneda USD a MXN | monto ya en MXN | test_cleaning_rules.py::test_monto_ya_en_mxn_no_cambia_de_valor | COMPLIANT |
| conversion de moneda USD a MXN | moneda fuera de USD y MXN no detiene la corrida | test_cleaning_rules.py::test_moneda_no_soportada_no_aborta_la_corrida_end_to_end, test_moneda_no_soportada_via_cmd_clean; probe manual (EUR en HS-100001, currency_unsupported, exit 0, cuatro salidas escritas) | COMPLIANT |
| conversion de moneda USD a MXN | mrr no numerico se reporta aparte | test_cleaning_rules.py::test_mrr_no_numerico_no_se_confunde_con_moneda_no_soportada; probe manual (n/a en HS-100002, mrr_not_numeric, mrr_mxn vacio) | COMPLIANT |
| conversion de moneda USD a MXN | mrr no numerico se vuelve a reportar en cada corrida | test_cleaning_rules.py::test_mrr_no_numerico_se_reemite_en_cada_corrida; probe manual (dos corridas seguidas, mrr_not_numeric presente en ambas, totals.corrections sin cambio) | COMPLIANT |
| imputacion de mrr desde deals con anualizacion | imputacion con confianza alta | test_cleaning_imputation.py::test_imputacion_confianza_alta; verificacion independiente contra master_dataset.csv (4 high) | COMPLIANT |
| imputacion de mrr desde deals con anualizacion | imputacion con confianza media | test_cleaning_imputation.py::test_imputacion_confianza_media; verificacion independiente contra master_dataset.csv (24 medium) | COMPLIANT |
| imputacion de mrr desde deals con anualizacion | empresa sin resolucion | test_cleaning_imputation.py::test_empresa_sin_resolucion_por_montos_ambiguos, test_empresa_sin_resolucion_sin_deals | COMPLIANT |
| imputacion de mrr desde deals con anualizacion | anualizacion contada como correccion propia | test_cleaning_imputation.py::test_anualizacion_contada_como_correccion_propia; cleaning_log.json (annualized_deals: 3) | COMPLIANT |
| imputacion de mrr desde deals con anualizacion | deal con monto vacio o no numerico no detiene la corrida | test_cleaning_imputation.py::test_deal_con_monto_vacio_se_reporta_y_no_aborta_la_imputacion, test_unico_deal_con_monto_no_numerico_queda_sin_resolver; probe manual (tres deals de HS-100012 vaciados, tres deal_amount_not_numeric, empresa mrr_unresolved, exit 0) | COMPLIANT |
| contrato del log de limpieza | conteos exactos en json y en md | test_cleaning_dataset_numbers.py::test_conteos_exactos_en_json_y_en_md (marca dataset); lectura directa de cleaning_log.json y cleaning_log.md | COMPLIANT |
| contrato del log de limpieza | fila de excepcion por correccion | test_cleaning_imputation.py::test_imputacion_confianza_alta, test_imputacion_confianza_media (cada caso valida su fila de cleaning_exceptions.csv segun el docstring del diseno) | COMPLIANT |
| contrato del log de limpieza | orden deterministico | test_cleaning_idempotency.py::test_orden_determinista | COMPLIANT |
| salida companies_clean.csv | mismas filas y mismo orden | test_cleaning_rules.py::test_mismas_filas_y_mismo_orden | COMPLIANT |
| salida companies_clean.csv | columnas originales mas las nuevas | test_cleaning_rules.py::test_columnas_originales_mas_las_nuevas | COMPLIANT |
| idempotencia de la corrida | cero correcciones sobre la salida propia | test_cleaning_idempotency.py::test_cero_correcciones_sobre_la_salida_propia; probe manual (segunda corrida por CLI, clean: 0 correcciones en 678 filas) | COMPLIANT |
| idempotencia de la corrida | salidas identicas entre corridas | test_cleaning_idempotency.py::test_salidas_identicas_entre_corridas_fixture, test_cmd_clean_dos_veces_seguidas_produce_el_mismo_companies_clean, test_salidas_identicas_entre_corridas_dataset (marca dataset); sha256 identico en tres corridas reales de esta sesion | COMPLIANT |
| coincidencia con el motor y goldens sin tocar otras salidas | coincidencia con mart_mrr | test_cleaning_equivalence.py::test_coincidencia_con_mart_mrr (marca dataset); verificacion independiente de esta sesion (28/28 filas, 4 high / 24 medium) | COMPLIANT |
| coincidencia con el motor y goldens sin tocar otras salidas | ningun golden previo cambia | test_cleaning_idempotency.py::test_ningun_golden_previo_cambia (marca dataset); sha256 de los veinte archivos identico antes y despues de tres corridas de esta sesion, git diff --stat main..HEAD sin salida sobre las rutas de solo lectura | COMPLIANT |

**Compliance summary**: 31/31 escenarios COMPLIANT con prueba automatizada o probe manual de esta sesion. 0 escenarios FAILING o UNTESTED.

### Correctness (Static Evidence)

| Elemento | Estado | Notas |
|---|---|---|
| worky_engine/cleaning/rules.py (normalize_dates, convert_currency, detect_missing_mrr) | Implementado | Lectura con dtype=str, keep_default_na=False (D3); preserva mrr_source igual a imputed_from_deal de corridas previas (correccion de PR2, no anticipada por tasks.md) |
| worky_engine/cleaning/impute.py (impute_mrr_from_deals) | Implementado | Replica linea por linea de mart_mrr.sql y mart_deal_normalized.sql (D6, D7); descarta deals con amount vacio o no numerico con deal_amount_not_numeric en vez de abortar (correccion de revision, 0fa82cb) |
| worky_engine/cleaning/runner.py (run_clean, escritor de bitacora) | Implementado | Convergencia por regla en cada corrida (D8, sin _passthrough_if_clean, correccion dcb188c); _build_counts cuenta corrected por excepcion de la corrida, no por estado final del marco |
| worky_engine/quality/cleaning_contracts.py (nueve contratos) | Implementado | assert_clone_deals_absent confirmado con probe manual (exit 1, deal apuntando a HS-900001) |
| worky_engine/cli.py (cmd_clean, _resolve_clean_inputs, _locate_clean_data_dir) | Implementado | Codigos 0/1/2 confirmados con seis probes manuales de esta sesion; D2, D12 |
| scripts/clean_companies.py | Implementado | Wrapper delgado, diff -rq identico contra el subcomando (D12) |
| outputs/clean/ (cuatro goldens) | Implementado y versionado | git ls-files confirma los cuatro trackeados; sha256 estable en tres corridas de esta sesion |
| README.md (paso 7, tabla de salidas) | Implementado | Lineas 48 a 51 y 71 a 74 confirmadas por lectura directa |

### Coherence (Design)

| Decision | Seguida? | Notas |
|---|---|---|
| D1 (reparto del modulo) | Si | rules.py, impute.py, runner.py separados como se decidio |
| D2 (CSV directo, sin las tres bases SQLite) | Si | _locate_clean_data_dir nunca exige las bases; confirmado con --data-dir fundation-docs |
| D3 (lectura en texto puro) | Si | pd.read_csv con dtype=str y keep_default_na=False en rules.py |
| D4 (regla de fecha) | Si | signup_date y churn_date por normalize_date; date_unresolved confirmado con probe manual |
| D5 (regla de moneda, to_mxn sin tocar) | Si | currency_unsupported capturado sin abortar, confirmado con probe manual |
| D6 (imputacion en pandas, clones excluidos, deal con monto no numerico tolerado) | Si, con el ajuste de revision ya sincronizado en el diseno | El ajuste post-revision (0fa82cb) ya esta documentado en la propia tabla de D6 |
| D7 (equivalencia contra goldens ya versionados) | Si | Verificado de forma independiente en esta sesion contra exceptions_log.csv y master_dataset.csv |
| D8 (columnas del CSV limpio, idempotencia por convergencia) | Si, con el ajuste de revision ya sincronizado en el diseno | _passthrough_if_clean eliminado (dcb188c); confirmado con dos corridas reales identicas |
| D9 (formato de montos, format_money) | Si | mrr, mrr_mxn, mrr_original con dos decimales fijos en el golden |
| D10 (bitacora sin marca de tiempo ni rutas absolutas) | Si | cleaning_log.json inspeccionado, sin campos de reloj ni rutas |
| D11 (diez columnas de la bitacora por fila) | Si | cleaning_exceptions.csv trae las diez columnas en el orden declarado |
| D12 (superficie del CLI, subcomando mas wrapper) | Si | Confirmado con diff -rq entre ambas rutas |
| Reglas sin cambio (normalization/, sql/, quality/contracts.py, goldens previos) | Si | git diff --stat main..HEAD sin salida sobre esas rutas, verificado en esta sesion |

### Task Completeness

21/21 casillas marcadas en tasks.md (PR1: 11, PR2: 10). Cero casillas sin marcar. apply-progress.md documenta cada tarea con su evidencia de cierre; el estado real del codigo verificado en esta sesion coincide, salvo la cifra de pruebas ya explicada en SUGGESTION 1.

### Proposal Success Criteria

| Criterio | Evidencia |
|---|---|
| python scripts/clean_companies.py corre sin build previo y termina en 0 | Verificado manualmente en esta sesion (tres corridas reales, exit 0, sin .build/ previo para el paquete cleaning) |
| El log reporta 28 imputaciones, 22 conversiones de USD, 31 fechas normalizadas, las 12 ambiguas y los deals anualizados | cleaning_log.json y cleaning_log.md leidos directamente en esta sesion (28/22/31/12/3) |
| Los 28 clones HS-9000xx quedan intactos y reportados como excluidos | test_un_clon_no_se_imputa, test_clon_no_se_toca_por_impute; probe manual (28 filas clone_excluded en la segunda corrida, ningun otro codigo) |
| Correr el comando sobre su propia salida reporta cero correcciones | Probe manual de esta sesion: clean con 0 correcciones en 678 filas |
| Las 28 imputaciones coinciden con mart_mrr sobre el dataset real | Verificacion independiente de esta sesion: 28/28 filas, 0 discrepancias en applied_value y evidence_ref |
| Dos corridas seguidas dan goldens identicos byte a byte y ningun golden previo cambia | sha256 identico en tres corridas de esta sesion para los cuatro goldens de outputs/clean/ y los veinte archivos previos de outputs/ |

Las seis casillas de proposal.md siguen sin marcar en el archivo (se marcan tipicamente en sdd-archive); las seis tienen evidencia de cumplimiento verificada en esta sesion.

### Desviaciones conocidas y aceptadas

- PR1 (1,190 lineas de autoria) supera el presupuesto de 800 lineas por PR de openspec/config.yaml (review_budget_lines: 800). state.yaml (fuente autoritativa del orquestador, review_receipts.pr1) registra size_exception aceptada por el usuario, con el corte PR1/PR2 ya decidido de antemano en tasks.md como mitigacion estructural. PR2 (476 lineas) queda dentro del presupuesto sin necesitar excepcion.
- La revision nativa de ambos PR no llego a un recibo terminal: los cuatro lentes se declararon no alcanzables por rechazo del proveedor del modelo (provider_safeguard_refusal / unachievable_lens_slot), segun state.yaml. Los hallazgos que si alcanzo a producir la revision antes del rechazo (diez en PR1, tres en PR2) se corrigieron en los commits dcb188c, 7b23e6a y 0fa82cb, verificados de punta a punta en esta sesion.

### Issues Found

**CRITICAL**: Ninguno.

**WARNING**:

1. Ni PR1 ni PR2 obtuvieron un recibo de revision nativa terminal (rechazo del proveedor del modelo en los cuatro lentes de ambos linajes, segun state.yaml); la entrega sigue la politica ordinaria del repositorio, con esta verificacion independiente y un verificador en contexto fresco como sustituto. No bloquea el archivado: el contrato de verificacion exige evidencia de ejecucion real y no un recibo de revision (el estado de revision es informativo, nunca un prerequisito de verificacion), y esta sesion ya corrio la suite completa (295 pruebas en verde) mas las pruebas de determinismo, aislamiento y equivalencia de punta a punta sobre el dataset real.

**SUGGESTION**:

1. apply-progress.md (tarea 2.10) cita 289 passed al cerrar PR2; la medicion real de esta sesion da 295, diferencia explicada por dos commits de correccion posteriores al cierre de esa tarea (7b23e6a y 0fa82cb, tres pruebas nuevas cada uno). Sin impacto en el resultado (0 fallas en cualquiera de los dos numeros); vale la pena actualizar la cifra en la proxima revision de ese archivo.
2. Las dos preguntas abiertas de design.md (redundancia entre mrr y mrr_mxn, y alcance de la normalizacion 12x acotado a las 28 candidatas en vez de las 261 anualizaciones del dataset completo) ya se declaran explicitamente como "no bloquea" dentro del propio diseno. No requieren accion para este archivado; conviene resolverlas formalmente si un cambio futuro extiende la normalizacion 12x a mart_deal_normalized.

### Verdict

**PASS WITH WARNINGS**

Las 21 tareas de tasks.md estan completas (PR1 y PR2), y las 295 pruebas de python -m pytest -q pasan (exit 0, 0 fallas, 0 saltadas). El comando clean corrio tres veces seguidas sobre el dataset real (subcomando, subcomando, wrapper) sin diferencia byte a byte en los cuatro goldens de outputs/clean/ ni en los veinte archivos previos de outputs/ (git status --short outputs vacio en cada corrida); una cuarta corrida sobre su propia salida reporto clean con 0 correcciones en 678 filas y exactamente 28 filas clone_excluded. Los seis probes de error del CLI de esta sesion confirmaron los codigos de salida 0, 1 y 2 exigidos por la especificacion, incluida la violacion deliberada del contrato assert_clone_deals_absent (exit 1, sin escritura parcial) y las cuatro condiciones de tolerancia (EUR, mrr no numerico, fecha imposible, deal sin monto) sin abortar la corrida. Las 28 imputaciones coincidieron de forma independiente, fila por fila, con outputs/exceptions_log.csv y outputs/master_dataset.csv (4 high, 24 medium). Ningun archivo de worky_engine/normalization/, worky_engine/sql/, worky_engine/quality/contracts.py ni de los goldens previos de outputs/ cambio contra main.

De los 31 escenarios del spec, los 31 tienen evidencia de cumplimiento con prueba automatizada, prueba de dataset o probe manual de esta sesion. No se encontro ningun CRITICAL. El unico WARNING (revision nativa sin recibo terminal en ambos PR) es informativo por contrato y no afecta la evidencia de ejecucion independiente que esta verificacion ya produjo. El cambio queda listo para sdd-archive.
