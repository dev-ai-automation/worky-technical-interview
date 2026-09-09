# Especificación: health score con validación medida (`health-score`)

## Propósito

Implementa el modelo del ADR-005: un puntaje de salud por empresa calculado en el mes de corte de la fecha de referencia de cada cuenta, con cuatro subpuntajes ponderados, la banda "sin historia", los umbrales por capacidad de los CSM y la validación medida contra `churn_date`. Cubre el comando `health`, sus dos salidas y las métricas de validación, incluidos el recall ponderado por MRR y la detección temprana.

## ADDED Requirements

### Requirement: comando `health` sin build previo

El comando `python -m worky_engine health --data-dir <dir> --out-dir outputs/health` MUST abrir su propia conexión de DuckDB, resolver identidad y ensamblar el dataset maestro en memoria sin depender de una corrida previa de `build` o `analyze`. MUST declarar el motor DuckDB 1.5.5, MUST escribir `outputs/health/health_scores.csv` y `outputs/health/validation.md`, MUST terminar con el mismo patrón de códigos de salida que `build` (cero en éxito, distinto de cero con mensaje en español si falta una base o una dependencia), y MUST NOT leer ni modificar ninguna salida existente bajo `outputs/` de A0 o A1.

#### Scenario: corrida sin build previo

- Dado un repositorio recién clonado, sin haber corrido `build` ni `analyze`
- Cuando alguien corre `python -m worky_engine health --data-dir ... --out-dir outputs/health`
- Entonces el comando termina en 0 y `outputs/health/` contiene `health_scores.csv` y `validation.md`

#### Scenario: dos corridas idénticas

- Dado la misma entrada sin cambios
- Cuando alguien corre `health` dos veces seguidas
- Entonces los archivos de la segunda corrida bajo `outputs/health/` son idénticos byte por byte a los de la primera

#### Scenario: goldens de A0 y A1 sin cambio

- Dado los goldens existentes de A0 y A1, incluido `backtest_report.md`
- Cuando alguien corre `health`
- Entonces ningún archivo fuera de `outputs/health/` cambia

#### Scenario: falta una dependencia o una base de datos

- Dado que falta DuckDB o una de las tres bases SQLite de origen
- Cuando alguien corre `health`
- Entonces el comando termina con código distinto de cero y un mensaje en español que nombra lo que falta, sin escribir salidas parciales

### Requirement: mes de corte igual para bajas y activas

El mes de referencia MUST ser el mes de `churn_date` para las cuentas con baja y el mes de cierre de los datos para las activas, derivado de los datos y no escrito como constante (2024-08 en el caso). El mes de corte (as-of) MUST ser el mes de referencia menos 2 meses, con el mismo desplazamiento para las dos poblaciones. Ninguna fila de uso ni de soporte fechada después del mes de corte MUST entrar a ningún subpuntaje, y para eso el soporte MUST leerse de una vista nueva ventanada al corte (`mart_support_asof`), sin modificar `mart_support.sql`. k = 3 y la lectura literal del caso (activas evaluadas en el mes más reciente) MUST reportarse solo como sensibilidad, nunca como la regla principal.

#### Scenario: mismo desplazamiento para las dos poblaciones

- Dado una cuenta con baja y una cuenta activa
- Cuando el comando calcula su mes de corte
- Entonces ambas usan su propio mes de referencia menos 2 meses, sin distinción por estado de baja

#### Scenario: ningún dato posterior al corte entra al subpuntaje

- Dado un ticket o una fila de uso fechada después del mes de corte de una cuenta
- Cuando el comando calcula los subpuntajes de esa cuenta
- Entonces esa fila queda excluida del cálculo

#### Scenario: lectura literal como sensibilidad

- Dado el reporte de validación
- Cuando alguien busca la lectura literal del caso para las activas
- Entonces la encuentra en la tabla de sensibilidad, separada de las métricas con el mes de corte principal

### Requirement: los cuatro subpuntajes normalizados por percentil

El comando MUST calcular, en el mes de corte de cada cuenta, momentum (EWMA span 3 contra span 9), cambio mes a mes de `active_users`, caída desde el mejor promedio de 3 meses, y antigüedad en meses desde `signup_date` al corte. Cada subpuntaje MUST normalizarse a una escala de 0 a 100 por rango percentil dentro de la población evaluada, con 100 como el valor más sano.

