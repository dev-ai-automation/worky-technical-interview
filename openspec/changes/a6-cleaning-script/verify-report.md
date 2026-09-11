```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:96791bd28e754ec3d9cb75422bfb71cd30e899b2ef513289e75f19d6adebcb02
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 11/11
scenarios: 33/33
test_command: python -m pytest -q
test_exit_code: 0
test_output_hash: sha256:7c74d5331eaadeadb7701777e60ad5e89305090334f24460fb3300111a4438de
build_command: python -m worky_engine clean --data-dir fundation-docs --out-dir outputs/clean
build_exit_code: 0
build_output_hash: sha256:208e84b48c0bc655cfa682c780869a9fa17b67dc34ca19b0d769fcadd6166a24
```

## Reporte de verificación

**Cambio**: a6-cleaning-script
**Capacidad**: data-cleaning (comando `clean` y wrapper `scripts/clean_companies.py`: detección y corrección de fechas DD/MM/YYYY, montos en USD y mrr nulo, imputación del ADR-002 desde `deals.csv` con anualización 12x, log auditable de correcciones)
**Modo**: estándar (Strict TDD no está activo; `strict_tdd: false` en `openspec/config.yaml`)
**Commit verificado**: a2b6bc53405a91ed441ba1fea96abcee6de59ed0 (rama `feat/a6-pr2-clean-impute`). `evidence_revision` es el sha256 de esta cadena de hash completa. El árbol de trabajo actual está en 77a82db, que solo actualiza `state.yaml` sobre a2b6bc5 sin tocar código ni specs; el código verificado en esta sesión es exactamente el de a2b6bc5.
**Alcance de esta verificación**: repetición de `sdd-verify` sobre el cambio completo, después de que un verificador independiente en contexto fresco (sobre f76b863) reportó dos advertencias sin efecto en el dataset del caso, cerradas en los commits 1572021 (código y pruebas) y a2b6bc5 (spec, diseño y apply-progress). La primera corrida de `sdd-verify` (sobre 9ca349c) ya había dado `pass_with_warnings` con 11/11 requisitos y 31/31 escenarios; esta repetición cubre los dos escenarios nuevos y el escenario modificado que agregó ese cierre.

### Completeness

| Métrica | Valor |
|---|---|
| Tareas totales (tasks.md) | 21 |
| Tareas completas | 21 |
| Tareas incompletas | 0 |
| Requisitos totales | 11 |
| Requisitos cumplidos | 11 |
| Escenarios totales | 33 |
| Escenarios cumplidos | 33 |

Conteo verificado con lectura directa de `openspec/changes/a6-cleaning-script/specs/data-cleaning/spec.md`: 11 encabezados `### Requirement:` y 33 encabezados `#### Scenario:` bajo `ADDED Requirements` (dos escenarios nuevos y uno modificado desde la primera verificación: "mrr con nan o infinito cuenta como no numérico", "deal_id duplicado con montos distintos no se colapsa", y "deal con monto vacío o no numérico no detiene la corrida" ampliado para cubrir nan/inf). `tasks.md` trae 21 casillas marcadas y cero sin marcar.

### Ejecución de pruebas

**Tests**: 304 passed / 0 failed / 0 skipped

```text
python -m pytest -q
........................................................................ [ 23%]
........................................................................ [ 47%]
........................................................................ [ 71%]
........................................................................ [ 94%]
................                                                         [100%]
304 passed in 808.02s (0:13:28)
```

304 pruebas, 9 más que las 295 de la primera verificación (sobre 9ca349c), diferencia explicada exactamente por las pruebas nuevas del commit 1572021: 4 parametrizadas de monto de deal no finito (`nan`, `inf`, `-inf`, `NaN`) en `tests/test_cleaning_imputation.py`, 2 de `deal_id` duplicado (montos distintos y montos iguales) en el mismo archivo, y 3 parametrizadas de `mrr` no finito (`nan`, `inf`, `-inf`) en `tests/test_cleaning_rules.py`. 295 + 9 = 304. Cero fallas, cero errores, cero pruebas saltadas.

**Determinismo e idempotencia sobre el dataset real (fundation-docs)**: Passed. Se calculó el sha256 de los cuatro goldens de `outputs/clean/` antes de correr nada, se corrió `python -m worky_engine clean --data-dir fundation-docs --out-dir outputs/clean` dos veces en esta sesión, y el sha256 de los cuatro archivos salió idéntico en ambas corridas y contra la versión ya comiteada:

