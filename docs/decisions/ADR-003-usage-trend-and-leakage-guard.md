# ADR-003: medir la tendencia de uso como momentum reciente, nunca en el mes de churn

- Estado: Aceptado (2026-09-07)
- Alcance: A0 (columna de tendencia del dataset maestro), A1.2 (consulta de caída de uso), A3 (señales de uso del health score)
- Decisores: candidato (responsable)

El dataset maestro necesita un número por empresa que diga si el uso del producto está creciendo o cayendo. Lo medimos como momentum: el promedio ponderado de los últimos tres meses de usuarios activos, comparado con el promedio ponderado de los últimos nueve, donde los meses recientes pesan más. Lo calculamos solo con meses anteriores al mes que estamos evaluando, para que el mes en que un cliente se fue nunca se filtre hacia el puntaje que se supone debe predecirlo. Para un analista, esto hace comparable una cuenta de dos meses de antigüedad con una de dos años. Para un director significa que el health score es honesto: un puntaje que espía la respuesta se ve perfecto en papel y falla en producción.

## Ruta rápida

1. Elegir el mes de referencia: el mes de churn para una empresa que se fue, agosto de 2024 (el último mes de los datos) para una empresa que sigue activa.
2. Retroceder k meses hasta el mes de corte (as-of month) (k = 2 para el health score, k = 3 como prueba de sensibilidad). Solo se permiten filas de uso hasta ese mes de corte.
3. Si la empresa tiene menos de 3 meses de uso hasta ese punto, se guarda el estado `insufficient_history`; si no tiene ninguno, se guarda `no_usage`. Nunca se guarda un NULL silencioso.
4. En cualquier otro caso se calcula el momentum: promedio móvil exponencialmente ponderado (EWMA) con span 3, dividido entre el EWMA con span 9, menos 1. Positivo significa que crece, negativo significa que cae.
5. El valor, el mes de corte y el estado se guardan en tres columnas: `trend_usage`, `trend_asof_month`, `trend_status`.

## Por qué el mes de churn debe quedar fuera

Corrimos un backtest: seis fórmulas de tendencia evaluadas sobre 78 empresas con churn que tienen uso y 515 activas. AUC es la probabilidad de que una empresa que hizo churn muestre una tendencia peor que una que se quedó; 0.5 equivale a lanzar una moneda y 1.0 es separación perfecta.

| Evaluado en | Resultado |
|---|---|
| El propio mes de churn (k = 0) | AUC de 1.000 para casi todas las fórmulas. El puntaje "predice" algo que ya pasó. |
| Dos meses antes (k = 2) | Separación real, ver la tabla siguiente. |
| Tres meses antes (k = 3) | Todas las fórmulas se debilitan. En este dataset la caída empieza unos tres meses antes del churn. |

## Cómo se compararon las fórmulas

Cada fórmula marcó al 20% de las empresas con la peor tendencia. "Definida" es la proporción de empresas para las que la fórmula se puede calcular.

| Fórmula | Definida | AUC en k = 2 | Recall en k = 2 | AUC en k = 3 |
|---|---|---|---|---|
| Primeros 3 meses contra últimos 3 meses (como lo redacta A1.2) | 76% | 0.980 | 49% | 0.814 |
| Últimos 3 meses contra los 3 meses anteriores | 76% | 0.962 | 47% | 0.764 |
| Pendiente normalizada a 6 meses | 85% | 0.996 | 65% | 0.829 |
| Caída (drawdown) desde el mejor promedio de 3 meses | 90% | 0.845 | 63% | 0.620 |
| Momentum, EWMA span 3 contra span 9 (elegida) | 90% | 1.000 | 77% | 0.894 |
| Mes contra mes anterior | 96% | 0.978 | 86% | 0.903 |

La cobertura pesó tanto como la precisión. Dos meses antes del churn, las empresas con churn tenían una mediana de 6 meses de historia de uso; 38 de las 78 tenían menos de 6 meses y 18 tenían menos de 3. Las empresas activas tenían una mediana de 16 meses. Cualquier fórmula que necesite 6 meses de historia queda ciega ante la mitad de las empresas que en realidad se fueron.

## Qué decidimos