#### Scenario: subpuntaje de momentum en el mes de corte

- Dado el EWMA span 3 y span 9 de una cuenta hasta su mes de corte
- Cuando el comando calcula su subpuntaje de momentum
- Entonces el valor normalizado queda entre 0 y 100, con 100 para la cuenta con mejor momentum de la población evaluada

#### Scenario: antigüedad con cobertura total

- Dado el `signup_date` de cualquier cuenta, con o sin historia de uso suficiente
- Cuando el comando calcula el subpuntaje de antigüedad
- Entonces la cuenta recibe un valor normalizado, incluidas las cuentas en banda "sin historia"

### Requirement: señales medidas con peso cero

El comando MUST calcular y publicar, sin darles peso en el score, tickets totales y urgentes y CSAT promedio en la ventana de 3 meses hasta el corte (`mart_support_asof`), y un puntaje de activación de los primeros 3 meses de uso. Estas señales MUST aparecer en `health_scores.csv` y en la tabla de AUC por señal de `validation.md`.

#### Scenario: columnas de peso cero en el CSV

- Dado `health_scores.csv`
- Cuando se inspeccionan sus columnas
- Entonces incluye `tickets_window_total`, `tickets_window_urgent`, `csat_window_avg` y `activation_score`

#### Scenario: AUC de las señales de peso cero

- Dado `validation.md`
- Cuando se busca la tabla de AUC por señal
- Entonces las señales de soporte y activación aparecen con su AUC individual y su peso de cero en la fórmula

### Requirement: score como suma ponderada de los subpuntajes del ADR-005

El `health_score` de cada cuenta con subpuntajes de uso definidos MUST calcularse como 0.35 × momentum + 0.20 × cambio mes a mes + 0.15 × caída + 0.30 × antigüedad, sobre los cuatro subpuntajes normalizados.

#### Scenario: suma ponderada verificable

- Dado los cuatro subpuntajes normalizados de una cuenta
- Cuando el comando calcula su `health_score`
- Entonces el valor es igual a la suma ponderada con los pesos 0.35, 0.20, 0.15 y 0.30

### Requirement: banda "sin historia" para cuentas sin uso suficiente

Una cuenta con menos de 3 meses de uso hasta su mes de corte MUST recibir `risk_band = "sin historia"`, MUST NOT recibir los tres subpuntajes de uso ni `health_score`, y MUST contarse en el denominador del recall como no detectable.

#### Scenario: cuenta nueva sin subpuntajes de uso

- Dado una cuenta con 1 mes de uso hasta su mes de corte
- Cuando el comando calcula su fila en `health_scores.csv`
- Entonces `risk_band` es "sin historia" y los tres subpuntajes de uso quedan vacíos

#### Scenario: contada en el recall como no detectable

- Dado una cuenta con baja en banda "sin historia"
- Cuando `validation.md` calcula el recall
- Entonces esa cuenta cuenta en el denominador y no aparece marcada como detectada

### Requirement: tasas de marcado por capacidad de CSM

El comando MUST marcar `flagged_10`, `flagged_15` y `flagged_20` como el top 10 %, 15 % y 20 % por `health_score` entre las cuentas activas con score definido, MUST reportar además un corte fijo de referencia, y MUST documentar el 15 % como umbral operativo (81 cuentas, unas 12 por cada uno de los 7 CSM). `risk_band` MUST tomar solo los valores "sin historia", "riesgo alto" (el 15 % marcado), "riesgo medio" (el siguiente 15 % del libro activo) y "riesgo bajo".

#### Scenario: 81 cuentas marcadas al 15 %

- Dado las cuentas activas con `health_score` definido
- Cuando el comando marca el 15 % con peor score
- Entonces el resultado marca 81 cuentas, documentadas como unas 12 por CSM

#### Scenario: corte fijo reportado aparte

- Dado `validation.md`
- Cuando se busca el corte fijo de referencia
- Entonces aparece junto a las tres tasas de marcado, sin sustituir al 15 % operativo

### Requirement: métricas de validación contra `churn_date`

`validation.md` MUST reportar, al 10, 15 y 20 % de marcado, precisión, recall, recall ponderado por MRR y AUC; MUST incluir la matriz de confusión al 15 %; MUST contar las cuentas no detectables por falta de historia; MUST reportar la detección temprana en k = 3 como la proporción de cuentas con baja marcadas en k = 2 que ya estaban marcadas un mes antes en k = 3; y MUST incluir tablas de sensibilidad para k = 3 y para la lectura literal del mes de corte en las activas.

