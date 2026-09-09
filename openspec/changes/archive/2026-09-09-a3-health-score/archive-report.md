# Informe de Archivo: health score de A3 con validación medida (`a3-health-score`)

**Archivado**: 2026-09-09  
**Cambio**: a3-health-score  
**Estado**: Ciclo SDD completado  
**Destinatario de archivo**: `openspec/changes/archive/2026-09-09-a3-health-score/`  
**Almacén de artefactos**: hybrid (archivos openspec + Engram proyecto 21-worky)

---

## Resumen Ejecutivo

El cambio a3-health-score implementó el modelo ADR-005 para la puntuación de salud de empresas, con cuatro subpuntajes ponderados, banda "sin historia", umbrales por capacidad de CSM y validación medida contra `churn_date`. Se entregaron tres PR apilados hacia main:

- **PR 1** (`feat/a3-pr1-health-scoring`, 4954cea): vistas as-of, modelo de puntuación, alias `auc`, contratos de forma y banda
- **PR 2** (`feat/a3-pr2-health-metrics`, 9c07767): métricas, comando `health`, salida `health_scores.csv`
- **PR 3** (`feat/a3-pr3-health-validation`, 82353a2): informe de validación con A3.4, README, pruebas de cierre

Todas las tareas completadas (28/28), todos los requisitos cumplidos (12/12), todos los escenarios probados (25/25), 213 pruebas pasadas. Verificación rerun con `pass_with_warnings` sin bloqueadores críticos. Modelo medido en el dataset del caso: AUC 0.997, recall detectable 1.000, recall general 0.753 (techo estructural por banda "sin historia").

---

## Autoridad de Estado Final

Este informe describe el estado del cambio en el cierre. Las fuentes de verdad se clasifican así (de mayor a menor autoridad):

1. **Artefacto `tasks.md` persistido**: completitud visible. Fuente: `openspec/changes/archive/2026-09-09-a3-health-score/tasks.md`, 28 casillas [x], cero sin marcar.
2. **Hechos finales del aviso de lanzamiento**: desviaciones documentadas, cambios posteriores a las instantáneas intermedias.
3. **Artefactos intermedios** (`apply-progress`, `verify-report`): descripción del estado en el momento de su escritura. Rango más bajo.

En donde las fuentes se contradicen, se cita la fuente más alta y el hecho se registra explícitamente.

---

## Especificación Sincronizada

**Dominio nuevo**: `health-score` (sin especificación principal anterior)

| Dominio | Acción | Detalles |
|---------|--------|---------|
| health-score | Creado | 12 requisitos ADDED, 25 escenarios, 206 líneas spec.md |

**Ubicación de la especificación sincronizada**: `openspec/specs/health-score/spec.md`

**Copia mecánica verificada**: Sí. La especificación delta se copió con `cp -R` y se verificó con `diff -r` idéntico (bytes idénticos). El diff readback fue vacío (PASS).

---

## Tareas Completadas

Todos los elementos de `tasks.md` están marcados completados. Conteo verificado:

- **Total de tareas**: 28 (1.1 a 1.12, 2.1 a 2.8, 3.1 a 3.8)
- **Tareas completadas**: 28 (100 %)
- **Tareas sin marcar**: 0

No hubo reconciliación de casillas obsoletas; todas las tareas completadas se marcaron oportunamente durante la aplicación.

**Fuente**: `openspec/changes/archive/2026-09-09-a3-health-score/tasks.md`, líneas 1-91

---

## Informe de Verificación (Estado Final)

**Veredicto**: pass_with_warnings (segundo intento; el primero fue fail por sección de aceptación no renderizada)

| Métrica | Valor |
|---------|-------|
| Bloqueadores | 0 |
| Hallazgos críticos | 0 |
| Requisitos cumplidos | 12/12 |
| Escenarios cumplidos | 25/25 |
| Pruebas pasadas | 213 |
| Salida de prueba | determinista, idéntica en dos corridas |
| Goldens A0 y A1 | sin cambios |

**Commit verificado**: 82353a2ca55c3f67632a1f6f67cc1bf3ece7b808 (rama feat/a3-pr3-health-validation)

**Advertencias** (no bloqueantes, registradas como seguimientos):
- La ruta de salida de `health` sin dependencias detectadas no tiene prueba dedicada (cobertura de rama implícita en `test_health_dataset_numbers.py`)
- Tres sugerencias de alineación de documentación en `apply-progress.md`

