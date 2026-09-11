# Informe de Archivo: script de limpieza automática de companies.csv (`a6-cleaning-script`)

**Archivado**: 2026-09-11  
**Cambio**: a6-cleaning-script  
**Estado**: Ciclo SDD completado  
**Destinatario de archivo**: `openspec/changes/archive/2026-09-11-a6-cleaning-script/`  
**Almacén de artefactos**: hybrid (archivos openspec + Engram proyecto 21-worky)

---

## Resumen Ejecutivo

El cambio a6-cleaning-script implementó un script en Python que lee `companies.csv` y `deals.csv`, detecta y corrige nulos en `mrr`, montos en USD y fechas DD/MM/YYYY, imputa el `mrr` faltante desde los deals según el ADR-002 con normalización de montos anuales (adenda 1), y genera un log auditable de cada corrección. Se entregaron dos PR apiladas hacia main:

- **PR1** (`feat/a6-pr1-clean-rules`): reglas de detección (fechas, moneda, nulos de MRR), log y comando `clean`
- **PR2** (`feat/a6-pr2-clean-impute`): imputación del ADR-002, contratos, equivalencia, idempotencia y goldens

Todas las tareas completadas (21/21), todos los requisitos del cambio cumplidos (11/11: data-cleaning) y todos sus escenarios con evidencia (33/33: 31 de la primera verificación + 2 nuevos + 1 modificado en la segunda), 304 pruebas pasadas (295 de la primera verificación del 2026-09-11 sobre el commit 9ca349c + 9 nuevas en el commit de corrección 1572021 que cierra las advertencias del verificador independiente). Verificación con `pass_with_warnings` sin bloqueadores críticos. Los dos PR pasaron por el ciclo de revisión nativa con rechazo del proveedor del modelo en ambos lineajes; la entrega se rige por política ordinaria del repositorio con esta verificación independiente como evidencia de ejecución.

---

## Autoridad de Estado Final

Este informe describe el estado del cambio en el cierre. Las fuentes de verdad se clasifican así (de mayor a menor autoridad):

1. **Artefacto `tasks.md` persistido**: completitud visible. Fuente: `openspec/changes/archive/2026-09-11-a6-cleaning-script/tasks.md`, 21 casillas [x], cero sin marcar.
2. **Hechos finales del aviso de lanzamiento**: desviaciones documentadas, cambios posteriores a las instantáneas intermedias. Fuente: estado.yaml y descripción de la sesión.
3. **Artefactos intermedios** (`apply-progress`, `verify-report`): descripción del estado en el momento de su escritura. Rango más bajo.

En donde las fuentes se contradicen, se cita la fuente más alta y el hecho se registra explícitamente.

---

## Especificación Sincronizada

**Dominio nuevo**: `data-cleaning` (sin especificación principal anterior)

| Dominio | Acción | Detalles |
|---------|--------|---------|
| data-cleaning | Creado | 11 requisitos ADDED, 33 escenarios, ~400 líneas spec.md |

**Ubicación de la especificación sincronizada**:
- `openspec/specs/data-cleaning/spec.md` (promovida)

**Copia mecánica verificada**: Sí. La especificación data-cleaning se copió con `cp` desde la delta y se verificó con `diff -r` idéntico (bytes idénticos). El diff readback fue vacío (PASS).

---

## Tareas Completadas

Todos los elementos de `tasks.md` están marcados completados. Conteo verificado:

- **Total de tareas**: 21 (1.1-1.11 de PR1, 2.1-2.10 de PR2)
- **Tareas completadas**: 21 (100%)
- **Tareas sin marcar**: 0

No hubo reconciliación de casillas obsoletas; todas las tareas completadas se marcaron oportunamente durante la aplicación.

**Fuente**: `openspec/changes/archive/2026-09-11-a6-cleaning-script/tasks.md`, líneas 1-67

---

## Informe de Verificación (Estado Final)

**Veredicto**: pass_with_warnings

| Métrica | Valor |
|---------|-------|
| Bloqueadores | 0 |
| Hallazgos críticos | 0 |
| Requisitos cumplidos | 11/11 (data-cleaning) |
| Escenarios cumplidos | 33/33 (31 en verificación inicial + 2 nuevos + 1 modificado en rerun) |
| Pruebas pasadas | 304 (295 de la primera verificación + 9 nuevas en el commit 1572021 que cierra las advertencias del verificador independiente) |
| Salida de prueba | determinista, idéntica en dos corridas de esta sesión sobre el dataset real |
| Goldens de A0-A5 | sin cambios (sha256 confirmado) |

