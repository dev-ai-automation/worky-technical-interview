# Propuesta: consultas SQL de A1 sobre la sábana de A0

## Intención

El caso pide siete respuestas de SQL sobre la sábana que construyó A0. El ADR-004 ya fijó la definición de cada una, y el ADR-002 y el ADR-003 fijaron las reglas de MRR y de ventana de uso que dos de ellas necesitan. Falta el código: hoy nadie puede correr esas consultas ni ver su resultado junto a la definición que lo produjo. Este cambio agrega la capa de análisis que las ejecuta con un comando y publica el resultado con el motor, la definición y la justificación en el mismo documento.

Éxito, en una frase: alguien clona el repositorio, corre un comando y obtiene los siete resultados, iguales byte a byte en cada corrida, sin haber corrido `build` antes.

## Alcance

### Dentro

- Siete archivos SQL en `worky_engine/sql/analysis/`, uno por ítem de A1.1 a A1.6 más la vista de último touch que A1.4 necesita. Cada archivo abre con un encabezado que nombra el motor (DuckDB 1.5.5) y la definición del ADR-004 que implementa.
- Un subcomando `analyze`, simétrico a `backtest`: abre su propia conexión, registra las tablas crudas y corre staging, marts y análisis. No depende de un `build` previo.
- Un CSV por consulta en `outputs/analysis/`, más `outputs/analysis/report.md` con la definición, el SQL, el motor, la tabla de resultado y las justificaciones de A1.6 (3 a 4 líneas) y A1.7 (respuesta de diseño con DDL ilustrativo).
- Goldens versionados bajo `outputs/analysis/`, con las mismas pruebas de idempotencia que ya protegen a `build`.
- Pruebas de comportamiento: por consulta, una sobre fixture mínimo que ejerce su regla, y una marcada `dataset` que fija el número real.

### Fuera

- Tocar `master_dataset.csv` o cualquiera de los ocho goldens de A0.
- Corregir el signo de las horas negativas en origen, que es de A6.
- Health score, tablero y script de limpieza (A3, A5, A6).
- Retención medida por uso real de producto en el mes k, rechazada en el ADR-004 y dejada como pregunta para A3.
- Llevar a valor mensual el monto de los 35 deals huérfanos: el ADR-002, adenda 1, ya explicó por qué no hay forma rigurosa de hacerlo.

## Capacidades

### Nuevas

- `sql-analysis`: las siete respuestas de A1, el comando que las corre, el formato de sus salidas y las reglas del ADR-004 como requisitos verificables.

### Modificadas

- Ninguna. La vista `mart_last_touch` vive en la capa de análisis, no en `mart_commercial.sql`, para que los marts de A0 y sus goldens queden congelados. Meterla al mart comercial habría obligado a un delta de `master-dataset-assembly` sin agregar una sola columna al dataset maestro.

## Enfoque

Es la opción A de la exploración, a escala mínima, siguiendo el patrón que ya existe en el repositorio.

| Pieza | Qué hace |
|---|---|
| `worky_engine/sql/analysis/a1_00_last_touch.sql` | Vista de último touch anterior al `created_date` del deal, empate por `touch_id`, simétrica a `mart_first_touch` |
| `a1_01_active_mrr.sql` a `a1_06_negative_hours.sql` | Una consulta por ítem, con la definición del ADR-004 en el encabezado |
| `worky_engine/analysis/` | Lista `ANALYSIS_FILES` con el orden fijo, reúso de `register_tables` y `run_sql_files`, y materialización de un DataFrame por consulta |
| `worky_engine/cli.py` | `cmd_analyze`, con importación diferida de DuckDB y el mismo mensaje claro en español cuando falta una dependencia |
| `worky_engine/analysis/report.py` | Arma `report.md` a partir de los mismos DataFrames, sin volver a abrir la conexión, igual que hace `quality.coverage` |
| `outputs/analysis/` | Un CSV por consulta, `analysis_exceptions.csv` con las filas de A1.6 y `report.md` |

Las siete definiciones del ADR-004 son vinculantes y el reporte las repite al lado de cada consulta: los dos totales de MRR con fila de totales en A1.1; la fórmula literal con el mes de baja fuera, la columna `windows_overlap` y las 89 cuentas en A1.2; cohortes por mes de `signup_date` con celdas censuradas vacías y una sola consulta con CTEs en A1.3; grano deal con los dos modelos lado a lado y si cambia el ganador en A1.4; los 35 deals por 667,251.00 en unidades mezcladas con la limitación declarada en A1.5; horas negativas en nulo para promedios, tickets conservados para conteos y CSAT, y la hipótesis de signo invertido como hallazgo en A1.6.

