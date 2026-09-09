# Una sola fila por empresa: el caso técnico de Worky, reproducible de punta a punta

Este repositorio resuelve el caso "Business Operations & Data Specialist" de Worky. Parte de tres sistemas que no se hablan entre sí (HubSpot, la base de producto y Vitally) y construye un dataset maestro con una fila por empresa, auditado y reproducible byte a byte. Sirve a dos lectores: a quien evalúa el caso, que puede correrlo y leer cada decisión con su evidencia; y a quien lo mantiene, que encuentra el contrato de cada pieza antes que el código.

## Ruta rápida

Requiere Python 3.12 o superior. El dataset del caso (`fundation-docs/dataset_caso_v3.zip`) ya está en el repositorio; el enunciado en PDF no se versiona.

1. Instala el motor y las herramientas de prueba:

   ```bash
   pip install -e ".[dev]"
   ```

2. Construye el dataset maestro. El comando extrae el zip a `.build/dataset/sistemas` la primera vez:

   ```bash
   python -m worky_engine build --data-dir fundation-docs --out-dir outputs
   ```

3. Comprueba que el resultado es idéntico al versionado y que las 146 pruebas pasan:

   ```bash
   git status --short outputs
   python -m pytest -q --data-dir .build/dataset/sistemas
   ```

   `git status` no debe mostrar cambios en `outputs/`. En Windows, ejecuta los comandos con `PYTHONIOENCODING=utf-8`.

4. Corre las siete consultas de A1 sobre la sábana (ADR-004), sin haber corrido `build` antes:

   ```bash
   python -m worky_engine analyze --data-dir fundation-docs --out-dir outputs/analysis
   ```

5. Corre el health score de A3 y su validación medida (ADR-005), sin haber corrido `build` antes:

   ```bash
   python -m worky_engine health --data-dir fundation-docs --out-dir outputs/health
   ```

## Qué produce

| Archivo en `outputs/` | Qué es |
|---|---|
| `master_dataset.csv` | 650 empresas, 35 columnas: empresa, MRR en MXN, uso, soporte, comercial y estatus de churn |
| `identity_crosswalk.csv` | Un `master_id` por empresa con sus ids de HubSpot, producto y Vitally |
| `match_audit.csv` | Una fila por registro de origen con el nivel de confianza, el puntaje y la evidencia de cada cruce |
| `quarantine_companies.csv` | 28 filas clon de HubSpot que no entran a la sábana |
| `quarantine_deals.csv` | 35 deals cuyo `hubspot_id` no existe en ningún sistema |
| `exceptions_log.csv` | Cada valor imputado o corregido, con su origen y su evidencia |
| `coverage_report.md` | Qué porcentaje de cada sistema se reconcilió y con qué confianza |
| `backtest_report.md` | Cómo se eligió la fórmula de tendencia de uso, medida contra el churn real |
| `analysis/report.md` | Las siete respuestas de A1 sobre la sábana, cada una con su definición del ADR-004, el SQL y el resultado |
| `health/health_scores.csv` | 650 empresas, el health score de A3 con sus cuatro subpuntajes, la banda de riesgo y las tres marcas por tasa de capacidad (ADR-005) |
| `health/validation.md` | La validación medida del health score contra `churn_date`: AUC por señal, precisión, recall, recall ponderado por MRR, sensibilidades y la respuesta a A3.4 |

## Dónde está cada cosa

| Carpeta | Contenido |
|---|---|
| `worky_engine/` | El motor: normalización pura en Python, resolución de identidad por niveles, ensamblaje en SQL de DuckDB, contratos del build, harness de backtest y la CLI |
| `tests/` | 146 pruebas de comportamiento; las marcadas con `dataset` usan las tres bases reales |
| `docs/decisions/` | Tres registros de decisión (ADR): cómo se cruzan las empresas, cómo se imputa y normaliza el MRR, cómo se mide la tendencia de uso sin filtrar el mes de churn |
| `docs/data-model/` | Perfil del esquema tal como llega de los tres sistemas |
| `docs/diagrams/` | Siete diagramas en HTML: sistemas actuales, flujo del motor, ERD, modelo relacional objetivo, flujo de identidad, journeys por actor y estados de una cuenta |
| `docs/research/` | Investigación previa sobre arquitectura de datos, BI y RevOps |
| `openspec/specs/` | El contrato vigente del motor: 41 requisitos y 60 escenarios en seis dominios |
| `openspec/changes/archive/` | El expediente completo del cambio A0: propuesta, diseño, tareas, verificación, revisión adversarial y reporte de cierre |

## Cómo se trabajó

El motor se construyó con desarrollo guiado por especificaciones (Gentle AI SDD): cada pieza tuvo requisitos y escenarios antes que código, y se cerró con una verificación independiente contra ese contrato. El código se entregó en seis cortes revisados por separado, cada uno con revisión automatizada y recibo, y el motor completo pasó una revisión adversarial a dos jueces ciegos (Judgment Day) cuyo ledger está en el expediente archivado. Las decisiones que un evaluador querrá cuestionar están en `docs/decisions/`, escritas para que las entienda tanto un analista junior como una dirección.

| Tema | Decisión |
|---|---|
| Cruce entre sistemas | Cascada de cuatro niveles (id directo, dominio, fecha de alta, nombre) con umbrales calibrados sobre los datos y una regla de veto para dominios compartidos; 100 % de cobertura, cero cruces manuales |
| MRR faltante | Se imputa desde el deal ganado y se marca `mrr_source` y `mrr_confidence`; se reportan dos totales, el del CRM y el completo |
| Montos de deals | El CRM mezcla montos mensuales y anuales; los anuales se detectan (exactamente 12 veces el mensual) y se llevan a mensual |
| Tendencia de uso | Momentum de los últimos meses, calculado siempre antes del mes de churn para que el puntaje no espíe la respuesta |
| Datos que no cuadran | Nada se borra ni se sobrescribe en silencio: clones y deals fantasma van a cuarentena, vínculos duplicados quedan marcados para revisión, y cada corrección deja una fila en `exceptions_log` |

## Lista de verificación para quien evalúa

- [ ] `python -m worky_engine build` termina con código 0 y `outputs/` no cambia
- [ ] `coverage_report.md` muestra 650 empresas reconciliadas y las 28 + 35 filas en cuarentena
- [ ] Cada ADR en `docs/decisions/` tiene alternativas consideradas y una lista de verificación
- [ ] `openspec/specs/identity-resolution/spec.md` describe la cascada que implementa `worky_engine/identity_resolution/`

## Siguiente paso

A0 (dataset maestro) está cerrado y archivado. Las secciones A1 (SQL sobre la sábana), A3 (health score), A4 (modelo de warehouse), A5 (tablero), A6 (script de limpieza) y la Parte B se irán agregando con el mismo método, cada una con su expediente en `openspec/`.
