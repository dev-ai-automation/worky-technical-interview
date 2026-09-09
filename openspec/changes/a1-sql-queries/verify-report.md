```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:afc4a43015bac13fd11814cf902ef9f89cc03616ebdc328fce8fb68657bae924
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 10/10
scenarios: 22/22
test_command: python -m pytest -q
test_exit_code: 0
test_output_hash: sha256:03ef5f226e65ffe983093f14b581bdac21401d3c3c2325c4eda552412de15e7f
build_command: python -m worky_engine analyze --data-dir data/raw/sistemas --out-dir outputs/analysis (x2) && python -m worky_engine build --data-dir data/raw/sistemas --out-dir outputs
build_exit_code: 0
build_output_hash: sha256:23b6445aafa425c8e9b4152b6fc905fc6f3880640a07a2eb484dfd096e67aac1
```

## Verification Report

**Change**: a1-sql-queries
**Capacidad**: sql-analysis (siete respuestas de A1 sobre la sabana de A0, comando `analyze`, `report.md` y `analysis_exceptions.csv`)
**Mode**: Standard (Strict TDD no activo)
**Commit verificado**: 2593273f4085b95cdd940d97e10f35a354f386da (rama feat/a1-pr3-exceptions-report, arbol limpio antes y despues de esta verificacion). `evidence_revision` es el sha256 de esta cadena de commit.
**Alcance de esta verificacion**: cierre del cambio completo (PR 1, PR 2 y PR 3 ya aplicados y con recibo RDD aprobado cada uno, ver `openspec/changes/a1-sql-queries/state.yaml`). Esta corrida vuelve a comprobar las siete respuestas de A1 completas sobre el estado actual del repositorio, no solo lo nuevo del ultimo PR.

### Completeness

| Metrica | Valor |
|---|---|
| Tareas totales (tasks.md) | 32 |
| Tareas completas | 32 |
| Tareas incompletas | 0 |
| Requisitos totales | 10 |
| Requisitos cumplidos | 10 |
| Escenarios totales | 22 |
| Escenarios cumplidos | 22 |

Conteo verificado con grep sobre `openspec/changes/a1-sql-queries/specs/sql-analysis/spec.md` bajo "## ADDED Requirements": 10 encabezados `### Requirement:` y 22 encabezados `#### Scenario:`. `tasks.md` trae 32 casillas `- [x]` (PR 1: 1.1 a 1.11, PR 2: 2.1 a 2.9, PR 3: 3.1 a 3.12) y cero `- [ ]`. Nota: `state.yaml` y `apply-progress.md` citan "33/33 tareas" en su resumen de la fase apply; el conteo real de casillas en `tasks.md` es 32, no 33. Es una inconsistencia de bitacora, no una tarea faltante: las 32 casillas existentes estan todas marcadas. Ver SUGGESTION 1.

### Ejecucion de pruebas

**Tests**: 179 passed / 0 failed / 0 skipped

```text
python -m pytest -q
........................................................................ [ 40%]
........................................................................ [ 80%]
...................................                                      [100%]
179 passed in 51.04s
```

El comando corrio sin `--data-dir`: `tests/conftest.py` resuelve la carpeta de datos por omision a `data/raw/sistemas`, que ya trae las tres bases SQLite del caso, asi que las pruebas marcadas dataset corrieron completas (no se saltaron). El total sube de los 178 que registra `apply-progress.md` al cierre del PR 3 a 179 porque esta corrida cuenta tambien test_dataset_metadata_con_dataset_maestro_vacio_falla_con_mensaje_claro de tests/test_analysis_rules.py, que no necesita el dataset real y ya estaba en el repositorio.

**Idempotencia de analyze**: Passed. Corrido dos veces seguidas directamente sobre outputs/analysis/ (la carpeta que ya tiene los goldens comiteados):

```text
python -m worky_engine analyze --data-dir data/raw/sistemas --out-dir outputs/analysis
analyze: 6 consultas escritas en outputs\analysis
codigo de salida: 0
(segunda corrida, mismo comando)
analyze: 6 consultas escritas en outputs\analysis
codigo de salida: 0
```

```text
git status --short outputs
(sin salida, antes y despues de las dos corridas)
```