```text
clean: 84 correcciones en 678 filas, salidas en outputs\clean
```

`git status --short outputs` salió vacío después de cada corrida (los cuatro goldens no cambiaron ni un byte).

| Archivo | sha256 |
|---|---|
| `outputs/clean/companies_clean.csv` | `c8e9eddccb86968b19d2b983d165debaa93f5c2a58034ac6b02467767bc5fc43` |
| `outputs/clean/cleaning_exceptions.csv` | `a640b0acb2beec7286f8e16e3bc24dc8375642d81d28438b3b1607c7d6997d48` |
| `outputs/clean/cleaning_log.json` | `397f5ba128509c1c34b52f5ec5ce90aaf9c99c50c2925e73f13ad5fdf0418528` |
| `outputs/clean/cleaning_log.md` | `1bce61dcb178f1f002842cb553b201f2647247c21d371658f01bb6aee4615341` |

**Probes manuales de esta sesión** (CSV mínimos en un directorio temporal fuera del repositorio, borrados al terminar):

| Caso | Entrada | Resultado observado |
|---|---|---|
| Deal con monto nan | Una empresa (HS-200001) con mrr nulo y un único deal con amount igual a nan | Exit 0; excepción deal_amount_not_numeric nombrando el deal_id; la empresa queda unresolved (sin deals numéricos) porque no le queda ningún deal válido |
| deal_id duplicado con montos distintos | Una empresa (HS-200003) con mrr nulo y dos filas de deal con el mismo deal_id y montos 1000 y 2000 | Exit 0; la empresa queda unresolved con evidence_ref igual a "montos ambiguos", sin ninguna fila mrr_imputed_from_deal |

Ambos casos corrieron en la misma llamada al comando (`clean: 0 correcciones en 2 filas`, exit 0), confirmando que ninguno de los dos detiene la corrida.

**Conteos del log sobre el dataset real** (`outputs/clean/cleaning_log.json`, verificado por lectura directa): rows_in 678, deals_in 997, deals_matched 962; missing_mrr detected 56 / corrected 28 / excluded_clones 28 / annualized_deals 3 / unresolved 0; currency_to_mxn detected 22 / corrected 22; date_format detected 31 / corrected 31 / ambiguous 12; totals.corrections 84, exception_rows 112. Sin cambio frente a la primera verificación, porque el dataset real no contiene montos de deal no finitos ni deal_id duplicados con montos distintos.

**Aislamiento respecto a A0-A5 y al resto del código**: Passed. `git diff 9ca349c..a2b6bc5 --stat` muestra cambios únicamente en `worky_engine/cleaning/rules.py`, `worky_engine/cleaning/impute.py`, `worky_engine/quality/cleaning_contracts.py`, `tests/test_cleaning_rules.py`, `tests/test_cleaning_imputation.py` y los cinco artefactos de `openspec/changes/a6-cleaning-script/` (`apply-progress.md`, `design.md`, `specs/data-cleaning/spec.md`, `state.yaml`, `verify-report.md`); ningún archivo de `worky_engine/normalization/`, `worky_engine/sql/`, `worky_engine/quality/contracts.py`, `worky_engine/cli.py`, `README.md` ni de los goldens previos aparece en ese diff.

**Coverage**: no hay umbral de cobertura de línea configurado (`coverage_threshold: 0`); no aplica.

