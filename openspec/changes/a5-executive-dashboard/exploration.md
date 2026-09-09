# Exploración: a5-executive-dashboard (dashboard ejecutivo de riesgo real para el VP de CS)

## Texto literal de la sección A5 del caso

"Wireframe (boceto o descripción por secciones) de un dashboard para el VP de CS que muestre, con los datos de este caso, qué cuentas están en riesgo real (no solo 'uso bajo'), priorizadas por impacto en MRR. Indica qué pasaría si dos cuentas tienen el mismo Health Score pero una tiene MRR de $3,000 y otra de $45,000: ¿el dashboard las trata igual?"

## Estado actual

A0/A1/A3/A4 ya entregan todo el dato real que A5 necesita: `outputs/health/health_scores.csv` (650 filas: 561 activas + 89 bajas evaluadas en su mes de corte, ADR-005), `outputs/master_dataset.csv`, `outputs/warehouse/dim_company.csv` (SCD2) y `outputs/warehouse/map_source_identity.csv` (ADR-006). El journey `docs/diagrams/src/05-journeys-por-actor.mmd` (sección "VP de Customer Success, con el motor A0") ya promete explícitamente: dashboard con matriz de riesgo por MRR, "ingreso en riesgo" como KPI único destacado, prioridad para MRR alto + riesgo alto. `docs/research/01-bi-revops-data-architecture.md` sección 5 recomienda la misma matriz de riesgo por valor y los principios de Few y Knaflic ("de un vistazo", color preatencional solo para riesgo). A5 no inventa el concepto, lo materializa con datos reales.

**Hallazgo crítico, verificado leyendo el CSV real:** `risk_band = 'riesgo alto'` (145 filas) no es la lista accionable. Mezcla 78 cuentas activas (`churned=False`) con 67 cuentas que ya hicieron churn, evaluadas dos meses antes de irse solo para medir el recall del modelo (ADR-005). La lista operativa real es `flagged_15 = True AND churned = False`: exactamente 78 cuentas, el 15.06 % del libro activo con score (518), unas 11.1 por CSM, que coincide con la tabla de capacidad de `validation.md`. Un dashboard que lea `risk_band` sin filtrar `churned` le mostraría al VP cuentas que ya no existen como si fueran accionables.

MRR en riesgo real (suma de `mrr_mxn` de esas 78 cuentas activas marcadas, calculado sobre el CSV): aproximadamente $2,216,115 MXN, el 13.7 % del MRR activo total ($16,223,225.50 MXN, 561 cuentas, A1.1/ADR-004). Una sola cuenta (Enterprise, canal Webinar, MRR $952,602) es el 43 % de todo ese MRR en riesgo. Distribución de `mrr_mxn` en las 650 filas: 351 (54 %) entre $1,000 y $9,999; 279 (43 %) entre $10,000 y $99,999; 20 (3 %) de $100,000 en adelante; máximo $952,602; mínimo entre $2,000 y $2,999. El ejemplo del caso ($3,000 contra $45,000) es realista: $3,000 cae en la mitad baja de las SMB, $45,000 ya es un top 3 % de la cartera.

`sin historia` (65 filas totales) mezcla dos poblaciones distintas: 22 son bajas reales sin 3 meses de uso al corte (cuentan en el denominador del recall, ADR-005 Adenda 1) y 43 son cuentas activas nuevas (menos de 3 meses de uso): riesgo de onboarding, no cuentas "sanas". Ejemplo real de la asimetría de MRR con el mismo score: HS-100065 (SMB, MRR $2,947, marcada) y HS-100507 (Enterprise, MRR $46,340, marcada) están en la misma banda "riesgo alto" con scores parecidos (35.56 y 27.68) pero MRR quince veces distinto.

## Áreas afectadas

- `outputs/health/health_scores.csv`, `outputs/health/validation.md`: fuente real de score, banda, marcas y MRR; la columna `churned` es la que separa lo accionable de la evidencia histórica.
- `outputs/master_dataset.csv`, `outputs/analysis/report.md` (A1.1, MRR activo por segmento): MRR activo total y contexto comercial (canal, segmento).
- `outputs/warehouse/dim_company.csv`, `map_source_identity.csv`, `docs/data-model/01-warehouse-model.md` (ADR-006): esquema en estrella disponible; `fact_health_score_monthly` hoy solo tiene una fecha de corrida (sin historia real todavía), así que la vista de tendencia del tablero es diseño a futuro, no dato mostrable hoy.
- `docs/decisions/ADR-005-health-score-model.md`: pesos, bandas, `flagged_15` como umbral operativo por capacidad, y la respuesta ya fundamentada a A3.4 (un falso negativo en una cuenta grande cuesta más).
- `docs/research/01-bi-revops-data-architecture.md` sección 5, `docs/diagrams/src/05-journeys-por-actor.mmd`: la promesa de diseño (matriz riesgo por MRR, ingreso en riesgo destacado) que A5 debe cumplir literalmente.
- `docs/diagrams/README.md`, skill `archify`: convención de diagramas si se agrega uno nuevo (no imprescindible para A5, que pide wireframe, no ERD).
- Ningún archivo de `outputs/` ni golden de A0/A1/A3/A4 se toca; A5 solo lee.