| Tema | Decisión |
|---|---|
| Columna del dataset maestro | `trend_usage` = momentum (EWMA span 3 / EWMA span 9, menos 1) sobre `active_users` |
| Historia mínima | 3 meses; por debajo de eso el estado es `insufficient_history`, y `no_usage` cuando no hay filas |
| Resguardo contra fuga de datos (leakage guard) | Solo entran al cálculo los meses en el mes de corte o antes; el mes de corte se guarda junto al valor |
| Mes de referencia | El mes de churn para las empresas con churn; 2024-08 para las empresas activas (ver ADR-001, pregunta abierta 2) |
| Horizonte | k = 2 meses para el health score; k = 3 reportado como prueba de sensibilidad |
| Entradas del health score (A3) | Tres subpuntajes de uso separados: momentum (tendencia), cambio mes a mes (choque), y caída desde el mejor promedio de 3 meses (nivel). Cada uno tiene su propio peso. |
| Consulta A1.2 | Se entrega exactamente como lo redacta el caso (primeros 3 meses contra los 3 meses antes del churn). Responde la pregunta planteada; no es la columna del dataset maestro. |
| Harness del backtest | Se conserva en el repositorio y se vuelve a correr cada vez que cambia una fórmula o un parámetro. Reporta la proporción definida, AUC, precisión y recall a una tasa de marcado ligada a la capacidad de los CSM, el recall ponderado por MRR, y el lead time. |

## Opciones que consideramos

| Opción | Por qué se rechazó o se eligió |
|---|---|
| Usar la redacción de A1.2 como columna de tendencia | Rechazada como columna: necesita 6 meses de historia, mezcla la rampa de onboarding con la caída real, y queda indefinida para el 24% de las empresas. Se conserva como la respuesta de A1.2. |
| Pendiente normalizada sobre los últimos 6 meses | Rechazada: fuerte en k = 2, débil en k = 3, y difícil de explicar a alguien sin perfil técnico. |
| Momentum, EWMA span 3 contra span 9 | Elegida: funciona desde 3 meses de historia, la mejor separación en ambos horizontes entre las fórmulas libres de escala, y se explica en una sola oración. Costo: los dos spans necesitan justificación, que el harness aporta. |
| Tres subpuntajes de uso para A3 | Elegida: refleja cómo Vitally y Gainsight estructuran sus health scores (subpuntajes ponderados y transparentes) y mantiene una señal de caída separada de una señal de nivel, como recomienda la investigación. |

## Qué cambia en las secciones siguientes

| Sección | Efecto |
|---|---|
| A1.2 | La consulta usa la fórmula literal del caso y regresa las empresas ordenadas por la mayor caída relativa. |
| A3 | El puntaje en k = 2 usa los tres subpuntajes de uso más las señales de soporte; la precisión, el recall y el lead time salen del harness. |
| A5 | Las empresas con `insufficient_history` se muestran como un grupo aparte, nunca como "sanas" por default. |
| Parte B | La mitad del churn ocurre temprano en la relación con el cliente, así que el onboarding y la activación merecen su propia señal de riesgo. |

## Riesgos y cómo los manejamos

| Riesgo | Mitigación |
|---|---|
| El dataset es sintético; un AUC de 1.000 no va a aparecer en producción | Se aclara "en este dataset" en cada afirmación, y se espera una separación menor con datos reales. |
| Los spans (3 y 9) se eligieron a partir de este backtest | Se versionan, se vuelve a correr el harness ante cualquier cambio, y se reporta la sensibilidad en k = 3. |
| Las cuentas jóvenes no tienen tendencia | El estado `insufficient_history` es explícito, y A3 recibe una señal de fase de onboarding (ver preguntas abiertas). |

## Lista de verificación para el revisor

- [ ] Ninguna fila de uso posterior a `trend_asof_month` entra a `trend_usage` para esa empresa.
- [ ] Cada empresa tiene uno de los tres estados; ningún trend en NULL sin estado.
- [ ] La salida del harness en el repositorio coincide con la tabla anterior para k = 0, 2 y 3.
- [ ] La consulta A1.2 usa la fórmula literal del caso, y el dataset maestro usa el momentum.

## Preguntas abiertas

1. Señal de fase de onboarding para A3: qué métrica de activación (por ejemplo `payroll_runs_completed` en los primeros meses) separa mejor el churn temprano.
2. Tasa de marcado para A3: la proporción de empresas que se marcan en riesgo debe salir de la capacidad de los CSM (7 CSMs), y el recall también debe reportarse ponderado por MRR.
