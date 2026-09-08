```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:4cb06ec0510c4d4dc36fdc49aa8dd7e71732e4fe1b294b2ac0679b3ce08adcdc
verdict: pass
blockers: 0
critical_findings: 0
requirements: 39/39
scenarios: 55/55
test_command: python -m pytest -q
test_exit_code: 0
test_output_hash: sha256:8cece6e25ef0a14fbdd4e24322427fb50a163f09da0a3c7ee76ca17df7a0364a
build_command: python -m worky_engine build --data-dir data/raw/sistemas --out-dir .build/verify3
build_exit_code: 0
build_output_hash: sha256:0c3a2103ecc1da71a21613ec49a6d2b195eadec37cca2b7f1b9e9d7f5a458579
```

## Verification Report

**Change**: a0-master-dataset-engine
**Version**: seis capacidades (build-cli, coverage-report, identity-resolution, master-dataset-assembly, source-normalization, trend-backtest-harness)
**Mode**: Standard (Strict TDD no activo)
**Commit verificado**: 7ba33546280c4fc99f2fba2c71b2ba3b2ffa30d7 (evidence_revision es el sha256 de este commit)

### Completeness

| Metrica | Valor |
|---|---|
| Tareas totales | 65 |
| Tareas completas | 65 |
| Tareas incompletas | 0 |
| Requisitos totales | 39 |
| Requisitos cumplidos | 39 |
| Escenarios totales | 55 |
| Escenarios cumplidos | 55 |

### Build y ejecucion de pruebas

**Build**: Passed

```text
python -m worky_engine build --data-dir data/raw/sistemas --out-dir .build/verify3
build: 650 empresas ensambladas en .build\verify3
codigo de salida: 0
```

El build se corrio tres veces (dos en .build/verify1 y .build/verify2, y una tercera en .build/verify3 para capturar la evidencia de este reporte). Las siete salidas de las tres corridas son identicas byte por byte entre si y contra la copia commiteada en outputs/ (sha256 verificado archivo por archivo):

| Archivo | sha256 |
|---|---|
| identity_crosswalk.csv | 3bd12df0894ad00845b3a705167a531e62705d20107fe32b1ca31ea359234a84 |
| match_audit.csv | bf5523f3fde007f6539dd456a62e273e978e88f6a36a582867f1f7881f03ad56 |
| quarantine_companies.csv | c41a6183bbff79b4d8a88e0e71405f2aef34e7249f90824f527e4d3e9f7375b1 |
| quarantine_deals.csv | f7c23553188a8f77e5536576b666a723ad36bca0f269d80a260e06bbc3f66c20 |
| master_dataset.csv | 223082f144c229f5c762ca6774ce671b1cbd02b44ef0e67f6112d8f83db96cfc |
| exceptions_log.csv | ba859cb1ca999de4a38ea3cb7da949aeb6bf5f5ec328e196a46d304de14bc27f |
| coverage_report.md | be1f1e9a2b9fb54c6a7e9c2dcbd2624a58645274a1938e9ca96fc30881573aa4 |

Adicionalmente se corrio python -m worky_engine backtest --data-dir data/raw/sistemas --out-dir .build/verify1 y backtest_report.md quedo identico (sha256 ab03a666b695a43032f037a78ffba7624c7113513163c6626dfb06d6f292dfa8) contra la copia en outputs/. Los directorios temporales .build/verify1, .build/verify2 y .build/verify3 se borraron despues de la comparacion; no quedan artefactos de verificacion en el repositorio.

**Tests**: 128 passed / 0 failed / 0 skipped

```text
python -m pytest -q
........................................................................ [ 56%]
........................................................                 [100%]
128 passed in 31.46s
```

```text
python -m pytest -q -m "not dataset"
........................................................................ [ 68%]
.................................                                        [100%]
105 passed, 23 deselected in 6.81s
```

Los 128 casos totales coinciden exactamente con el conteo registrado en el apply-progress (105 sin la marca dataset mas 23 con esa marca). No hubo pruebas en rojo ni saltadas en ninguna de las dos corridas.

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
| codificacion explicita de archivos | archivo con caracteres acentuados | tests/test_normalization.py y tests/test_writers.py, ida y vuelta con Gaitan, gaitan115.com.mx, Sanchez | COMPLIANT |

Verificacion adicional en el dataset real: el nombre de la empresa HS-100113 se lee en outputs/master_dataset.csv con los bytes UTF-8 correctos para la letra ene con tilde (secuencia hex c3 b1), confirmado por inspeccion directa de bytes del archivo.

