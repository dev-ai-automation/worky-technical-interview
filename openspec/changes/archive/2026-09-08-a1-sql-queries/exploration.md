# Exploración: a1-sql-queries (SQL avanzado sobre la sábana de A0)

Fase `sdd-explore` ejecutada el 2026-09-08 por el agente explorador; persistida por el orquestador. Referencia en Engram: `sdd/a1-sql-queries/explore`. Texto literal de la sección A1 del caso en el bloque final.

## Estado actual

El motor A0 (archivado en `openspec/changes/archive/2026-09-08-a0-master-dataset-engine/`) ya produce `outputs/master_dataset.csv` (650 filas, 35 columnas), `quarantine_deals.csv`, `quarantine_companies.csv`, `match_audit.csv`, `identity_crosswalk.csv`, `exceptions_log.csv` y `coverage_report.md`, todos deterministas. El motor de SQL es DuckDB 1.5.5 (fijado en `pyproject.toml`). El ensamblaje corre en `worky_engine/master_dataset/assemble.py`: registra los DataFrames crudos con `con.register`, ejecuta `sql/staging/*.sql` y luego `sql/marts/*.sql` en un orden fijo (`STAGING_FILES`, `MART_FILES`). Ya existen vistas que A1 puede reutilizar directamente: `mart_master_dataset`, `mart_mrr`, `mart_deal_normalized` (regla 12x de ADR-002 Adenda 1), `mart_usage` (momentum, ADR-003), `mart_support`, `mart_commercial` (con `mart_first_touch`, sin `mart_last_touch`), y `mart_coverage*` (que ya calcula el conteo y monto de `quarantine_deals`, base de A1.5).

## Por ítem del caso: tablas, reúso y ambigüedades

### A1.1, MRR activo por segmento e industria, MXN, sin duplicados

- Tablas: `mart_master_dataset` (`segment`, `industry`, `mrr_mxn`, `mrr_source`, `churn_status`). Ya viene en MXN (tipo de cambio 18.5 aplicado en `stg_companies.sql` y `stg_deals.sql`) y ya viene deduplicado (los 28 clones quedan en `quarantine_companies`, nunca entran a `mart_master_dataset`).
- Falta: el `GROUP BY segment, industry` con los dos totales que exige ADR-002 (MRR solo del CRM y MRR total incluyendo imputados), filtrando `churn_date IS NULL`.
- Ambigüedad real: si el cruce debe ser segmento por industria en una sola tabla, o dos desgloses separados; y cuál de los dos totales es "el" MRR activo cuando el caso pide un solo número.

### A1.2, active_users en los 3 meses previos al churn contra los primeros 3 meses activa

- No reusable: hay que volver a `stg_product_usage` o `raw_product_usage` vía `account_id` (existe en `master_dataset.csv`, cobertura 650 de 650 en el dataset real).
- Ambigüedades que el spec debe resolver: (a) "primeros 3 meses activa" como las primeras 3 filas de la serie de uso por orden calendario, no necesariamente los 3 meses siguientes a `signup_date`; (b) si "3 meses previos a la baja" incluye o excluye el mes de churn; se recomienda excluirlo, por el mismo argumento de fuga de datos que ya usó ADR-003 para `trend_usage`; (c) empresas con menos de 6 meses de uso, donde las dos ventanas se traslapan. Este último punto ya está medido: ADR-003 corrió exactamente esta fórmula en su backtest y reporta que solo está definida para el 76 % de las empresas con churn; el prototipo del orquestador sobre las 89 cuentas con churn y `account_id` da 30 con menos de seis meses, 67 con caída y 19 con "subida" (casi todas de tres meses de vida), mediana de caída relativa 0.538.

### A1.3, curva de retención por cohorte de mes de alta

- Reusable solo con `mart_master_dataset` (`signup_date`, `churn_date`); a diferencia de A1.2, aquí no hace falta volver a `product_usage` porque "activa" se puede definir a nivel contrato (no ha hecho churn todavía).
- Ambigüedades: (a) fuente del "mes de alta": `companies.signup_date` (ya en el dataset maestro) contra `accounts.created_at` (product_db, sistema distinto, con su propia fecha); (b) qué significa "activa en el mes k": no ha hecho churn todavía, contra uso real de producto ese mes; (c) cohortes censuradas que aún no llegan al mes 6 o 12 (empresas con alta reciente): si esa celda queda vacía o se calcula con dato parcial (riesgo de sesgo de supervivencia si se mezcla).

