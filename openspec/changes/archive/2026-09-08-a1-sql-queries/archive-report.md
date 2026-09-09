# Reporte de archivado: a1-sql-queries

**Cambio**: a1-sql-queries  
**Dominio**: sql-analysis (siete respuestas de A1 sobre la sábana de A0)  
**Fecha de archivado**: 2026-09-08  
**Estado final**: Aprobado y archivado

## Resumen ejecutivo

El cambio a1-sql-queries se ha completado, verificado y archivado. Las tres ramas encadenadas (feat/a1-pr1-analyze-runner, feat/a1-pr2-cohort-attribution, feat/a1-pr3-exceptions-report) se entregaron con recibos RDD aprobados. El comando `analyze` ejecuta las siete respuestas de SQL que pide A1 sobre la sábana de A0, materializa seis CSV más `analysis_exceptions.csv` y `report.md`, y se puede correr sin depender de un `build` previo. El dominio sql-analysis se sincronizó a las especificaciones principales con 10 requisitos y 22 escenarios.

## Tareas completadas

| Métrica | Valor |
|---|---|
| Tareas totales (tasks.md) | 32 |
| Tareas completadas | 32 |
| Tareas incompletas | 0 |
| Requisitos del spec | 10/10 |
| Escenarios del spec | 22/22 |
| Pruebas de suite | 179 passed |

Todos los 32 elementos de checklist en `tasks.md` se marcaron como completados durante la aplicación. Las 11 tareas del PR 1 (1.1 a 1.11) incluyen el corredor de análisis, el subcomando `analyze` y las tres primeras respuestas (A1.1, A1.2, A1.5). Las 9 del PR 2 (2.1 a 2.9) agregan el último touch y las dos respuestas siguientes (A1.3, A1.4). Las 12 del PR 3 (3.1 a 3.12) incluyen los tickets negativos, el reporte y el diseño de escalamiento (A1.6, A1.7).

**Nota de reconciliación**: `state.yaml` y `apply-progress.md` citan "33/33 tareas" en el cierre del PR 3, pero el conteo real de casillas en `tasks.md` es 32 (todas marcadas). Esta es una inconsistencia de bitácora entre documentos, no una tarea sin marcar. El archivo de tareas es la fuente de verdad: 32 completadas, 0 incompletas.

## Especificaciones sincronizadas

| Dominio | Acción | Detalles |
|---|---|---|
| sql-analysis | Creado (nuevo dominio) | 10 requisitos ADDED, 22 escenarios, copiado como especificación principal |

La especificación delta en `openspec/changes/a1-sql-queries/specs/sql-analysis/spec.md` se copió mecánicamente a `openspec/specs/sql-analysis/spec.md`. Es la fuente de verdad para futuras iteraciones del análisis SQL.

## Contenido del archivo

| Artefacto | Estado | Detalles |
|---|---|---|
| proposal.md | ✅ Presente | Propuesta del cambio, Engram sdd/a1-sql-queries/proposal |
| design.md | ✅ Presente | Diseño con 15 decisiones (D1 a D15), Engram sdd/a1-sql-queries/design |
| specs/sql-analysis/spec.md | ✅ Presente | Especificación, 10 requisitos, 22 escenarios, Engram sdd/a1-sql-queries/spec |
| tasks.md | ✅ Presente | 32 tareas completadas (11+9+12 por PR), Engram sdd/a1-sql-queries/tasks |
| apply-progress.md | ✅ Presente | Bitácora de aplicación de PR 1, 2 y 3, Engram sdd/a1-sql-queries/apply-progress |
| verify-report.md | ✅ Presente | Verificación pass_with_warnings, Engram sdd/a1-sql-queries/verify-report |

Todos los artefactos de cambio están presentes en el directorio archivado.

## Estado de entrega

### Ramas entregadas (receipt-driven development activo)

| Rama | Commit | Lineage | Resultado |
|---|---|---|---|
| feat/a1-pr1-analyze-runner | f4337c9 | review-8bc3a88cddf2ccca | Aprobado y reconocido tras corrección R3-a1-02 (orden numerico de drop_relative) |
| feat/a1-pr2-cohort-attribution | ce5297f | review-19c5d811de3c8e83 | Aprobado y reconocido en primera pasada |
| feat/a1-pr3-exceptions-report | 728d9a0 | review-effc98586c8e243b | Aprobado y reconocido tras corrección R3-fetchone-unpack (dataset_metadata) |

Las tres ramas se apilaron hacia `main`, cada una sobre la anterior. Todos los recibos de revisión (lineage IDs) están registrados en `state.yaml`. El cambio está listo para merge sin cambios adicionales.

### Verificación final

La corrida de verificación (commit 2593273f4085b95cdd940d97e10f35a354f386da) confirmó:

- **Pruebas**: 179 passed / 0 failed / 0 skipped
- **Idempotencia de analyze**: Pasada. Dos corridas seguidas generan salidas byte-identicas a la copia commiteada
- **A0 sin cambios**: Pasada. Los ocho goldens de `outputs/` (A0, read-only) quedan identicos antes y despues de correr `analyze`
- **Verdedicto**: PASS WITH WARNINGS (10/10 requisitos, 22/22 escenarios, 0 critical findings)

Tres advertencias en el reporte de verificación se marcaron como seguimientos futuros, no bloqueadores:

1. La ruta de error de analyze para "falta una dependencia" no tiene prueba dedicada a traves de `analyze` (comparte código con `build` ya probado, bajo riesgo)
2. El cambio de canal ganador de A1.4 no tiene prueba cuando si difieren (se verifica manualmente en la sesion de verificación, bajo riesgo)
3. La clausula "nulo en promedios" de A1.6 no tiene computo que probar (se satisface por ausencia en el alcance actual, documentacion preventiva)

Una sugerencia se incluyó en el cierre de verificación: sincronizar la cifra de "33/33 tareas" en `state.yaml` y `apply-progress.md` con el conteo real de 32 en `tasks.md` (hecho en el archivado).

## Mediciones del dataset real

El cambio se verificó sobre el dataset de caso (systems SQLite con datos 2024-08 como cierre):

| Ítem | Métrica | Valor |
|---|---|---|
| A1.1 | Empresas activas | 561 |
| A1.1 | MRR CRM | 13,819,780.50 MXN |
| A1.1 | MRR con imputados | 16,223,225.50 MXN |
| A1.2 | Cuentas churned | 89 |
| A1.2 | Con ventanas traslapadas | 33 (Adenda 1 del ADR-004 corrige de 30 a 33) |
| A1.2 | Mediana de caída relativa | 0.538 |
| A1.3 | Cohortes | 30 |
| A1.3 | Celdas totales | 120 (30 cohortes × 4 valores de k) |
| A1.3 | Celdas censuradas | 15 |
| A1.4 | Deals atribuidos (ambos modelos) | 962 |
| A1.4 | Canal ganador | Paid Search en primer y último touch (sin cambio entre modelos) |
| A1.4 | Deals en no_prior_touch | 326 |
| A1.5 | Deals huerfanos | 35 |
| A1.5 | Monto (unidades mezcladas) | 667,251.00 MXN |
| A1.6 | Tickets con horas negativas | 48 (10 Open, 38 Closed) |
| A1.6 | Mediana valor absoluto (negativos) | 13.5 horas |
| A1.6 | Mediana valor absoluto (positivos) | 12.2 horas |

Todas las mediciones coinciden con lo publicado en `outputs/analysis/report.md`. El ADR-004 ya se corrigió con Adenda 1 (2026-09-08) documentando la cifra real de windows_overlap.

## Deviaciones documentadas

- **AnalysisResult gana `dataset_asof` y `ruleset_version`**: El diseño original describía solo `outputs` y `sql_text`. Se agregaron estos dos campos porque `report.py` no abre conexion ni lee archivos (decisión D13), así que el corredor los debe pasar. Extension menor, documentada en `apply-progress.md`.

- **DDL de A1.7 con MERGE INTO en vez de DELETE+INSERT**: El diseño ilustraba con DELETE seguido de INSERT. Se cambió a MERGE INTO por instruccion explicita de la fase apply. El DDL sigue marcado como ilustrativo y no ejecutable.

- **report.py mide 336 líneas, no ~180 estimadas**: Subestima del diseño. El total de autoría del PR 3 (700 líneas) sigue dentro del presupuesto de 800 sin cambios de alcance.

- **Canal ganador no cambia sobre dataset real**: El diseño anticipaba que podria cambiar entre modelos. Se publico la medida: Paid Search en ambos.

Ninguna desviacion rompe un requisito. Todas están documentadas en `apply-progress.md`.

## Observaciones de Engram para traceabilidad

El cambio se registró en Engram con las siguientes observaciones (topic keys):

- `sdd/a1-sql-queries/proposal`: Propuesta aprobada
- `sdd/a1-sql-queries/spec`: Especificación del dominio sql-analysis
- `sdd/a1-sql-queries/design`: Diseño con D1 a D15
- `sdd/a1-sql-queries/tasks`: 32 tareas, todas completadas
- `sdd/a1-sql-queries/apply-progress`: Bitácora de los tres PR
- `sdd/a1-sql-queries/verify-report`: Verificación pass_with_warnings
- `sdd/a1-sql-queries/archive-report`: Este reporte
- `worky/a1/decision-sql-definitions`: Decisiones de ADR-004
- `worky/rdd/a1-pr1-review`: Recibo RDD del PR 1 (lineage review-8bc3a88cddf2ccca)
- `worky/rdd/a1-pr2-review`: Recibo RDD del PR 2 (lineage review-19c5d811de3c8e83)
- `worky/rdd/a1-pr3-review`: Recibo RDD del PR 3 (lineage review-effc98586c8e243b)

## Estado del archivo

**Carpeta archivada**: `openspec/changes/archive/2026-09-08-a1-sql-queries/`

El contenido del cambio se movió con git mv desde `openspec/changes/a1-sql-queries`. La verificación mecanica (diff -r sobre snapshot pre-movimiento vs. destination post-movimiento) confirmó byte-identidad exacta. El directorio activo ya no contiene este cambio.

**Especificación principal**: `openspec/specs/sql-analysis/spec.md`

La especificación delta se copió mecánicamente. Diff readback confirmo byte-identidad. Esta es la fuente de verdad para futuras iteraciones.

## Siguiente paso

El cambio completo está listo para merge en `main` desde las tres ramas apiladas. Aplicar los tres merge con confirmacion del usuario, en el orden:

1. Mergear `feat/a1-pr1-analyze-runner` a `main`
2. Mergear `feat/a1-pr2-cohort-attribution` a `feat/a1-pr1-analyze-runner`
3. Mergear `feat/a1-pr3-exceptions-report` a `feat/a1-pr2-cohort-attribution`
4. Confirmar que los tres están en `main`

El ciclo de SDD (explore, proposal, spec, design, tasks, apply, verify, archive) se ha completado exitosamente para el cambio a1-sql-queries.
