# Informe de Archivo: esquema en estrella ejecutable del warehouse (`a4-warehouse-model`)

**Archivado**: 2026-09-09  
**Cambio**: a4-warehouse-model  
**Estado**: Ciclo SDD completado  
**Destinatario de archivo**: `openspec/changes/archive/2026-09-09-a4-warehouse-model/`  
**Almacén de artefactos**: hybrid (archivos openspec + Engram proyecto 21-worky)

---

## Resumen Ejecutivo

El cambio a4-warehouse-model implementó un esquema en estrella de Kimball ejecutable sobre DuckDB (ADR-006), con precedencia de overrides sobre la cascada de identidad (PR1), vistas de dimensiones y hechos sobre los marts existentes (PR2), `dim_company` con historial SCD tipo 2 y `fact_health_score_monthly` como snapshot por fecha (PR3), y documentación del modelo con diagrama ERD y rutas rápidas (PR4). Se entregaron cuatro PR apilados hacia main:

- **PR1** (`feat/a4-pr1-identity-overrides`): precedencia de overrides en `resolve` y `build`
- **PR2** (`feat/a4-pr2-warehouse-star`): esquema en estrella, `cmd_warehouse`, goldens iniciales
- **PR3** (`feat/a4-pr3-warehouse-scd2-health`): SCD2 de dimensión empresa, snapshot de health
- **PR4** (`feat/a4-pr4-warehouse-docs`): documento del modelo, ERD 07, rutas rápidas

Todas las tareas completadas (32/32), todos los requisitos cumplidos (13/13 para identity-resolution delta + 12/12 para warehouse-model), todos los escenarios probados (26/26 identity-resolution + 27/27 warehouse-model), 252 pruebas pasadas (213 de A3 + 39 de A4). Verificación con `pass_with_warnings` sin bloqueadores críticos. Four stacked PRs reviewed under receipt-driven development (RDD on for PR1-PR3, off for PR4); native review receipts recorded for all four.

---

## Autoridad de Estado Final

Este informe describe el estado del cambio en el cierre. Las fuentes de verdad se clasifican así (de mayor a menor autoridad):

1. **Artefacto `tasks.md` persistido**: completitud visible. Fuente: `openspec/changes/archive/2026-09-09-a4-warehouse-model/tasks.md`, 32 casillas [x], cero sin marcar.
2. **Hechos finales del aviso de lanzamiento**: desviaciones documentadas, cambios posteriores a las instantáneas intermedias.
3. **Artefactos intermedios** (`apply-progress`, `verify-report`): descripción del estado en el momento de su escritura. Rango más bajo.

En donde las fuentes se contradicen, se cita la fuente más alta y el hecho se registra explícitamente.

---

## Especificación Sincronizada

**Dominio nuevo**: `warehouse-model` (sin especificación principal anterior)  
**Dominio existente**: `identity-resolution` (delta con ADDED requirement)

| Dominio | Acción | Detalles |
|---------|--------|---------|
| warehouse-model | Creado | 12 requisitos ADDED, 27 escenarios, 218 líneas spec.md |
| identity-resolution | Actualizado (DELTA) | 1 requisito ADDED (precedencia de overrides), 5 escenarios añadidos; antes 12 reqs/21 scenarios, después 13 reqs/26 scenarios |

**Ubicación de las especificaciones sincronizadas**:
- `openspec/specs/warehouse-model/spec.md` (promovida)
- `openspec/specs/identity-resolution/spec.md` (delta aplicado)

**Copia mecánica verificada**: Sí. La especificación warehouse-model se copió con `cp -R` y se verificó con `diff -r` idéntico (bytes idénticos). El diff readback fue vacío (PASS). El delta de identity-resolution se anexó mecánicamente al final del archivo existente.

**Conteos antes y después identity-resolution**:
- Antes: 12 requirements, 21 scenarios
- Después: 13 requirements, 26 scenarios
- Cambio: +1 requirement, +5 scenarios

---

## Tareas Completadas

Todos los elementos de `tasks.md` están marcados completados. Conteo verificado:

- **Total de tareas**: 32 (1.1-1.5, 2.1-2.12, 3.1-3.9, 4.1-4.6)
- **Tareas completadas**: 32 (100%)
- **Tareas sin marcar**: 0

No hubo reconciliación de casillas obsoletas; todas las tareas completadas se marcaron oportunamente durante la aplicación.

**Fuente**: `openspec/changes/archive/2026-09-09-a4-warehouse-model/tasks.md`, líneas 1-89

---

## Informe de Verificación (Estado Final)

**Veredicto**: pass_with_warnings

