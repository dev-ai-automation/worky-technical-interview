# Propuesta: motor del dataset maestro de A0

## Intención

HubSpot, la base de datos de producto y Vitally llevan cada uno su propia lista de clientes, y hoy no existe una sola fila por empresa que un analista o un director pueda usar sin volver a reconciliar todo a mano. El perfil del esquema mide el tamaño del problema:

| Hallazgo | Medición |
|---|---|
| Filas de empresa en HubSpot | 678, de las cuales 28 (ids HS-9000xx) son clones de filas reales |
| Cuentas de producto sin `hubspot_id` | 54 de 650 |
| Clientes de Vitally con cruce exacto de dominio | 573 de 650 |
| Deals huérfanos | 35, todos en `closedwon`, por 667,251 |
| Empresas sin valor de MRR | 56 nulos, de los cuales 28 son empresas reales |

Mientras eso siga así, cualquier total de ingresos mezcla clones y huérfanos, y las 28 empresas reales sin MRR desaparecen de un reporte ordenado por MRR. Este cambio construye el motor que produce una fila por empresa real, reproducible, con la evidencia de cada cruce guardada para poder revisarla.

## Alcance

### Dentro del alcance

- Normalización compartida de fechas, dominio, nombre de empresa y conversión de moneda a MXN.
- Resolución de identidad por niveles T0 a T3 con la regla de veto, más `identity_crosswalk`, `match_audit`, `quarantine_companies` y `quarantine_deals` (ADR-001).
- Ensamblaje del dataset maestro con supervivencia de atributos, imputación de MRR y `churn_status` (ADR-002).
- Agregados de uso con `trend_usage`, `trend_asof_month`, `trend_status` y el resguardo contra fuga de datos (ADR-003).
- Agregados de soporte y comerciales.
- Reporte de cobertura de A0.3, desglosado por sistema y por nivel.
- Harness de backtest del ADR-003 promovido al repositorio, con cobertura de pruebas.
- CLI `python -m worky_engine build` como único comando de construcción.

### Fuera del alcance

- A1 (consultas SQL de analítica), A3 (health score), A4 (modelo de warehouse) y A5 (tablero): cambios posteriores encadenados a este.
- A6 (script de limpieza): cambio de seguimiento propio, que reutilizará `worky_engine.normalization` en lugar de reimplementarla.

## Capacidades (Capabilities)

### Capacidades nuevas (New Capabilities)

- `source-normalization`: fechas a ISO, etiqueta de dominio registrable, nombre de empresa normalizado, monto en USD convertido a MXN a 18.5.
- `identity-resolution`: blocking, puntaje con RapidFuzz, cascada T0 a T3, veto, `master_id` idempotente, crosswalk, auditoría y cuarentenas.
- `master-dataset-assembly`: supervivencia de atributos, imputación de MRR con sus marcas, agregados de uso, soporte y comercial, `churn_status`, una fila por empresa.
- `coverage-report`: cobertura medida por sistema y por nivel, más el tamaño de la cola de revisión manual (responde a A0.3).
- `trend-backtest-harness`: reproduce la comparación de fórmulas del ADR-003 en k = 0, 2 y 3.
- `build-cli`: un comando reproducible que genera todas las salidas de `outputs/`.

### Capacidades modificadas (Modified Capabilities)

Ninguna. `openspec/specs/` está vacío, así que no hay capacidades existentes que reutilizar.

## Enfoque

Motor híbrido en tres piezas, aprobado por el usuario y tomado de la exploración:

1. `normalization` en Python puro, sin dependencia de base de datos, compartida entre la resolución de identidad y el futuro script de A6 para que nunca existan dos versiones de "quitar acentos y quitar la razón social".
2. `identity_resolution` en Python con RapidFuzz. Los umbrales del ADR-001 (WRatio de 94 o más con margen de 10 puntos, token_set_ratio de 90 o más, partial_ratio de 90 o más) son algoritmos compuestos de RapidFuzz. DuckDB trae `jaro_winkler_similarity`, `levenshtein` y similares, y ninguna reimplementa esos tres, así que recalcular los niveles en SQL produciría puntajes distintos a los de la calibración con 596 pares e invalidaría los umbrales medidos.
3. Ensamblaje en SQL de DuckDB, en capas staging y marts. Son operaciones de unión y agregación que un revisor de datos espera leer como SQL, y un archivo `.duckdb` persistido deja un artefacto que A1 y A4 pueden reutilizar en lugar de una segunda copia de ETL.

## Entrega en dos PR encadenados

| PR | Contenido | Líneas autoradas estimadas |
|---|---|---|
| 1 | `normalization`, `identity_resolution`, ensamblaje mínimo (atributos, MRR, `churn_status`), reporte de cobertura, CLI y `pyproject.toml` | ~500 |
| 2 | Agregados de uso con `trend_usage` y el resguardo contra fuga, agregados de soporte y comerciales, harness del ADR-003 | ~250 |

