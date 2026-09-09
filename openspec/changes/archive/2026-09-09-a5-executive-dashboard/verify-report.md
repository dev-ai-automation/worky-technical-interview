```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:4bddfbbf6a889bcf755e7f9efac0bc0339556708629294f554fc75924dae5cc2
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 9/9
scenarios: 22/22
test_command: python -m pytest -q tests/test_dashboard_figures.py
test_exit_code: 0
test_output_hash: sha256:8609a8d2fcaa8fdfccce7efd15eda8752d8a1d7a3b1c0baf9500eece603d2d0c
build_command: python -m pytest -q -m "not dataset"
build_exit_code: 0
build_output_hash: sha256:9dfd68886c6589a6f7131c027a0b12a63155c12eb357119d3a9c4a96b065f660
```

## Verification Report

**Change**: a5-executive-dashboard
**Capacidad**: executive-dashboard (wireframe por secciones en docs/dashboard/01-dashboard-vp-cs.md, mockup HTML autocontenido en docs/dashboard/02-mockup-vp-cs.html, y la prueba tests/test_dashboard_figures.py que ancla toda cifra citada a outputs/health/health_scores.csv y outputs/master_dataset.csv)
**Mode**: Tasks + specs + design. strict_tdd: false (openspec/config.yaml). Este worktree aislado no trae data/raw/sistemas/ (carpeta ignorada por git), asi que las pruebas marcadas dataset se saltan aqui por diseno; test_dashboard_figures.py no lleva esa marca (decision D14) y corrio completa.
**Commit verificado**: 946b0a7fe27bad73589c5e6d612db13d2af32f89 (rama feat/a5-pr1-dashboard, worktree aislado 21-worky-a5, arbol limpio antes y despues de esta verificacion). evidence_revision es el sha256 de este commit.
**Alcance de esta verificacion**: primera corrida de sdd-verify sobre el cambio completo (27/27 tareas, un solo PR). Cubre la capacidad nueva executive-dashboard, las catorce decisiones de diseno (D1 a D14) y evidencia de ejecucion real sobre el dataset del caso.

### Completeness

| Metrica | Valor |
|---|---|
| Tareas totales (tasks.md) | 27 |
| Tareas completas | 27 |
| Tareas incompletas | 0 |
| Requisitos totales | 9 |
| Requisitos cumplidos | 9 |
| Escenarios totales | 22 |
| Escenarios cumplidos | 22 (2 con salvedad, ver WARNING 2 y WARNING 3) |

Conteo verificado con lectura directa de openspec/changes/a5-executive-dashboard/specs/executive-dashboard/spec.md: 9 encabezados de Requirement y 22 encabezados de Scenario bajo ADDED Requirements. tasks.md trae 27 casillas [x] (fase 1: 1.1-1.4, fase 2: 2.1-2.11, fase 3: 3.1-3.9, fase 4: 4.1-4.3) y cero casillas sin marcar.

### Ejecucion de pruebas

**Prueba enfocada**: 18 passed / 0 failed

```text
python -m pytest -q tests/test_dashboard_figures.py
18 passed in 1.38s
```

**Suite completa (sin marca dataset)**: 229 passed / 41 deselected / 0 failed

```text
python -m pytest -q -m "not dataset"
229 passed, 41 deselected in 706.45s (0:11:46)
```

**Autocontencion del mockup**: grep -c -E de scripts, links, imports y http(s) sobre docs/dashboard/02-mockup-vp-cs.html da 0; grep -c de "<script" tambien da 0 (ningun script, ni siquiera opcional). Tamano: 02-mockup-vp-cs.html 24,989 bytes (242 lineas), 01-dashboard-vp-cs.md 16,557 bytes (209 lineas). Cero em dash en los dos documentos.

**Prueba de deriva (drift proof), sobre una copia temporal fuera del repositorio**: se copio outputs/health/health_scores.csv a un directorio temporal, se altero ahi la fila de HS-100406 (churned de False a True, una cuenta que hoy si esta en la cola) y se recalculo la cola desde la copia alterada: bajo de 78 a 77 cuentas. El archivo real bajo outputs/health/health_scores.csv se releyo despues sin tocarlo y sigue dando 78. Esto demuestra la propiedad que ejercita test_la_cola_lista_las_78_cuentas_accionables y test_mrr_en_riesgo_y_proporcion: si el golden cambia, las cifras ancladas en los documentos (78, 2216115, 13.7 por ciento) dejan de cuadrar y la prueba falla. Ningun archivo bajo control de versiones fue modificado; solo se uso una copia en un directorio temporal, borrada al final.

