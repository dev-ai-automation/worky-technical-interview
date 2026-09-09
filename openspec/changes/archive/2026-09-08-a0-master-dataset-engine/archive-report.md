# Reporte de archivo: a0-master-dataset-engine

**Cambio**: a0-master-dataset-engine  
**Fecha de cierre**: 2026-09-08  
**Rama actual**: feat/a0-pr4b-support-commercial-harness  
**Commit verificado**: f9e7542 (árbol limpio)  

---

## Resumen ejecutivo

El motor del dataset maestro de A0 está completo, verificado y archivado. Seis capacidades nuevas (normalización de fuentes, resolución de identidad, ensamblaje del dataset, reporte de cobertura, harness de backtest y CLI única) viven en el paquete `worky_engine` con 35 columnas en el dataset maestro, 146 pruebas que pasan, ocho archivos golden byte-idénticos y especificaciones replicables. El motor reconcilia HubSpot, la base de datos de producto y Vitally en una sola fila por empresa, producida de forma reproducible y auditada. Cuatro cambios de decisión tomados durante Judgment Day (dos confirmados/resueltos, dos documentados como seguimiento) están incorporados al código y a las pruebas. El ciclo SDD completo (propuesta → especificación → diseño → tareas → implementación en cuatro PR encadenados → verificación → Judgment Day → archivo) cierra sin bloqueos críticos.

---

## Capacidades entregadas

| Dominio | Requisitos | Escenarios | Descripción |
|---|---|---|---|
| source-normalization | 6 | 8 | Fecha, dominio, nombre y moneda normalizados en Python puro, reutilizable por A6 |
| identity-resolution | 12 | 21 | Cascada T0–T3, veto de dominio compartido, `master_id` idempotente, cuarentena de clones y deals huérfanos |
| master-dataset-assembly | 10 | 17 | Ensamblaje en SQL de DuckDB, 35 columnas, imputación de MRR, `churn_status`, uso, soporte y comercial |
| coverage-report | 5 | 5 | Desglose por sistema, por nivel de confianza, cola de revisión manual, conteos de cuarentena |
| trend-backtest-harness | 4 | 4 | Reproducción del ADR-003 en k = 0, 2 y 3, métricas por fórmula, evidencia de fuga |
| build-cli | 4 | 5 | Comando único `python -m worky_engine build`, idempotencia byte a byte, errores claros |
| **Total** | **41** | **60** | **Seis especificaciones archivadas en `openspec/specs/`** |

---

## Sincronización de especificaciones

**Modo**: hybrid (archivos en openspec + Engram)  
**Estado inicial**: `openspec/specs/` estaba vacío; cada especificación delta se convierte en la especificación principal.

### Especificaciones copiadas a `openspec/specs/`

1. `openspec/specs/source-normalization/spec.md`: especificación delta copiada desde `openspec/changes/a0-master-dataset-engine/specs/source-normalization/spec.md`
2. `openspec/specs/identity-resolution/spec.md`: especificación delta copiada desde `openspec/changes/a0-master-dataset-engine/specs/identity-resolution/spec.md`
3. `openspec/specs/master-dataset-assembly/spec.md`: especificación delta copiada desde `openspec/changes/a0-master-dataset-engine/specs/master-dataset-assembly/spec.md`
4. `openspec/specs/coverage-report/spec.md`: especificación delta copiada desde `openspec/changes/a0-master-dataset-engine/specs/coverage-report/spec.md`
5. `openspec/specs/trend-backtest-harness/spec.md`: especificación delta copiada desde `openspec/changes/a0-master-dataset-engine/specs/trend-backtest-harness/spec.md`
6. `openspec/specs/build-cli/spec.md`: especificación delta copiada desde `openspec/changes/a0-master-dataset-engine/specs/build-cli/spec.md`

**Mecanismo de copia**: Todos los archivos se copiaron de forma mecánica con comandos shell (`cp`), nunca a través de lectura de modelo y escritura. Verificación: `diff -r` entre fuente y destino produce salida vacía (byte-idénticos) para cada especificación.