git status --short outputs no mostro ninguna linea antes ni despues de las dos corridas: las ocho salidas de analyze (seis CSV, analysis_exceptions.csv y report.md) quedaron exactamente iguales, byte por byte, a la copia ya comiteada. Ademas, tests/test_analysis_idempotency.py::test_dos_corridas_de_analyze_son_identicas_entre_si_y_contra_el_golden (marca dataset, parte de los 179 casos en verde) corre analyze dos veces en carpetas temporales, compara las ocho salidas entre si y contra el golden comiteado, y compara el hash sha256 de los ocho archivos de outputs/ (A0) antes y despues: la prueba automatizada cubre exactamente esta propiedad en cada corrida de la suite, no solo en esta verificacion manual.

**A0 sin cambio (build)**: Passed. Se corrio build una vez despues de las dos corridas de analyze, para confirmar que A1 no altero ninguna salida de A0:

```text
python -m worky_engine build --data-dir data/raw/sistemas --out-dir outputs
build: 650 empresas ensambladas en outputs
codigo de salida: 0
```

```text
git status --short outputs
(sin salida)
```

Los ocho goldens de A0 (identity_crosswalk.csv, match_audit.csv, quarantine_companies.csv, quarantine_deals.csv, master_dataset.csv, exceptions_log.csv, coverage_report.md, backtest_report.md) quedaron identicos a la copia comiteada. git status --short sobre todo el repositorio, corrido al final de la sesion de verificacion, tampoco mostro ninguna linea: ningun archivo de trabajo quedo sucio.

**Em dash**: la busqueda del caracter em dash sobre README.md, worky_engine/analysis, worky_engine/sql/analysis, outputs/analysis, docs/decisions/ADR-004-sql-analysis-definitions.md y openspec/changes/a1-sql-queries/design.md no encontro ninguna coincidencia. tests/test_analysis_report.py::test_sin_em_dash_en_el_documento fija esta regla como prueba automatizada sobre report.md.

**Coverage**: no hay umbral de cobertura de linea configurado en openspec/config.yaml (coverage_threshold: 0); no aplica.

