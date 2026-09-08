# Exploración: motor del dataset maestro de A0, enfoque de implementación

## Contexto

La sección A0 del caso pide una fila por empresa, reconciliada a partir de tres sistemas sin sincronizar (el CRM de HubSpot, una base de datos interna de producto, el soporte de Vitally), más una estrategia de cruce documentada y un reporte de cobertura. Tres ADR ya confirman las decisiones de producto:

- ADR-001 (`docs/decisions/ADR-001-identity-resolution-scorecard.md`): scorecard por niveles (T0 a T3), regla de veto, supervivencia de atributos, `master_id` idempotente, `match_audit`, `identity_crosswalk`, tablas de cuarentena.
- ADR-002 (`docs/decisions/ADR-002-mrr-imputation-and-normalization.md`): imputación de MRR a partir del monto del deal para las 28 empresas reales sin MRR, `mrr_mxn`/`mrr_source`/`mrr_confidence`/`mrr_original`, dos totales reportados lado a lado, USD a 18.5.
- ADR-003 (`docs/decisions/ADR-003-usage-trend-and-leakage-guard.md`): `trend_usage` como momentum EWMA (span 3 contra span 9), resguardo contra fuga de datos (solo meses en el mes de corte o antes), `trend_status`, harness de backtest conservado en el repositorio.

Esta exploración cubre cómo construir el motor que implementa esos tres ADR. No cubre si las decisiones son correctas.

## Estado actual

- Todavía no existe ningún andamiaje: no hay `pyproject.toml`, no hay corredor de pruebas, no hay paquete de código fuente. El repositorio de Git es nuevo, sin commits.
- Python 3.14.7 con pandas, duckdb, pytest y rapidfuzz instalados a nivel de usuario (sin entorno virtual). Node 24 está presente solo para el skill de diagramas `archify`.
- Ya existe un script prototipo de backtest en la ruta del harness del scratchpad, escrito como un script plano de pandas/sqlite3 (sin estructura de paquete, sin pytest). Reproduce la metodología del ADR-003 y debería promoverse al repositorio en lugar de reescribirse.
- La inspección directa de los gemelos en CSV confirma que aparecen caracteres acentuados en los nombres de empresa, en los nombres de los CSM, e incluso dentro de las cadenas de dominio (por ejemplo `gaitán115.com.mx`), y que los bytes del CSV están en UTF-8. Hay un riesgo real de codificación en Windows, que se cubre en la sección de riesgos más abajo.
- `openspec/config.yaml` confirma `persistence.mode: hybrid`, `delivery_strategy: auto-chain`, `review_budget_lines: 800`, y que todavía no se detecta ningún manifiesto de paquete.

## Áreas afectadas

- `docs/decisions/ADR-001-identity-resolution-scorecard.md`, `ADR-002-mrr-imputation-and-normalization.md`, `ADR-003-usage-trend-and-leakage-guard.md`: decisiones ya confirmadas que este motor implementa, incluyendo la lista de verificación numérica que cada ADR trae para su revisor.
- `docs/data-model/00-as-is-schema-profile.md`: el esquema origen, los conteos de filas, y cada hallazgo de calidad de datos que la normalización y el cruce deben manejar.
- `docs/research/01-bi-revops-data-architecture.md`, carriles 1, 2 y 6: patrones de resolución de entidades y de calidad de datos.
- La copia del dataset en el scratchpad y el script del harness: inspeccionados en modo solo lectura para verificar los hallazgos de codificación y de dominio, y como candidatos a promoverse al repositorio.

## Pregunta 1: enfoque de implementación

Un hecho descarta una solución en SQL puro, sin importar el motor: los umbrales calibrados del ADR-001 (WRatio >= 94 con un margen de 10 puntos para T3, token_set_ratio >= 90 para T1, partial_ratio >= 90 para T2) son algoritmos compuestos específicos de RapidFuzz. Una verificación directa confirma que DuckDB trae `jaro_similarity`, `jaro_winkler_similarity`, `levenshtein`, `damerau_levenshtein`, `hamming`, `jaccard` y `editdist3`, y ninguna de estas reimplementa WRatio, token_set_ratio o partial_ratio. Recalcular los niveles con las funciones nativas de DuckDB produciría en silencio puntajes distintos a los de la calibración con los 596 pares, e invalidaría los umbrales medidos. Por eso el puntaje de identidad (T1 a T3) debe correr en Python con RapidFuzz, en cualquiera de las opciones siguientes.