#### identity-resolution (10 requisitos, 16 escenarios, todos cumplidos)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| deduplicacion de filas clon en companies | fila clon aislada | tests/test_identity_resolution.py, caso de fila clon aislada; dataset real: 28 filas en quarantine_companies.csv | COMPLIANT |
| cascada de niveles de confianza | cruce por T0 | tests/test_identity_resolution.py; dataset real: 596 filas T0 en match_audit.csv | COMPLIANT |
| cascada de niveles de confianza | cruce por T1 | tests/test_identity_resolution.py; dataset real: 650 filas T1 | COMPLIANT |
| cascada de niveles de confianza | cruce por T2 con candidato unico | tests/test_identity_resolution.py; dataset real: 54 filas T2 | COMPLIANT |
| cascada de niveles de confianza | bloque de T2 con mas de un candidato | tests/test_identity_resolution.py, bloque de fecha con dos candidatos que cae a M sin margen | COMPLIANT |
| cascada de niveles de confianza | cruce por T2, cuenta con nombre truncado | tests/test_identity_resolution.py; dataset real: ACC-2027 resuelto por T2 con partial_ratio 100.0, evidence_json confirmado en match_audit.csv | COMPLIANT |
| cascada de niveles de confianza | cruce por T3 | tests/test_identity_resolution.py, fixture dedicado con WRatio mayor o igual a 94 y margen mayor o igual a 10 | COMPLIANT |
| regla de veto | dominio compartido club290.com.mx | tests/test_identity_resolution.py -k club290; dataset real: 9 filas veto_applied verdadero en match_audit.csv, y las 2 empresas de club290.com.mx conservan master_id distinto | COMPLIANT |
| revision manual | registro sin cruce resuelto | tests/test_identity_resolution.py, bloque ambiguo cae a M; dataset real: 0 filas M, sin cola de revision manual | COMPLIANT |
| master_id idempotente | id de origen ya en el crosswalk | tests/test_master_id.py y tests/test_identity_idempotency.py | COMPLIANT |
| master_id idempotente | registro dorado nuevo | tests/test_master_id.py, determinismo del hash sha256 sobre etiqueta de dominio y nombre normalizado | COMPLIANT |
| tabla identity_crosswalk | fila completa de crosswalk | tests/test_identity_resolution.py; dataset real: 650 filas con las columnas master_id, hubspot_id, account_id, vitally_id, confidence_tier y resolved_at presentes | COMPLIANT |
| tabla match_audit | una fila por registro de origen | tests/test_calibration.py, prueba de conteo total; dataset real: 1978 filas, igual a 650 registros dorados mas 28 en cuarentena mas 596 T0 mas 54 T2 mas 650 T1 | COMPLIANT |
| cuarentena de deals huerfanos | deals huerfanos aislados | tests/test_identity_resolution.py, caso de deal huerfano aislado; dataset real: 35 filas en quarantine_deals.csv, excluidas de closed_revenue_mxn | COMPLIANT |
| supervivencia de atributos | conflicto de moneda entre clon y original | tests/test_build_contracts.py, fixture con clone_attribute_conflict; mart_company_core.sql implementa la tabla de supervivencia de la seccion 3.7 del diseno | COMPLIANT |
| calibracion reproducible | prueba de calibracion | tests/test_calibration.py, tres pruebas; WRatio acierta 590 de 596, es decir 99.0%; desglose 596 T0, 650 T1, 54 T2, 0 T3 confirmado | COMPLIANT |