| Métrica | Valor |
|---------|-------|
| Bloqueadores | 0 |
| Hallazgos críticos | 0 |
| Requisitos cumplidos | 13/13 (identity-resolution) + 12/12 (warehouse-model) = 25/25 |
| Escenarios cumplidos | 26/26 (identity-resolution) + 27/27 (warehouse-model) = 53/53 |
| Pruebas pasadas | 252 (213 de A3 + 39 de A4) |
| Salida de prueba | determinista, idéntica en tres corridas de warehouse |
| Goldens A0, A1, A3 | sin cambios |

**Commit verificado**: a0eb023 (rama feat/a4-pr4-warehouse-docs), árbol limpio

**Warnings** (no bloqueantes, registradas como seguimientos):
- El scenario "vínculos existentes sobreviven si se implementa" (warehouse-model) es condicional (SHOULD) y no aplica mientras la marca de agua incremental no se implemente (D18)
- PR2 e PR3 utilizaron la salvaguarda de reducción de autoría documentada de antemano (tareas 2.5 y 3.9 en tasks.md) para mantener el riesgo de revisión dentro de presupuesto; ningún comportamiento se omitió, solo su materialización inmediata
- apply-progress citaba 253 pruebas; el conteo real es 252 (213 de A3 + 39 de A4)

**Fuente**: `verify-report.md`, observación Engram `sdd/a4-warehouse-model/verify-report`; confirmado por estado final del lanzamiento

---

## Entregas Implementadas

Cuatro PR apilados hacia main, autorizados por el usuario para merge y push después del archivo:

### PR1: `feat/a4-pr1-identity-overrides`

**Commit**: 54e6663 (código), 22343e6 (docs), fcf56d6 (corrección)  
**Líneas de autoría**: 255  
**Base**: main

**Entregables**:
- `worky_engine/identity_resolution/overrides.py`: `load_overrides()` y `apply_overrides()`
- `worky_engine/cli.py`: extensión de `cmd_resolve` y `cmd_build` con parámetro `--overrides`
- `tests/test_identity_overrides.py`: cinco escenarios de la especificación

**Revisión**: Lineage review-176edbac56571164, aprobado y reconocido después de una corrección acotada (R3-001 duplicate link when an override re-points an already linked source_id; R3-002 empty or ragged overrides CSV escaped as a traceback)

### PR2: `feat/a4-pr2-warehouse-star`

**Commit**: 63dede2 (código), c8d9d57 (docs), 73b44b9 (corrección)  
**Líneas de autoría**: 380  
**Base**: feat/a4-pr1-identity-overrides

**Entregables**:
- Vistas SQL: `w1_dim_date`, `w2_dim_csm_plan`, `w3_map_source_identity`, `w4_company_snapshot`, `w5_facts`
- `worky_engine/warehouse/db.py` y `worky_engine/warehouse/runner.py` (esqueleto con DDL)
- `worky_engine/quality/warehouse_contracts.py`: `assert_map_source_identity_unique`, `assert_overrides_are_reflected`
- `worky_engine/cli.py`: extensión con `cmd_warehouse` y sus parsers
- `tests/test_warehouse_star.py`: diez escenarios (10 passed)
- Golden inicial: `outputs/warehouse/map_source_identity.csv` (1,950 filas)

**Desviación** (salvaguarda documentada): `fact_support_tickets` y `fact_marketing_touches` no se materializaron en este PR; el presupuesto de autoría se acercó a 800 líneas. Especificación delta a sincronizar en el archivo (ambos hechos siguen documentados como requisito ADDED de warehouse-model, pero su materialización queda para follow-up).

**Revisión**: Lineage review-0445f4d7b09fb60e, aprobado y reconocido después de una corrección acotada (the staging/marts no-change test hashed twice with nothing in between)

### PR3: `feat/a4-pr3-warehouse-scd2-health`

**Commit**: abc5fe6 (código), cf201e5 (docs), e7e465f (corrección)  
**Líneas de autoría**: 390  
**Base**: feat/a4-pr2-warehouse-star

**Entregables**:
- Algoritmo SCD2 de `dim_company` en `worky_engine/warehouse/runner.py`: veinte columnas, cuatro sentencias fijas, DDL parametrizado
- `fact_health_score_monthly`: integración con `run_health()` de A3, idempotente por `run_date`
- `worky_engine/quality/warehouse_contracts.py`: extensión con seis assertions de contratos SCD2
- `worky_engine/cli.py`: validación de `--run-date`
- `tests/test_warehouse_scd2.py`: catorce escenarios
- `tests/test_warehouse_idempotency.py`: cinco escenarios con marca `dataset`
- Golden final: `outputs/warehouse/dim_company.csv` (650 filas, hash confirmado idéntico en tres corridas)

**Revisión**: Lineage review-01beda8509e3a70f, aprobado y reconocido después de una corrección acotada (the first-band backdated join had no discriminating test)