## Pregunta 1: forma del entregable

| Opción | Qué incluye | A favor | En contra | Líneas autoría | Presupuesto |
|---|---|---|---|---|---|
| a. Solo Markdown por secciones | `docs/dashboard/01-dashboard-vp-cs.md`, layout ASCII + tabla por widget (métrica, definición, tabla fuente, filtro, acción) | Es literalmente lo que pide el caso ("boceto o descripción"); cero riesgo | No muestra números reales renderizados; menos persuasivo en vivo que A0 a A4 (código real) | ~150 a 250 | Sin riesgo |
| b. (a) + mockup HTML estático autocontenido (recomendada) | HTML bajo `docs/dashboard/`, sin JS ni librería externa, con las cifras reales de este dataset (los $2,216,115 y las 78 cuentas) en tablas y barras SVG inline; abre en GitHub o local | Cumple el caso y además es visualmente defendible en vivo, coherente con la sección 5 de la investigación; reusa el patrón "autocontenido" ya validado en el diagrama 05 | Los números quedan congelados a la fecha de redacción si no hay generador | ~350 a 500 | Dentro de 800, similar a A3 |
| c. (b) + generador Python (`worky_engine dashboard`) | Comando que reconstruye el HTML leyendo `health_scores.csv`/`master_dataset.csv` en cada corrida | Nunca se desincroniza; sigue el patrón de código real de A0 a A4 | Alcance no pedido por el texto del caso; nuevo subcomando + pruebas (~300 a 400 líneas extra); riesgo de comerse presupuesto de A6/Parte B | +300 a 400 | Riesgo medio de exceder 800 o necesitar PR encadenada |

Recomiendo (b), con (c) documentada como trabajo futuro (igual que A4 dejó Data Vault y la marca de agua), solo si sobra presupuesto tras A6 y Parte B.

## Pregunta 2: lógica del widget de riesgo real

Regla propuesta: la lista de prioridad solo incluye `churned = False AND flagged_15 = True` (78 cuentas hoy). Orden de prioridad: `flagged_15` primero, luego `mrr_mxn` descendente (no `health_score` ascendente): esto responde directo a la pregunta del caso, porque ordena por impacto en MRR dentro del mismo nivel de riesgo, no por qué tan bajo es el número. "Por qué está marcada" por cuenta: mostrar los 4 subpuntajes (momentum, cambio mes a mes, caída, antigüedad) como mini-barras, más `usage_months_asof` si es menor a 6. La banda "sin historia" se muestra en su propia vista de onboarding, nunca mezclada con "sano". Las 67 cuentas `riesgo alto` que ya hicieron churn se muestran solo en un panel separado de "evidencia del modelo" (cuántas se habrían detectado a tiempo), nunca en la cola de trabajo del CSM.

## Pregunta 3: la pregunta de $3,000 contra $45,000

No, el dashboard no debe tratarlas igual, y el mecanismo ya está fundamentado en el ADR-005 (un falso negativo en una cuenta grande cuesta más, recall ponderado por MRR): (1) la lista de prioridad ordena por MRR descendente dentro de `flagged_15`, así que la cuenta de $45,000 siempre aparece arriba de la de $3,000 con el mismo score; (2) el KPI "MRR en riesgo" agrega por cuenta, no cuenta cuentas, así que una sola cuenta grande mueve el número más que diez chicas; (3) un segundo eje de severidad visual (tamaño o color = tramo de MRR: menos de $5k, de $5k a $20k, más de $20k, pendiente de confirmación) sobre el mismo eje de riesgo, replicando la matriz riesgo por valor de la investigación y la promesa del journey. Evidencia real: HS-100065 ($2,947) y HS-100507 ($46,340) están en la misma banda hoy; con esta regla, HS-100507 sale primero en la lista y pesa 15 veces más en el KPI de MRR en riesgo.

## Pregunta 4: secciones del dashboard