### Spec Compliance Matrix — data-cleaning (11 requisitos, 33 escenarios)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| comando clean y wrapper equivalentes | corrida exitosa desde ambas rutas | test_cleaning_rules.py::test_corrida_exitosa_desde_ambas_rutas | COMPLIANT |
| comando clean y wrapper equivalentes | falta companies.csv | test_cleaning_rules.py::test_falta_companies_csv_termina_con_codigo_2 | COMPLIANT |
| comando clean y wrapper equivalentes | falta una dependencia | test_cleaning_rules.py::test_falta_una_dependencia_termina_con_codigo_2 | COMPLIANT |
| entradas requeridas companies.csv y deals.csv | ambos archivos presentes | test_cleaning_rules.py::test_ambos_archivos_presentes_corre_las_tres_detecciones | COMPLIANT |
| entradas requeridas companies.csv y deals.csv | falta deals.csv | test_cleaning_rules.py::test_falta_deals_csv_termina_con_codigo_2_sin_salida_parcial | COMPLIANT |
| entradas requeridas companies.csv y deals.csv | archivo vacío o con bytes fuera de UTF-8 | test_cleaning_rules.py::test_companies_csv_vacio_termina_con_codigo_2_sin_salida, test_companies_csv_no_utf8_termina_con_codigo_2_sin_salida | COMPLIANT |
| detección de mrr nulo con exclusión de clones | conteo exacto sobre el dataset | test_cleaning_dataset_numbers.py::test_conteo_exacto_sobre_el_dataset (marca dataset); cleaning_log.json (56/28/28) | COMPLIANT |
| detección de mrr nulo con exclusión de clones | un clon no se imputa | test_cleaning_rules.py::test_un_clon_no_se_imputa, test_cleaning_imputation.py::test_clon_no_se_toca_por_impute | COMPLIANT |
| detección de moneda USD | conteo exacto de USD | test_cleaning_dataset_numbers.py::test_conteo_exacto_de_usd (marca dataset); cleaning_log.json (22/22) | COMPLIANT |
| detección y normalización de signup_date | conteo y normalización de signup_date | test_cleaning_dataset_numbers.py::test_conteo_y_normalizacion_de_signup_date (marca dataset); cleaning_log.json (31/31, 12 ambiguas) | COMPLIANT |
| detección y normalización de signup_date | fecha calendario imposible | test_cleaning_rules.py::test_fecha_calendario_imposible_conserva_el_original | COMPLIANT |
| detección y normalización de signup_date | churn_date sin mezcla de formatos | test_cleaning_dataset_numbers.py::test_churn_date_sin_mezcla_de_formatos (marca dataset) | COMPLIANT |
| conversión de moneda USD a MXN | monto en USD | test_cleaning_rules.py::test_monto_en_usd_se_convierte_a_mxn | COMPLIANT |
| conversión de moneda USD a MXN | monto ya en MXN | test_cleaning_rules.py::test_monto_ya_en_mxn_no_cambia_de_valor | COMPLIANT |
| conversión de moneda USD a MXN | moneda fuera de USD y MXN no detiene la corrida | test_cleaning_rules.py::test_moneda_no_soportada_no_aborta_la_corrida_end_to_end, test_moneda_no_soportada_via_cmd_clean | COMPLIANT |
| conversión de moneda USD a MXN | mrr no numérico se reporta aparte | test_cleaning_rules.py::test_mrr_no_numerico_no_se_confunde_con_moneda_no_soportada | COMPLIANT |
| conversión de moneda USD a MXN | mrr no numérico se vuelve a reportar en cada corrida | test_cleaning_rules.py::test_mrr_no_numerico_se_reemite_en_cada_corrida | COMPLIANT |
| conversión de moneda USD a MXN | mrr con nan o infinito cuenta como no numérico (nuevo) | test_cleaning_rules.py::test_mrr_no_finito_se_reporta_como_no_numerico, 3 casos parametrizados (nan, inf, -inf); usa rules.parse_finite_amount (math.isfinite) | COMPLIANT |
| imputación de mrr desde deals con anualización | imputación con confianza alta | test_cleaning_imputation.py::test_imputacion_confianza_alta; verificación contra master_dataset.csv (4 high) | COMPLIANT |
| imputación de mrr desde deals con anualización | imputación con confianza media | test_cleaning_imputation.py::test_imputacion_confianza_media; verificación contra master_dataset.csv (24 medium) | COMPLIANT |
| imputación de mrr desde deals con anualización | empresa sin resolución | test_cleaning_imputation.py::test_empresa_sin_resolucion_por_montos_ambiguos, test_empresa_sin_resolucion_sin_deals | COMPLIANT |
| imputación de mrr desde deals con anualización | anualización contada como corrección propia | test_cleaning_imputation.py::test_anualizacion_contada_como_correccion_propia; cleaning_log.json (annualized_deals: 3) | COMPLIANT |
| imputación de mrr desde deals con anualización | deal con monto vacío o no numérico no detiene la corrida (modificado: ahora incluye nan/inf) | test_cleaning_imputation.py::test_deal_con_monto_vacio_se_reporta_y_no_aborta_la_imputacion, test_unico_deal_con_monto_no_numerico_queda_sin_resolver, test_deal_con_monto_no_finito_se_reporta_como_no_numerico (4 casos parametrizados: nan, inf, -inf, NaN); probe manual de esta sesión (deal nan único, empresa unresolved) | COMPLIANT |
| imputación de mrr desde deals con anualización | deal_id duplicado con montos distintos no se colapsa (nuevo) | test_cleaning_imputation.py::test_deal_id_duplicado_con_montos_distintos_queda_sin_resolver, test_deal_id_duplicado_con_el_mismo_monto_se_imputa; probe manual de esta sesión (deal_id repetido, montos 1000/2000, empresa unresolved por montos ambiguos) | COMPLIANT |
| contrato del log de limpieza | conteos exactos en json y en md | test_cleaning_dataset_numbers.py::test_conteos_exactos_en_json_y_en_md (marca dataset); lectura directa de cleaning_log.json y cleaning_log.md | COMPLIANT |
| contrato del log de limpieza | fila de excepción por corrección | test_cleaning_imputation.py::test_imputacion_confianza_alta, test_imputacion_confianza_media | COMPLIANT |
| contrato del log de limpieza | orden determinista | test_cleaning_idempotency.py::test_orden_determinista | COMPLIANT |
| salida companies_clean.csv | mismas filas y mismo orden | test_cleaning_rules.py::test_mismas_filas_y_mismo_orden | COMPLIANT |
| salida companies_clean.csv | columnas originales más las nuevas | test_cleaning_rules.py::test_columnas_originales_mas_las_nuevas | COMPLIANT |
| idempotencia de la corrida | cero correcciones sobre la salida propia | test_cleaning_idempotency.py::test_cero_correcciones_sobre_la_salida_propia | COMPLIANT |
| idempotencia de la corrida | salidas idénticas entre corridas | test_cleaning_idempotency.py::test_salidas_identicas_entre_corridas_fixture, test_cmd_clean_dos_veces_seguidas_produce_el_mismo_companies_clean, test_salidas_identicas_entre_corridas_dataset (marca dataset); sha256 idéntico en dos corridas reales de esta sesión | COMPLIANT |
| coincidencia con el motor y goldens sin tocar otras salidas | coincidencia con mart_mrr | test_cleaning_equivalence.py::test_coincidencia_con_mart_mrr (marca dataset) | COMPLIANT |
| coincidencia con el motor y goldens sin tocar otras salidas | ningún golden previo cambia | test_cleaning_idempotency.py::test_ningun_golden_previo_cambia (marca dataset); sha256 de los cuatro goldens de outputs/clean/ idéntico antes y después de dos corridas de esta sesión, git diff --stat 9ca349c..a2b6bc5 sin salida sobre las rutas de solo lectura | COMPLIANT |