#### master-dataset-assembly (10 requisitos, 17 escenarios, todos cumplidos)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| una fila por empresa real | conteo final de filas | tests/test_assembly_contracts.py; dataset real: 650 filas, master_id unico confirmado | COMPLIANT |
| columnas minimas del dataset maestro | fila con todas las columnas | tests/test_assembly_contracts.py; dataset real: 35 columnas presentes, con el orden fisico documentado en la seccion 2 del diseno | COMPLIANT |
| imputacion de MRR desde el monto del deal | imputacion con deal closedwon | tests/test_mrr_imputation.py; dataset real: 4 filas high imputadas | COMPLIANT |
| imputacion de MRR desde el monto del deal | imputacion sin deal closedwon | tests/test_mrr_imputation.py; dataset real: 24 filas medium imputadas | COMPLIANT |
| imputacion de MRR desde el monto del deal | empresa con valor de CRM | tests/test_mrr_imputation.py; dataset real: 622 filas con mrr_source igual a crm | COMPLIANT |
| MRR sin resolver | empresa con dos montos ambiguos | tests/test_assembly_contracts.py, fixture sintetico con 2 filas unresolved segun el diseno; dataset real: 0 filas unresolved | COMPLIANT |
| MRR sin resolver | empresa sin deals | tests/test_assembly_contracts.py, contrato assert_mrr_confidence_matches_source verificado en las dos direcciones sobre master_dataset.csv real, 0 filas con mrr_mxn vacio | COMPLIANT |
| bitacora de excepciones de imputacion | 28 filas de imputacion | dataset real: exceptions_log.csv tiene exactamente 28 filas, todas con exception_code mrr_imputed_from_deal, cada una con su deal_id en evidence_ref | COMPLIANT |
| mes de referencia | empresa con baja | tests/test_usage_trend.py; dataset real: 89 empresas con baja, trend_asof_month es el mes de churn_date menos 2 | COMPLIANT |
| mes de referencia | empresa activa | tests/test_usage_trend.py; dataset real: mes de referencia 2024-08 para las 561 empresas activas | COMPLIANT |
| calculo de trend_usage | tendencia calculada | tests/test_usage_trend.py, forma cerrada del EWMA contra pandas.Series.ewm dentro de 1e-9; dataset real: 585 filas computed | COMPLIANT |
| calculo de trend_usage | historia insuficiente | tests/test_usage_trend.py; dataset real: 61 filas insufficient_history | COMPLIANT |
| calculo de trend_usage | sin uso | tests/test_usage_trend.py; dataset real: 4 filas no_usage, la suma da las 650 filas | COMPLIANT |
| resguardo contra fuga de datos | fila posterior al mes de corte excluida | tests/test_leakage_guard.py, marca dataset, recalcula el conjunto contribuyente de forma independiente sobre las 585 filas computed sin confiar en el mart | COMPLIANT |
| canal de adquisicion | empresa con touches | tests/test_support_commercial.py; dataset real: las 650 empresas tienen al menos un touch, sin ninguna fila en unknown | COMPLIANT |
| canal de adquisicion | empresa sin touches | tests/test_support_commercial.py, fixture con respaldo de lead_source | COMPLIANT |
| revenue cerrado | suma de deals cerrados | tests/test_support_commercial.py; dataset real: closed_revenue_mxn total 11046172.00 MXN, mensual normalizado, excluyendo cuarentena | COMPLIANT |

#### coverage-report (5 requisitos, 5 escenarios, todos cumplidos)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| cobertura por sistema | tres porcentajes por sistema | dataset real: coverage_report.md seccion 2, crm_hubspot 95.87%, product_db 100.00%, vitally 100.00% | COMPLIANT |
| cobertura por nivel de confianza | desglose por nivel | dataset real: coverage_report.md seccion 3, T0 45.85% con 596, T1 50.00% con 650, T2 4.15% con 54, T3 0.00%, M 0.00% | COMPLIANT |
| tamano de la cola de revision manual | conteo de la cola manual | dataset real: coverage_report.md seccion 4, 0 registros en M | COMPLIANT |
| conteos de cuarentena | conteos de cuarentena en el reporte | dataset real: coverage_report.md seccion 6, 28 empresas clon, 35 deals huerfanos, 667251.00 excluidos | COMPLIANT |
| recalculo desde match_audit | porcentaje recalculado | tests/test_coverage_report.py, prueba que mueve una fila de T0 a M entre dos corridas en memoria y confirma que la cobertura por nivel cambia | COMPLIANT |

#### trend-backtest-harness (4 requisitos, 4 escenarios, todos cumplidos)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| reproduccion de la comparacion de formulas | corrida completa del backtest | tests/test_harness_regression.py; dataset real: backtest_report.md con las seis formulas en k igual a 0, 2 y 3 | COMPLIANT |
| metricas reportadas por formula | metricas de una formula | dataset real: backtest_report.md reporta columnas Definida, AUC, Precision y Recall por formula y por k | COMPLIANT |
| regresion del momentum ganador en k igual a 2 | prueba de regresion | tests/test_harness_regression.py; dataset real: momentum EWMA con AUC 1.000 en k igual a 2, el mas alto entre las seis formulas, valores 0.980, 0.962, 0.996, 0.845, 1.000, 0.978 | COMPLIANT |
| evidencia de fuga de datos en k igual a 0 | AUC cercano a 1.0 en k igual a 0 | dataset real: backtest_report.md en k igual a 0, cinco de seis formulas con AUC mayor o igual a 0.93, momentum en 1.000; solo mes contra mes anterior queda en 0.578 | COMPLIANT |

