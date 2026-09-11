# Propuesta: script de limpieza automática de companies.csv

## Intención

A6 pide un script real en Python que tome `companies.csv`, detecte nulos en `mrr`, cuentas en `currency = USD` y fechas DD/MM/YYYY mezcladas con ISO, las normalice y deje un log de cuántos registros corrigió de cada tipo. Hoy esa limpieza vive repartida en el pipeline (`stg_companies.sql`, `mart_mrr.sql`) y no hay ni un comando que la corra sola ni un log de conteos. El ADR-002 además ya comprometió a A6 a imputar el `mrr` faltante desde los deals y a registrar cada deal anualizado como una corrección más.

Éxito: correr un solo archivo y obtener el CSV limpio más un log que reporte 28 imputaciones, 22 conversiones de USD y 31 fechas normalizadas; correrlo otra vez sobre su propia salida reporta cero correcciones.

## Alcance

### Dentro

- Subcomando `python -m worky_engine clean` y wrapper `scripts/clean_companies.py` que solo lo invoca.
- Tres detecciones sobre 678 filas, con conteos verificados: 56 `mrr` nulo (28 clones `HS-9000xx` excluidos, 28 imputables), 22 en USD, 31 fechas DD/MM/YYYY en `signup_date` (12 ambiguas con día ≤ 12, contadas aparte). `churn_date` no trae fechas mezcladas.
- Imputación desde `deals.csv` por `hubspot_id` crudo, replicando en pandas la regla del ADR-002: monto único por empresa, anualización 12x registrada como corrección propia, confianza `high` con deal `closedwon` y `medium` sin él.
- Conversión con `to_mxn` (18.5) a `mrr_mxn`, `mrr_original`, `currency_original`; fechas con `normalize_date`.
- Salidas en `outputs/clean/`: `companies_clean.csv`, `cleaning_log.json`, `cleaning_log.md` (resumen en español), `cleaning_exceptions.csv` a grano fila con el shape de `exceptions_log`. Versionadas como golden.
- Orden determinista, idempotencia y códigos de salida 0, 1 y 2 del CLI.

### Fuera

- Tocar marts, staging, `worky_engine/normalization/` o cualquier golden de A0 a A4.
- Ejecutar la regla vía DuckDB, usar el crosswalk de identidad o escribir sobre `data/raw/`.
- Imputar los 28 clones en cuarentena del ADR-001.

## Capacidades

### Nuevas

- `data-cleaning`: entradas, las tres detecciones con sus conteos, la imputación del ADR-002 con confianza y anualización, la conversión de moneda, la normalización de fechas, las salidas y sus columnas, el contrato del log, la idempotencia, el wrapper y los goldens.

### Modificadas

Ninguna. `source-normalization` ya fija la fecha ISO, la conversión a 18.5 con original conservado y la idempotencia; A6 las consume sin cambiar ningún requisito.

## Enfoque

Un módulo nuevo `worky_engine/cleaning/` concentra la detección, la imputación y el armado del log como funciones puras que importan `normalize_date` y `to_mxn` sin modificarlos. `cmd_clean` en `cli.py` solo resuelve rutas, llama al módulo y escribe con `write_csv` y `write_markdown`. La lectura usa `keep_default_na=False, na_values=[""]`. Una prueba compara las 28 imputaciones contra `mart_mrr` sobre el dataset real.

## Áreas afectadas

| Área | Impacto | Descripción |
|---|---|---|
| `worky_engine/cleaning/`, `tests/test_cleaning.py` | Nueva | Detección, imputación, log y pruebas de conteos e idempotencia |
| `scripts/clean_companies.py` | Nueva | Wrapper delgado sobre el subcomando |
| `outputs/clean/` | Nueva | CSV limpio, log JSON, resumen Markdown y excepciones por fila, como golden |
| `worky_engine/cli.py`, `README.md` | Modificado | `cmd_clean`, su parser y los pasos de corrida |
| `worky_engine/normalization/`, staging, marts, goldens previos | Sin cambio | Verificado por prueba |

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| La regla del ADR-002 queda en pandas y en SQL, y ambos deben coincidir | Alta | Prueba que compara las imputaciones contra `mart_mrr` en el dataset real |
| 12 fechas donde DD/MM y MM/DD son ambas válidas | Media | Se normalizan como DD/MM según el ADR-001 y el log las reporta por separado |
| Pandas infiere nulos donde no los hay | Media | Lectura con `keep_default_na=False` |
| Rebasar las 800 líneas de autoría | Media | Una sola PR; si crece, el corte es detección, normalización y log primero, e imputación más `cleaning_exceptions.csv` en una PR encadenada |
| A5 corre en paralelo y también toca `README.md` | Baja | A6 es dueño de la sección de pasos de corrida |

## Plan de reversión

`git revert` del merge. Todo es archivo nuevo más un subcomando aditivo, así que `resolve`, `build`, `analyze`, `health` y `warehouse` quedan intactos. Se borra a mano `outputs/clean/`.

## Dependencias

pandas, ya fijado en `pyproject.toml`. ADR-001 y ADR-002 con su adenda 1. `worky_engine/normalization/{dates,currency}.py` y `writers.py`.

## Criterios de éxito

- [ ] `python scripts/clean_companies.py` corre sin `build` previo y termina en 0.
- [ ] El log reporta 28 imputaciones, 22 conversiones de USD, 31 fechas normalizadas, las 12 ambiguas y los deals anualizados.
- [ ] Los 28 clones `HS-9000xx` quedan intactos y reportados como excluidos.
- [ ] Correr el comando sobre su propia salida reporta cero correcciones.
- [ ] Las 28 imputaciones coinciden con `mart_mrr` sobre el dataset real.
- [ ] Dos corridas seguidas dan goldens idénticos byte a byte y ningún golden previo cambia.