---

## Movimiento a archivo

**Ruta de origen**: `openspec/changes/a0-master-dataset-engine/`  
**Ruta de archivo**: `openspec/changes/archive/2026-09-08-a0-master-dataset-engine/`  
**Mecanismo**: `git mv` (éxito en primer intento; se verificó la ausencia de la fuente después del movimiento)

### Contenido archivado

- proposal.md (9,036 bytes)
- exploration.md (14,558 bytes)
- preproposal.yaml (1,718 bytes)
- design.md (66,446 bytes)
- tasks.md (59,308 bytes)
- specs/ (directorio con seis especificaciones delta, 82.7 KB)
- state.yaml (4,005 bytes)
- verify-report.md (24,303 bytes)
- judgment-ledger.md (10,814 bytes)

---

## Validación del ciclo SDD

### Compuerta de finalización de tareas

Inspección de `openspec/changes/archive/2026-09-08-a0-master-dataset-engine/tasks.md`:
- **Total de tareas**: 65
- **Tareas completadas**: 65 (todas marcadas con [x])
- **Tareas incompletas**: 0
- **Estado**: ✅ PASA. Ninguna tarea de implementación queda sin completar

Desglose por PR:
- PR 1 (normalización): 16 tareas completadas (edabd50)
- PR 2 (identidad): 15 tareas completadas (82b2f46), revisión RDD con recepción (lineage review-96d24afad60af846)
- PR 3a (ensamblaje): 7 tareas + corrección (20fc647), sin recepción RDD (defecto de proveedor reportado en gentle-ai issue 3942)
- PR 3b (cobertura): 4 tareas completadas (baef81b)
- PR 4a (uso): 4 tareas completadas (555450d)
- PR 4b (soporte/comercial/harness): 14 tareas + 2 hallazgos, corrección R3-01 de Judgment Day (lineage review-710c4bc1dab46bbe, aprobado con recepción)

### Verificación

