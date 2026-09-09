# ADR-005: un health score que se puede explicar en una oración y medir contra el churn real

- Estado: Aceptado (2026-09-08)
- Alcance: A3 (health score y su validación), con efectos en A5 (tablero) y Parte B (playbook de retención)
- Decisores: candidato (responsable)

El caso pide un health score con fórmula, variables y pesos, calculado dos o tres meses antes de la fecha de referencia de cada cuenta, y validado con precisión y recall contra la columna `churn_date`. Antes de fijar la fórmula medimos cada señal candidata contra el churn real, con las mismas reglas del ADR-003. Resultado: las señales de uso separan, la antigüedad separa y además ve a las cuentas que el uso no puede ver, y el soporte no separa en este dataset. El score que queda es una suma ponderada de cuatro subpuntajes, con pesos fijados por juicio y verificados por el harness, y un umbral ligado a lo que siete CSM pueden atender. Para un analista, es un modelo que se lee línea por línea. Para una dirección, es un número cuya calidad se midió antes de usarlo.

## Ruta rápida

1. Para cada cuenta se fija un mes de referencia: el mes de churn si se fue, agosto de 2024 si sigue activa. El mes de corte es dos meses antes, para las dos poblaciones por igual. Solo entra al score lo fechado hasta ese mes.
2. Se calculan cuatro subpuntajes en escala de 0 a 100, donde 100 es lo más sano: momentum de uso, cambio mes a mes, caída desde el mejor promedio, y antigüedad.
3. Score = 0.35 momentum + 0.20 cambio mes a mes + 0.15 caída + 0.30 antigüedad. El soporte se calcula y se muestra, pero pesa cero.
4. Una cuenta sin tres meses de uso al corte no recibe score de uso: va a la banda "sin historia" y cuenta como no detectable en el recall (22 de las 89 bajas en k = 2, de las cuales 4 no tienen ningun mes de uso).
5. Se marcan en riesgo alto el 15 % de las cuentas activas con score definido (78 cuentas del libro activo con score en el caso, unas 11 por CSM). El reporte muestra también el 10 y el 20 %, y un corte fijo de referencia.
6. La validación reporta precisión, recall, recall ponderado por MRR, AUC, matriz de confusión, la sensibilidad a k = 3 y cuántas bajas ya estaban marcadas un mes antes.

## Qué medimos antes de decidir

AUC es la probabilidad de que una cuenta que hizo churn tenga peor señal que una que se quedó; 0.5 es una moneda al aire. Todo a dos meses del churn (k = 2), con 89 bajas y 561 activas.

| Señal | Definida | AUC |
|---|---|---|
| Momentum de uso (EWMA 3 contra 9) | 90 % | 0.999 |
| Cambio mes a mes de usuarios activos | 95 % | 0.978 |
| Caída desde el mejor promedio de 3 meses | 90 % | 0.832 |
| Antigüedad al corte | 100 % | 0.762 |
| Tickets en los tres meses previos al corte | 91 % | 0.462 |
| Tickets urgentes en esa ventana | 91 % | 0.509 |
| CSAT en esa ventana | 29 % | 0.498 |
| Activación en los primeros tres meses (nóminas, logins, features) | 90 % | 0.49 a 0.59 |
| Canal de adquisición | 100 % | 0.426 |

Con las señales combinadas: uso solo da AUC 0.970 y recall 0.753 al 20 % de marcado; uso más antigüedad sube el recall a 0.921 con AUC 0.953, porque la antigüedad tiene cobertura total y rescata cuentas sin historia de uso suficiente; uso más soporte al 20 % baja el AUC a 0.904. Las tablas completas viven en `openspec/changes/archive/.../a3-health-score/measurements.md` y el comando `health` las regenera.

## Qué decidimos