| Enfoque | Cómo se ve | Ventajas | Desventajas | Esfuerzo |
|---|---|---|---|---|
| (a) DuckDB en capas al estilo dbt, Python solo para el puntaje y la orquestación | El SQL de staging normaliza cada tabla origen; un paso en Python corre el puntaje de T0 a T3 y escribe crosswalk/audit/quarantine; el SQL de marts ensambla el dataset maestro, la imputación de MRR, los agregados y el reporte de cobertura | Lee SQLite/CSV directamente, sin una copia de ETL aparte; A1 puede unir el dataset maestro con `product_usage`/`marketing_touches` en el mismo motor; un archivo `.duckdb` persistido siembra la historia del warehouse de A4; los marts en SQL son los que prueban el requisito del caso de "indicar el motor" usado | Dos lenguajes que hay que mantener sincronizados; necesita instalada la extensión de SQLite de DuckDB | Media |
| (b) Pipeline en pandas, SQL solo para A1 | Todo en DataFrames; el SQL de A1 se escribe después, contra una copia ya cargada | Menos piezas en movimiento; cada transformación es una función que se puede probar; no requiere instalar ninguna extensión | Sigue necesitando un motor SQL para A1, así que posterga la elección del motor en lugar de evitarla, y agrega un segundo salto de ETL; una historia más débil para A4 (sin un artefacto de warehouse que de verdad funcione) | De baja a media |
| (c) Nativo en SQLite con UDF de Python | Registrar los puntajes de RapidFuzz como UDF de SQLite; correr el pipeline como SQL contra SQLite | Un solo formato de origen | Un archivo `.sql` con UDF personalizadas no puede correr de forma independiente en `sqlite3` plano; aritmética de fechas más débil y sin `QUALIFY` ni un tipo DATE nativo | De media a alta |

Recomendación: la opción (a), acotada con precisión. La normalización es un módulo puro de Python, sin dependencia de SQL o pandas (compartido entre la resolución de identidad y el futuro script de A6, para que nunca terminen en dos implementaciones distintas de "quitar acentos, quitar la razón social"). El puntaje de identidad es Python/RapidFuzz puro, para preservar exactamente la calibración del ADR-001. El ensamblaje (supervivencia, imputación de MRR, agregados, reporte de cobertura) es SQL de DuckDB, primero en staging y después en marts.

## Pregunta 2: estructura del repositorio

```
worky_engine/
  normalization/        fechas, etiqueta de dominio, nombre de empresa, moneda a MXN
  identity_resolution/  blocking, puntaje (RapidFuzz), cascada de niveles + veto, crosswalk, quarantine
  master_dataset/       supervivencia, imputación de MRR, agregados de uso/soporte/comercial, ensamblaje
  quality/              reporte de cobertura (A0.3), validaciones de integridad referencial e idempotencia
  harness/              backtest del ADR-003, promovido desde el prototipo del scratchpad
  sql/staging/  sql/marts/
  cli.py                 python -m worky_engine build
pyproject.toml
tests/  fixtures/ (fixtures sintéticos pequeños, no el dataset completo de 650 filas)
outputs/  master_dataset.csv, match_audit.csv, identity_crosswalk.csv,
          quarantine_companies.csv, quarantine_deals.csv, coverage_report.md, exceptions_log.csv
```

Empaquetado: un `pyproject.toml` mínimo con versiones fijas de pandas/duckdb/pytest/rapidfuzz y una entrada `[project.scripts]` para que `python -m worky_engine build` funcione sin instalación.

Trade-off de qué se commitea: se commitean las salidas que exige el caso (`master_dataset.csv`, `coverage_report.md`, `match_audit.csv`, `identity_crosswalk.csv`, los CSV de quarantine) como goldens generados; la regla de presupuesto de revisión de SDD excluye los goldens del conteo de líneas escritas, así que esto no infla el presupuesto de 800 líneas, y además funcionan como fixtures para la prueba de idempotencia. Todo lo demás generado se ignora en Git. Al revisor se le explica que el único comando de build es lo que demuestra que la copia commiteada sigue coincidiendo con lo que se genera; no es algo que haya que tomar solo de palabra.

## Pregunta 3: límites de los módulos y contratos de datos

| Módulo | Entradas | Salidas | Pruebas |
|---|---|---|---|
| normalization | Fechas crudas con formatos mixtos, dominios crudos, nombres crudos, pares (monto, moneda) | Fecha en ISO, etiqueta de dominio registrable, nombre normalizado, `mrr_mxn` | Pruebas basadas en tabla sobre los ejemplos del ADR-001; idempotencia por registro; ida y vuelta en UTF-8 con fixtures acentuados |
| identity_resolution | companies/accounts/customers normalizados, los 596 pares etiquetados (solo para calibración) | `identity_crosswalk`, `match_audit`, `quarantine_companies`, `quarantine_deals` | (source_system, source_id) único; integridad referencial; idempotencia (rerun idéntico byte por byte); prueba de regresión de calibración contra los 596 pares; el fixture de veto de club290 debe seguir sin fusionarse |
| master_dataset (ensamblaje) | Crosswalk, fuentes normalizadas, `product_usage`, `tickets`, `deals`, `marketing_touches` | Una fila por master_id: atributos, campos de MRR, agregados de uso/soporte/comercial, `trend_usage`/`trend_asof_month`/`trend_status`, churn_status | master_id único; not-null en las columnas requeridas; integridad referencial de las filas imputadas hacia la bitácora de excepciones; prueba del resguardo contra fuga de datos; idempotencia completa |
| quality / coverage_report | `match_audit`, crosswalk, conteos por sistema | % de cobertura por sistema y por nivel, tamaño de la cola de revisión manual (responde a A0.3) | Los porcentajes recalculados coinciden con los números que cada ADR declara en su propia lista de verificación |
| harness (ADR-003) | `churn_date`, series de `product_usage`, fórmulas candidatas | Métricas por fórmula y por k | Aserción de regresión de que el momentum EWMA sigue ganando en k=2 por AUC |