#### build-cli (4 requisitos, 5 escenarios, todos cumplidos)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| comando unico de construccion | corrida completa | python -m worky_engine build corrido tres veces contra data/raw/sistemas, siete salidas generadas en cada corrida | COMPLIANT |
| idempotencia byte a byte | dos corridas seguidas | sha256 identico en las tres corridas de build de esta verificacion y contra outputs/, ver tabla en la seccion de build | COMPLIANT |
| mensajes de error claros | falta una base de datos | tests/test_build_contracts.py, codigo de salida 2 con --data-dir inexistente, mensaje en espanol | COMPLIANT |
| mensajes de error claros | falta una dependencia | tests/test_build_contracts.py, simulacion de ImportError con monkeypatch, codigo de salida 2, nombre del modulo faltante | COMPLIANT |
| carpeta de datos configurable | carpeta de datos indicada | --data-dir data/raw/sistemas usado en toda esta verificacion, resuelto por la funcion interna de resolucion de carpeta de datos | COMPLIANT |

**Compliance summary**: 55/55 escenarios compliant.

### Correctness (Static Evidence)

| Requisito | Estado | Notas |
|---|---|---|
| mrr_confidence dominio high, medium, none | Implementado | worky_engine/sql/marts/mart_mrr.sql expone las tres ramas; 0 filas none en el dataset real, 2 en el fixture sintetico segun el diseno |
| contrato assert_mrr_confidence_matches_source | Implementado | worky_engine/quality/contracts.py, verifica las dos direcciones de la regla none contra unresolved |
| mart_deal_normalized.sql, regla de normalizacion 12x, Adenda 1 del ADR-002 | Implementado | Vista compartida entre mart_mrr.sql y mart_commercial.sql, evita duplicar la regla en dos archivos |
| candidate_deal con ROW_NUMBER | Implementado | mart_mrr.sql usa ROW_NUMBER particionado por master_id y ordenado para que evidence_ref apunte al deal mensual, no al anual |
| ORDER BY en las vistas de cobertura | Implementado | mart_coverage.sql lleva ORDER BY explicito en sus seis vistas, corrigiendo el hallazgo de orden no determinista de GROUP BY documentado en la tarea 4.13 |
| orden fisico de columnas de master_dataset | Implementado | outputs/master_dataset.csv reproduce exactamente el orden de bloques de la seccion 2 del diseno: identidad, atributos, MRR, baja, uso, soporte, comercial, metadatos |

### Coherence (Design)

| Decision | Seguida? | Notas |
|---|---|---|
| D1, puntaje de identidad en Python con RapidFuzz | Si | identity_resolution/scoring.py envuelve WRatio, token_set_ratio y partial_ratio; ningun calculo se movio a SQL |
| D3, carga de las tres SQLite via sqlite3 y DataFrame registrado | Si | sources.py abre en modo solo lectura y assemble.py registra los DataFrames en DuckDB |
| D4, instalacion automatica de extensiones apagada | Si | la conexion de DuckDB desactiva autoinstall y autoload de extensiones de forma explicita | 
| D6, archivo duckdb regenerado, no persistido | Si | .gitignore incluye .build/ y *.duckdb; no se encontro ningun archivo duckdb commiteado |
| D7, dataset_asof derivado de los datos | Si | dataset_asof quedo en 2024-08-31 en las tres corridas de build de esta verificacion, sin variar |
| D9, desempate de bloque de fecha baja de nivel, nunca por orden de filas | Si | cascade.py implementa la caida a T3 y a M; tests/test_identity_resolution.py cubre el caso de cuatro candidatos |
| D12, normalizacion 12x de montos de deal | Si | mart_deal_normalized.sql, verificado contra las tres empresas reales con el patron 12x |
| D13, mrr_confidence en none solo cuando mrr_source es unresolved | Si | assert_mrr_confidence_matches_source verificado en las dos direcciones sobre el dataset real |
| Corte en cuatro PR encadenados, decision D11 | Si, con excepcion de tamano aceptada | PR 2 y PR 4b superaron el presupuesto de 800 lineas, 1324 y 1012 lineas respectivamente; el usuario acepto size:exception para ambos, documentado en tasks.md en las tareas 2.15 y 4.14 |
| Seccion 9 de coverage_report.md, canal de adquisicion | Parcial, desviacion documentada | El diseno describe filas por primer touch, filas por respaldo de lead_source y filas en unknown; la implementacion usa en su lugar la distribucion de valores de canal, documentada en la tarea 4.5. No viola ningun requisito del spec coverage-report, que no exige ese desglose especifico |