**Fuente**: `verify-report.md` (rerun), observación Engram `sdd/a3-health-score/verify-report`; confirmado por `state.yaml` líneas 27, 52-55

---

## Entregas Implementadas

Tres PR apilados hacia main, autorizados por el usuario para merge y push después del archivo:

### PR 1: `feat/a3-pr1-health-scoring`

**Commit**: 4954cea  
**Líneas de autoría**: 597 (reducidas de 991 iniciales mediante optimizaciones legítimas: fixture sintético sobre DataFrame, ventanas de SQL de un paso, alcance de equivalencia acotado)  
**Base**: main  

**Entregables**:
- Vistas SQL as-of (`h1_company_asof`, `h2_usage_signals`, `h3_tenure`, `h4_support_asof`, `h5_activation`, `h6_asof_inputs`)
- Modelo de puntuación (`scoring.py`): normalización percentil, banda "sin historia", suma ponderada 0.35/0.20/0.15/0.30
- Alias `auc` exportado de `worky_engine.harness`
- Ocho contratos de forma y banda (`health_contracts.py`)
- Pruebas de regla y equivalencia contra fixture mínimo (test_health_rules.py, test_health_equivalence.py)

**Revisión**: Lineage review-36d34a05d433c9c4, lens review-reliability, aprobado y reconocido después de una corrección acotada (contrato R3-risk-band-thresholds-unproved, bandas contra umbrales y pruebas)

### PR 2: `feat/a3-pr2-health-metrics`

**Commit**: 9c07767  
**Líneas de autoría**: 678 (bajo presupuesto de 800)  
**Base**: feat/a3-pr1-health-scoring  

**Entregables**:
- Ejecutor (`runner.py`): tres corridas (primaria k=2, sensibilidad k=3, sensibilidad literal)
- Métricas (`metrics.py`): AUC por señal, precisión, recall, recall ponderado por MRR, matriz de confusión, detección temprana, capacidad por CSM
- Comando `health` en cli.py: sin build previo, abre su propia conexión, escribe `health_scores.csv`
- Tres contratos adicionales en `health_contracts.py` (as-of verificación, denominador de recall, orden de fila)
- Pruebas de dataset (89 bajas, 22 no detectables, 78 marcadas al 15 %, AUC y recall detectables)
- Pruebas de idempotencia sobre corridas independientes y goldens de A0/A1

**Decisión D21/D6**: Conteo de no detectables medido en 22 (no 10 de la prosa del ADR-005). Corrida de sensibilidad k=3. Adenda 1 del ADR-005: pesos originales mantenidos (mezcla medida probada, no ayudaba).

**Revisión**: Lineage review-59a55bcf91116c86, lens review-reliability, aprobado y reconocido en primera pasada (primer capture falló con invalid_request del proveedor; reoferta admitida)

### PR 3: `feat/a3-pr3-health-validation`

**Commit**: 30484ba (código), 82353a2 (cierre con sección de aceptación y guardia de cero bajas)  
**Líneas de autoría PR 3**: 470 + sección de aceptación (~10 líneas) y guardia (~20 líneas de prueba)  
**Base**: feat/a3-pr2-health-metrics  

**Entregables**:
- Informe (`report.py`): 12 secciones, cada cifra etiquetada "en este dataset", tabla de AUC por señal con pesos cero, métricas al 10/15/20 %, matriz de confusión, no detectables, detección temprana k=3, sensibilidades (k=3, lectura literal, pesos iguales, convención harness), capacidad por CSM, narrativa de A3.4, contexto comercial
- Modificación cli.py: comando `health` escribe `validation.md` + mensaje final
- Pruebas de reporte: 12 secciones en orden, cifras en dataset, soporte con AUC y peso cero, sin em dashes
- Pruebas de idempotencia extendidas: byte idéntico para `validation.md`
- README actualizado: una línea nueva + una fila en tabla

**Correcciones post-verify** (commits fc19791, 82353a2):
- fc19791: Sección de aceptación agregada (umbrales AUC/recall detectables, alternativa mezcla medida), rutas de referencia corregidas
- 82353a2: Guardia para dataset sin bajas (zero_undetectable), dos pruebas adicionales de cobertura

**Revisión PR 3 original** (30484ba): Lineage review-450cc7fb355c16c7, lens review-reliability, aprobado y reconocido después de una corrección acotada (R3-undetectable-zero-division)