### Spec Compliance Matrix (sql-analysis, 10 requisitos, 22 escenarios)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| comando analyze sin build previo | corrida sin build previo | tests/test_analysis_idempotency.py::test_dos_corridas_de_analyze_son_identicas_entre_si_y_contra_el_golden corre analyze en carpetas temporales sin build previo; corrida manual de esta verificacion, dos veces, exit 0 | COMPLIANT |
| comando analyze sin build previo | dos corridas identicas | mismo test (marca dataset); verificacion manual git status --short outputs vacio en las dos corridas de esta sesion | COMPLIANT |
| comando analyze sin build previo | falta una dependencia o una base de datos | Sin test que invoque analyze con --data-dir inexistente o con duckdb simulado ausente. cmd_analyze (worky_engine/cli.py:234-296) llama a las mismas funciones _resolve_data_dir y _exit_missing_dependency que cmd_build, y esas rutas si tienen prueba dedicada (tests/test_build_contracts.py::test_build_con_data_dir_inexistente_termina_con_codigo_2, ::test_build_con_duckdb_faltante_termina_con_codigo_2). Ver WARNING 1 | COMPLIANT (evidencia indirecta, ver WARNING 1) |
| A1.1, MRR activo por segmento e industria | tabla segmentada con dos totales | tests/test_analysis_rules.py::test_a1_01_dos_columnas_mrr_y_fila_de_totales | COMPLIANT |
| A1.1, MRR activo por segmento e industria | el total imputado coincide con la sabana | tests/test_analysis_rules.py::test_a1_01_total_coincide_con_master_dataset (fixture) y tests/test_analysis_dataset_numbers.py::test_a1_01_total_imputado_coincide_con_master_dataset (marca dataset) | COMPLIANT |
| A1.2, caida relativa de uso al churn | mes de baja excluido de la ventana | tests/test_analysis_rules.py::test_a1_02_mes_de_baja_excluido_de_la_ventana | COMPLIANT |
| A1.2, caida relativa de uso al churn | 89 cuentas en el dataset real | tests/test_analysis_dataset_numbers.py::test_a1_02_89_cuentas_33_con_windows_overlap (marca dataset): 89 filas confirmadas. windows_overlap mide 33 cuentas, no las 30 que citaba la primera version del ADR-004; la Adenda 1 del ADR-004 (2026-09-08) ya corrige la cifra citada a 33 y documenta el desglose. Sin desviacion pendiente | COMPLIANT |
| A1.2, caida relativa de uso al churn | ventanas traslapadas marcadas | tests/test_analysis_rules.py::test_a1_02_windows_overlap_en_cuenta_de_tres_meses | COMPLIANT |
| A1.2, caida relativa de uso al churn | cuenta con churn sin filas de uso | tests/test_analysis_rules.py::test_a1_02_drop_status_sin_uso | COMPLIANT |
| A1.3, retencion por cohorte de alta | retencion por cohorte y k | tests/test_analysis_rules.py::test_a1_03_caso_frontera_churn_exacto_en_mes_k (caso frontera) y tests/test_analysis_dataset_numbers.py::test_a1_03_monotonia_no_creciente_sobre_dataset_real (marca dataset, 30 cohortes, monotonia verificada en las 30) | COMPLIANT |
| A1.3, retencion por cohorte de alta | celda censurada vacia | tests/test_analysis_rules.py::test_a1_03_celda_censurada_vacia_en_cohorte_reciente | COMPLIANT |
| A1.4, atribucion por primer y ultimo touch | dos canales por deal | tests/test_analysis_rules.py::test_a1_04_empate_por_touch_id_en_los_dos_extremos y ::test_a1_04_deal_creado_antes_del_primer_touch_es_no_prior_touch | COMPLIANT |
| A1.4, atribucion por primer y ultimo touch | tasas lado a lado y bandera de cambio de ganador | tests/test_analysis_dataset_numbers.py::test_a1_04_canal_ganador_medido_por_modelo (marca dataset) prueba los dos ganadores sobre el dataset real (sin cambio: Paid Search en los dos). Ningun test automatizado ejercita el caso en que el ganador si cambia entre modelos. Verificado manualmente en esta sesion: sobre el fixture minimo, format_report produce el texto correcto de cambio de ganador cuando first_touch gana con el canal unknown y last_touch gana con no_prior_touch (logica confirmada correcta, sin assert automatizado). Ver WARNING 2 | COMPLIANT (verificado manualmente en esta sesion, ver WARNING 2) |
| A1.5, deals sin empresa real | 35 deals huerfanos | tests/test_analysis_dataset_numbers.py::test_a1_05_35_deals_667251_pesos_todos_closedwon (marca dataset) y tests/test_analysis_rules.py::test_a1_05_deal_huerfano_detectado / ::test_a1_05_deal_de_clon_remapeado_no_es_huerfano (fixture) | COMPLIANT |
| A1.6, tickets con horas de resolucion negativas | 48 tickets listados y neutralizados en promedios | tests/test_analysis_dataset_numbers.py::test_a1_06_48_tickets_negativos_y_su_excepcion (marca dataset) fija las 48 filas. Ningun mart ni vista de este cambio ni de A0 calcula un promedio de resolution_hours (busqueda de AVG sobre resolution_hours en worky_engine no muestra ninguna coincidencia); el ADR-004 confirma que A3 usara conteos y CSAT en vez de tiempo de resolucion hasta que A6 corrija el signo. La clausula de nulo en promedios no tiene ningun computo que probar en este cambio; se satisface por ausencia, no por una prueba directa. Ver WARNING 3 | COMPLIANT (parcial: filas probadas, clausula de promedio sin computo que probar, ver WARNING 3) |
| A1.6, tickets con horas de resolucion negativas | tickets conservados en conteos y CSAT | worky_engine/sql/marts/mart_support.sql (A0, sin cambio de este cambio) cuenta tickets_total y promedia csat_score sin filtrar por signo de resolution_hours; heredado de A0 y cubierto por la suite completa (179 casos en verde, incluye tests/test_support_commercial.py) | COMPLIANT |
| A1.6, tickets con horas de resolucion negativas | excepcion escrita sin tocar el log de A0 | tests/test_analysis_rules.py::test_a1_06_ticket_negativo_en_detalle_y_su_fila_de_excepcion (fixture) y tests/test_analysis_idempotency.py::test_dos_corridas_de_analyze_son_identicas_entre_si_y_contra_el_golden, que compara el hash de exceptions_log.csv (A0) antes y despues de correr analyze | COMPLIANT |
| A1.7, respuesta de diseno para escalar | seccion narrativa sin consulta | tests/test_analysis_report.py::test_una_seccion_por_item_de_a1_1_a_a1_7 confirma el encabezado de A1.7; worky_engine/sql/analysis/ solo trae siete archivos (a1_00 a a1_06), ningun a1_07.sql, confirmado por listado de directorio en esta verificacion | COMPLIANT |
| reporte de resultados por item | seccion completa por item | tests/test_analysis_report.py::test_una_seccion_por_item_de_a1_1_a_a1_7 y ::test_bloque_sql_igual_al_archivo_caracter_por_caracter | COMPLIANT |
| reporte de resultados por item | justificacion de A1.6 en 3 a 4 lineas | tests/test_analysis_report.py::test_a1_06_justificacion_presente_en_tres_a_cuatro_lineas | COMPLIANT |
| pruebas de comportamiento por consulta | prueba de fixture por regla | tests/test_analysis_rules.py::test_a1_02_mes_de_baja_excluido_de_la_ventana, entre otras nueve pruebas de fixture del mismo archivo | COMPLIANT |
| pruebas de comportamiento por consulta | prueba marcada dataset con el numero real | tests/test_analysis_dataset_numbers.py, ocho pruebas con marca dataset que fijan 89, 33, 35, 667251.00, 48, 962 y las medianas 13.5/12.2 | COMPLIANT |