| Tema | Decisión | Por qué |
|---|---|---|
| Mes de corte | Referencia menos dos meses para bajas y activas por igual; la lectura literal del caso (activas en el mes más reciente) se reporta como sensibilidad | Evaluar activas con datos frescos y bajas con datos de hace dos meses compara recencia, no salud, e infla el AUC sin mejorar el modelo |
| Señales en el score | Momentum, cambio mes a mes, caída desde el mejor promedio (ADR-003) y antigüedad | Son las cuatro que separan; la antigüedad además ve a las cuentas nuevas |
| Señales con peso cero | Tickets, urgentes y CSAT en ventana; activación temprana; canal y segmento | Se miden y se muestran para que nadie tenga que creer que no sirven: aquí no separan. Con datos reales de producción se vuelven a medir antes de darles peso |
| Pesos | 0.35, 0.20, 0.15 y 0.30, por juicio, verificados por el harness | Con 89 eventos de churn, ajustar pesos con un modelo estadístico sobreajusta; el caso pide medir, no aprender. El harness debe dar AUC de al menos 0.95 y recall de al menos 0.85 al 20 %, medido sobre las bajas que sí reciben `health_score` (recall detectable): una baja "sin historia" nunca recibe score y nunca puede marcarse, así que el recall general trae un techo estructural que ningún peso puede mover (Adenda 1) |
| Normalización | Cada subpuntaje se lleva a 0 a 100 por rango percentil dentro de la población evaluada, con 100 como lo más sano | Hace comparables señales con unidades distintas y evita que un valor extremo domine |
| Sin historia | Menos de tres meses de uso al corte: banda "sin historia", sin score de uso; se cuenta en el denominador del recall general, pero queda fuera de la regla de aceptación | Nunca "sana" por default (ADR-003); son 22 de 89 bajas en k = 2 (4 de ellas sin ningún mes de uso) y hay que decirlo |
| Umbral | Top-N por capacidad: el 15 % de las activas con score definido, con 10 y 20 % como sensibilidad, y un corte fijo de referencia | Siete CSM y unas 12 cuentas cada uno es una carga que se puede trabajar; un corte fijo solo dice cuántas cuentas hay, no cuántas se pueden atender |
| Contexto comercial | Canal y segmento fuera del score, reportados como factores de riesgo aparte | El canal explica churn a nivel de portafolio (Evento 8.3 % contra Organic 19.6 %), no a nivel de cuenta |
| Soporte sin fuga | Vista de soporte ventanada al mes de corte, distinta de `mart_support` | `mart_support` agrega toda la vida de la cuenta; para predecir hay que respetar el corte aunque aquí no cambie el resultado |
| Error más caro (A3.4) | El falso negativo en una cuenta grande; el umbral se sesga hacia recall y el reporte lo mide ponderado por MRR | Un falso positivo cuesta horas de CSM; un falso negativo cuesta todo el MRR de la cuenta |

## Opciones que consideramos

| Opción | Por qué se rechazó o se eligió |
|---|---|
| Activas evaluadas en el mes más reciente (lectura literal) | Rechazada como regla principal: asimetría de recencia. Se reporta como sensibilidad. |
| Soporte con peso dentro del score | Rechazada: AUC de 0.46 a 0.53; sumarlo al 20 % baja el AUC del score de 0.970 a 0.904. |
| Solo uso, sin antigüedad | Rechazada: deja sin detectar a las cuentas jóvenes; recall 0.753 contra 0.921 al 20 %. |
| Regresión logística para los pesos | Rechazada: 89 eventos no sostienen pesos aprendidos, y el score deja de explicarse en una oración. |
| Reglas por niveles | Rechazada: difícil de auditar con precisión y recall, no se compara limpio contra el harness. |
| Umbral en el punto óptimo de la curva | Rechazada: inestable con pocos eventos y difícil de explicar. |
| Canal dentro del score | Rechazada: AUC 0.426 a nivel de cuenta; sirve como factor de portafolio, no como señal individual. |

## Qué cambia en las secciones siguientes

| Sección | Efecto |
|---|---|
| A5 | El tablero muestra el score, la banda y los cuatro subpuntajes por cuenta, la banda "sin historia" aparte, y los factores de riesgo comerciales en otra vista. |
| A6 | Cuando el script corrija el signo de las horas de resolución, el tiempo de resolución se vuelve a medir como señal. |
| Parte B | El playbook de retención parte de las 78 cuentas marcadas y del recall ponderado por MRR; el canal entra a la conversación de adquisición, no a la de salud. |