### A1.4, atribución primer touch contra último touch

- `mart_first_touch` (dentro de `mart_commercial.sql`) ya resuelve primer touch con empate por `touch_id`; no existe una vista de último touch, hay que crear una simétrica.
- Ambigüedad central: el grano de "conversión a closedwon". A nivel empresa (esta empresa, con este primer o último touch, tiene al menos un deal closedwon) contra a nivel deal (este deal específico, atribuido al touch anterior a su `created_date`, cerró). Con 997 deals sobre 678 empresas (cerca de 1.5 deals por empresa), estos dos granos pueden dar un canal ganador distinto, que es justo lo que el caso pide comparar, así que el spec debe fijar el grano antes de escribir el SQL. Ambigüedad secundaria: regla de empate del último touch, y si usar el mismo respaldo a `lead_source` o `unknown` que usa `acquisition_channel` (el perfil real dice que las 650 empresas tienen al menos un touch, así que el respaldo debería dar 0 filas).

### A1.5, hubspot_id de deals sin empresa real

- Ya resuelto por Python (`worky_engine/identity_resolution/quarantine.py`) en `quarantine_deals.csv`: 35 filas, `hubspot_id` HS-990000 a HS-990034, todas `closedwon`, monto total 667,251.00.
- Cada `hubspot_id` huérfano tiene exactamente un deal: no hay un segundo monto de la misma empresa contra el cual detectar el múltiplo de 12 (regla de `mart_deal_normalized`), y no hay fila de `companies` de la que heredar moneda. Conclusión: no se puede normalizar este monto a valor mensual con el mismo rigor que el resto del dataset; solo se puede reportar el monto crudo y declarar la limitación como hallazgo. A1 debe entregar el SQL equivalente (`LEFT JOIN` de deals contra companies con `WHERE company IS NULL`) aunque el número ya se conozca por el motor Python, porque el caso pide explícitamente la consulta.

### A1.6, resolution_hours negativo

- 48 de 1,888 tickets tienen `resolution_hours` negativo (`docs/data-model/00-as-is-schema-profile.md`); 206 son NULL. El `design.md` archivado de A0 dice explícitamente (línea 213) que A0 no publica ninguna columna derivada de `resolution_hours` y que ese defecto pertenece a A6; A1 es el primer lugar donde alguien decide qué hacer con estos 48 casos. `mart_support.sql` no usa `resolution_hours`, así que la decisión de A1.6 no toca nada existente del dataset maestro.

### A1.7, optimización y pipeline incremental

- `assemble.py` hoy reconstruye todo desde SQLite en cada corrida (`con.register` de los DataFrames completos, staging y marts desde cero); no hay particionamiento, ventanas materializadas ni actualización incremental. Es una respuesta narrativa (diseño), no una consulta ejecutable, aunque puede incluir SQL o DDL ilustrativo.

## Dónde debe vivir el entregable

| Opción | Qué es | Pros | Contras | Esfuerzo |
|---|---|---|---|---|
| A. `worky_engine/sql/analysis/a1_0N_*.sql` más un subcomando CLI nuevo `analyze` | Sigue el patrón `MART_FILES`, `writers` y goldens; escribe un CSV por consulta y un `outputs/analysis/report.md` con el SQL, el motor, los resultados y las justificaciones de A1.6 y A1.7 | Consistente con cómo se construyó A0; reproducible byte a byte; probado contra el dataset real con `pytest -m dataset`; auditable | Más superficie: un módulo Python nuevo, cableado en `cli.py`, pruebas nuevas | Medio |
| B. Solo archivos `.sql` con comentarios, sin CLI ni pruebas automatizadas | Mínimo, rápido de revisar | Nadie prueba que corren contra el dataset real; sin protección de regresión si cambian los marts; rompe el patrón de reproducibilidad de A0 | Bajo |

Recomendación: opción A, a escala mínima (un subcomando `analyze` simétrico a `backtest`, que no depende de haber corrido `build` antes: registra tablas y corre staging, marts y analysis en su propia conexión). Si el conteo de líneas se acerca al presupuesto de revisión, cortar en dos PR encadenados: PR 1 con A1.1 a A1.5 (las consultas sobre la sábana), PR 2 con A1.6 (decisión de calidad de datos), A1.7 (narrativa de escalamiento) y el ensamblaje del reporte final. Esto separa la corrección de SQL puro de las decisiones de juicio y diseño, que se revisan distinto.

