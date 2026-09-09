# Tablero ejecutivo del VP de Customer Success (A5)

Este documento es el wireframe por secciones que responde la pregunta del caso: qué cuentas están en riesgo real, priorizadas por impacto en MRR, y si dos cuentas con el mismo puntaje de salud pero MRR muy distinto reciben el mismo trato. Implementa el ADR-007. Cada sección declara su columna fuente exacta, su filtro y la acción esperada del CSM o del VP, para que cualquiera pueda rastrear un widget hasta el archivo que lo alimenta sin leer el resto del documento.

Fuente de datos: `outputs/health/health_scores.csv` y `outputs/master_dataset.csv` (A1 y A3), unidos por `master_id`. `dataset_asof`: 2024-08-31. `ruleset_version`: 1.0.0. El mockup con las mismas cifras en una interfaz visual vive en `docs/dashboard/02-mockup-vp-cs.html`.

## Índice

1. [KPIs de encabezado](#1-kpis-de-encabezado)
2. [Cola de prioridad](#2-cola-de-prioridad)
   - 2.1 [Respuesta a $3,000 contra $45,000](#21-respuesta-a-3000-contra-45000)
3. [Cohorte de onboarding](#3-cohorte-de-onboarding)
4. [Carga por CSM](#4-carga-por-csm)
5. [Evidencia del modelo](#5-evidencia-del-modelo)
6. [Tendencia en el tiempo](#6-tendencia-en-el-tiempo)
7. [Drill-down por cuenta](#7-drill-down-por-cuenta)
8. [Lo que este tablero no muestra](#8-lo-que-este-tablero-no-muestra)

## Boceto de referencia

Forma que repiten las cuatro tarjetas de encabezado y el inicio de la cola de prioridad, tal como aparecen en el mockup:

```
+----------------------+----------------------+----------------------+----------------------+
| MRR en riesgo        | Cuentas por atender  | Carga por CSM        | Aviso anticipado     |
| $2,216,115 MXN       | 78                   | 11.1 (ref. 12)       | 92.9 % con 1 mes     |
| 13.7 % del activo    | de 518 con puntaje   | 7 personas           | 52 de 56 evaluables  |
+----------------------+----------------------+----------------------+----------------------+
| Cuenta    | Segmento   | Responsable | MRR mensual | Tramo | Nivel | Por qué está marcada |
| HS-100155 | Enterprise | Luis Peña   | $952,602    | Alto  | Alto  | barras de subpuntaje  |
```

Cada sección de abajo usa la misma tabla de seis columnas: métrica, definición en lenguaje llano, columna o consulta fuente, filtro, acción del CSM o del VP, y cadencia.

## 1. KPIs de encabezado

| Métrica | Definición en lenguaje llano | Columna o consulta fuente | Filtro | Acción | Cadencia |
|---|---|---|---|---|---|
| MRR en riesgo | Cuánto dinero mensual está en cuentas que necesitan atención esta semana | `SUM(mrr_mxn)` de `health_scores.csv` | `flagged_15 = True AND churned = False` | El VP decide si se refuerza al equipo de CSM esta semana | Por corrida del comando `health` |
| Cuentas por atender | Cuántas cuentas activas entraron a la lista de trabajo | `COUNT(*)` de `health_scores.csv` | `flagged_15 = True AND churned = False` | El CSM abre su cola de trabajo | Por corrida |
| Carga por CSM | Cuántas cuentas marcadas le tocan a cada responsable, en promedio | `COUNT(*)` de la cola dividido entre 7 CSM | mismo filtro que la cola, agrupado por `csm_owner` (de `master_dataset.csv`) | El VP redistribuye cuentas si algún CSM está sobre capacidad | Por corrida |
| Aviso anticipado | Qué tan seguido el modelo hubiera avisado un mes antes de que la cuenta se marcara | cifra citada de `outputs/health/validation.md` | cuentas marcadas al 15 % con historia suficiente en k = 3 | El VP usa esta cifra para defender el modelo frente a otras áreas | Por corrida |

Cifras de esta corrida: MRR en riesgo **$2,216,115** MXN, **13.7 %** del MRR activo total (**$16,223,225.50** MXN sobre 561 cuentas activas con puntaje). Cuentas por atender: 78 de 518 cuentas activas con `health_score` definido. Carga por CSM: 78 entre 7 personas, 11.1 en promedio, contra una línea de referencia de 12 (sección 4). Aviso anticipado: **92.9 %** (52 de 56 cuentas evaluables) ya estaban marcadas un mes antes.

El origen de la regla de la cola (`flagged_15 = True AND churned = False`, nunca `risk_band` sola) está documentado en `docs/decisions/ADR-007-executive-dashboard.md`.

## 2. Cola de prioridad

| Métrica | Definición en lenguaje llano | Columna o consulta fuente | Filtro | Acción | Cadencia |
|---|---|---|---|---|---|
| Cola de prioridad | Lista de cuentas activas que el modelo marcó, ordenada por cuánto dinero mensual pesan | `health_scores.csv` unido a `csm_owner` de `master_dataset.csv` por `master_id` | `flagged_15 = True AND churned = False`, orden `mrr_mxn` descendente | El CSM trabaja la lista de arriba hacia abajo | Por corrida |
| Tramo de MRR (segundo eje) | Un segundo semáforo, aparte del nivel de riesgo, que dice qué tan grande es la cuenta | `pd.cut(mrr_mxn, [.., 5000, 20000, ..])` sobre las cuentas activas | mismas 561 cuentas activas con puntaje | El CSM no trata igual una cuenta chica que una grande dentro del mismo nivel de riesgo | Por corrida |

La cola contiene exactamente **78 cuentas** activas, ninguna con `churned = True` sin importar su nivel de riesgo. El orden es siempre `mrr_mxn` descendente: cuando dos cuentas activas comparten el mismo `health_score`, la de mayor MRR mensual queda arriba (por ejemplo, HS-100598 con MRR $6,483 queda arriba de HS-100134 con MRR $2,721, ambas con puntaje 33.97).

El corte por tramo agrega 131 cuentas por debajo de $5,000, 250 cuentas entre $5,000 y $20,000, y 180 cuentas por arriba de $20,000, sobre las 561 cuentas activas con puntaje. Cada fila de la cola en el mockup muestra el tramo al que pertenece esa cuenta, además de su nivel de riesgo.

### 2.1 Respuesta a $3,000 contra $45,000

Dos cuentas con el mismo `health_score` y MRR muy distinto **no** reciben el mismo trato. Tres mecanismos combinados lo garantizan:

1. **Orden por MRR**: dentro del mismo nivel de riesgo, la cuenta con mayor `mrr_mxn` siempre aparece primero en la cola.
2. **KPI agregado**: el MRR en riesgo suma el `mrr_mxn` de cada cuenta marcada, así que una cuenta grande pesa más en el número que ve el VP que diez cuentas chicas juntas.
3. **Tramo de MRR**: el segundo eje visual de la sección 2 separa a la cuenta grande de la chica aunque compartan nivel de riesgo, con una insignia de texto que no depende del color.

Evidencia con datos reales de este dataset: HS-100507 (Enterprise, MRR **$46,340**, `health_score` **27.68**) y HS-100065 (SMB, MRR **$2,947**, `health_score` **35.56**) están en la misma banda de riesgo alto. HS-100507 queda arriba de HS-100065 en la cola por su mayor MRR, y pesa quince veces más en el KPI de MRR en riesgo, pese a tener un puntaje de salud parecido.

## 3. Cohorte de onboarding

| Métrica | Definición en lenguaje llano | Columna o consulta fuente | Filtro | Acción | Cadencia |
|---|---|---|---|---|---|
| Cohorte de onboarding | Cuentas activas tan nuevas que todavía no tienen historia de uso suficiente para calificarse | `health_scores.csv`, columna `usage_months_asof` menor a 3 | `risk_band = 'sin historia' AND churned = False` | El CSM de onboarding da seguimiento activo, no espera a que el modelo las marque | Por corrida |

La cohorte muestra exactamente **43 cuentas** activas nuevas, etiquetadas como "sin historia de uso suficiente" y **nunca** como "sana": el modelo simplemente todavía no tiene datos para calificarlas. La banda completa "sin historia" son 65 filas: 22 son bajas reales que se fueron antes de acumular tres meses de uso (cuentan en el denominador del recall del modelo, ADR-005) y 43 son estas cuentas activas nuevas. El origen de la banda "sin historia" y de la regla de los tres meses mínimos está en `docs/decisions/ADR-005-health-score-model.md`.

## 4. Carga por CSM

| Métrica | Definición en lenguaje llano | Columna o consulta fuente | Filtro | Acción | Cadencia |
|---|---|---|---|---|---|
| Carga por CSM | Cuántas cuentas de la cola le tocan a cada responsable, contra una línea de referencia | `csm_owner` de `master_dataset.csv` cruzado con la cola de prioridad | mismo filtro de la cola, agrupado por `csm_owner` | El VP redistribuye cuentas del CSM sobre capacidad | Por corrida |

Conteo de esta corrida, contra una línea de referencia operativa de 12 cuentas por CSM (una decisión de operación, no una cifra medida en ningún CSV):

| CSM | Cuentas marcadas | Estado |
|---|---|---|
| Jorge Ibarra: 21 | 21 | Sobre capacidad |
| Ana Ruiz: 15 | 15 | Sobre capacidad |
| Diego Ortega: 10 | 10 | Dentro del rango |
| Luis Peña: 10 | 10 | Dentro del rango |
| Carla Nuñez: 9 | 9 | Dentro del rango |
| Fernanda Solís: 8 | 8 | Dentro del rango |
| Marta Díaz: 5 | 5 | Dentro del rango |

Jorge Ibarra y Ana Ruiz quedan marcados como "sobre capacidad" porque su conteo supera la línea de referencia de 12; el resto queda dentro del rango. `outputs/health/validation.md` mide 11.1 cuentas por CSM al 15 % de marcado (14.9 al 20 %), nunca 12: la línea de 12 es una decisión operativa que el documento y el mockup declaran como tal, no como un dato medido.

## 5. Evidencia del modelo

| Métrica | Definición en lenguaje llano | Columna o consulta fuente | Filtro | Acción | Cadencia |
|---|---|---|---|---|---|
| Evidencia del modelo | Cuentas que ya se fueron y que el modelo había marcado como riesgo alto, en un panel separado de la cola de trabajo | `health_scores.csv` | `risk_band = 'riesgo alto' AND churned = True` | El VP usa este panel para defender la calidad del modelo, nunca como lista de trabajo | Por corrida |

El panel separa **67 cuentas** ya dadas de baja que el modelo había marcado en riesgo alto; ninguna de ellas aparece en la cola de prioridad de la sección 2, porque la cola solo incluye cuentas activas. Estas 67 cuentas demuestran qué tan bien detecta el modelo el riesgo, no qué debe hacer un CSM hoy. Citando `outputs/health/validation.md`: de las cuentas marcadas al 15 % con historia suficiente para evaluarse también un mes antes (k = 3), **92.9 %** (52 de 56 evaluables) ya estaban marcadas con un mes de anticipación.

## 6. Tendencia en el tiempo

```
+---------------------------------------------------------------+
|  (sin serie que dibujar todavia)                               |
|                                                                 |
|  fact_health_score_monthly necesita dos o mas corridas del      |
|  comando `warehouse` en fechas distintas antes de poder trazar  |
|  una linea de tendencia real por cuenta o por cartera.          |
+---------------------------------------------------------------+
```

`fact_health_score_monthly` (A4, `docs/decisions/ADR-006-star-schema.md`) hoy tiene una sola fecha de corrida (2024-08-31), así que no hay todavía dos puntos que unir. Esta sección se documenta como el camino que abrirá el warehouse una vez existan corridas reales en fechas distintas; el tablero no dibuja una serie inventada solo para llenar el espacio.

## 7. Drill-down por cuenta

| Métrica | Definición en lenguaje llano | Columna o consulta fuente | Filtro | Acción | Cadencia |
|---|---|---|---|---|---|
| Drill-down por cuenta | Desglose de por qué una cuenta puntual quedó marcada | `health_scores.csv`, las cuatro columnas de subpuntaje más `usage_months_asof` | una cuenta seleccionada por el CSM | El CSM decide qué palanca tocar primero con esa cuenta | Bajo demanda |

Ejemplo con HS-100507 (Enterprise, MRR $46,340, `health_score` 27.68, 4 meses de uso al corte):

| Subpuntaje | Valor (0 a 100, más alto es mejor) | Qué mide |
|---|---|---|
| Tendencia de uso (momentum) | 23.08 | Uso reciente contra uso de fondo |
| Cambio contra el mes pasado | 14.36 | Cuánto subió o bajó el uso mes a mes |
| Caída desde el mejor momento | 76.92 | Qué tan lejos está del mejor promedio de tres meses que tuvo |
| Antigüedad de la cuenta | 17.31 | Meses desde el alta hasta el mes de corte |

El puntaje más bajo de los cuatro (antigüedad, 17.31) es la primera pista de por qué esta cuenta quedó marcada: es una cuenta relativamente nueva con una caída fuerte desde su mejor momento de uso.

## 8. Lo que este tablero no muestra

- **La historia completa del `health_score` en el tiempo por cuenta**: hoy solo se ve el valor del corte más reciente, no cómo llegó ahí (ver sección 6).
- **Las 22 bajas no detectables**: son bajas reales que se fueron sin acumular los tres meses de uso que el modelo necesita para calificarlas; el modelo, por diseño, nunca pudo verlas venir (ADR-005, Adenda 1). No aparecen marcadas en ningún panel de este tablero porque nunca recibieron `health_score`.
- **El `health_score` no es la única alerta temprana posible**: soporte (tickets, urgentes, CSAT) y activación temprana se miden y se publican en `outputs/health/validation.md`, pero pesan cero en la fórmula porque en este dataset no separan tan bien como las cuatro señales de uso y antigüedad que sí entran (ADR-005). Un CSM que solo mire este tablero puede perderse una señal cualitativa que el modelo no captura todavía.

## Lenguaje llano

Esta tabla es la única que nombra columnas técnicas; el mockup (`02-mockup-vp-cs.html`) nunca las muestra.

| Columna interna | Cómo se lee en el tablero |
|---|---|
| `flagged_15 = True` | En la lista de esta semana |
| `churned = False` | Cuenta viva |
| `hubspot_id` | Cuenta (el identificador que el VP y el CSM reconocen; `master_id` es un hash interno y nunca se muestra) |
| `risk_band` | Nivel de riesgo |
| `health_score` | Puntaje de salud (0 a 100, más alto es mejor) |
| `score_momentum` | Tendencia de uso |
| `score_mom` | Cambio contra el mes pasado |
| `score_drawdown` | Caída desde su mejor mes |
| `score_tenure` | Antigüedad de la cuenta |
| `usage_months_asof` | Meses de uso acumulados |
| `mrr_mxn` | MRR mensual |
| `csm_owner` | Responsable de la cuenta |
| `risk_band = 'sin historia'` | Cuenta nueva, todavía sin puntaje |

Nota de ortografía: los nombres de CSM se escriben tal como vienen en `master_dataset.csv` (por ejemplo, "Carla Nuñez", sin el acento que llevaría "Núñez" en español estándar). Corregirlo en el documento rompería la coincidencia literal contra el dato y, peor, inventaría una grafía que el sistema origen no tiene.

## Apéndice: snippet de pandas para recomputar todas las cifras citadas

Corrida única, documentada aquí para que cualquiera la repita. Cada bloque nombra la columna y el filtro exacto de la cifra que produce (decisión D3 del diseño de A5).

```python
import pandas as pd

health = pd.read_csv("outputs/health/health_scores.csv")
master = pd.read_csv("outputs/master_dataset.csv")

# D9: csm_owner sale de master_dataset.csv, unido por master_id.
df = health.merge(master[["master_id", "csm_owner"]], on="master_id", how="left")

# Cola de prioridad: flagged_15 = True AND churned = False (ADR-007).
queue = df[(df["flagged_15"] == True) & (df["churned"] == False)]
active = df[df["churned"] == False]

cuentas_en_cola = len(queue)                              # 78
mrr_en_riesgo = queue["mrr_mxn"].sum()                     # 2216115.0
mrr_activo = active["mrr_mxn"].sum()                       # 16223225.5
proporcion = round(mrr_en_riesgo / mrr_activo * 100, 1)    # 13.7

# risk_band = 'riesgo alto', separado por churned (ADR-007).
riesgo_alto = df[df["risk_band"] == "riesgo alto"]
riesgo_alto_activas = riesgo_alto[riesgo_alto["churned"] == False]     # 78
riesgo_alto_churn = riesgo_alto[riesgo_alto["churned"] == True]        # 67

# risk_band = 'sin historia', separado por churned (ADR-005).
sin_historia = df[df["risk_band"] == "sin historia"]
sin_historia_churn = sin_historia[sin_historia["churned"] == True]     # 22
sin_historia_activas = sin_historia[sin_historia["churned"] == False]  # 43

# Tramos de MRR sobre el libro activo (D8): < 5000, 5000-20000, >= 20000.
bins = [-float("inf"), 5000, 20000, float("inf")]
tramos = pd.cut(active["mrr_mxn"], bins=bins, right=False)
conteo_tramos = tramos.value_counts()                      # 131, 250, 180

# Conteo por csm_owner sobre la cola de prioridad.
por_csm = queue.groupby("csm_owner").size().sort_values(ascending=False)

# Evidencia viva: HS-100065 y HS-100507.
ejemplo = df[df["hubspot_id"].isin(["HS-100065", "HS-100507"])]
print(ejemplo[["hubspot_id", "mrr_mxn", "health_score"]])
```

La cifra de aviso anticipado (**92.9 %**, 52 de 56 evaluables) no sale de este snippet: se lee directo del encabezado y la sección "Detección temprana en k = 3" de `outputs/health/validation.md`, porque requiere volver a correr el modelo con un mes de corte distinto (k = 3), no solo agregar el CSV ya calculado.