El PR 1 ya entrega el CSV de A0 y el reporte de cobertura de punta a punta. El total estimado de ~750 líneas viene de la exploración; los goldens generados en `outputs/` quedan fuera del conteo del presupuesto de 800 líneas.

## Áreas afectadas

| Área | Impacto | Descripción |
|---|---|---|
| `worky_engine/` | Nueva | Paquete por dominio: normalization, identity_resolution, master_dataset, quality, harness, `sql/staging`, `sql/marts`, `cli.py` |
| `pyproject.toml` | Nuevo | Versiones fijas de rapidfuzz, duckdb, pandas y pytest, más el punto de entrada del CLI |
| `tests/` | Nueva | Pruebas por módulo con fixtures sintéticos pequeños y acentuados |
| `outputs/` | Nueva | Salidas generadas y commiteadas: `master_dataset.csv`, `match_audit.csv`, `identity_crosswalk.csv`, los dos CSV de cuarentena, `exceptions_log.csv`, `coverage_report.md` |

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Mala decodificación silenciosa de UTF-8 en Windows, que desplaza los puntajes cerca de los umbrales | Alta | `encoding="utf-8"` explícito en cada apertura de archivo, más un fixture de pytest con nombres acentuados |
| La extensión de SQLite de DuckDB necesita red en su primera instalación | Media | Fijar la versión, documentar un fallback sin conexión y verificarlo antes de cerrar el PR 1 |
| Desempate en un grupo de bloque de fecha de T2 con más de un candidato (tamaño máximo observado: 4) | Media | Aplicar la regla del ADR-001: si el candidato no es único en el bloque, baja al siguiente nivel o cae a revisión manual, nunca al orden implícito de las filas |
| Una actualización de rapidfuzz o duckdb genera diffs ruidosos en los goldens | Media | Versiones fijas en `pyproject.toml` y cualquier actualización que toque goldens se entrega como su propio cambio revisado |
| Los goldens commiteados se quedan atrasados respecto al código | Baja | La prueba de idempotencia corre el build dos veces y compara contra la copia commiteada |

## Plan de reversión

Todo lo que produce este cambio es código y archivos generados dentro de `outputs/`. Revertir es volver al commit anterior. No se toca ningún sistema externo, ninguna base de datos compartida y ningún dato de origen: las tres bases SQLite se leen en modo solo lectura.

## Dependencias

- Dataset `fundation-docs/dataset_caso_v3.zip` (tres bases SQLite con sus gemelos en CSV), sin cambios.
- Python 3.14 con rapidfuzz, duckdb, pandas y pytest en versiones fijas.
- Extensión de SQLite de DuckDB, con su caché resuelta antes de la primera corrida.
- Los tres ADR aceptados como contrato de comportamiento.

## Criterios de éxito

- [ ] El dataset maestro tiene exactamente 650 filas, una por empresa real, con `master_id` único.
- [ ] Correr `python -m worky_engine build` dos veces produce salidas idénticas byte por byte.
- [ ] La prueba de calibración reproduce los números del ADR-001 sobre los 596 pares etiquetados, con WRatio eligiendo el cruce correcto en primer lugar al menos el 99.0% de las veces (590 de 596 con la normalización del motor; los 6 restantes son empates de nombre irresolubles).
- [ ] Las empresas que comparten el dominio `club290.com.mx` se quedan separadas por el veto, cada una con su propio `master_id`, y el veto queda registrado en `match_audit`; solo van a revisión manual los registros que ningún nivel logra resolver.
- [ ] La cuenta con el nombre truncado `Sanches y Asocia` queda resuelta a su empresa por T2 o T3, con la evidencia registrada en `match_audit`.
- [ ] El reporte muestra los dos totales de MRR lado a lado: el reportado del CRM y el que incluye valores imputados, con la proporción imputada.
- [ ] `exceptions_log.csv` tiene exactamente 28 filas de imputación, cada una nombrando su `deal_id` origen.
- [ ] `trend_status` está poblado en todas las filas, sin ningún nulo silencioso, y ninguna fila de uso posterior a `trend_asof_month` entra al cálculo.
- [ ] `coverage_report.md` reporta el porcentaje de cobertura por sistema y por nivel, más el tamaño de la cola de revisión manual.

## Preguntas para el diseño

1. Si los goldens commiteados en `outputs/` deben ser las tablas completas o una muestra con su comando de regeneración documentado.
2. Qué versión exacta de la extensión de SQLite de DuckDB se fija, y si conviene empaquetar su caché para una construcción sin conexión.
3. La forma exacta del CLI y si el archivo `.duckdb` se persiste en el repositorio o se regenera en cada corrida.