**Recomputo independiente desde los dos goldens (pandas, union por master_id)**:

| Cifra | Recalculado | Citado en propuesta/ADR-007/diseno |
|---|---|---|
| Cuentas en la cola (flagged_15=True AND churned=False) | 78 | 78 |
| MRR en riesgo | 2216115.0 | 2,216,115 |
| MRR activo total | 16223225.5 | 16,223,225.50 |
| Proporcion | 13.7 | 13.7 por ciento |
| riesgo alto: total/activas/churneadas | 145 / 78 / 67 | 145 / 78 / 67 |
| sin historia: total/churneadas/activas | 65 / 22 / 43 | 65 / 22 / 43 |
| Tramos de MRR (activas) | 131 / 250 / 180 | 131 / 250 / 180 |
| Conteo por CSM | Jorge Ibarra 21, Ana Ruiz 15, Diego Ortega 10, Luis Pena 10, Carla Nunez 9, Fernanda Solis 8, Marta Diaz 5 | identico |
| HS-100065 | MRR 2947.0, score 35.56, flagged_15=True, churned=False | 2,947, score 35.56 |
| HS-100507 | MRR 46340.0, score 27.68, flagged_15=True, churned=False | 46,340, score 27.68 |

Las diez cifras recalculadas coinciden exactamente con las citadas. health_scores.csv tiene 22 columnas (verificado con pandas), confirma D9 (no trae csm_owner).

**Grep de las cadenas literales en los dos documentos**: los ocho literales de D11, los siete conteos por CSM (formato "Nombre: N") y los tres conteos de tramo (formato "N cuentas") aparecen al menos una vez en ambos archivos, verificado con grep -c -F, igual que las 18 pruebas de Fase 2. El literal "145" da 0 coincidencias en los dos documentos (ver WARNING 2).

**Aislamiento**: git diff main..HEAD --stat toca ocho rutas: README.md (mas una linea), docs/dashboard/01-dashboard-vp-cs.md (nuevo), docs/dashboard/02-mockup-vp-cs.html (nuevo), tests/test_dashboard_figures.py (nuevo), openspec/changes/a5-executive-dashboard/apply-progress.md y tasks.md (SDD), y openspec/changes/a6-cleaning-script/state.yaml y tasks.md. Estas dos ultimas NO son cambios de A5: git merge-base main HEAD confirma que feat/a5-pr1-dashboard se bifurco en el commit 15310ea, y main avanzo despues con el commit 680edc7 (persistencia de las tareas de a6-cleaning-script) que A5 nunca incorporo; el diff solo refleja esa divergencia de rama, no una edicion de A5. git status --short da vacio. Cero cambios bajo worky_engine/ u outputs/.

**Coverage**: sin umbral configurado (coverage_threshold: 0); no aplica.

### Spec Compliance Matrix - executive-dashboard (9 requisitos, 22 escenarios)