Las filas de excepción de A1.6 se escriben en `outputs/analysis/analysis_exceptions.csv`, con las mismas columnas que `exceptions_log.csv`, en lugar de agregarse al log de A0. El ADR-004 dice "se registran en el log de excepciones" sin nombrar el archivo, y escribir en el de A0 rompería su golden y el contrato que ya lo valida. A6 puede fusionar los dos logs cuando corrija el signo en origen.

## Áreas afectadas

| Área | Impacto | Descripción |
|---|---|---|
| `worky_engine/sql/analysis/` | Nueva | Siete archivos SQL, encabezado con motor y definición |
| `worky_engine/analysis/` | Nuevo | Corredor y formateador del reporte |
| `worky_engine/cli.py` | Modificado | Subcomando `analyze` y su parser |
| `outputs/analysis/` | Nueva | Seis CSV de resultado, `analysis_exceptions.csv` y `report.md` |
| `tests/` | Modificado | Pruebas por consulta y de idempotencia del comando |
| `outputs/` (ocho goldens de A0) | Sin cambio | Se verifica que siguen idénticos |

## Plan de PR (presupuesto de 800 líneas por PR)

Encadenados a `main`, cada uno con su propia verificación y reversión.

| PR | Contenido | Líneas de autoría estimadas | Qué revisa primero el revisor |
|---|---|---|---|
| 1 | Corredor de análisis, subcomando `analyze`, A1.1, A1.2, A1.5, pruebas y sus tres CSV | 520 (más ~95 filas de golden, fuera del conteo de autoría) | Que `analyze` no dependa de `build` y que A1.2 excluya el mes de baja y marque `windows_overlap` |
| 2 | A1.3 y A1.4, con `a1_00_last_touch.sql` | 380 | Que las celdas censuradas de A1.3 queden vacías y que A1.4 atribuya cada deal a dos canales con el mismo empate por `touch_id` que el motor |
| 3 | A1.6, A1.7 y el ensamblaje de `report.md` | 430 | La justificación de 3 a 4 líneas de A1.6 y que ningún golden de A0 haya cambiado |

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Una consulta toca por accidente una salida de A0 | Baja | El corredor escribe solo bajo `outputs/analysis/`; una prueba compara los ocho goldens de A0 antes y después |
| El monto de A1.5 se lee como revenue perdido | Media | El reporte lo etiqueta "unidades mezcladas" y cita la adenda 1 del ADR-002 |
| El evaluador esperaba otra lectura de A1.2 o A1.4 | Media | Cada consulta lleva su definición al lado y el reporte dice qué cambia con la lectura alterna |
| PR 1 se acerca al presupuesto por el golden de 89 filas de A1.2 | Media | El golden es generado y queda fuera del conteo de autoría; si el SQL crece, A1.5 se mueve al PR 3 |
| Duplicar en la capa de análisis reglas que ya viven en los marts | Media | Las consultas parten de los marts existentes y solo regresan a las fuentes donde el caso lo pide: uso mensual en A1.2, touches y deals en A1.4, deals en A1.5, tickets en A1.6 |

## Plan de reversión

Cada PR se revierte solo con `git revert` de su merge. Nada de A0 queda en estado intermedio: el cambio agrega archivos nuevos y una rama del parser de argumentos, así que revertir los tres PR deja el repositorio con los ocho goldens de A0 intactos y `pytest -m dataset` en verde sin ningún paso manual. `outputs/analysis/` se borra completo con la reversión.

## Dependencias

- DuckDB 1.5.5 y pandas, ya fijados en `pyproject.toml`. No se agrega ninguna dependencia.
- Las tres bases SQLite del caso, leídas con `load_raw_tables` en modo solo lectura.

## Criterios de éxito

- [ ] `python -m worky_engine analyze --data-dir ... --out-dir outputs` corre en una máquina sin `build` previo y termina en 0.
- [ ] Dos corridas seguidas producen archivos idénticos byte a byte bajo `outputs/analysis/`.
- [ ] Los ocho goldens de A0 quedan sin cambio, verificado por prueba.
- [ ] `report.md` muestra, por ítem, la definición del ADR-004, el SQL, el motor DuckDB 1.5.5 y la tabla de resultado.
- [ ] Los números del ADR-004 quedan fijados por pruebas marcadas `dataset`: 89 cuentas en A1.2, 35 deals por 667,251.00 en A1.5, 48 tickets negativos en A1.6.
- [ ] La lista de verificación del ADR-004 pasa completa.
- [ ] Ningún PR de la cadena supera 800 líneas de autoría.