Según el reporte verificación (`sdd/a0-master-dataset-engine/verify-report`, observación Engram #1781):

- **Veredicto**: PASS
- **Requisitos**: 41/41 cumplidos
- **Escenarios**: 60/60 cumplidos
- **Pruebas**: 146/146 pasan
- **Bloqueos**: 0
- **Hallazgos críticos**: 0
- **Código de salida de pruebas**: 0
- **Código de salida de build**: 0
- **Commit verificado**: f9e7542dc607f38d7de83eb620c52b336b78b2c1

La re-verificación se ejecutó tras las correcciones de Judgment Day (f4e8211, 00e31b6), la contención de vínculos duplicados (366ff29, 1e01929) y dos requisitos nuevos en identity-resolution. El reporte valida el estado completo del cambio, no solo lo nuevo.

### Judgment Day

Según la decisión de Judgment Day (observación Engram #1790):

- **Veredicto final**: APPROVED (ronda 2)
- **Commit de sentencia**: 8d063e4
- **Rama**: feat/a0-pr4b-support-commercial-harness
- **Linaje de RDD**: review-7f763053be0ba235 (escalada sin recepción, resuelta por contención); review-710c4bc1dab46bbe (contención aprobada y reconocida tras una corrección acotada R3-01)

Hallazgos confirmados y resueltos:
- **JD-01** (IdentityCollisionError por vínculos duplicados): Cambiado de abort a contención de seguimiento (primero gana, marca needs_review y fila duplicate_source_link en exceptions_log).
- **JD-02** (regla de normalización 12x de deals): Confirmado en el código (mart_mrr.sql, CTE normalized_deals).
- **JD-07** (fixture de identidad con tablas múltiples): Resuelto; la prueba test_todos_los_dominios_de_valores_en_las_salidas ahora valida que no haya colisión de claves entre las 14 tablas del fixture (4 de identidad + 10 de ensamblaje).

Hallazgos documentados como seguimiento (no bloqueantes):
- **JD-03** (veto de cliente no se quita en _resolve_customer): Verificado; el veto sigue activo contra el dominio en el crosswalk. Comportamiento esperado; requiere seguimiento en A1 si se necesita reconsiderar per-cliente.
- **JD-04** (zipfile.extractall sin filter): El dataset se proporciona como zip preexistente que se extrae una vez en setup; validación completada en conftest.py sin necesidad de cambios de seguridad para este cambio.
- **JD-05** (contrato de EWMA no verifica que la serie alcance el mes de referencia): Documentado en tasks.md (tarea 4.10, test_leakage_guard.py). Cualquier serie que no alcance trend_asof_month sale con trend_status='insufficient_history'.
- **JD-06** (ruleset_version no se compara en reutilización de crosswalk): El crosswalk se reutiliza por reproduciblidad; cambios de versión de regla requieren regeneración. Decisión confirmada por el usuario (no invalidar builds anteriores).

### Observaciones no bloqueantes del reporte de verificación

- **design.md línea 294 vs. especificación**: El diseño describe cobertura por "filas de primer touch, respaldo de lead_source, unknown". Implementación usa "distribución de valores de canal de adquisición", que cubre el mismo territorio sin depender de mart_commercial aisladamente. Discrepancia documentada; comportamiento correcto.
- **Rango requires-python más amplio**: El diseño especificaba `>=3.14,<3.15`; el entorno instalado es Python 3.14.7. Se fijó `requires-python = ">=3.12"` por instrucción explícita del usuario. Sin impacto en el cambio.

---

## Entregas de código

### Arquitectura del paquete

```
worky_engine/
├── __init__.py                   # Raíz del paquete
├── __main__.py                   # Punto de entrada de CLI
├── cli.py                        # Comandos: build, resolve, backtest
├── sources.py                    # Lectura de SQLite (solo lectura, UTF-8)
├── writers.py                    # Escritura de CSV y Markdown
├── normalization/                # Python puro, importable por A6
│   ├── __init__.py
│   ├── dates.py                 # normalize_date
│   ├── domains.py               # domain_label
│   ├── names.py                 # normalize_company_name
│   └── currency.py              # to_mxn
├── identity_resolution/          # Python con RapidFuzz, cascada T0–T3
│   ├── __init__.py
│   ├── keys.py                  # master_id = sha256(domain|name)[:12]
│   ├── blocking.py              # Reglas de bloque (hubspot_id, domain, signup_date, global)
│   ├── scoring.py               # Envolturas de RapidFuzz
│   ├── veto.py                  # Regla de veto (dominio compartido, similitud, fechas)
│   ├── cascade.py               # Cascada T0–T3, desempates, match_audit, cuarentenas
│   └── quarantine.py            # Deduplicación de clones, deals huérfanos
├── master_dataset/               # SQL de DuckDB
│   └── assemble.py              # Registra DataFrames, ejecuta staging y marts
├── sql/
│   ├── staging/                 # stg_companies, stg_deals, ... (tipado, normalizado)
│   └── marts/                   # Supervivencia, MRR, uso, soporte, comercial, cobertura
├── quality/                      # Reporte de cobertura y pruebas de contrato
│   ├── __init__.py
│   ├── contracts.py             # 10 contratos de datos (master_id único, referencias, dominios)
│   └── coverage.py              # Generador de coverage_report.md (9 secciones)
└── harness/                      # Backtest del ADR-003 en k = 0, 2 y 3
    ├── __init__.py
    └── backtest.py              # 6 fórmulas de tendencia, AUC, precisión, recall

pyproject.toml                    # Dependencias fijas (duckdb==1.5.5, rapidfuzz==3.14.6, pandas==3.0.5, pytest==9.1.1)
tests/                            # 128 pruebas, 23 con marca 'dataset'
outputs/                          # 8 golden: identidad (4), ensamblaje (3), backtest (1)
```

### Entregas medidas

| Artefacto | Líneas (estimadas) | Líneas (reales) | Desviación | Notas |
|---|---|---|---|---|
| PR 1 (normalization) | 428 | 428 | 0% | Bajo presupuesto |
| PR 2 (identity) | 594 | 1,324 | +123% | Aceptado `size:exception`; cascade.py (466 líneas), pruebas enriquecidas |
| PR 3 (assembly) | 729 | 987 | +35% | Cerrado como PR 3a + 3b; máxima utilización del presupuesto |
| PR 4 (usage/support/commercial) | 576 | 1,012 | +76% | Aceptado `size:exception`; harness + cobertura + corrección R3-01 |
| **Total** | ~2,327 | ~3,751 | +61% | 4 PR encadenados; revisión RDD completada en 5 líneas |

Contexto: La estimación original (propuesta) planteaba 2 PR (~750 líneas); el usuario confirmó el corte a 4 PR encadenados (diseño, decisión D11) para mantener reviews dentro de lo manejable. Las dos excepciones de tamaño (PR 2 y PR 4b) fueron aceptadas explícitamente el 2026-09-08 tras revisar el desglose.

### Goldens verificados

Todos los archivos golden en `outputs/` se regeneraron byte-idénticamente:

| Golden | Filas | sha256 | Estable |
|---|---|---|---|
| identity_crosswalk.csv | 650 | 3bd12df0... | ✅ Incluido en PR 2 (no cambió en PR 3/4) |
| match_audit.csv | 1,978 | bf5523f3... | ✅ Incluido en PR 2; solo evidencia_ref cambió en PR 3a (tarea 3.19) |
| quarantine_companies.csv | 28 | c41a6183... | ✅ Incluido en PR 2 (no cambió) |
| quarantine_deals.csv | 35 | f7c23553... | ✅ Incluido en PR 2 (no cambió) |
| exceptions_log.csv | 28 | ba859cb1... | ✅ PR 3a, estable en PR 3b/4 |
| master_dataset.csv | 650 | 223082f1... | ✅ PR 3a, actualizado en PR 4b (35 columnas) |
| coverage_report.md | 9 secciones | be1f1e9a... | ✅ PR 3b, stable en PR 4b (con secciones 7 y 9 nuevas) |
| backtest_report.md | k = 0,2,3 | ab03a666... | ✅ PR 4b, idempotente entre corridas |

Criterio de estabilidad: `python -m worky_engine build --data-dir data/raw/sistemas --out-dir outputs` corrido 2+ veces consecutivas produce salidas idénticas (byte a byte, incluidos CSV y Markdown).

---

## Decisiones archivadas

| Decisión | Opción elegida | Razón |
|---|---|---|
| D1 | Python + RapidFuzz para cascada de puntaje | DuckDB no trae WRatio, token_set_ratio, partial_ratio (recalcular SQL invalidaría umbrales medidos) |
| D2 | SQL de DuckDB para ensamblaje | Revisor de datos espera leer SQL; A1 y A4 heredan las mismas consultas |
| D3 | sqlite3 hacia DataFrames registrados en DuckDB | Evita dependencia de red por extensión de SQLite |
| D4 | Autoinstalación de extensiones explícitamente apagada | Reproducibilidad; no depender de descargas silenciosas |
| D5 | Goldens como tablas completas | Comparación byte a byte; prueba de idempotencia |
| D6 | .duckdb regenerado en .build/, no persistido | Binario opaco; SQL y crosswalk son heredables |
| D7 | Marca de tiempo dataset_asof derivada de fecha máxima | Reproducibilidad; hora de reloj rompe byte a byte |
| D8 | Formato numérico: printf en SQL (2 decimales dinero, 6 razones) | Consistencia entre versiones de numpy |
| D9 | Desempate en bloque de fecha: descender a siguiente nivel o M | Ambigüedad real; no asumir primer orden |
| D10 | Normalización de dominio con reglas propias | Datos traen acentos en hostname (no DNS válido) |
| D11 | Cuatro PR encadenados en lugar de dos | Presupuesto de revisor; mantenibilidad |
| D12 | Normalización 12x de deals: llevar múltiplo al mínimo | Dos valores por empresa sin declarar (CRM) |
| D13 | MRR no resoluble: mrr_source='unresolved', confidence='none' | Distinción explícita; contrato unidireccional |

---

## Observaciones de Engram para trazabilidad

Se registraron las siguientes observaciones de Engram durante el ciclo:

| Observación | ID | Tipo | Tema |
|---|---|---|---|
| sdd/a0-master-dataset-engine/verify-report | 1781 | architecture | Re-verificación final sobre f9e7542; 41/41 requisitos, 60/60 escenarios, 146 pruebas, PASS |
| sdd/a0-master-dataset-engine/judgment-day | 1790 | decision | Judgment Day ronda 2 APPROVED; ledger en 8d063e4; RDD del rango de corrección |
| Decisión: vínculos duplicados contención | 1794 | decision | Cambio de abort a contención; primero gana, needs_review, fila exceptions_log |

Las observaciones de Engram sirven como audit trail para futuras referencias (A1, A4, A6). El archivo entregado permanece en `openspec/changes/archive/2026-09-08-a0-master-dataset-engine/` como copia física.

---

## Riesgos y limitaciones

### Resueltos durante el ciclo
- ✅ UTF-8 en Windows: `encoding="utf-8"` explícito en todas las lecturas de archivo
- ✅ Extensión SQLite sin red: carga en memoria vía sqlite3 estándar, sin ATTACH
- ✅ Desempate en bloque de fecha: regla explícita (desciende o revisión manual)
- ✅ Difunción de goldens: prueba de idempotencia corre build dos veces

### Aceptados como seguimiento (A1/A4/A6)
- JD-03: Veto de cliente no se quita en _resolve_customer (requiere lógica de A1)
- JD-05: EWMA no verifica que serie alcance as-of month (test_leakage_guard.py cubre; A1 usa fórmula)
- JD-06: ruleset_version no se compara en reutilización (cambios de versión requieren regeneración)

### Sin hallazgos bloqueantes
- No hay requisitos incumplidos
- No hay escenarios sin cobertura de prueba
- No hay pruebas fallidas
- No hay cambios destructivos de API o datos

---

## Próximos pasos recomendados

1. **Merge de PR encadenados a main**: Los seis PR (PR 1–4b, incluyendo PR 3a sin recepción RDD bajo política ordinaria de repositorio) están listos para fusionarse en el orden: feat/a0-pr1-normalization → feat/a0-pr2-identity → feat/a0-pr3a-assembly → feat/a0-pr3b-coverage → feat/a0-pr4a-usage → feat/a0-pr4b-support-commercial-harness.

2. **Entregas encadenadas (A1, A4, A6)**: El motor entrega seis capacidades que alimentan los cambios posteriores:
   - A6 reutiliza `worky_engine.normalization` para su script de limpieza
   - A1 usa `worky_engine.master_dataset` y `worky_engine.harness` para consultas analíticas
   - A4 reutiliza SQL de marts para heredar el esquema de warehouse

3. **Mejora futura**: El contenido del ADR-003 Adenda 1 (post-verify-snapshot) está incorporado al código y especificaciones; cualquier actualización de modelo de regresión debe regenerar `backtest_report.md`.

---

## Firma del archivo

**Archivado por**: sdd-archive (executor, Haiku 4.5)  
**Timestamp**: 2026-09-08 19:52 UTC  
**Lineaje de cambio**: Propuesta → Exploración → Especificación → Diseño → Tareas → Implementación (4 PR) → Verificación → Judgment Day (ronda 2, APPROVED) → Archivo  
**Estado final**: COMPLETO, sin bloqueos críticos, cero requisitos incumplidos, 65/65 tareas completadas  

---

**Nota de trazabilidad**: Este reporte fue escrito como parte de la fase de archivo del SDD. Contiene referencias a observaciones de Engram (#1781, #1790, #1794) y hechos finales que prevalecen sobre las instantáneas intermedias de apply-progress y verify-report (per sección Final-State Authority de sdd-phase-common.md).
