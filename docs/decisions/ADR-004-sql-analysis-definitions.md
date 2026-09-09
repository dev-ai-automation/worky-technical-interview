# ADR-004: definiciones de las consultas de A1 antes de escribir el SQL

- Estado: Aceptado (2026-09-08)
- Alcance: A1 (SQL sobre la sábana), con efectos en A3 (señales de soporte), A5 (tablero) y A6 (script de limpieza)
- Decisores: candidato (responsable)

La sección A1 del caso pide siete consultas sobre la sábana de A0. Cuatro de ellas tienen más de una lectura posible, y cada lectura da un número distinto. Este documento fija esas lecturas antes de escribir una línea de SQL, para que el evaluador vea la definición primero y el resultado después, y para que nadie tenga que rehacer las consultas cuando alguien pregunte "¿y por qué así?". Para un analista, son las reglas de negocio de cada consulta. Para una dirección, es la garantía de que un número de MRR, retención o atribución significa lo mismo cada vez que se reporta.

## Ruta rápida

1. El motor de SQL es DuckDB 1.5.5, el mismo que ensambla la sábana; las consultas viven en el repositorio y se corren con un comando.
2. Cada consulta parte de la sábana (`master_dataset`) y regresa a las tablas de origen solo cuando el caso lo pide: uso mensual para A1.2, touches y deals para A1.4, deals para A1.5, tickets para A1.6.
3. Las definiciones de abajo son las que valen; el reporte de resultados las repite junto a cada consulta.

## Qué decidimos

| Consulta | Definición | Por qué |
|---|---|---|
| A1.1 MRR activo | Una tabla segmento por industria con dos columnas de MRR: el que reporta el CRM y el total con valores imputados (ADR-002), más una fila de totales. "El" MRR activo es el total con imputados; el del CRM va al lado. Activa significa `churn_date` nulo. | El caso pide un número; el ADR-002 obliga a mostrar de dónde sale la diferencia entre ambos. |
| A1.2 caída de uso | Fórmula literal del caso: promedio de `active_users` en los tres meses calendario anteriores al mes de baja, contra el promedio de los primeros tres meses con uso de la cuenta; caída relativa = (inicial menos final) entre inicial; orden descendente. El mes de baja no entra. Se entregan las 89 cuentas con churn y cuenta de producto, con una columna `windows_overlap` que marca a las 30 con menos de seis meses de uso. | Incluir el mes de baja es leer la respuesta antes de predecirla (ADR-003). Con menos de seis meses las dos ventanas se traslapan y la fórmula dice "subió" cuando la cuenta apenas arrancaba; marcarlo es más honesto que ocultarlas o dejarlas fuera. |
| A1.3 retención por cohorte | Cohorte por mes de `signup_date` de HubSpot. Una cuenta sigue activa en el mes k si no ha hecho churn k meses después del alta. Las celdas de cohortes que no cumplen k meses al cierre de los datos (agosto de 2024) quedan vacías; no se calculan con dato parcial. Una sola consulta con CTEs. | La fecha de alta comercial es la del contrato; la de la cuenta de producto es otro sistema y otra fecha. Calcular una celda con cohortes a medias mezcla sobrevivientes con recién llegados y exagera la retención. |
| A1.4 atribución | Grano deal. Cada deal se atribuye a dos canales: el primer touch de su empresa y el último touch anterior a la fecha de creación del deal. Convierte si su etapa es `closedwon`. La tasa por canal es deals ganados entre deals atribuidos. Empates por `touch_id`, igual que el motor. Se reportan ambos modelos lado a lado y se dice si cambia el canal ganador. | El caso habla de deals, no de empresas, y el último touch solo tiene sentido relativo a un evento con fecha. Con cerca de 1.5 deals por empresa, el grano cambia la respuesta, y eso es lo que se pide comparar. |
| A1.5 deals sin empresa | Consulta SQL equivalente a la cuarentena del motor: deals cuyo `hubspot_id` no existe en ninguna empresa real. Son 35, todos ganados, por 667,251.00 en unidades mezcladas. | Cada uno es el único deal de su id, así que no hay forma rigurosa de saber si su monto es mensual o anual (ADR-002, adenda 1); se reporta el monto crudo y la limitación. |
| A1.6 horas negativas | Los 48 tickets con `resolution_hours` negativo se dejan en nulo para cualquier promedio de tiempo de resolución, se conservan para conteos y CSAT, se registran en el log de excepciones, y se reporta la hipótesis de fechas invertidas como hallazgo. La corrección en origen queda para A6. | Sin el signo, 39 de los 48 caen en el rango normal de los tickets positivos (mediana 13.5 contra 12.2), lo que apunta a un error de signo. Pero 10 siguen abiertos con horas ya registradas, así que asumir el signo es adivinar. Nulo con rastro es lo único que no inventa datos. |
| A1.7 escalamiento | Respuesta de diseño, no una consulta: particionar el uso por mes y cliente, agregar por adelantado lo que la sábana consume, y refrescar solo las particiones que cambian. Se entrega con DDL ilustrativo. | El caso pregunta qué cambiaría en el modelo y en el pipeline; la respuesta es arquitectura. |