| Requisito | Escenario | Test / evidencia | Resultado |
|---|---|---|---|
| Secciones obligatorias del documento de wireframe | el documento cubre las seis secciones obligatorias | Inspeccion: indice de 01-dashboard-vp-cs.md trae ocho secciones que incluyen las seis exigidas (KPIs, cola, onboarding, carga por CSM, evidencia del modelo, drill-down) | COMPLIANT |
| Secciones obligatorias del documento de wireframe | cada seccion declara su fuente y su filtro | Inspeccion: cada seccion trae su tabla de seis columnas con Columna o consulta fuente y Filtro (D2) | COMPLIANT |
| Secciones obligatorias del documento de wireframe | la vista de tendencia se documenta como camino a futuro, no como dato inventado | Inspeccion: seccion 6, bloque ASCII vacio mas texto explicando que fact_health_score_monthly necesita dos o mas corridas; mockup con div equivalente | COMPLIANT |
| Secciones obligatorias del documento de wireframe | el README enlaza el entregable | git diff main..HEAD -- README.md: una fila nueva con la liga a docs/dashboard/ | COMPLIANT |
| Regla de la cola de prioridad del CSM | la cola lista las 78 cuentas accionables | test_la_cola_lista_las_78_cuentas_accionables, test_una_cuenta_flagged_pero_churneada_queda_excluida | COMPLIANT |
| Regla de la cola de prioridad del CSM | la cuenta de mayor MRR aparece primero | test_la_cuenta_de_mayor_mrr_aparece_primero (HS-100155, 952602) | COMPLIANT |
| Regla de la cola de prioridad del CSM | un empate de health score se rompe por MRR | test_un_empate_de_health_score_se_rompe_por_mrr (HS-100598 antes que HS-100134, score 33.97 ambas) | COMPLIANT |
| Segundo eje visual por tramos de MRR | cada cuenta de la cola muestra su tramo de MRR | test_cada_cuenta_de_la_cola_muestra_su_tramo_de_mrr (131/250/180); inspeccion de la columna Tramo en cada fila de la tabla del mockup | COMPLIANT |
| Respuesta explicita a la pregunta de 3000 contra 45000 | el documento nombra los tres mecanismos de trato distinto | Inspeccion: seccion 2.1 del Markdown enumera orden por MRR, KPI agregado y tramo de MRR; el callout del mockup los repite en prosa | COMPLIANT |
| Respuesta explicita a la pregunta de 3000 contra 45000 | HS-100065 y HS-100507 quedan como evidencia viva de la respuesta | test_HS_100065_y_HS_100507_quedan_como_evidencia_viva_de_la_respuesta; inspeccion de la seccion 2.1 y del callout del mockup | COMPLIANT |
| Panel de evidencia del modelo para cuentas ya churneadas | el panel de evidencia lista las 67 cuentas ya churneadas | test_el_panel_de_evidencia_lista_las_67_cuentas_churneadas (conjunto disjunto de la cola) | COMPLIANT |
| Panel de evidencia del modelo para cuentas ya churneadas | el panel reporta la deteccion temprana del modelo | Inspeccion mas grep literal de 92.9 por ciento en los dos documentos (seccion 5 del Markdown, KPI del mockup) | COMPLIANT |
| Cohorte de onboarding sin historia | la cohorte de onboarding lista las 43 cuentas activas nuevas | test_la_cohorte_de_onboarding_lista_las_43_cuentas_activas_nuevas; conteo manual de filas en la seccion de cohorte del mockup: 43 | COMPLIANT |
| Cohorte de onboarding sin historia | la cohorte nunca se etiqueta como sana | Inspeccion: nunca como sana en el Markdown y No estan sanas en el mockup; 65 = 22 + 43 presente en el Markdown | COMPLIANT |
| Carga de trabajo por CSM | el conteo por CSM coincide con las cifras verificadas | test_el_conteo_por_csm_coincide_con_las_cifras_verificadas, test_los_siete_conteos_por_csm_aparecen_en_los_dos_documentos | COMPLIANT |
| Carga de trabajo por CSM | un CSM por encima de su capacidad queda senalado | Inspeccion: tabla del Markdown marca Sobre capacidad en Jorge Ibarra y Ana Ruiz; mockup usa la etiqueta de texto sobre capacidad | COMPLIANT (ver WARNING 3, desviacion de diseno sobre el uso de color) |
| Mockup HTML autocontenido y en lenguaje llano | el mockup no depende de ningun recurso externo | grep de scripts, links, imports y http(s) sobre el mockup da 0 | COMPLIANT |
| Mockup HTML autocontenido y en lenguaje llano | el mockup se lee en modo claro y en modo oscuro | Inspeccion: bloque prefers-color-scheme dark con variables propias; contraste calculado manualmente para el color de riesgo alto sobre el fondo: 6.53 a 1 en claro, 8.20 a 1 en oscuro (ambos sobre el minimo 4.5 a 1 de D7) | COMPLIANT |
| Mockup HTML autocontenido y en lenguaje llano | el mockup usa lenguaje de negocio, no nombres de columna | grep de flagged_15, mrr_mxn, risk_band, hubspot_id, health_score, csm_owner y churned sobre el mockup: unica coincidencia es el pie de procedencia citando los nombres de archivo CSV, no nombres de columna de widget | COMPLIANT |
| Trazabilidad de cifras y prueba que las ancla a los goldens | cada cifra citada nombra su columna fuente | Inspeccion mas recomputo pandas (tabla arriba): 78, 2216115, 13.7 por ciento, 65=22+43 trazables y presentes en texto; 145 = 78 + 67 (mencionado en el Dado del escenario) NO aparece como literal en ningun documento | COMPLIANT con salvedad (ver WARNING 2) |
| Trazabilidad de cifras y prueba que las ancla a los goldens | la prueba dataset recalcula las cifras y coincide | test_la_prueba_dataset_recalcula_las_cifras_y_coincide | COMPLIANT |
| Trazabilidad de cifras y prueba que las ancla a los goldens | la prueba falla si un golden regenerado cambia una cifra citada | test_la_prueba_falla_si_un_golden_regenerado_cambia_una_cifra_citada; prueba de deriva manual sobre copia temporal (arriba): la cola bajo de 78 a 77 al alterar una fila fuera del repositorio | COMPLIANT |