**Verificación fix** (82353a2): Lineage review-499e7ae7b187668e, lens review-reliability, aprobado y reconocido en primera pasada (lineaje anterior fc19791, review-b600ca2dee708aed, escaló sin recibo)

---

## Mediciones Finales (Objetivo A3)

**Modelo**: ADR-005, pesos 0.35 momentum + 0.20 mom + 0.15 drawdown + 0.30 antigüedad, sub-puntajes percentil 0-100, "sin historia" < 3 meses de uso, umbrales por capacidad CSM

**Dataset del caso**: 650 empresas (518 activas, 89 bajas, 43 sin estado), mes de corte derivado (2024-06 para activas, churn_date para bajas)

| Métrica | Valor | Nota |
|---------|-------|------|
| AUC | 0.997 | Excelente discriminación |
| Recall detectable | 1.000 | Todas las 67 bajas con historia marcadas al 20 % |
| Recall general | 0.753 (67/89) | Techo estructural: 22 no detectables en banda "sin historia" |
| MRR-weighted recall | 0.608 | Ponderado por tamaño de cuenta |
| Precisión (15 %) | 0.563 | 78 marcadas al 15 % sobre 518 activas |
| No detectables | 22/89 (24.7 %) | 4 sin uso, 6 con 1 mes, 12 con 2 meses |
| Detección temprana k=3 | 52/56 (0.929) | 52 de 56 bajas detectadas 1 mes antes |
| Activas marcadas (15 %) | 78 cuentas | ~11 por cada 7 CSM |

**Aceptación del harness**: CUMPLE (AUC >= 0.95, recall detectable >= 0.85 al 20 %)

**Hallazgo de onboarding (Parte B)**: Una cuarta parte del churn ocurre antes de 3 meses de uso, por lo que la banda "sin historia" es un techo estructural. El score no puede ser el único indicador temprano; se recomiendan señales de activación tempranas adicionales.

**Fuente**: Documento de mediciones (sección de diseño), verificación rerun, datos de `validation.md`

---

## Desviaciones Documentadas

Registradas en el diseño y tareas, sin impacto en la funcionalidad:

1. **Activación**: `activation_raw` es la media de cuatro columnas tempranas de actividad (no una sola señal de soporte), documentado en comentario de `metrics.py`

2. **Versionado**: `HealthResult` lleva `dataset_asof` y `ruleset_version` para reproducibilidad futura

3. **Apéndice SQL**: La sección 13 del informe es un apéndice SQL (requerimiento no mencionado en la especificación pero parte del patrón de A1)

4. **Correcciones de documentación**:
   - Prosa del ADR-005 original decía "10 no detectables"; correcto es 22 (Adenda 1)
   - `measurements.md` sección 1 ya sostenía 22 (discrepancia interna heredada)

5. **Reducción de PR 1 de autoría**: 991 líneas iniciales -> 798 finales mediante:
   - Fixture sintético sobre DataFrame (responsabilidad correcta de `scoring.py`, no DuckDB)
   - Ventanas SQL de un paso en `h2_usage_signals.sql` (mismo resultado, menos CTE)
   - Alcance acotado de equivalencia (no ensamblaje completo de identidad)

**Fuente**: `tasks.md` secciones "Brechas encontradas en el diseño", `design.md` decisiones D6-D21

---

## Contenido del Archivo

El cambio se ha movido a `openspec/changes/archive/2026-09-09-a3-health-score/` con verificación de integridad mecánica:

```
openspec/changes/archive/2026-09-09-a3-health-score/
├── proposal.md                      PRESENTE
├── exploration.md                   PRESENTE
├── measurements.md                  PRESENTE
├── preproposal.yaml                 PRESENTE
├── design.md                        PRESENTE
├── tasks.md (28/28 marcadas)        PRESENTE
├── apply-progress.md                PRESENTE
├── verify-report.md                 PRESENTE
├── state.yaml (actualizado)         PRESENTE
├── specs/health-score/spec.md       PRESENTE
└── archive-report.md (este archivo) PRESENTE
```

**Verificación de movimiento**: Diff readback entre snapshot pre-movimiento y carpeta archivada fue vacío (PASS). Fuente raíz ausente después del movimiento.

**Especificación sincronizada**: `openspec/specs/health-score/spec.md` contiene la copia idéntica de la especificación delta (diff readback vacío, PASS).

---

## Artefactos Engram Relacionados

Los siguientes artefactos fueron persistidos en Engram durante la ejecución de SDD y se registran para trazabilidad:

