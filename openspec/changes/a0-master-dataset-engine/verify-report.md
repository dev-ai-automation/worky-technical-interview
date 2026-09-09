```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:ea3c8caac1ba2819ae681528eb74c8a95f8aeba986fc098f071888344a8f8c98
verdict: pass
blockers: 0
critical_findings: 0
requirements: 41/41
scenarios: 60/60
test_command: python -m pytest -q
test_exit_code: 0
test_output_hash: sha256:823594f055aa4403fca0bf23b5d0feddf445b22d176a1fd68c1f0389d367df79
build_command: python -m worky_engine build --data-dir data/raw/sistemas --out-dir outputs
build_exit_code: 0
build_output_hash: sha256:2d10d767677595dded5e541271c984e29fa6d9ef4933a59ff917635cef82db06
```

## Verification Report

**Change**: a0-master-dataset-engine
**Version**: seis capacidades (build-cli, coverage-report, identity-resolution, master-dataset-assembly, source-normalization, trend-backtest-harness)
**Mode**: Standard (Strict TDD no activo)
**Commit verificado**: f9e7542dc607f38d7de83eb620c52b336b78b2c1 (rama feat/a0-pr4b-support-commercial-harness, arbol limpio). `evidence_revision` es el sha256 de esta cadena de commit.
**Motivo de esta re-verificacion**: el reporte anterior (PASS 39/39 y 55/55) quedo obsoleto tras las correcciones de Judgment Day (f4e8211, 00e31b6), la contencion de vinculos duplicados y su endurecimiento (366ff29, 1e01929), y dos requisitos nuevos con cinco escenarios en `specs/identity-resolution/spec.md`. Esta corrida vuelve a comprobar las seis capacidades completas sobre el estado actual, no solo lo nuevo.

### Completeness

| Metrica | Valor |
|---|---|
| Tareas totales | 65 |
| Tareas completas | 65 |
| Tareas incompletas | 0 |
| Requisitos totales | 41 |
| Requisitos cumplidos | 41 |
| Escenarios totales | 60 |
| Escenarios cumplidos | 60 |