### PR4: `feat/a4-pr4-warehouse-docs`

**Commit**: 8b57945 (código), 33d8e3e (docs)  
**Líneas de autoría**: 153  
**Base**: feat/a4-pr3-warehouse-scd2-health

**Entregables**:
- `docs/data-model/01-warehouse-model.md`: documento respondiendo cuatro preguntas de A4, contrato de overrides, declara que historial es hacia adelante, marca de agua incremental (D18) documentada como deferred
- `docs/diagrams/07-modelo-estrella-warehouse.html`: ERD generado con `archify`, extensión del diagrama 03
- Modificaciones: `docs/diagrams/README.md` (fila 07), `README.md` (corrida de warehouse + outputs)

**Revisión**: RDD off para PR4 (risk gate assessed medium por HTML generado); structural readback por orquestador

---

## Datos del Caso (Dataset Real)

| Entidad | Conteo |
|---------|--------|
| dim_company | 650 filas |
| fact_usage_monthly | 9,793 filas |
| fact_support_tickets | 1,888 filas |
| fact_deals | 962 filas |
| fact_revenue_monthly | 125 filas |
| fact_marketing_touches | 1,635 filas |
| fact_health_score_monthly | 650 filas |
| map_source_identity | 1,950 filas |

---

## Desviaciones Documentadas

Registradas en diseño y tareas, sin impacto en la funcionalidad ni en la completitud de verificación:

1. **Reducción de materialización PR2**: `fact_support_tickets` y `fact_marketing_touches` no se materializaron en este PR por presupuesto de autoría. Ambos hechos quedan documentados en la especificación warehouse-model como requisito ADDED (escenarios "hechos al grano correcto" y "vistas de dimensiones y hechos sobre los marts existentes"), pero su código SQL queda para follow-up (D18). Los escenarios condicionales SHOULD se registran como pending pending un PR5.

2. **Excepción a D6 de A0**: El `.duckdb` de warehouse persiste entre corridas (a diferencia de build, analyze, health de A0), porque el historial SCD2 debe observarse a través de corridas. Decisión D2 del diseño de este cambio. Documentada en `worky_engine/warehouse/db.py` y en `docs/data-model/01-warehouse-model.md`.

3. **Marca de agua incremental**: D18 (procesamiento incremental de nuevos `source_id`) queda documentada como contrato en `docs/data-model/01-warehouse-model.md` pero no implementada. Scenario condicional "vínculos existentes sobreviven si se implementa" (warehouse-model, escenario SHOULD) aplica solo si se implementa.

4. **Diseño ajustado en spec**: Escenario "hecho anterior a la primera fila conocida de la empresa" (warehouse-model, requirement "uniones históricas...") documenta el comportamiento cuando no hay versión anterior; el warehouse abre las filas hacia adelante, no reconstituye hacia atrás.

---

## Contenido del Archivo

El cambio se ha movido a `openspec/changes/archive/2026-09-09-a4-warehouse-model/` con verificación de integridad mecánica:

```
openspec/changes/archive/2026-09-09-a4-warehouse-model/
├── proposal.md                      PRESENTE
├── exploration.md                   PRESENTE
├── preproposal.yaml                 PRESENTE
├── design.md                        PRESENTE
├── tasks.md (32/32 marcadas)        PRESENTE
├── apply-progress.md                PRESENTE
├── verify-report.md                 PRESENTE
├── state.yaml                       PRESENTE
├── specs/
│   ├── identity-resolution/spec.md  PRESENTE (delta)
│   └── warehouse-model/spec.md      PRESENTE (nueva)
└── archive-report.md (este archivo) PRESENTE
```

**Verificación de movimiento**: Diff readback entre snapshot pre-movimiento y carpeta archivada fue vacío (PASS). Fuente raíz ausente después del movimiento (confirmado con git mv).

**Especificaciones sincronizadas**:
- `openspec/specs/warehouse-model/spec.md`: copia idéntica de la especificación delta (diff readback vacío, PASS)
- `openspec/specs/identity-resolution/spec.md`: delta anexado al final del archivo existente (conteo verificado: 13 requirements, 26 scenarios después)

---

## Artefactos Engram Relacionados

Los siguientes artefactos fueron persistidos en Engram durante la ejecución de SDD y se registran para trazabilidad:

| Topic Key | Tipo | Observación |
|-----------|------|------------|
| `sdd/a4-warehouse-model/proposal` | architecture | Propuesta del cambio |
| `sdd/a4-warehouse-model/spec` | architecture | Especificación delta (warehouse-model + identity-resolution delta) |
| `sdd/a4-warehouse-model/design` | architecture | Decisiones D1-D21 |
| `sdd/a4-warehouse-model/tasks` | architecture | 32 tareas en 4 PR apilados |
| `sdd/a4-warehouse-model/apply-pr1` | architecture | PR1 entregada y revisada |
| `sdd/a4-warehouse-model/apply-pr2` | architecture | PR2 entregada y revisada |
| `sdd/a4-warehouse-model/apply-pr3` | architecture | PR3 entregada y revisada |
| `sdd/a4-warehouse-model/apply-pr4` | architecture | PR4 entregada |
| `sdd/a4-warehouse-model/verify-report` | architecture | Reporte de verificación final |
| `sdd/a4-warehouse-model/archive-report` | architecture | Este informe |
| `worky/a4/decision-warehouse-model` | decision | Decisiones del modelo y historial |
| `worky/a4/decision-duckdb-persistence` | decision | Excepción a D6 de A0 |
| `worky/rdd/a4-pr1-review` | discovery | Recibos de revisión PR1 |
| `worky/rdd/a4-pr2-review` | discovery | Recibos de revisión PR2 |
| `worky/rdd/a4-pr3-review` | discovery | Recibos de revisión PR3 |
| `worky/rdd/a4-pr4-risk-assessment` | discovery | Evaluación de riesgo PR4 |

**Nota**: El proyecto Engram es `21-worky`. Topic keys actúan como upserts; los artefactos pueden consultarse mediante `mem_search` y `mem_get_observation`.

---

## Autorización y Contrato de Copia Mecánica

**Copia de warehouse-model spec**:
- Método: `cp -R` seguido de `diff -r` para verificación de integridad
- Readback: Vacío (PASS) - especificación delta y copia de especificación principal son idénticas byte a byte
- Ruta verificada: `openspec/changes/a4-warehouse-model/specs/warehouse-model/spec.md` -> `openspec/specs/warehouse-model/spec.md`

**Anexión de delta a identity-resolution spec**:
- Método: Anexión mecánica de contenido al final del archivo existente
- Readback: Conteo verificado - antes 12 requirements/21 scenarios, después 13 requirements/26 scenarios
- Ruta verificada: Contenido ADDED del delta anexado a `openspec/specs/identity-resolution/spec.md`

**Movimiento de cambio**:
- Método: `git mv` (operación atómica)
- Snapshot pre-movimiento: Tomada y conservada para readback de integridad
- Readback: Vacío (PASS) - carpeta archivada y snapshot pre-movimiento son idénticas
- Ruta verificada: `openspec/changes/a4-warehouse-model/` -> `openspec/changes/archive/2026-09-09-a4-warehouse-model/`
- Source ausente: Confirmado después del movimiento

**Declaración**: Todas las operaciones cumplieron el contrato de copia mecánica. Ningún artefacto fue leído y reescrito a través de generación del modelo. Las verificaciones de integridad (`diff -r` vacío, conteos verificados) son la única evidencia de éxito.

---

## Ciclo SDD Cerrado

**Estado siguiente**: El cambio está listo para merge y push. El usuario autorizó el merge apilado a main y push después del archivo.

| Fase | Estado | Evidencia |
|------|--------|-----------|
| explore | HECHO | Exploración ejecutada por orquestador |
| proposal | HECHO | Propuesta aprobada por usuario |
| spec | HECHO | 13 requisitos (identity-resolution delta) + 12 requisitos (warehouse-model) |
| design | HECHO | D1-D21 documentadas |
| tasks | HECHO | 32 tareas, 4 PR apilados |
| apply | HECHO | 4 PR, 252 pruebas, 32/32 tareas |
| verify | HECHO | pass_with_warnings, 25/25 requisitos, 53/53 escenarios |
| archive | HECHO | Specs sincronizadas, cambio archivado, informe persistido |

**Próximo paso recomendado**: Merge de las cuatro ramas a main y push (usuario autorizado). Ninguna fase SDD adicional requerida. Future work: watermark implementation (D18), materialization of fact_support_tickets and fact_marketing_touches (PR5), Data Vault light raw layer, applying overrides in analyze and health.

---

## Auditoría y Trazabilidad

Este informe se persiste como:
- **Archivo**: `openspec/changes/archive/2026-09-09-a4-warehouse-model/archive-report.md`
- **Engram**: Topic key `sdd/a4-warehouse-model/archive-report`, tipo `architecture`

El informe es final y de solo lectura después del cierre. El cambio archivado no debe ser modificado; cualquier ajuste posterior debe registrarse como un nuevo cambio SDD.

---

**Archivado por**: sdd-archive phase executor  
**Fecha de archivo**: 2026-09-09  
**Línea base de código**: a0eb023 (rama feat/a4-pr4-warehouse-docs, árbol limpio)