**Commits verificados**: 
- Primera verificación: 9ca349c (rama feat/a6-pr2-clean-impute)
- Segunda verificación (rerun): a2b6bc5 (rama feat/a6-pr2-clean-impute)

**Conteos del log sobre el dataset real** (desde cleaning_log.json verificado en la segunda corrida):
- rows_in 678, deals_in 997, deals_matched 962
- missing_mrr detected 56 / corrected 28 / excluded_clones 28 / annualized_deals 3 / unresolved 0
- currency_to_mxn detected 22 / corrected 22
- date_format detected 31 / corrected 31 / ambiguous 12
- totals.corrections 84, exception_rows 112

**Warnings** (no bloqueantes):
- PR1 y PR2 no obtuvieron recibo de revisión nativa terminal: ambos lineajes experimentaron provider_safeguard_refusal (rechazo del proveedor del modelo en salvaguardas de Opus 5, estado.yaml). La entrega sigue política ordinaria del repositorio con esta verificación independiente como evidencia de ejecución.
- Las dos advertencias del verificador independiente en contexto fresco (sobre f76b863, después del cierre del PR 2) quedan cerradas: (1) montos nan/inf que esquivaban la tolerancia de no numérico → se agregó parse_finite_amount con math.isfinite (commit 1572021), (2) deal_id duplicado colapsado por diccionario → se cambió acumulación por fila de deal (commit 1572021). Ambos se documentaron en spec y diseño (commits a2b6bc5, f76b863) y se confirmaron con pruebas nuevas + probes manuales en la sesión de rerun.

**Fuente**: `verify-report.md` (rerun del 2026-09-11 sobre a2b6bc5); confirmado por estado final del lanzamiento

---

## Entregas Implementadas

Dos PR apilados hacia main:

### PR1: `feat/a6-pr1-clean-rules`

**Commits**: 47c30c8 (código), e24639d (docs sdd), dcb188c (corrección), 59242df (diseño y spec sincronizados)  
**Líneas de autoría**: 1,190  
**Base**: main

**Entregables**:
- `worky_engine/cleaning/__init__.py`: exportaciones
- `worky_engine/cleaning/rules.py`: `normalize_dates`, `convert_currency`, `detect_missing_mrr`
- `worky_engine/cleaning/runner.py`: `run_clean` y `_passthrough_if_clean` para idempotencia
- `worky_engine/quality/cleaning_contracts.py`: siete contratos (D4)
- `worky_engine/cli.py`: extensión con `cmd_clean`, su parser y resolución de rutas
- `scripts/clean_companies.py`: wrapper delgado
- `tests/test_cleaning_rules.py`, `test_cleaning_dataset_numbers.py` (parcial), `test_cleaning_idempotency.py` (parcial)

**Revisión**: Lineage review-a1ac5a1a71fed293 (riesgo alto). Resultado: sin recibo terminal, provider_safeguard_refusal en las cuatro capturas del linaje recuperado; entrega por política ordinaria (verificador independiente en contexto fresco dcb188c).

### PR2: `feat/a6-pr2-clean-impute`

**Commits**: 932222b (imputación y goldens), 50ac1a2 (docs), 7b23e6a (cierre de las tres advertencias del verificador del PR 1), b6f1077 (docs y spec), 0fa82cb (corrección de la revisión), f76b863 (docs, spec y diseño con los ajustes de nan/inf y deal_id duplicado)  
**Líneas de autoría**: 476 (+ 79 en los commits de cierre de advertencias)  
**Base**: feat/a6-pr1-clean-rules (tip 059e12a)

**Entregables**:
- `worky_engine/cleaning/impute.py`: `impute_mrr_from_deals` (réplica en pandas del ADR-002 con normalización 12x)
- `worky_engine/cleaning/rules.py`: extensión con `parse_finite_amount` para rechazar nan/inf (commit 1572021, cierre de las advertencias del verificador independiente)
- `worky_engine/cleaning/runner.py`: conexión de imputación, log completo, segunda pasada, idempotencia
- `worky_engine/quality/cleaning_contracts.py`: extensión con dos contratos más de imputación
- `tests/test_cleaning_imputation.py`, extensión de `test_cleaning_dataset_numbers.py`, `test_cleaning_equivalence.py`, extensión de `test_cleaning_idempotency.py`
- `outputs/clean/companies_clean.csv`, `cleaning_exceptions.csv`, `cleaning_log.json`, `cleaning_log.md` (goldens, 84 correcciones sobre 678 filas)
- `README.md`: actualización con paso 7 de la ruta rápida y salidas de A6