### Desviaciones conocidas y aceptadas

- Excepcion de tamano en PR 2, identity-resolution: el conteo final de lineas de autoria fue 1324 contra el presupuesto de 800, un 66 por ciento por encima. Documentado en tasks.md, tarea 2.15, con el desglose exacto y la justificacion: la correccion del gate agrego escenarios de prueba que faltaban del spec.
- Excepcion de tamano en PR 4b, soporte, comercial y harness: el conteo final fue 1012 lineas contra el presupuesto de 800, un 26 por ciento por encima. Aceptado de forma explicita por el usuario el 2026-09-08, documentado en tasks.md, tarea 4.14, y en el apply-progress de Engram, observacion 1665.
- PR 3a sin recibo RDD por defecto del proveedor de revision: registrado como una limitacion conocida del proveedor, identificada como issue 3942, sin bloquear el cierre del PR. No afecta la evidencia de pruebas ni de build reunida en esta verificacion.
- Regla de normalizacion 12x de montos, Adenda 1 del ADR-002: documentada como correccion sobre la version original del ADR-002 tras medir la relacion real entre monto de deal y MRR, 655 casos en razon 1.0 y 261 en razon 12.0, ningun otro valor. Implementada en mart_deal_normalized.sql y verificada contra las tres empresas reales que la necesitaban.
- requires-python en pyproject.toml: el diseno proponia un rango entre 3.14 y 3.15; la implementacion fijo 3.12 o superior por instruccion explicita del entorno, con Python 3.14.7 instalado. La reproducibilidad estricta descansa en las versiones exactas de rapidfuzz, duckdb, pandas y pytest, no en el rango de Python, segun la seccion 7 del diseno.
- Hallazgo de orden no determinista en mart_coverage.sql, agrupamiento sin ordenamiento explicito: detectado durante la regeneracion de goldens del PR 4b, corregido con ordenamiento explicito en las vistas nuevas, verificado con ocho builds consecutivos sin diferencia. Documentado en tasks.md, tarea 4.13, e incorporado a la seccion 7 del diseno.
- Desviacion de nombres de carpeta de datos: la carpeta real de datos es data/raw/sistemas, no data/raw, porque el paquete comprimido del caso guarda las tres bases dentro de una carpeta llamada sistemas. Documentado desde la tarea 1.12 y usado de forma consistente en toda la implementacion y en esta verificacion.

### Issues Found

**CRITICAL**: None

**WARNING**:

1. PR 2 y PR 4b superaron el presupuesto de revision de 800 lineas, con 1324 y 1012 lineas respectivamente. Ambas excepciones de tamano fueron aceptadas de forma explicita por el usuario y quedan documentadas en tasks.md; no representan un riesgo tecnico pendiente, pero sdd-archive deberia registrar ambas excepciones en el reporte de archivo.
2. La seccion 9 de coverage_report.md, canal de adquisicion, se implemento con un desglose distinto al que describe la seccion 2 del diseno, usando la distribucion de valores de canal en vez de filas por camino de resolucion. Es una desviacion de diseno documentada que no rompe ningun requisito del spec coverage-report, pero conviene que el diseno se actualice para reflejar la implementacion real antes de archivar.

**SUGGESTION**:

1. El diseno documenta un seguimiento pendiente para agregar la variante s r l de c v a la lista de razones sociales eliminadas en normalize_company_name, ya que 29 nombres del dataset la traen; no afecta el cruce actual y queda correctamente diferido a un cambio posterior.
2. El rango de requires-python en pyproject.toml quedo mas amplio que el que proponia el diseno original; vale la pena que un cambio posterior alinee ambos documentos si el equipo decide fijar el rango en el entorno de integracion continua.

### Verdict

**PASS**

Las 65 tareas de las cuatro unidades de PR encadenadas, normalizacion, resolucion de identidad, ensamblaje del dataset maestro con MRR y cobertura, y uso, soporte, comercial y harness, estan completas y verificadas. Los 39 requisitos y 55 escenarios de las seis capacidades, build-cli, coverage-report, identity-resolution, master-dataset-assembly, source-normalization y trend-backtest-harness, tienen evidencia de prueba en tiempo de ejecucion, con 128 pruebas en verde y cero fallidas. El build es reproducible byte por byte en tres corridas independientes contra los siete goldens commiteados, y el backtest reproduce la tabla del ADR-003 dentro de la tolerancia declarada. Las dos excepciones de tamano de PR y la desviacion de diseno en la seccion 9 del reporte de cobertura quedan como WARNING, sin bloquear el cierre del cambio.