Compliance summary: 22 de 22 escenarios con evidencia de cumplimiento (prueba automatizada, inspeccion directa o recomputo independiente); 2 de 22 con una salvedad documentada (WARNING 2 y WARNING 3) que no rompe ningun escenario del spec tal como esta redactado. 0 escenarios FAILING o UNTESTED.

### Correctness (Static Evidence)

| Elemento | Estado | Notas |
|---|---|---|
| test_dashboard_figures.py sin la marca dataset (D14) | Implementado | Confirmado por inspeccion directa del archivo; corrio en el worktree aislado sin data/raw/sistemas/ |
| Rutas resueltas con Path(__file__).resolve().parent.parent, igual que test_health_idempotency.py | Implementado | Lineas 35 a 39 del archivo de prueba |
| csm_owner unido desde master_dataset.csv por master_id (D9) | Implementado | Funcion _load_joined, snippet del apendice del Markdown |
| Ortografia de nombres de CSM tal como en el CSV (D10) | Implementado | Verificado con pandas.unique sobre csm_owner; nota de ortografia explicita en el Markdown |
| 22 columnas de health_scores.csv, sin csm_owner (D9) | Implementado | Confirmado con pandas en esta sesion |
| Barras SVG con rect de ancho fijo (D5) | Implementado | Cola de prioridad y barras de CSM en el mockup |
| Linea de referencia de 12 declarada como referencia operativa, no medida (D12) | Implementado | Markdown seccion 4 y mockup, ambos con la palabra referencia |

### Coherence (Design)

| Decision | Seguida? | Notas |
|---|---|---|
| D1 a D5, D7 a D14 | Si | Sin desviacion observada contra el documento y el mockup |
| D6 (color solo para nivel de riesgo; tramo de MRR y sobre capacidad nunca por color) | Parcial | El tramo de MRR sigue la regla (insignia de texto y encabezado, sin color). La etiqueta sobre capacidad del mockup si usa color ademas del texto, contra la propia seccion de diseno y la tarea 3.6 que piden nunca por color. Ver WARNING 3 |

### Task Completeness

27 de 27 casillas marcadas en tasks.md (fase 1: 4, fase 2: 11, fase 3: 9, fase 4: 3). Cero casillas sin marcar. apply-progress.md documenta cada tarea con su evidencia de cierre y coincide con el estado real del codigo verificado en esta sesion.

### Proposal Success Criteria

| Criterio | Evidencia |
|---|---|
| El documento cubre las seis secciones y responde por escrito la pregunta de 3000 contra 45000 | Indice de ocho secciones (superset de las seis exigidas) y seccion 2.1 con los tres mecanismos |
| La cola de prioridad lista 78 cuentas y la de mayor MRR aparece primero | test_la_cola_lista_las_78_cuentas_accionables, test_la_cuenta_de_mayor_mrr_aparece_primero |
| El mockup abre sin conexion y sin recursos externos, sin nombres de columna tecnicos | grep en 0 para scripts, links, imports y http; grep en 0 para nombres de columna tecnicos fuera del pie de procedencia |
| pytest tests/test_dashboard_figures.py pasa con el dataset real y falla si se altera una cifra citada | 18 passed; prueba de deriva manual sobre copia temporal confirmo la propiedad |
| Las 67 cuentas ya churneadas aparecen solo en el panel de evidencia del modelo | test_el_panel_de_evidencia_lista_las_67_cuentas_churneadas (conjunto disjunto) |
| git status no reporta cambios en worky_engine/, outputs/ ni en los goldens | git status --short vacio; git diff main..HEAD --stat sin rutas bajo worky_engine/ u outputs/ |

Las seis casillas de proposal.md siguen sin marcar en el archivo (se marcan tipicamente en sdd-archive); las seis tienen evidencia de cumplimiento verificada en esta sesion.

### Issues Found

CRITICAL: Ninguno.

WARNING:

1. La tabla Cola de prioridad del mockup se titula "20 de 78 cuentas, ordenadas por MRR" y su pie dice "Las 58 cuentas restantes de la cola siguen la misma regla" (78 menos 58 es 20), pero la tabla real solo trae 19 filas (confirmado contando las filas de HS-100155 a HS-100231). Ninguna prueba automatizada cuenta las filas visibles del mockup, asi que el hueco no rompe la suite verde y ninguna cifra agregada (78, 2216115, 13.7 por ciento, etc.) se ve afectada. Antes de archivar conviene agregar la fila faltante o corregir el texto a "19 de 78" y "59 cuentas restantes".
2. El numero combinado 145 (78 activas mas 67 churneadas), citado en la propuesta, en el ADR-007 y en el diseno como la cifra que ilustra por que no usar risk_band sola, nunca aparece escrito de forma literal en 01-dashboard-vp-cs.md ni en 02-mockup-vp-cs.html (una busqueda de "145" da 0 coincidencias en los dos archivos). El escenario de spec "cada cifra citada nombra su columna fuente" cita textualmente "145 = 78 + 67" como una de las cifras citadas en el documento. El documento si explica la idea con 78 y 67 por separado y en prosa (risk_band sola mezcla activas con churneadas), pero el lector no puede rastrear el numero que resume el hallazgo central de A5 porque nunca se escribe. La lista de cadenas ancladas por la prueba (decision D11 del diseno) excluye deliberadamente el 145, asi que ninguna prueba lo exige; es una brecha entre el ejemplo del spec y lo que el diseno decidio anclar, no una falla de prueba.
3. La etiqueta "sobre capacidad" de la seccion Carga por CSM del mockup usa el color reservado al nivel de riesgo alto ademas de la negrita y el texto, mientras que el diseno (seccion 3, decision D6) y la tarea 3.6 declaran explicitamente que esa distincion debe hacerse por texto y nunca por color, que se reserva al nivel de riesgo. No rompe ningun escenario del spec, que solo exige que la fila quede marcada y distinta de las filas dentro del rango sin mencionar color, pero es una desviacion observable de una decision de diseno explicita.

SUGGESTION:

1. La afirmacion del mockup de que HS-100507 "pesa quince veces mas en el MRR en riesgo" que HS-100065 es razonable (46340 dividido entre 2947 es aproximadamente 15.7), pero ese multiplo no esta en la lista de cifras trazadas del diseno; documentarlo en el apendice del snippet de pandas evitaria que un lector tecnico tenga que adivinar la operacion.

### Verdict

PASS WITH WARNINGS

Las 27 tareas de tasks.md estan completas, y las 18 pruebas de tests/test_dashboard_figures.py mas las 229 de la suite completa (python -m pytest -q -m "not dataset") pasan (0 fallas, 0 saltadas dentro del alcance corrido). El recomputo independiente con pandas desde los dos goldens (health_scores.csv, master_dataset.csv) reprodujo exactamente las diez cifras citadas en la propuesta, el ADR-007, el diseno y los dos documentos entregables: 78 cuentas, 2216115, 13.7 por ciento, 16223225.50, 145/78/67, 65/22/43, los tramos 131/250/180, el conteo por CSM y las dos cuentas de evidencia HS-100065 y HS-100507. Una prueba de deriva sobre una copia temporal (fuera del repositorio) confirmo que alterar una fila cambia la cola de 78 a 77, demostrando que la prueba versionada detectaria una desincronizacion real. El mockup no depende de ningun recurso externo, se lee en modo claro y oscuro con contraste verificado sobre el minimo de 4.5 a 1, y no muestra nombres de columna tecnicos fuera del pie de procedencia. El aislamiento es correcto: los unicos cuatro archivos que A5 toca son README.md (una fila), los dos documentos nuevos de docs/dashboard/ y tests/test_dashboard_figures.py; el diff que aparece sobre openspec/changes/a6-cleaning-script/ es divergencia de rama frente a main (confirmado con git merge-base), no una edicion de A5.

No se encontro ningun CRITICAL. Las tres WARNING (19 filas donde el texto dice 20 y 58, el numero 145 nunca escrito de forma literal pese a ser un ejemplo citado en el spec, y el color adicional en la etiqueta sobre capacidad contra la decision D6) son brechas de redaccion y de una decision de diseno puntual; ninguna rompe una prueba ni una cifra agregada de las que sostienen la respuesta a la pregunta del caso. El cambio queda listo para sdd-archive, con la recomendacion de que el humano revise las tres WARNING antes o despues de archivar segun el criterio del equipo.