**Compliance summary**: 22/22 escenarios compliant, tres con evidencia indirecta o parcial documentada arriba y en WARNING 1 a 3.

### Correctness (Static Evidence)

| Elemento | Estado | Notas |
|---|---|---|
| ANALYSIS_FILES con a1_00_last_touch.sql primero | Implementado | worky_engine/analysis/runner.py:35-43; a1_04 consume mart_last_touch |
| ANALYSIS_OUTPUTS con ORDER BY repetido en el SELECT de materializacion | Implementado | worky_engine/analysis/runner.py:55-65,108-111, incluye el CAST(drop_relative AS DOUBLE) de A1.2 |
| dataset_metadata reporta contrato ante mart_master_dataset vacio | Implementado | worky_engine/analysis/runner.py:79-95; probado por tests/test_analysis_rules.py::test_dataset_metadata_con_dataset_maestro_vacio_falla_con_mensaje_claro (correccion R3-fetchone-unpack de la revision RDD del PR 3) |
| cmd_analyze corre los contratos de A0 antes que los de A1 | Implementado | worky_engine/cli.py:262-284 |
| Los trece contratos de analysis_contracts.py | Implementados y corridos | worky_engine/quality/analysis_contracts.py:177-203, run_analysis_contracts en orden fijo; ejercidos sobre el fixture minimo por test_analysis_contracts_pasan_sobre_el_fixture y sobre el dataset real dentro de cmd_analyze en cada corrida de esta verificacion |
| report.py no abre conexion ni lee archivos | Implementado | worky_engine/analysis/report.py, sin import duckdb ni open(); recibe AnalysisResult ya materializado |
| mart_last_touch fuera de mart_commercial.sql | Implementado | worky_engine/sql/analysis/a1_00_last_touch.sql; worky_engine/sql/marts/mart_commercial.sql sin cambio de este cambio |
| DDL ilustrativo de A1.7 con MERGE INTO | Implementado | worky_engine/analysis/report.py:273-292, marcado como no ejecutable en este repositorio; desviacion documentada del diseno (que usaba DELETE + INSERT), pedida explicitamente en esta fase |

### Coherence (Design)