| Topic Key | Tipo | Observación |
|-----------|------|------------|
| `sdd/a3-health-score/explore` | architecture | Exploración inicial, mediciones de señales |
| `sdd/a3-health-score/explore-measurements` | architecture | Detalles de medición de señales |
| `sdd/a3-health-score/proposal` | architecture | Propuesta del cambio |
| `sdd/a3-health-score/spec` | architecture | Especificación con 12 requisitos |
| `sdd/a3-health-score/design` | architecture | Decisiones D1-D21 |
| `sdd/a3-health-score/tasks` | architecture | 28 tareas en 3 PR apilados |
| `sdd/a3-health-score/apply-pr1` | architecture | PR 1 entregada y revisada |
| `sdd/a3-health-score/apply-pr2` | architecture | PR 2 entregada y revisada |
| `sdd/a3-health-score/apply-pr3` | architecture | PR 3 entregada y revisada |
| `sdd/a3-health-score/verify-report` | architecture | Reporte de verificación final |
| `sdd/a3-health-score/archive-report` | architecture | Este informe |
| `worky/a3/decision-health-score` | decision | Decisiones de modelo y umbrales |
| `worky/a3/decision-recall-ceiling` | decision | Hallazgo de techo estructural |
| `worky/rdd/a3-pr1-review` | discovery | Recibos de revisión PR 1 |
| `worky/rdd/a3-pr2-review` | discovery | Recibos de revisión PR 2 |
| `worky/rdd/a3-pr3-review` | discovery | Recibos de revisión PR 3 |
| `worky/rdd/a3-verify-fix-review` | discovery | Recibos de revisión fix de verificación |

**Nota**: El proyecto Engram es `21-worky`. Topic keys actúan como upserts; los artefactos pueden consultarse mediante `mem_search` y `mem_get_observation`.

---

## Autorización y Contrato de Copia Mecánica

**Copia de especificación**:
- Método: `cp -R` seguido de `diff -r` para verificación de integridad
- Readback: Vacío (PASS) - especificación delta y copia de especificación principal son idénticas byte a byte
- Ruta verificada: `openspec/changes/a3-health-score/specs/health-score/spec.md` -> `openspec/specs/health-score/spec.md`

**Movimiento de cambio**:
- Método: `git mv` (fallback a `mv` plano si git mv falló sin cambios en source)
- Snapshot pre-movimiento: Tomada y conservada para readback de integridad
- Readback: Vacío (PASS) - carpeta archivada y snapshot pre-movimiento son idénticas
- Ruta verificada: `openspec/changes/a3-health-score/` -> `openspec/changes/archive/2026-09-09-a3-health-score/`
- Source ausente: Confirmado después del movimiento

**Declaración**: Ambas operaciones cumplieron el contrato de copia mecánica. Ningún artefacto fue leído y reescrito a través de generación del modelo. Las verificaciones de integridad (`diff -r` vacío) son la única evidencia de éxito.

---

## Ciclo SDD Cerrado

**Estado siguiente**: El cambio está listo para merge y push. El usuario autorizó el merge apilado a main y push después del archivo.

| Fase | Estado | Evidencia |
|------|--------|-----------|
| explore | HECHO | Mediciones ejecutadas por orquestador |
| proposal | HECHO | Propuesta aprobada por usuario |
| spec | HECHO | 12 requisitos, 25 escenarios |
| design | HECHO | D1-D21 documentadas |
| tasks | HECHO | 28 tareas, 3 PR apilados |
| apply | HECHO | 3 PR, 213 pruebas, 28/28 tareas |
| verify | HECHO | pass_with_warnings, 12/12 requisitos, 25/25 escenarios |
| archive | HECHO | Specs sincronizadas, cambio archivado, informe persistido |

**Próximo paso recomendado**: Merge de las tres ramas a main y push (usuario autorizado). Ninguna fase SDD adicional requerida.

---

## Auditoría y Trazabilidad

Este informe se persiste como:
- **Archivo**: `openspec/changes/archive/2026-09-09-a3-health-score/archive-report.md`
- **Engram**: Topic key `sdd/a3-health-score/archive-report`, tipo `architecture`

El informe es final y de solo lectura después del cierre. El cambio archivado no debe ser modificado; cualquier ajuste posterior debe registrarse como un nuevo cambio SDD.

---

**Archivado por**: sdd-archive phase executor  
**Fecha de archivo**: 2026-09-09  
**Línea base de código**: 1668f99 (rama feat/a3-pr3-health-validation, árbol limpio)