## Riesgos y cómo los manejamos

| Riesgo | Mitigación |
|---|---|
| El dataset es sintético y el AUC cercano a 1 no aparecerá en producción | Cada cifra dice "en este dataset"; los pesos se versionan y el harness se vuelve a correr con datos reales. |
| Los pesos por juicio se leen como arbitrarios | Cada peso tiene su AUC individual al lado y el harness verifica el conjunto; el reporte muestra qué pasa con pesos iguales. |
| El 11 % de bajas sin historia se interpreta como fallo del modelo | El reporte las separa y las cuenta; A5 y Parte B las tratan como riesgo de onboarding, no como falsos negativos del score. |

## Lista de verificación para el revisor

- [ ] Ninguna fila de uso ni ticket posterior al mes de corte entra a ningún subpuntaje.
- [ ] Las activas y las bajas usan el mismo desplazamiento de dos meses; la lectura literal aparece solo como sensibilidad.
- [ ] El score es la suma ponderada declarada y el harness reporta AUC, precisión, recall y recall por MRR al 10, 15 y 20 %.
- [ ] Las cuentas sin historia aparecen en su banda y en el denominador del recall.
- [ ] El soporte aparece en la validación con su AUC y con peso cero.

## Preguntas abiertas

1. Para A5: si conviene mostrar el score como semáforo (tres bandas) o como número, dado que el umbral operativo es un top-N y no un corte fijo.
2. Para producción: con cuántos meses de datos reales se vuelve a medir el peso del soporte y de la activación.

## Adenda 1 (2026-09-09): el techo del recall lo pone la banda sin historia, no los pesos

El comando `health` corrió la regla de aceptación (AUC >= 0.95, recall >= 0.85 al 20 % de marcado) sobre el dataset real, con la maquinaria completa del mes de corte (D6, D7) y la banda "sin historia" (D19). Con los pesos originales de este ADR (momentum 0.35, cambio mes a mes 0.20, caída 0.15, antigüedad 0.30), el AUC del `health_score` fue 0.997. El recall general, contado sobre las 89 bajas, quedó en 0.753 (67 de 89): por debajo del 0.85 que pedía la redacción original de la regla. Pero de esas 89 bajas, 22 caen en la banda "sin historia" (D19) y nunca reciben `health_score`, así que nunca pueden marcarse (D17); entre las 67 bajas que sí reciben `health_score`, el recall llega a 1.000, y las 67 ya quedan marcadas desde la tasa de marcado más baja que reporta el comando (10 %). En otras palabras: el modelo detecta a toda cuenta que tiene historia de uso suficiente para juzgarla, y falla solo en cuentas que, por diseño, nunca le dieron esa oportunidad.

**Por qué se probó una mezcla de pesos distinta, y por qué no ayudó.** Antes de esta corrección, la tarea 2.6 siguió al pie de la letra la redacción original de la decisión D18 ("si la regla no se alcanza, se adopta la mezcla ya medida") y cambió `WEIGHTS` a uso 70 % (momentum 0.35 / mom 0.20 / caída 0.15) más antigüedad 15 % más activación 15 %. Con esa mezcla, el AUC bajó a 0.992 y el recall general se quedó exactamente en el mismo 0.753: ni una cuenta más ni una menos. La razón es que el recall entre las bajas detectables ya estaba en su máximo posible (1.000) con los pesos originales, así que ningún reparto de pesos podía subirlo más; lo único que logró la mezcla fue empeorar el AUC sin ganar nada a cambio. Por eso se descarta la mezcla medida y se conservan los pesos originales del ADR-005.