**Revisión**: Lineage review-0539e1f6aec41428 (riesgo alto). Resultado: sin recibo terminal, provider_safeguard_refusal en sucesor review-a6pr2-recovered; entrega por política ordinaria (verificador independiente en contexto fresco f76b863 + sdd-verify rerun).

---

## Cambios Posteriores a Verificación

### Corrección por Verificador Independiente (commits 1572021, a2b6bc5)

**Fuente**: Verificador independiente en contexto fresco sobre f76b863 (después del cierre del PR 2)

**Hallazgos y correcciones**:
1. **Montos nan/inf esquivaban la tolerancia de no numérico**: Agregada función `parse_finite_amount` que usa `math.isfinite` para rechazar nan, inf y -inf. Se agregaron 3 pruebas parametrizadas en `test_cleaning_rules.py` y un probe manual en la sesión de rerun.
2. **deal_id duplicado colapsado por diccionario**: Cambio de acumulación de montos por `deal_id` a acumulación por fila de deal (tuplas `(deal_id, amount_mxn)`). Se agregaron 2 pruebas en `test_cleaning_imputation.py` (deal_id duplicado con montos distintos y con montos iguales) y un probe manual de empresa unresolved.
3. **Especificación y diseño sincronizados**: Los dos nuevos escenarios ("mrr con nan o infinito", "deal_id duplicado") se documentaron en spec (a2b6bc5), y el escenario modificado ("deal con monto vacío o no numérico", ahora incluye nan/inf) se actualizó en diseño (f76b863).

**Conteo de pruebas post-corrección**: 304 pasadas (9 más que la primera verificación sobre 9ca349c). Las 9 nuevas son: 3 de parse_finite_amount (nan, inf, -inf) en test_cleaning_rules.py, 4 parametrizadas de montos de deal no finitos en test_cleaning_imputation.py, 2 de deal_id duplicado en test_cleaning_imputation.py.

**Ledger**: apply-a6-post-verify-fix settled passed (evidence sha256:96791bd28e754ec3d9cb75422bfb71cd30e899b2ef513289e75f19d6adebcb02).

---

## Especificación y Diseño en Archivo

La especificación y el diseño reflejan los estados finales después de los cambios post-verificación:

- **spec.md**: 11 requisitos, 33 escenarios (31 + 2 nuevos + 1 modificado); incluye `parse_finite_amount` y acumulación por fila de deal
- **design.md**: D1-D12 sincronizadas con el código final; D6 documenta `parse_finite_amount`, acumulación por fila, y el requisito de que un deal_id duplicado con montos distintos deje a la empresa unresolved

---

## Contenido del Archivo

- `proposal.md` ✅ (5,270 bytes)
- `specs/data-cleaning/spec.md` ✅ (sincronizada a openspec/specs/data-cleaning/spec.md)
- `design.md` ✅ (29,787 bytes, sincronizado post-verify)
- `tasks.md` ✅ (21/21 tareas, 15,127 bytes)
- `apply-progress.md` ✅ (17,847 bytes)
- `verify-report.md` ✅ (19,343 bytes, resultado rerun pass_with_warnings)
- `exploration.md` ✅ (10,762 bytes)
- `preproposal.yaml` ✅ (2,416 bytes)
- `state.yaml` ✅ (actualizado con fecha de archivo y next_recommended)

---

## Actualización de state.yaml

La sección `phases` se actualizó de:
```yaml
archive: blocked
next_recommended: sdd-archive
```

A:
```yaml
archive: done (2026-09-11)
next_recommended: integration de A6 y A5 a main
```

---

## Autoridad de Observación Engram

Esta sesión de archivo guardó los artefactos en modo hybrid:
- Archivo openspec: `openspec/specs/data-cleaning/spec.md`, `openspec/changes/archive/2026-09-11-a6-cleaning-script/` con todos sus archivos
- Engram: topic_key `sdd/a6-cleaning-script/archive-report` con esta entrada

**Observación IDs de Engram** (registrados para traceabilidad):
- proposal: (originalmente sdd/a6-cleaning-script/proposal)
- spec: (originalmente sdd/a6-cleaning-script/spec)
- design: (originalmente sdd/a6-cleaning-script/design)
- tasks: (originalmente sdd/a6-cleaning-script/tasks)
- verify-report: (originalmente sdd/a6-cleaning-script/verify-report)
- archive-report: (esta entrada)

---

## Ciclo SDD Completo

El cambio ha sido completamente planeado, especificado, diseñado, con tareas, implementado (21/21 tareas en dos PR apiladas), verificado (304 pruebas pasadas, pass_with_warnings) y archivado. Listo para integración a main según política ordinaria del repositorio.