#### Scenario: tabla de métricas a las tres tasas

- Dado `validation.md`
- Cuando se abre la sección de métricas
- Entonces muestra precisión, recall, recall ponderado por MRR y AUC en 10, 15 y 20 %

#### Scenario: detección temprana definida sobre las marcadas en k = 2

- Dado las cuentas con baja marcadas al 15 % en k = 2 con historia suficiente en k = 3
- Cuando el comando calcula la detección temprana
- Entonces reporta qué proporción de esas cuentas ya estaba marcada un mes antes, en k = 3

#### Scenario: tabla de sensibilidad en k = 3

- Dado `validation.md`
- Cuando se busca la sensibilidad al horizonte k = 3
- Entonces muestra cómo cambian AUC y recall frente al mes de corte principal en k = 2

### Requirement: aceptación del harness sobre los pesos del ADR-005

El comando MUST verificar, sobre el dataset del caso, si el score con los pesos 0.35 / 0.20 / 0.15 / 0.30 alcanza AUC de al menos 0.95 y recall de al menos 0.85 al 20 % de marcado. Si no los alcanza, `validation.md` MUST reportarlo y el resultado MUST recomendar adoptar la mezcla medida (uso 70 %, antigüedad 15 %, activación 15 %) como adenda al ADR-005.

#### Scenario: los pesos por juicio pasan el harness

- Dado el score con los pesos del ADR-005 sobre el dataset del caso
- Cuando el harness verifica AUC y recall al 20 %
- Entonces `validation.md` confirma que ambos umbrales se cumplen

#### Scenario: los pesos no pasan y se recomienda la mezcla medida

- Dado que el score con los pesos del ADR-005 no alcanza alguno de los dos umbrales
- Cuando el harness reporta el resultado
- Entonces `validation.md` muestra la mezcla medida (uso 70, antigüedad 15, activación 15) como alternativa a documentar en una adenda al ADR-005

### Requirement: respuesta narrativa de A3.4 en `validation.md`

`validation.md` MUST incluir una sección que responda A3.4: un falso positivo cuesta horas de un CSM en una cuenta sana, un falso negativo cuesta el MRR completo de la cuenta que se va, el error más caro es un falso negativo en una cuenta grande, y el umbral operativo MUST sesgarse hacia recall aunque baje la precisión.

#### Scenario: narrativa de A3.4 presente

- Dado `validation.md`
- Cuando se busca la sección de A3.4
- Entonces explica el costo asimétrico de cada tipo de error y por qué el umbral se sesga hacia recall

### Requirement: contexto comercial fuera del score

`acquisition_channel` y `segment` MUST aparecer en `health_scores.csv` y en `validation.md` como factores de riesgo comerciales reportados aparte, y MUST NOT entrar como término de la fórmula del `health_score`.

#### Scenario: canal y segmento en el CSV sin pesar en el score

- Dado `health_scores.csv`
- Cuando se inspecciona la fórmula del `health_score` de cualquier fila
- Entonces `acquisition_channel` y `segment` están presentes en la fila pero no son parte de la suma ponderada

### Requirement: pruebas por regla y sobre el dataset real

Cada regla del ADR-005 (exclusión por mes de corte, normalización percentil, banda "sin historia", suma ponderada, tasas de marcado) MUST tener una prueba sobre un fixture mínimo, y las cifras fijadas por el dataset real MUST tener una prueba marcada `dataset` que fije 89 cuentas con baja, 10 no detectables en k = 2, 81 cuentas marcadas al 15 %, y que el harness cumple los umbrales de AUC y recall al 20 % o que la adenda queda documentada.

#### Scenario: prueba de fixture por regla

- Dado un fixture mínimo con una fila de uso posterior al mes de corte
- Cuando la prueba corre el cálculo de subpuntajes sobre ese fixture
- Entonces la prueba verifica que esa fila queda excluida

#### Scenario: prueba marcada dataset con los números reales

- Dado el dataset real y la marca `dataset` de pytest
- Cuando la prueba corre `health` sobre ese dataset
- Entonces compara el resultado contra 89 cuentas con baja, 10 no detectables en k = 2 y 81 cuentas marcadas al 15 %