## Áreas afectadas

- `worky_engine/sql/analysis/` (nuevo): las seis consultas de A1.1 a A1.6
- `worky_engine/cli.py`: nuevo subcomando `analyze`, siguiendo el patrón de `cmd_backtest`
- `worky_engine/master_dataset/assemble.py` o un módulo hermano: exponer staging y marts sin depender de `build`
- `worky_engine/writers.py`: reusar `write_csv` y `write_markdown` tal cual
- `worky_engine/sql/marts/mart_commercial.sql`: agregar la vista simétrica de último touch
- `tests/`: pruebas nuevas siguiendo el patrón de `test_support_commercial.py` (fixture mínimo) y marca `dataset` para el real
- `docs/decisions/`: un ADR nuevo o una adenda si alguna ambigüedad (A1.2, A1.3, A1.4) se resuelve con una decisión no trivial

## Riesgos y preguntas abiertas de producto

- A1.1: cruce segmento por industria en una tabla o dos desgloses; cuál total es "el" MRR activo cuando el caso pide un solo número.
- A1.2: excluir o no el mes de churn de la ventana previa; qué hacer con las empresas con churn que no alcanzan 6 meses de uso.
- A1.3: `companies.signup_date` contra `accounts.created_at` como fecha de cohorte; definición de "activa"; tratamiento de cohortes censuradas.
- A1.4: grano de conversión (empresa contra deal), que puede cambiar el canal ganador reportado; es el punto que el caso pide comparar, así que hay que fijarlo antes de escribir el SQL.
- A1.5: aceptar reportar el monto crudo sin normalizar a mensual como hallazgo.
- A1.6: la decisión es del candidato por diseño del caso; solo confirmar que no debe tocar el `master_dataset.csv` existente.

## Recomendación

Proceder a `sdd-propose` para fijar el alcance y las decisiones de arriba (especialmente A1.2, A1.3 y A1.4, que cambian el resultado numérico). `sdd-research` no es necesaria: todo el trabajo es interno al repositorio, sin incógnitas externas que investigar.

## Listo para propuesta

Sí. Las ambigüedades están identificadas y acotadas; falta que el usuario confirme las decisiones de la sección anterior antes de escribir el spec, para no tener que rehacer el SQL después.

## Texto literal de la sección A1 del caso

"A1. SQL avanzado, sobre tu propia sábana. Usando la sábana que construiste en A0 (y regresando a las tablas fuente cuando necesites el detalle mensual o de touches), escribe el SQL (indica el motor) para:

1. MRR activo total (excluyendo cuentas con churn_date no nulo) por segmento e industria, ya con las cuentas en USD normalizadas a MXN (tipo de cambio 18.5) y sin duplicados.
2. Volviendo a product_db.product_usage (nivel mensual, que tu sábana no conserva), calcula para cada cuenta que churneó el promedio de active_users en los 3 meses previos a su baja vs. el promedio de sus primeros 3 meses activa. Ordena por la mayor caída relativa.
3. Curva de retención por cohorte de mes de alta: para cada cohorte, qué % de cuentas seguía activa en el mes 1, 3, 6, 12 después del alta. Una sola query, con CTEs.
4. Atribución: usando marketing_touches y deals de crm_hubspot.db, calcula la tasa de conversión a closedwon por primer touch y por último touch, y compara si cambia el canal "ganador" según el modelo de atribución.
5. Verifica si todos los hubspot_id en crm_hubspot.deals tienen correspondencia con una empresa real en tu sábana. Si encuentras casos que no la tienen, cuantifica cuánto amount representan (sería un hallazgo de calidad de datos con impacto directo en cifras de negocio).
6. Con tickets, identifica registros con resolution_hours negativo, decide cómo tratarlos y justifica tu decisión en 3-4 líneas.
7. (Optimización) product_usage tiene hoy ~10k filas mensuales; en producción real serían cientos de millones (uso diario de miles de clientes). ¿Qué cambiarías en el modelo para que estas queries sigan corriendo en segundos, y cómo diseñarías el pipeline para que la sábana se refresque sin tener que reprocesar todo desde cero cada vez?"

Formato de entrega que pide el caso: archivo .sql (o notebook) con las queries, documento o slides con el análisis y recomendaciones, script de Python si aplica.