| Decision | Seguida? | Notas |
|---|---|---|
| D1, analyze con su propia conexion, simetrico a backtest | Si | cmd_analyze no llama a cmd_build; corrida sin build previo verificada en esta sesion |
| D2, analyze llama a assemble_master_dataset y corre ANALYSIS_FILES en la misma conexion | Si | worky_engine/cli.py:263,277 |
| D3, identidad resuelta en memoria, nunca lee outputs/ | Si | resolve_identity con existing_crosswalk None y reuse_crosswalk True en cmd_analyze |
| D4, --out-dir es la ruta literal, valor por omision outputs/analysis | Si | DEFAULT_ANALYSIS_OUT_DIR en worky_engine/cli.py:32,341 |
| D5, siete archivos SQL, sin vista base tipada compartida | Si | worky_engine/sql/analysis/ trae exactamente siete archivos |
| D6, ORDER BY declarado dos veces, con CAST donde el texto formateado lo exige | Si | Confirmado en a1_02_usage_drop.sql (ORDER BY CAST(drop_relative AS DOUBLE) DESC NULLS LAST, master_id) y en runner.py con la misma llave |
| D7, mart_last_touch a grano deal en la capa de analisis | Si | worky_engine/sql/analysis/a1_00_last_touch.sql |
| D8, A1.3 en formato largo, pivoteada en report.py | Si | worky_engine/analysis/report.py, funcion de pivote; probado por tests/test_analysis_report.py::test_a1_03_matriz_pivotada_con_celdas_censuradas_vacias |
| D9, cierre de datos derivado de dataset_asof, nunca constante | Si | substr(MAX(dataset_asof), 1, 7) en a1_03_cohort_retention.sql; sin ningun literal de fecha |
| D10, columna de estado al lado de cada valor no calculable | Si | drop_status en A1.2, cell_status en A1.3 |
| D11, analysis_exceptions.csv con las once columnas de exceptions_log, applied_value literal null | Si | a1_06_negative_hours.sql, confirmado por assert_analysis_exceptions_shape |
| D12, numeros reales solo en pruebas dataset, nunca en contratos | Si | worky_engine/quality/analysis_contracts.py no trae ningun literal 89/35/48; los ocho contratos son invariantes |
| D13, el SQL del reporte es el texto del archivo, sin copia a mano | Si | tests/test_analysis_report.py::test_bloque_sql_igual_al_archivo_caracter_por_caracter |
| D14, analyze corre los contratos de A0 antes de los propios | Si | worky_engine/cli.py:264-275 |
| D15, la prueba de idempotencia compara el hash de los ocho archivos de A0 | Si | tests/test_analysis_idempotency.py, funcion de hash de outputs de A0, mas la verificacion manual de esta sesion |

### Desviaciones conocidas y aceptadas

- windows_overlap mide 33 cuentas, no las 30 que citaba la primera version del ADR-004: la Adenda 1 del ADR-004 (2026-09-08) ya corrige la cifra publicada a 33 y documenta el desglose exacto (3 con 0 meses, 1 con 2, 6 con 3, 12 con 4, 11 con 5). Sin pendiente.
- AnalysisResult gana dataset_asof y ruleset_version sobre lo que describia el diseno original (solo outputs y sql_text): extension menor, documentada en apply-progress.md, necesaria porque report.py no abre conexion ni lee archivos (D13).
- ANALYSIS_OUTPUTS no incluye mart_last_touch (no tiene CSV propio): la tarea 2.4 de tasks.md decia agregarla a ambas listas, pero la tabla de la seccion 1 del diseno solo la lista en ANALYSIS_FILES. Se siguio la tabla del diseno.
- DDL de A1.7 con MERGE INTO en vez de DELETE mas INSERT del diseno original: instruccion explicita de la fase de aplicacion del PR 3; el DDL sigue marcado ilustrativo y no ejecutable.
- report.py mide 336 lineas, no las aproximadamente 180 estimadas por el diseno; el total de autoria del PR 3 (700 lineas) sigue dentro del presupuesto de 800 sin necesidad de mover alcance.
- El canal ganador de A1.4 no cambia entre modelos sobre el dataset real (Paid Search en los dos, 326 deals en no_prior_touch con el modelo de ultimo touch); el diseno anticipaba que podria cambiar. Se publico el numero medido, siguiendo la decision D12.
- state.yaml y apply-progress.md citan 33/33 tareas en el resumen de cierre del PR 3; tasks.md trae 32 casillas, todas marcadas. Inconsistencia de bitacora entre documentos, no una tarea sin marcar.

### Issues Found

**CRITICAL**: None

**WARNING**:

1. La ruta de error de analyze para "falta una dependencia o una base de datos" (requisito comando analyze sin build previo) no tiene una prueba que invoque el subcomando analyze con --data-dir inexistente o con duckdb no instalado. cmd_analyze reusa exactamente las mismas funciones (_resolve_data_dir, _exit_missing_dependency) que cmd_build, y esa ruta si tiene dos pruebas dedicadas en tests/test_build_contracts.py, pero ninguna prueba ejercita el codigo de salida 2 a traves del subcomando analyze. Riesgo bajo, mismo codigo y mismo mensaje, pero conviene agregar una prueba dedicada para analyze en un cambio futuro.
2. La bandera de cambio de ganador de A1.4 (si el canal con la tasa mas alta cambia entre el modelo de primer touch y el de ultimo touch) no tiene ninguna prueba automatizada que la ejercite cuando los dos ganadores si difieren. La unica prueba dataset confirma el caso en que no cambian (Paid Search en los dos modelos). Se verifico manualmente en esta sesion, corriendo format_report sobre el fixture minimo de tests/test_analysis_rules.py, que la logica de worky_engine/analysis/report.py si detecta y reporta correctamente el cambio de ganador (el modelo de primer touch gana con el canal unknown y el de ultimo touch con no_prior_touch en ese fixture), pero esa verificacion no quedo como prueba automatizada. Conviene agregar una prueba de fixture dedicada.
3. La clausula de que los 48 tickets aportan nulo al promedio, dentro del escenario de A1.6, no tiene ningun computo que probar: ni A0 ni este cambio calculan un promedio de resolution_hours en ninguna vista o mart. El ADR-004 confirma que A3 usara conteos y CSAT en vez de tiempo de resolucion hasta que A6 corrija el signo, asi que la garantia de nulo en promedios es hoy una regla sin artefacto que la ejerza, no una funcionalidad rota. Queda como documentacion preventiva para cuando A3 o A6 agreguen ese promedio.

**SUGGESTION**:

1. state.yaml y apply-progress.md citan 33/33 tareas en el cierre del PR 3; tasks.md trae 32 casillas marcadas (11 mas 9 mas 12). Vale la pena corregir la cifra citada en esos dos documentos antes o durante el archivado, para que no contradigan el conteo real de tasks.md.
2. Ninguna prueba invoca analyze con un outputs/analysis que ya tenga contenido de una corrida previa con datos distintos (por ejemplo, un report.md viejo con mas o menos filas); write_csv y write_markdown sobrescriben, pero no hay una prueba que lo confirme explicitamente para analyze como si la hay para build.
3. La mediana de A1.6 (13.5 contra 12.2) se fija con tolerancia 0.05 en tests/test_analysis_dataset_numbers.py, pero el texto generado por report.py ya no cita esas cifras literales: usa el total y el conteo de tickets abiertos medidos en tiempo de ejecucion, sin repetir 13.5 contra 12.2. Vale la pena que un cambio futuro verifique que el texto generado y la cifra del ADR-004 seguirian coincidiendo si alguien corre analyze sobre un dataset actualizado.

### Verdict

**PASS WITH WARNINGS**

Las 32 tareas de tasks.md (11 del PR 1, 9 del PR 2, 12 del PR 3) estan completas. Los 10 requisitos y 22 escenarios de la capacidad sql-analysis tienen evidencia de cumplimiento: 19 escenarios con prueba automatizada directa dentro de los 179 casos en verde de python -m pytest -q, y 3 escenarios con evidencia indirecta o parcial (codigo compartido con build ya probado, verificacion manual de esta sesion, o clausula sin computo que probar en el alcance actual), documentados en las tres WARNING de arriba. analyze corrio dos veces seguidas sobre outputs/analysis/ sin diferencia byte a byte (git status --short outputs vacio en ambas corridas), y build corrido despues no toco ninguno de los ocho goldens de A0 (git status --short outputs vacio otra vez). Ningun archivo generado ni la prosa de README.md o report.md contiene el caracter em dash. Las quince decisiones de diseno D1 a D15 se verificaron contra el codigo y coinciden, incluida la Adenda 1 del ADR-004 que ya corrige windows_overlap de 30 a 33. Ninguna desviacion rompe un requisito del spec. El cambio esta listo para sdd-archive.