## Pregunta 4: cómo rebanar el alcance

El alcance se mantiene en A0 más el harness que exige el ADR-003. A1, A3, A4, A5 y A6 son cambios separados con sus propios evaluadores. Estimado aproximado de líneas: normalization ~150, identity_resolution ~250, assembly ~200, quality ~100, andamiaje ~50, unas 750 líneas escritas en total, justo por debajo del presupuesto de 800 líneas antes de contar los goldens (que no cuentan). Se recomiendan dos rebanadas encadenadas:

- Rebanada 1 (la más pequeña que entrega el CSV de A0 y el reporte de cobertura de punta a punta): normalization, identity_resolution, ensamblaje mínimo (atributos de empresa, MRR, churn_status), reporte de cobertura, CLI.
- Rebanada 2: agregados de uso/soporte/comercial, incluyendo trend_usage y el resguardo contra fuga de datos, más promover el harness.

A6 debería convertirse en su propio cambio pequeño de seguimiento, que importe `worky_engine.normalization`, ya que tiene un énfasis de evaluación distinto y el caso lo marca como opcional.

## Pregunta 5: riesgos e incógnitas

1. Codificación en Windows: se confirmaron caracteres acentuados en nombres y dominios, con los bytes del CSV en UTF-8. Usar `open()` sin `encoding="utf-8"` explícito en Windows arriesga una mala decodificación silenciosa que desplaza en secreto los puntajes de RapidFuzz cerca de los umbrales calibrados. Se necesita un argumento de codificación explícito en todas partes, más un fixture de pytest con nombres acentuados.
2. Determinismo de RapidFuzz: RapidFuzz en sí mismo es determinista; el riesgo real está en el desempate dentro de un grupo de bloque de fecha de T2 más grande que 1 (tamaño máximo observado de 4), algo que el ADR-001 no especifica más allá del caso de tamaño 1. Se necesita un fallback explícito a revisión manual, y no el orden implícito de las filas. Fijar la versión de RapidFuzz.
3. Dialecto de DuckDB contra SQLite: la aritmética de DATE nativa de DuckDB, las funciones de ventana y `QUALIFY` divergen de SQLite. Indicar el motor de forma explícita en el `.sql` entregado, cargar las fuentes de SQLite mediante la extensión de SQLite de DuckDB, y documentar un fallback sin conexión, ya que la extensión necesita acceso a internet en su primera instalación.
4. Hallazgo de calidad de datos en el dominio: algunos valores de dominio traen el carácter acentuado tal cual dentro de lo que parece un hostname (`gaitán115.com.mx`), que no es una etiqueta DNS válida en el mundo real. Esto confirma que se trata de un cruce sobre cadenas de texto ya limpiadas para mostrarse, y no una normalización DNS real; una dependencia de la Public Suffix List aquí sería sobreingeniería.
5. Volatilidad de los goldens: los CSV commiteados de `match_audit`/`identity_crosswalk`/quarantine van a producir diffs con mucho ruido ante cualquier futura actualización de versión de RapidFuzz o DuckDB, salvo que las versiones queden fijas y cualquier actualización que toque los goldens se entregue como su propio cambio revisado.

## Recomendación

Motor híbrido: `normalization` en Python puro (sin dependencia de base de datos, compartido con el futuro A6), `identity_resolution` en Python puro con RapidFuzz para preservar la calibración del ADR-001, SQL de DuckDB para el ensamblaje de staging y marts, la imputación de MRR y el reporte de cobertura. Promover el prototipo existente del harness agregándole cobertura de pruebas. Entregar en dos rebanadas encadenadas para mantenerse dentro del presupuesto de 800 líneas. Dejar A1/A3/A4/A5/A6 como cambios separados más adelante.

## Preguntas abiertas

1. Regla de desempate para un grupo de bloque de fecha de T2 más grande que 1.
2. Si los goldens commiteados en `outputs/` deben ser tablas completas o una muestra documentada.
3. La versión exacta de la extensión de SQLite de DuckDB que se debe fijar, y si conviene empaquetar su caché para builds sin conexión.

## Referencias

`docs/decisions/ADR-001/002/003`, `docs/data-model/00-as-is-schema-profile.md`, `docs/research/01-bi-revops-data-architecture.md` (carriles 1, 2, 6), el PDF del caso, `openspec/config.yaml`, Engram `worky/a0/decision-identity-resolution` (#1622), `worky/a0/matching-calibration` (#1621), `worky/a0/decision-mrr-imputation` (#1624), `worky/a0/decision-usage-trend` (#1627).

## Lista para propuesta

Sí, con una salvedad: las tres preguntas abiertas de arriba deben resolverse durante la propuesta o el diseño; ninguna de ellas cambia el enfoque elegido, solo ajusta sus bordes exactos.
