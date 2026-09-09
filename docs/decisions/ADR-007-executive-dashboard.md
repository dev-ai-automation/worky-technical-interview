# ADR-007: un tablero ejecutivo que ordena por MRR dentro del mismo riesgo, para que $45,000 nunca pese lo mismo que $3,000

- Estado: Aceptado (2026-09-09)
- Alcance: A5 (tablero ejecutivo), con efectos en la Parte B (B2 dashboards y B4 resumen ejecutivo)
- Decisores: candidato (responsable)

El caso pide un wireframe (boceto o descripción por secciones) del tablero que vería el VP de Customer Success, con los datos reales de este caso: qué cuentas están en riesgo real, priorizadas por impacto en MRR, y qué pasa si dos cuentas comparten health score pero su MRR es muy distinto. El journey de A0 (`docs/diagrams/src/05-journeys-por-actor.mmd`) ya prometía esa vista: matriz de riesgo por MRR y el ingreso en riesgo como KPI único destacado. Antes de diseñar una sola sección se leyó el CSV real que produce A3, y ahí apareció un hallazgo que cambia el diseño: `risk_band = 'riesgo alto'` mezcla 78 cuentas activas con 67 que ya hicieron churn, así que usar esa columna sola en el tablero le mostraría al VP cuentas que ya no existen como si fueran trabajo pendiente. Resultado: un wireframe en Markdown más un mockup HTML autocontenido, construidos con las cifras reales de `health_scores.csv`, que ordenan por MRR dentro del mismo nivel de riesgo y nunca usan `risk_band` sola como filtro.

## Ruta rápida

1. El entregable son dos archivos: `docs/dashboard/01-dashboard-vp-cs.md` (wireframe por secciones) y `docs/dashboard/02-mockup-vp-cs.html` (mockup autocontenido, sin librerías externas, que abre en local y en GitHub), los dos con las cifras reales de este dataset.
2. La cola de trabajo del CSM es `flagged_15 = True AND churned = False`: 78 cuentas activas, el 15.06 % del libro activo con score (518 cuentas), unas 11 por CSM. Nunca `risk_band = 'riesgo alto'` sola, que trae 145 filas y mezcla 67 cuentas que ya se fueron.
3. Dentro de la misma banda de riesgo, la lista ordena por `mrr_mxn` descendente, no por qué tan bajo es el score. Un segundo eje visual usa tramos de MRR: menos de $5,000, de $5,000 a $20,000, y más de $20,000.
4. El KPI de encabezado es "MRR en riesgo": $2,216,115 MXN, el 13.7 % del MRR activo total ($16,223,225.50 MXN). Una sola cuenta Enterprise ($952,602) concentra el 43 % de ese monto.
5. Las 67 cuentas de riesgo alto que ya hicieron churn aparecen solo en un panel separado de "evidencia del modelo" (detección temprana), nunca dentro de la cola de trabajo. La banda "sin historia" separa a 22 bajas reales (que sí cuentan en el denominador del recall) de 43 cuentas activas nuevas, mostradas en su propia vista de onboarding.
6. El mockup lee `outputs/health/health_scores.csv` y `outputs/master_dataset.csv` (A1/A3), no el esquema en estrella de A4. La vista de tendencia en el tiempo queda documentada como el camino que abre `fact_health_score_monthly` una vez existan dos o más corridas del comando `warehouse`.
7. Un generador en Python (`worky_engine dashboard`) que reconstruya el HTML en cada corrida queda documentado como trabajo futuro; no se construye en este corte.

## Qué secciones tiene el tablero

El wireframe organiza el tablero en seis secciones, cada una con su fuente exacta y su cadencia de actualización, para que el revisor pueda rastrear cada widget hasta el archivo que lo alimenta.

| Sección | Fuente exacta | Cadencia |
|---|---|---|
| KPIs de encabezado (MRR en riesgo, cuentas marcadas, carga por CSM, lead time a k = 3) | `health_scores.csv` agregado más `validation.md` | Por corrida del comando `health` |
| Lista de prioridad (riesgo real por MRR) | `flagged_15=True AND churned=False`, ordenada por `mrr_mxn` descendente | Por corrida |
| Cohorte de onboarding (sin historia, activas) | `risk_band='sin historia' AND churned=False` (43 cuentas) | Por corrida |
| Carga por CSM | `csm_owner` cruzado con la lista de prioridad | Por corrida |
| Tendencia en el tiempo | `fact_health_score_monthly` (A4); hoy una sola fecha, se llena con corridas reales | Cuando existan dos o más corridas |
| Drill-down por cuenta | Los cuatro subpuntajes de `health_scores.csv` más el historial de plan y CSM de `dim_company` (SCD2, A4) | Por corrida |