Conteo verificado con grep sobre los seis archivos specs/*/spec.md bajo "## ADDED Requirements": build-cli 4/5, coverage-report 5/5, identity-resolution 12/21, master-dataset-assembly 10/17, source-normalization 6/8, trend-backtest-harness 4/4. Suma: 41 requisitos, 60 escenarios.

### Build y ejecucion de pruebas

**Tests**: 146 passed / 0 failed / 0 skipped

```text
python -m pytest -q
........................................................................ [ 49%]
........................................................................ [ 98%]
..                                                                       [100%]
146 passed in 35.82s
```

Los 146 casos coinciden con el conteo que dejo registrado el ledger de Judgment Day y de la revision RDD (143 tras la contencion, 146 tras la correccion acotada R3-01). No hubo pruebas en rojo ni saltadas.

**Build**: Passed. Corrido dos veces seguidas directamente sobre outputs/ (la carpeta que ya tiene los goldens commiteados), en vez de una carpeta temporal, para comprobar la idempotencia de la forma mas directa posible:

```text
python -m worky_engine build --data-dir data/raw/sistemas --out-dir outputs
build: 650 empresas ensambladas en outputs
codigo de salida: 0
```

```text
git status --short outputs
(sin salida, antes y despues de las dos corridas)
```

git status --short outputs no mostro ninguna linea ni antes ni despues de las dos corridas: las siete salidas de build quedaron exactamente iguales, byte por byte, a la copia que ya estaba comiteada. sha256 de cada archivo tras la segunda corrida:

| Archivo | sha256 | Cambio contra el commit anterior |
|---|---|---|
| identity_crosswalk.csv | 3bd12df0894ad00845b3a705167a531e62705d20107fe32b1ca31ea359234a84 | Sin cambio |
| match_audit.csv | bf5523f3fde007f6539dd456a62e273e978e88f6a36a582867f1f7881f03ad56 | Sin cambio |
| quarantine_companies.csv | c41a6183bbff79b4d8a88e0e71405f2aef34e7249f90824f527e4d3e9f7375b1 | Sin cambio |
| quarantine_deals.csv | f7c23553188a8f77e5536576b666a723ad36bca0f269d80a260e06bbc3f66c20 | Sin cambio |
| master_dataset.csv | 223082f144c229f5c762ca6774ce671b1cbd02b44ef0e67f6112d8f83db96cfc | Sin cambio |
| exceptions_log.csv | ba859cb1ca999de4a38ea3cb7da949aeb6bf5f5ec328e196a46d304de14bc27f | Sin cambio |
| coverage_report.md | be1f1e9a2b9fb54c6a7e9c2dcbd2624a58645274a1938e9ca96fc30881573aa4 | Sin cambio |

Ningun archivo cambio de sha256, ni siquiera exceptions_log.csv ni quarantine_deals.csv, que son los dos que la contencion y el remapeo de deals de clones podrian tocar. Esto confirma lo que ya decia el ledger: los dos defectos que corrigio Judgment Day, y el enlace duplicado que corrigio la contencion, estan dormidos sobre el dataset real del caso (0 deals sobre un clon, 0 vinculos duplicados de una fuente); su cobertura de prueba vive en los fixtures sinteticos de tests/test_deal_remap_clone.py y tests/test_duplicate_link_containment.py.

Ademas se corrio python -m worky_engine backtest --data-dir data/raw/sistemas --out-dir outputs, y git status --short (sobre todo el repositorio, no solo outputs/) tampoco mostro ninguna linea despues: backtest_report.md (sha256 ab03a666b695a43032f037a78ffba7624c7113513163c6626dfb06d6f292dfa8) quedo igual a la copia comiteada.

**Coverage**: no hay umbral de cobertura de linea configurado en openspec/config.yaml (coverage_threshold: 0); no aplica.

### Spec Compliance Matrix

#### source-normalization (6 requisitos, 8 escenarios, todos cumplidos)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| normalizacion de fecha | fecha ya en formato ISO | tests/test_normalization.py -k date | COMPLIANT |
| normalizacion de fecha | fecha en formato DD/MM/YYYY | tests/test_normalization.py -k date | COMPLIANT |
| etiqueta de dominio | mismo negocio con y sin subdominio | tests/test_normalization.py -k domain | COMPLIANT |
| nombre normalizado de empresa | nombre con razon social y acentos | tests/test_normalization.py -k name | COMPLIANT |
| conversion de moneda a MXN | monto en USD | tests/test_normalization.py -k currency | COMPLIANT |
| conversion de moneda a MXN | monto ya en MXN | tests/test_normalization.py -k currency | COMPLIANT |
| idempotencia de la normalizacion | segunda normalizacion | tests/test_normalization.py, idempotencia por registro | COMPLIANT |
| codificacion explicita de archivos | archivo con caracteres acentuados | tests/test_normalization.py y tests/test_writers.py | COMPLIANT |

Sin cambios de codigo desde la verificacion anterior; los 146 casos en verde incluyen estos mismos tests.

#### identity-resolution (12 requisitos, 21 escenarios, todos cumplidos)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| deduplicacion de filas clon en companies | fila clon aislada | tests/test_identity_resolution.py; dataset real: 28 filas en quarantine_companies.csv | COMPLIANT |
| cascada de niveles de confianza | cruce por T0 | tests/test_identity_resolution.py; dataset real: 596 filas T0 en match_audit.csv | COMPLIANT |
| cascada de niveles de confianza | cruce por T1 | tests/test_identity_resolution.py; dataset real: 650 filas T1 | COMPLIANT |
| cascada de niveles de confianza | cruce por T2 con candidato unico | tests/test_identity_resolution.py; dataset real: 54 filas T2 | COMPLIANT |
| cascada de niveles de confianza | bloque de T2 con mas de un candidato | tests/test_identity_resolution.py, bloque de fecha con dos candidatos que cae a M sin margen | COMPLIANT |
| cascada de niveles de confianza | cruce por T2, cuenta con nombre truncado | tests/test_identity_resolution.py; dataset real: ACC-2027 resuelto por T2 con partial_ratio 100.0 | COMPLIANT |
| cascada de niveles de confianza | cruce por T3 | tests/test_identity_resolution.py, fixture dedicado con WRatio mayor o igual a 94 y margen mayor o igual a 10 | COMPLIANT |
| regla de veto | dominio compartido club290.com.mx | tests/test_identity_resolution.py -k club290; dataset real: 9 filas veto_applied en match_audit.csv | COMPLIANT |
| revision manual | registro sin cruce resuelto | tests/test_identity_resolution.py, bloque ambiguo cae a M; dataset real: 0 filas M | COMPLIANT |
| master_id idempotente | id de origen ya en el crosswalk | tests/test_master_id.py y tests/test_identity_idempotency.py | COMPLIANT |
| master_id idempotente | registro dorado nuevo | tests/test_master_id.py, determinismo del hash sha256 | COMPLIANT |
| tabla identity_crosswalk | fila completa de crosswalk | tests/test_identity_resolution.py; dataset real: 650 filas con las seis columnas del contrato | COMPLIANT |
| tabla match_audit | una fila por registro de origen | tests/test_calibration.py, prueba de conteo total; dataset real: 1978 filas | COMPLIANT |
| cuarentena de deals huerfanos | deals huerfanos aislados | tests/test_identity_resolution.py; dataset real: 35 filas en quarantine_deals.csv | COMPLIANT |
| remapeo de deals que apuntan a un clon (nuevo) | deal de un clon llega al sobreviviente | tests/test_deal_remap_clone.py, tres pruebas dedicadas; worky_engine/sql/marts/mart_mrr.sql lineas 96 a 124 y worky_engine/sql/staging/stg_deals.sql linea 9 | COMPLIANT |
| remapeo de deals que apuntan a un clon (nuevo) | deal de una empresa real no deja evidencia de remapeo | tests/test_deal_remap_clone.py, dos pruebas dedicadas; guardia d.master_id = q.survivor_master_id en mart_mrr.sql linea 122 | COMPLIANT |
| contencion de vinculos duplicados de una fuente (nuevo) | dos accounts para la misma empresa | tests/test_duplicate_link_containment.py, tres pruebas dedicadas; worky_engine/identity_resolution/cascade.py lineas 143 a 166, funcion _mark_duplicate_link | COMPLIANT |
| contencion de vinculos duplicados de una fuente (nuevo) | el mismo id descartado aparece dos veces | tests/test_duplicate_link_containment.py; SELECT DISTINCT en mart_mrr.sql linea 150 | COMPLIANT |
| contencion de vinculos duplicados de una fuente (nuevo) | el mismo account repetido no es un duplicado | tests/test_duplicate_link_containment.py | COMPLIANT |
| supervivencia de atributos | conflicto de moneda entre clon y original | tests/test_build_contracts.py, fixture con clone_attribute_conflict | COMPLIANT |
| calibracion reproducible | prueba de calibracion | tests/test_calibration.py; WRatio acierta 590 de 596, 99.0% | COMPLIANT |

Evidencia adicional sobre el dataset real para los dos requisitos nuevos: los ocho goldens de outputs/ no cambiaron de sha256 tras correr build dos veces (ver tabla de la seccion anterior), lo que confirma que ni un deal real apunta hoy a un clon en cuarentena ni dos accounts o customers reales resuelven al mismo master_id; ambas reglas quedan probadas solo con fixtures sinteticos, como documenta el ledger de Judgment Day y la adenda 1 del ADR-001.

#### master-dataset-assembly (10 requisitos, 17 escenarios, todos cumplidos)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| una fila por empresa real | conteo final de filas | tests/test_assembly_contracts.py; dataset real: 650 filas, master_id unico | COMPLIANT |
| columnas minimas del dataset maestro | fila con todas las columnas | tests/test_assembly_contracts.py; dataset real: 35 columnas presentes | COMPLIANT |
| imputacion de MRR desde el monto del deal | imputacion con deal closedwon | tests/test_mrr_imputation.py; dataset real: 4 filas high | COMPLIANT |
| imputacion de MRR desde el monto del deal | imputacion sin deal closedwon | tests/test_mrr_imputation.py; dataset real: 24 filas medium | COMPLIANT |
| imputacion de MRR desde el monto del deal | empresa con valor de CRM | tests/test_mrr_imputation.py; dataset real: 622 filas mrr_source = crm | COMPLIANT |
| MRR sin resolver | empresa con dos montos ambiguos | tests/test_assembly_contracts.py, fixture con 2 filas unresolved; dataset real: 0 filas unresolved | COMPLIANT |
| MRR sin resolver | empresa sin deals | tests/test_assembly_contracts.py, assert_mrr_confidence_matches_source en las dos direcciones | COMPLIANT |
| bitacora de excepciones de imputacion | 28 filas de imputacion | dataset real: exceptions_log.csv, 28 filas mrr_imputed_from_deal | COMPLIANT |
| mes de referencia | empresa con baja | tests/test_usage_trend.py; dataset real: 89 empresas con baja | COMPLIANT |
| mes de referencia | empresa activa | tests/test_usage_trend.py; dataset real: mes de referencia 2024-08 | COMPLIANT |
| calculo de trend_usage | tendencia calculada | tests/test_usage_trend.py, forma cerrada del EWMA contra pandas.Series.ewm dentro de 1e-9; dataset real: 585 filas computed | COMPLIANT |
| calculo de trend_usage | historia insuficiente | tests/test_usage_trend.py; dataset real: 61 filas insufficient_history | COMPLIANT |
| calculo de trend_usage | sin uso | tests/test_usage_trend.py; dataset real: 4 filas no_usage | COMPLIANT |
| resguardo contra fuga de datos | fila posterior al mes de corte excluida | tests/test_leakage_guard.py, recalcula el conjunto contribuyente de forma independiente | COMPLIANT |
| canal de adquisicion | empresa con touches | tests/test_support_commercial.py; dataset real: las 650 empresas tienen al menos un touch | COMPLIANT |
| canal de adquisicion | empresa sin touches | tests/test_support_commercial.py, fixture con respaldo de lead_source | COMPLIANT |
| revenue cerrado | suma de deals cerrados | tests/test_support_commercial.py; dataset real: closed_revenue_mxn total 11,046,172.00 MXN | COMPLIANT |

#### coverage-report (5 requisitos, 5 escenarios, todos cumplidos)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| cobertura por sistema | tres porcentajes por sistema | dataset real: coverage_report.md seccion 2, crm_hubspot 95.87%, product_db 100.00%, vitally 100.00% | COMPLIANT |
| cobertura por nivel de confianza | desglose por nivel | dataset real: coverage_report.md seccion 3, T0 45.85% con 596, T1 50.00% con 650, T2 4.15% con 54, T3 0.00%, M 0.00% | COMPLIANT |
| tamano de la cola de revision manual | conteo de la cola manual | mart_coverage_manual_queue cuenta needs_review, no solo tier M (worky_engine/sql/marts/mart_coverage.sql lineas 38 a 46); dataset real: 0 registros | COMPLIANT |
| conteos de cuarentena | conteos de cuarentena en el reporte | dataset real: coverage_report.md seccion 6, 28 empresas clon, 35 deals huerfanos | COMPLIANT |
| recalculo desde match_audit | porcentaje recalculado | tests/test_coverage_report.py, prueba que mueve una fila de T0 a M entre dos corridas en memoria | COMPLIANT |

La cola de revision manual ahora se calcula con WHERE needs_review en vez de WHERE tier = 'M', para que un vinculo duplicado contenido tambien aparezca ahi sin dejar de resolver en T0-T3; sobre el dataset real el conteo sigue en 0 porque no hay vinculos duplicados reales.

#### trend-backtest-harness (4 requisitos, 4 escenarios, todos cumplidos)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| reproduccion de la comparacion de formulas | corrida completa del backtest | tests/test_harness_regression.py; dataset real: backtest_report.md con las seis formulas en k = 0, 2 y 3 | COMPLIANT |
| metricas reportadas por formula | metricas de una formula | dataset real: backtest_report.md reporta Definida, AUC, Precision y Recall por formula y por k | COMPLIANT |
| regresion del momentum ganador en k = 2 | prueba de regresion | tests/test_harness_regression.py; dataset real: momentum EWMA con AUC 1.000 en k = 2, el mas alto | COMPLIANT |
| evidencia de fuga de datos en k = 0 | AUC cercano a 1.0 en k = 0 | dataset real: backtest_report.md en k = 0, cinco de seis formulas con AUC mayor o igual a 0.93 | COMPLIANT |

#### build-cli (4 requisitos, 5 escenarios, todos cumplidos)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| comando unico de construccion | corrida completa | python -m worky_engine build corrido dos veces contra data/raw/sistemas, siete salidas generadas en cada corrida | COMPLIANT |
| idempotencia byte a byte | dos corridas seguidas | git status --short outputs vacio despues de las dos corridas de esta verificacion | COMPLIANT |
| mensajes de error claros | falta una base de datos | tests/test_build_contracts.py, codigo de salida 2 con --data-dir inexistente | COMPLIANT |
| mensajes de error claros | falta una dependencia | tests/test_build_contracts.py, simulacion de ImportError con monkeypatch, codigo de salida 2 | COMPLIANT |
| carpeta de datos configurable | carpeta de datos indicada | --data-dir data/raw/sistemas usado en toda esta verificacion | COMPLIANT |

**Compliance summary**: 60/60 escenarios compliant.

### Correctness (Static Evidence)

| Requisito | Estado | Notas |
|---|---|---|
| IdentityCollisionError en las dos direcciones (JD-01) | Implementado | worky_engine/identity_resolution/keys.py, ambos bucles de deteccion; tests/test_master_id.py verifica el mensaje con los dos ids |
| Remapeo de deal sobre un clon a su sobreviviente (JD-02) | Implementado | worky_engine/sql/staging/stg_deals.sql linea 9 (COALESCE al survivor_master_id) y mart_mrr.sql lineas 96 a 124 (fila deal_remapped_from_clone) |
| Fixture del remapeo con las cuatro tablas de identidad fusionadas (JD-07) | Implementado | tests/test_deal_remap_clone.py, fixture con las cuatro tablas de resolve_identity mas las diez de assemble_master_dataset sin colision de claves |
| Contencion de vinculos duplicados sin abortar el build | Implementado | worky_engine/identity_resolution/cascade.py lineas 143 a 166, funcion _mark_duplicate_link; mart_mrr.sql lineas 126 a 166, fila duplicate_source_link |
| Contrato exceptions_log_unique_exception_id | Implementado | worky_engine/quality/contracts.py lineas 98 a 113; corrige el hallazgo R3-01 con SELECT DISTINCT en la rama de vinculos duplicados |
| Contrato quarantine_companies_unique_hubspot_id | Implementado | worky_engine/quality/contracts.py lineas 237 a 250; protege el remapeo de deals de clones contra un fan-out de filas |
| mrr_confidence dominio high, medium, none | Implementado | worky_engine/sql/marts/mart_mrr.sql expone las tres ramas; 0 filas none en el dataset real |
| ORDER BY en las vistas de cobertura | Implementado | mart_coverage.sql lleva ORDER BY explicito en sus seis vistas |
| orden fisico de columnas de master_dataset | Implementado | outputs/master_dataset.csv reproduce el orden de la seccion 2 del diseno |

### Coherence (Design)

| Decision | Seguida? | Notas |
|---|---|---|
| D1, puntaje de identidad en Python con RapidFuzz | Si | identity_resolution/scoring.py; ningun calculo se movio a SQL |
| D3, carga de las tres SQLite via sqlite3 y DataFrame registrado | Si | sources.py abre en modo solo lectura y assemble.py registra los DataFrames en DuckDB |
| D4, instalacion automatica de extensiones apagada | Si | la conexion de DuckDB desactiva autoinstall y autoload de forma explicita |
| D6, archivo duckdb regenerado, no persistido | Si | .gitignore incluye .build/ y *.duckdb |
| D7, dataset_asof derivado de los datos | Si | dataset_asof en 2024-08-31 en las dos corridas de build de esta verificacion |
| D9, desempate de bloque de fecha baja de nivel, nunca por orden de filas | Si | cascade.py implementa la caida a T3 y a M |
| D12, normalizacion 12x de montos de deal | Si | mart_deal_normalized.sql, verificado contra las tres empresas reales con el patron 12x |
| D13, mrr_confidence en none solo cuando mrr_source es unresolved | Si | assert_mrr_confidence_matches_source verificado en las dos direcciones |
| Corte en cuatro PR encadenados, decision D11 | Si, con excepcion de tamano aceptada | PR 2 y PR 4b superaron el presupuesto de 800 lineas; excepciones ya documentadas y aceptadas |
| Seccion 3.6 del diseno, contencion de vinculos duplicados | Si | cascade.py implementa "el primero gana", needs_review, duplicate_link en evidence_json; mart_mrr.sql escribe duplicate_source_link |
| Seccion 3.8 caso 2 del diseno, remapeo de deal sobre un clon | Si | stg_deals.sql y mart_mrr.sql implementan el remapeo al survivor_master_id y la fila de exceptions_log |
| Seccion 9 de coverage_report.md, canal de adquisicion | Parcial, desviacion documentada y todavia no reflejada en design.md | El diseno (linea 294) sigue describiendo filas por primer touch, filas por respaldo de lead_source y filas en unknown; la implementacion usa la distribucion de valores de canal (tasks.md, tarea 4.5). No viola ningun requisito del spec coverage-report |

### Desviaciones conocidas y aceptadas

- Excepcion de tamano en PR 2 (identity-resolution) y PR 4b (soporte, comercial y harness): 1,324 y 1,012 lineas contra el presupuesto de 800, aceptadas por el usuario y documentadas en tasks.md, tareas 2.15 y 4.14. Sin cambio desde la verificacion anterior.
- Correccion sobre la marcha de Judgment Day (jd-round1-fix, jd-round2-fix): resolvio JD-01, JD-02 y JD-07 del ledger; 134 pruebas en verde tras la ronda 2, goldens intactos. Documentado en judgment-ledger.md.
- Contencion de vinculos duplicados (commit 366ff29) y su endurecimiento (commit 1e01929, correccion R3-01 de la revision RDD): agrego dos requisitos y cinco escenarios a specs/identity-resolution/spec.md, mas los contratos exceptions_log_unique_exception_id y quarantine_companies_unique_hubspot_id. Documentado en judgment-ledger.md y en la adenda 1 del ADR-001.
- Regla de normalizacion 12x de montos de deal, Adenda 1 del ADR-002: sin cambio desde la verificacion anterior.
- requires-python en pyproject.toml: sin cambio desde la verificacion anterior (mayor o igual a 3.12, en vez del rango 3.14 a 3.15 del diseno original).
- Seccion 9 de coverage_report.md, canal de adquisicion: la desviacion senalada en la verificacion anterior sigue presente; design.md linea 294 todavia no se actualizo para reflejar la implementacion real.
- Suspects de Judgment Day sin severidad confirmada por ambos jueces (JD-03, JD-04, JD-05) e info (JD-06): quedan como seguimientos documentados en judgment-ledger.md, sin bloquear este cierre porque ninguno es un requisito de spec incumplido.
- PR 3a sin recibo RDD por un defecto del proveedor de revision (issue 3942 reportado): sin cambio desde la verificacion anterior; no afecta la evidencia de prueba ni de build de este reporte.

### Issues Found

**CRITICAL**: None

**WARNING**:

1. La seccion 9 de coverage_report.md (canal de adquisicion) sigue implementada con un desglose distinto al que describe la linea 294 de design.md. Es la misma desviacion que senalo la verificacion anterior; no rompe ningun requisito del spec coverage-report, pero design.md deberia actualizarse antes o durante el archivado para que el documento no contradiga el codigo.
2. Las excepciones de tamano de PR 2 y PR 4b (1,324 y 1,012 lineas contra el presupuesto de 800) siguen sin reflejarse en un reporte de archivo; sdd-archive deberia registrarlas de forma explicita, igual que senalo la verificacion anterior.

**SUGGESTION**:

1. Los tres hallazgos "sospecha de un solo juez" del ledger de Judgment Day (JD-03: _resolve_customer no saca al candidato vetado del bloque de dominio; JD-04: ZipFile.extractall sin filter="data" en cli.py; JD-05: la forma cerrada del EWMA no verifica que la serie llegue hasta trend_asof_month) siguen dormidos en el dataset real y quedan como seguimientos documentados, no como bloqueo de este cambio.
2. El seguimiento de JD-06 (comparar ruleset_version antes de reutilizar un master_id del crosswalk) sigue pendiente y sigue siendo inofensivo mientras la version se mantenga en la constante 1.0.0.
3. El rango de requires-python en pyproject.toml sigue mas amplio que el que proponia el diseno original; vale la pena que un cambio posterior alinee ambos documentos.

### Verdict

**PASS**

Las 65 tareas de las cuatro unidades de PR encadenadas estan completas. Los 41 requisitos y 60 escenarios de las seis capacidades (build-cli, coverage-report, identity-resolution, master-dataset-assembly, source-normalization y trend-backtest-harness) tienen evidencia de prueba en tiempo de ejecucion, con 146 pruebas en verde y cero fallidas, incluidas las que cubren los dos requisitos nuevos (remapeo de deals que apuntan a un clon, y contencion de vinculos duplicados de una fuente) agregados tras Judgment Day y la revision RDD de contencion. El build es reproducible byte por byte: dos corridas seguidas sobre outputs/ no dejaron ninguna diferencia en git status, y el backtest reproduce su golden sin cambios. Las dos excepciones de tamano de PR, la desviacion de diseno en la seccion 9 del reporte de cobertura, y los tres suspects de Judgment Day sin severidad confirmada quedan como WARNING y SUGGESTION, sin bloquear el cierre del cambio.