**Compliance summary**: 33/33 escenarios COMPLIANT con prueba automatizada, prueba de dataset o probe manual de esta sesión. 0 escenarios FAILING o UNTESTED.

### Correctness (Static Evidence)

| Elemento | Estado | Notas |
|---|---|---|
| worky_engine/cleaning/rules.py (parse_finite_amount, normalize_dates, convert_currency, detect_missing_mrr) | Implementado | parse_finite_amount usa math.isfinite para rechazar nan/inf/-inf en convert_currency; confirmado con 3 pruebas parametrizadas y probe manual |
| worky_engine/cleaning/impute.py (impute_mrr_from_deals) | Implementado | Comparte parse_finite_amount con rules.py; los montos se acumulan por fila de deal (amounts_mxn, lista de tuplas) y no por deal_id, así que un deal_id repetido con montos distintos deja a la empresa unresolved |
| worky_engine/quality/cleaning_contracts.py (_CODE_TO_COUNT_PATH) | Implementado | deal_amount_not_numeric mapea a (missing_mrr, deal_amount_not_numeric), confirmado por lectura directa |
| outputs/clean/ (cuatro goldens) | Sin cambio | sha256 idéntico frente a la primera verificación; el dataset real no ejercita los dos casos nuevos |

### Coherence (Design)