## Qué medimos antes de decidir

Cada cifra de abajo viene de leer `health_scores.csv` y `master_dataset.csv` directamente, no de repetir un número ya escrito en otro documento. Es la misma disciplina de verificación de los ADR anteriores: antes de fijar una regla de diseño, se corrobora contra los datos reales.

| Cifra | Valor | Fuente |
|---|---|---|
| Cola de trabajo real (`flagged_15=True`, `churned=False`) | 78 cuentas, 15.06 % de 518 activas con score | `health_scores.csv` |
| `risk_band = 'riesgo alto'` sin filtrar `churned` | 145 filas (78 activas + 67 ya churneadas) | `health_scores.csv` |
| MRR en riesgo | $2,216,115 MXN, 13.7 % del MRR activo | `health_scores.csv` |
| MRR activo total | $16,223,225.50 MXN, 561 cuentas | `outputs/analysis/report.md` (A1.1) |
| Concentración en una cuenta | Una Enterprise de $952,602 es el 43 % del MRR en riesgo | `health_scores.csv` |
| "Sin historia" | 65 filas: 22 bajas reales sin tres meses de uso + 43 activas nuevas | `health_scores.csv`, ADR-005 Adenda 1 |
| Tramos de MRR entre activas | Menos de $5k: 131; de $5k a $20k: 250; más de $20k: 180 | `preproposal.yaml`, verified_counts |
| Carga por CSM (marcadas) | Jorge Ibarra 21, Ana Ruiz 15, Diego Ortega 10, Luis Peña 10, Carla Nuñez 9, Fernanda Solís 8, Marta Díaz 5 | `preproposal.yaml`, verified_counts |
| Detección temprana a k = 3 | 92.9 % (52 de 56 cuentas evaluables) ya estaban marcadas un mes antes | `outputs/health/validation.md` |
| Ejemplo vivo | HS-100065 (SMB, $2,947, score 35.56) y HS-100507 (Enterprise, $46,340, score 27.68), misma banda | `exploration.md` |

La tasa de marcado del 15 % no se eligió sola: se comparó contra 10 % y 20 % para ver cuánto trabajo le tocaría a cada CSM antes de fijar el umbral que alimenta la lista de prioridad.

| Tasa de marcado | Libro activo con score | Marcadas | Marcadas por CSM |
|---|---|---|---|
| 10 % | 518 | 52 | 7.4 |
| 15 % (elegida) | 518 | 78 | 11.1 |
| 20 % | 518 | 104 | 14.9 |

## Qué decidimos

| Tema | Decisión | Por qué |
|---|---|---|
| Forma del entregable | Markdown por secciones más mockup HTML autocontenido con cifras reales | Cumple la lectura literal del caso y además es defendible en vivo; el generador Python queda para después de A6 y la Parte B |
| Cola de trabajo del CSM | `flagged_15 = True AND churned = False` (78 cuentas), nunca `risk_band` sola | `risk_band = 'riesgo alto'` mezcla 67 cuentas que ya no existen; mostrarlas como trabajo pendiente confunde al VP |
| Orden de prioridad | `mrr_mxn` descendente dentro de la misma banda de riesgo | Responde directo a la pregunta del caso: ordena por impacto, no por qué tan bajo es el número |
| Respuesta a $3,000 contra $45,000 | No se tratan igual: el orden por MRR, el KPI que agrega MRR y el segundo eje por tramos hacen que la cuenta grande siempre pese más | El ADR-005 ya fundamentó que un falso negativo en una cuenta grande cuesta más; A5 lo hace visible en la interfaz |
| Tramos de MRR | Menos de $5k, de $5k a $20k, más de $20k | Corte basado en la distribución real (percentiles 54/43/3 de la cartera), confirmado por el usuario |
| Cuentas ya churneadas en riesgo alto | Panel separado de "evidencia del modelo", nunca en la cola de trabajo | Muestran qué tan bien detecta el modelo, no qué debe hacer un CSM hoy |
| Banda "sin historia" | Vista propia de onboarding, nunca mezclada con "sana" | Son cuentas nuevas sin tres meses de uso, no cuentas verificadas como sanas (ADR-005) |
| Fuente de datos del mockup | CSV de A1/A3 (`health_scores.csv`, `master_dataset.csv`) | Ya están probados y no dependen de correr `warehouse`; la tendencia futura queda documentada sobre A4 |
| Lenguaje del mockup | Sin nombres de columnas técnicas; esos nombres solo viven en la tabla de especificación | El VP de Customer Success no es un perfil técnico |
| Generador Python | Documentado como trabajo futuro, no construido en este corte | A6 y la Parte B siguen pendientes; el caso no pide código ejecutable para A5 |