| Sección | Fuente exacta | Cadencia |
|---|---|---|
| KPIs de encabezado (MRR en riesgo $2.2M, 78 cuentas marcadas, ~11 por CSM, lead time de 1 mes en 92.9 % de los casos) | `health_scores.csv` agregado + `validation.md` (detección temprana k=3) | Por corrida de `health` |
| Lista de prioridad (riesgo real por MRR) | `flagged_15=True AND churned=False`, ordenada por `mrr_mxn` descendente | Por corrida |
| Cohorte de onboarding (sin historia, activas) | `risk_band='sin historia' AND churned=False` (43 cuentas) | Por corrida |
| Carga por CSM | `dim_company.csm_owner` (warehouse) o `master_dataset.csm_owner` cruzado con la lista de prioridad | Por corrida |
| Tendencia en el tiempo (a futuro) | `fact_health_score_monthly` (warehouse, ADR-006): hoy solo una fecha; se puebla con corridas reales | Cuando existan 2 o más corridas |
| Drill-down por cuenta | `health_scores.csv` (4 subpuntajes) + `dim_company` (SCD2 de plan y CSM) | Por corrida |

## Pregunta 5: riesgos

- Inventar números si el mockup no se regenera del CSV real (mitigado por la opción c documentada, no ejecutada por defecto).
- Confundir `risk_band` con `flagged_15`: ya verificado y documentado arriba; el diseño debe fijar el filtro `churned=False` explícito en cada consulta.
- Mostrar el score sin la regla de capacidad (78, no 145) infla el problema frente al VP.
- Presupuesto de líneas y tiempo frente a A6 y la Parte B, que siguen pendientes.
- Lenguaje llano para un VP no técnico: los nombres de columnas técnicas no deben aparecer en el mockup, solo en la tabla de especificación.

## Recomendación

Opción (b): documento Markdown por secciones + mockup HTML autocontenido con las cifras reales de este dataset ($2,216,115 MXN en riesgo, 78 cuentas, el caso HS-100065/HS-100507 como ejemplo vivo de la pregunta del caso), filtrando siempre `churned=False` para la lista accionable. El generador Python (opción c) y la vista de tendencia real (`fact_health_score_monthly` con 2 o más corridas) quedan como trabajo futuro explícito.

## Decisiones de producto pendientes

1. **Forma del entregable (pregunta 1).** a, b (recomendada) o c. Consecuencia: (a) es más rápido pero menos persuasivo en vivo; (c) agrega ~300 a 400 líneas y riesgo de presupuesto frente a A6 y la Parte B.
2. **Tramos de MRR para el segundo eje visual (pregunta 3).** Sin ADR que fije umbrales; se proponen menos de $5k, de $5k a $20k y más de $20k con base en la distribución real (percentiles 54/43/3), pero el VP o el usuario puede preferir otro corte. Se recomiendan los propuestos.
3. **Fuente de datos del mockup:** marts de A1/A3 (`health_scores.csv`, `master_dataset.csv`) o el esquema en estrella de A4 (`dim_company`, `fact_health_score_monthly`). Se recomiendan los CSV de A1/A3 para el mockup estático (ya probados, sin dependencia de correr `warehouse`), y documentar el camino del warehouse para la vista de tendencia futura, tal como A4 dejó abierto.
4. **Qué hacer con las 67 cuentas ya churneadas dentro de `risk_band='riesgo alto'`.** Se recomienda un panel separado de "evidencia del modelo" (detección temprana), nunca mezclado con la cola de trabajo de 78 cuentas activas.
5. **Si se ejecuta el generador Python (opción c) en este corte o se documenta como trabajo futuro.** Se recomienda documentarlo, dado que A6 y la Parte B siguen pendientes y el caso no pide código para A5.

## Listo para propuesta

Sí, una vez que el usuario confirme las cinco decisiones de arriba. Ninguna cambia la regla central (`flagged_15 AND churned=False`, orden por MRR) ni las cifras ya verificadas contra el CSV real.

## Referencias

`docs/decisions/ADR-005-health-score-model.md` (incluida la Adenda 1), `docs/decisions/ADR-006-warehouse-model.md`, `outputs/health/health_scores.csv`, `outputs/health/validation.md`, `outputs/analysis/report.md` (A1.1), `outputs/warehouse/dim_company.csv`, `docs/data-model/01-warehouse-model.md`, `docs/research/01-bi-revops-data-architecture.md` sección 5, `docs/diagrams/src/05-journeys-por-actor.mmd`, `docs/diagrams/README.md`.