| Decisión | ¿Seguida? | Notas |
|---|---|---|
| D6 (imputación en pandas, parse_finite_amount, montos acumulados por fila de deal) | Sí | design.md ya documenta ambos ajustes dentro de la propia celda D6, sincronizado en a2b6bc5 |
| Resto de decisiones (D1-D5, D7-D12) | Sí, sin cambio | Nada en el diff 9ca349c..a2b6bc5 las afecta; ya confirmadas en la primera verificación |

### Task Completeness

21/21 casillas marcadas en tasks.md (PR1: 11, PR2: 10). Cero casillas sin marcar. Sin cambio frente a la primera verificación.

### Desviaciones conocidas y aceptadas

- Mismas de la primera verificación: PR1 (1,190 líneas de autoría) superó el presupuesto de 800 con size:exception aceptada por el usuario; PR2 (476 líneas) queda dentro del presupuesto. Ninguno de los dos linajes de revisión nativa obtuvo un recibo terminal (rechazo del proveedor del modelo en los cuatro lentes), según state.yaml.
- Los commits posteriores al cierre de PR2 (1572021, a2b6bc5) tampoco pasaron por un recibo de revisión nativa terminal: la corrección se originó en un verificador independiente en contexto fresco, no en el ciclo de revisión nativa de 4 lentes.

### Issues Found

**CRITICAL**: Ninguno.

**WARNING**:

1. Ni PR1 ni PR2, ni la corrección posterior al verify (1572021, a2b6bc5), obtuvieron un recibo de revisión nativa terminal (rechazo del proveedor del modelo). La entrega sigue la política ordinaria del repositorio con esta verificación independiente como evidencia de ejecución. No bloquea el archivado: el contrato de verificación exige evidencia de ejecución real y no un recibo de revisión (el estado de revisión es informativo, nunca un prerrequisito de verificación), y esta sesión corrió la suite completa (304 pruebas en verde) más las pruebas de determinismo, idempotencia y los dos probes manuales sobre los escenarios nuevos.

Las dos advertencias que un verificador independiente había dejado abiertas después de la primera verificación de este cambio (montos nan/inf que esquivaban la tolerancia de no numérico, y deal_id duplicado colapsado por diccionario) quedan cerradas en esta repetición: el código las corrige (parse_finite_amount, acumulación por fila), la especificación las documenta (dos escenarios nuevos, uno modificado), y esta sesión las confirmó con pruebas automatizadas más probes manuales independientes.

**SUGGESTION**: Ninguna nueva. Las dos preguntas abiertas de design.md (redundancia entre mrr y mrr_mxn, y alcance de la normalización 12x) siguen sin bloquear el archivado, como ya señaló la primera verificación.

### Verdict

**PASS WITH WARNINGS**

Las 21 tareas de tasks.md siguen completas, y las 304 pruebas de python -m pytest -q pasan (exit 0, 0 fallas, 0 saltadas; 9 más que la primera verificación, todas explicadas por el commit 1572021). El comando clean corrió dos veces sobre el dataset real en esta sesión sin diferencia byte a byte en los cuatro goldens de outputs/clean/ (git status --short outputs vacío en ambas corridas). Los dos probes manuales de esta sesión, sobre CSV mínimos fuera del repositorio, confirmaron que un monto de deal nan se reporta como deal_amount_not_numeric sin detener la corrida (exit 0), y que dos filas con el mismo deal_id y montos distintos (1000 y 2000) dejan a la empresa unresolved por montos ambiguos en vez de colapsarse a la última. git diff 9ca349c..a2b6bc5 --stat confirma que el cambio quedó acotado a worky_engine/cleaning/, worky_engine/quality/cleaning_contracts.py, tests/test_cleaning_rules.py, tests/test_cleaning_imputation.py y los artefactos de openspec/changes/a6-cleaning-script/.

De los 33 escenarios del spec, los 33 tienen evidencia de cumplimiento con prueba automatizada, prueba de dataset o probe manual de esta sesión. No se encontró ningún CRITICAL. El único WARNING (revisión nativa sin recibo terminal) es informativo por contrato y no afecta la evidencia de ejecución independiente que esta verificación ya produjo. Las dos advertencias del verificador independiente que motivaron esta repetición quedan cerradas con evidencia. El cambio queda listo para sdd-archive.