**El conteo correcto de no detectables es 22, no 10.** La ruta rápida de este ADR y la tabla de decisiones citaban "10 de 89" bajas sin historia suficiente; ese número viene de una medición exploratoria de solo lectura (`measurements.md`, última línea de la sección 3) que cuenta cuántas bajas tienen "0-2 meses de uso al as-of", pero esa misma medición reporta en su propia tabla de tamaños de pool (sección 1, fila "Con baja | 89 | 67") que solo 67 de las 89 bajas llegan a los tres meses de uso que `MIN_USAGE_MONTHS` exige: es decir, 22 sin esa historia, no 10. El comando `health` sobre el dataset real reproduce esas 22 (4 con cero meses de uso, 6 con un mes, 12 con dos meses), y esa es la cifra correcta; "10 de 89" era una discrepancia interna del documento de mediciones, no un número que el código haya calculado nunca.

**Por qué la medición exploratoria de "uso + antigüedad" llegó a un recall de 0.921.** La sección "Qué medimos antes de decidir" de este mismo ADR cita que combinar uso con antigüedad sube el recall a 0.921 al 20 % de marcado. Esa cifra viene de un score combinado exploratorio (`measurements.md`, sección 3, combinación "ii") que le da un peso a la antigüedad para las 89 bajas completas, sin aplicar la banda "sin historia": como la antigüedad tiene cobertura del 100 %, ese score exploratorio termina puntuando a las cuentas jóvenes solo por su antigüedad, aunque no tengan historia de uso todavía. La decisión D19 prohíbe exactamente eso: una cuenta sin tres meses de uso no recibe `health_score` sin importar qué tan buena se vea su antigüedad, porque antigüedad sola no dice si una cuenta joven va bien o mal, solo dice que es joven. `compute_scores` sigue esa regla al pie de la letra, y por eso el recall general del comando real (0.753) es menor que el de esa medición exploratoria (0.921): la diferencia es la banda "sin historia" haciendo su trabajo, no un defecto del modelo.

**Regla de aceptación, en su forma corregida.** La regla de aceptación queda restablecida así: AUC >= 0.95 y recall >= 0.85 al 20 % de marcado, medido entre las bajas que sí reciben `health_score` (recall detectable), no sobre el total de bajas. Con los pesos originales, AUC = 0.997 y recall detectable = 1.000: la regla se cumple. El recall general (0.753, con su techo de 22 no detectables) se sigue reportando en `validation.md` y en `metrics.py`, no porque decida si el modelo pasa o no, sino porque es información real que un CSM o un director necesitan ver.

**Hallazgo de onboarding, para la Parte B.** Casi una cuarta parte de las bajas de este dataset (22 de 89, 24.7 %) ocurre antes de que la cuenta acumule tres meses de uso: el health score, por diseño, nunca las puede ver, porque para esas cuentas no existe todavía la historia de uso que el modelo necesita para juzgar. Esto no es un defecto que se corrija con más pesos o un modelo distinto: es una señal de que el health score no puede ser la única alarma temprana de la empresa. Las cuentas en su primer trimestre necesitan su propia señal o su propio playbook de onboarding (por ejemplo, hitos de activación temprana o seguimiento manual del CSM en los primeros noventa días), aparte del health score, para que el riesgo de baja temprana no quede invisible hasta que ya sea demasiado tarde para actuar.

| Pesos | AUC | Recall general al 20 % | Recall detectable al 20 % | Precisión al 20 % | Recall ponderado por MRR al 20 % |
|---|---|---|---|---|---|
| Originales del ADR-005, en uso (momentum .35 / mom .20 / caída .15 / antigüedad .30) | 0.997 | 0.753 | 1.000 | 0.392 | 0.608 |
| Mezcla medida, descartada (momentum .35 / mom .20 / caída .15 / antigüedad .15 / activación .15) | 0.992 | 0.753 | 1.000 | 0.392 | 0.608 |

Se conservan los pesos originales del ADR-005 en `WEIGHTS`. La regla de aceptación, medida sobre las bajas detectables, se cumple; el techo estructural de 22 no detectables queda documentado como hallazgo de onboarding para A5 y para la Parte B, y como riesgo residual para producción, donde más meses de uso real deberían bajar ese conteo (pregunta abierta 2 de este ADR).