## Opciones que consideramos

| Opción | Por qué se rechazó o se eligió |
|---|---|
| A1.1 en dos desgloses separados | Rechazada: pierde el cruce que el caso pide y duplica la explicación de los dos totales. |
| A1.2 solo con cuentas de seis meses o más | Rechazada: deja fuera a 30 de 89 cuentas, un tercio del churn, y esconde el límite de la fórmula en lugar de mostrarlo. |
| A1.2 incluyendo el mes de baja | Rechazada: contamina la ventana con el mes en que la cuenta ya se fue (ADR-003). |
| A1.3 con "activa" como uso real en el mes k | Rechazada como definición principal: mezcla retención de contrato con adopción de producto; queda como pregunta para A3. |
| A1.3 con `created_at` de la cuenta de producto | Rechazada: fecha de otro sistema, con su propio desfase. |
| A1.4 a grano empresa | Rechazada: el último touch de una empresa con dos deals no dice a cuál de los dos pertenece. |
| A1.4 con ambos granos | Rechazada: cuatro tablas para una pregunta; el grano deal ya compara los dos modelos. |
| A1.6 con valor absoluto | Rechazada: asume el error de signo sin poder comprobarlo ticket por ticket. |
| A1.6 excluyendo los tickets | Rechazada: borra 48 tickets reales de los conteos y del CSAT por un campo dañado. |

## Qué cambia en las secciones siguientes

| Sección | Efecto |
|---|---|
| A3 | Las señales de soporte del health score usan conteos y CSAT, no tiempo de resolución, hasta que A6 corrija el signo. |
| A5 | El tablero muestra los dos totales de MRR con la misma etiqueta que A1.1 y la retención por cohorte con celdas vacías donde no hay dato completo. |
| A6 | El script de limpieza registra los 48 tickets negativos como una corrección más, con la regla que se decida ahí. |
| Parte B | La comparación de atribución alimenta la conversación sobre canal de adquisición y churn (Evento 8.3 % contra Organic 19.6 %). |

## Riesgos y cómo los manejamos

| Riesgo | Mitigación |
|---|---|
| El evaluador esperaba otra lectura de A1.2 o A1.4 | Cada consulta lleva su definición escrita al lado y el reporte muestra qué cambia con la lectura alterna. |
| Las definiciones se desalinean del SQL con el tiempo | Cada consulta tiene una prueba sobre un fixture mínimo que ejerce la regla, y otra sobre el dataset real que fija el número. |
| El monto de A1.5 se lee como revenue perdido | El reporte lo etiqueta como "unidades mezcladas" y explica por qué no se puede llevar a mensual. |

## Lista de verificación para el revisor

- [ ] A1.1 muestra dos columnas de MRR y una fila de totales; la suma del total con imputados coincide con la sábana.
- [ ] A1.2 excluye el mes de baja y marca `windows_overlap` en las cuentas con menos de seis meses.
- [ ] A1.3 deja vacías las celdas de cohortes que no cumplen k meses en agosto de 2024.
- [ ] A1.4 atribuye cada deal a dos canales y reporta si el ganador cambia.
- [ ] A1.6 no cambia ninguna cifra del dataset maestro y deja los 48 tickets en el log de excepciones.

## Preguntas abiertas

1. Para A3: si "activa" medida por uso real en el mes k (la lectura rechazada en A1.3) sirve como señal de adopción temprana.
2. Para A6: qué regla de corrección aplicar a los 48 tickets una vez confirmada la hipótesis de fechas invertidas con el equipo de soporte.