## Opciones que consideramos

| Opción | Por qué se rechazó o se eligió |
|---|---|
| Solo Markdown por secciones | Rechazada como única entrega: cumple el caso pero congela las cifras en texto plano, menos persuasivo en vivo que el resto del proyecto |
| Markdown más mockup HTML con cifras reales (elegida) | Cumple el caso y demuestra las cifras reales en una interfaz visual, coherente con la investigación de la sección 5 |
| Markdown más mockup más generador Python ejecutado ahora | Rechazada: agrega 300 a 400 líneas de código no pedidas por el caso y compite por presupuesto con A6 y la Parte B |
| Usar `risk_band` como filtro de la cola de trabajo | Rechazada: mezcla cuentas activas con cuentas que ya hicieron churn, verificado al leer el CSV |
| Esquema en estrella de A4 como fuente del mockup | Rechazada por ahora: los CSV de A1/A3 ya están probados; el warehouse queda como camino documentado para la tendencia en el tiempo |
| Excluir del tablero a las 67 cuentas ya churneadas | Rechazada: esconder la evidencia de detección temprana le quita al VP la prueba de que el modelo funciona |

## Qué cambia en las secciones siguientes

| Sección | Efecto |
|---|---|
| Parte B (B2, dashboards) | El wireframe y el mockup de este ADR son la base directa de los dashboards de retención; la regla `flagged_15 AND churned=False` y el orden por MRR se reutilizan sin volver a derivarlos |
| Parte B (B4, resumen ejecutivo) | El KPI "MRR en riesgo" y el ejemplo HS-100065 contra HS-100507 se citan como evidencia de que el diseño responde la pregunta del caso, no solo la describe |

## Riesgos y cómo los manejamos

| Riesgo | Mitigación |
|---|---|
| Las cifras del mockup se desincronizan si el CSV cambia y nadie las regenera a mano | El documento declara la fecha de corte y las cifras exactas usadas; el generador Python queda como la solución de fondo, documentado como trabajo futuro |
| Confundir `risk_band` con `flagged_15` en una lectura rápida | Cada consulta del diseño fija el filtro `churned=False` de forma explícita y el wireframe lo explica en su propia sección |
| Mostrar el score sin la regla de capacidad infla el problema frente al VP | El encabezado siempre reporta 78 cuentas y 11 por CSM, nunca las 145 de `risk_band` sin filtrar |
| Presupuesto de líneas y tiempo frente a A6 y la Parte B | La opción con generador Python se documenta pero no se ejecuta en este corte |

## Lista de verificación para el revisor

- [ ] La cola de trabajo del mockup usa `flagged_15 = True AND churned = False` y nunca `risk_band` sola.
- [ ] El orden dentro de cada banda de riesgo es `mrr_mxn` descendente.
- [ ] El KPI "MRR en riesgo" y el total de MRR activo coinciden con las cifras de esta tabla.
- [ ] Las 67 cuentas ya churneadas de `risk_band = 'riesgo alto'` aparecen solo en el panel de evidencia del modelo.
- [ ] La banda "sin historia" separa a las 22 bajas reales de las 43 cuentas activas nuevas.
- [ ] El mockup no usa librerías externas y abre tanto en local como en GitHub.
- [ ] Ningún nombre de columna técnica aparece en el mockup mismo, solo en la tabla de especificación.

## Preguntas abiertas

1. Cuántas corridas reales del comando `warehouse` hacen falta para que `fact_health_score_monthly` dé una tendencia útil en el tablero, más allá de la fecha única de corte que existe hoy.
2. Si el generador Python de la opción rechazada se construye después de A6 y la Parte B, o se deja como mejora de producción fuera del alcance de este caso.
3. Si el VP de Customer Success prefiere ver el segundo eje de MRR como color, como tamaño de burbuja, o como ambos a la vez, una vez que exista el mockup para revisarlo en vivo.
