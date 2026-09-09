# Especificación: análisis SQL sobre la sábana (`sql-analysis`)

## Propósito

Ejecuta las siete respuestas de SQL que pide la sección A1 del caso sobre la sábana que ensambla A0, con las definiciones del ADR-004 como reglas vinculantes, y publica cada resultado junto con su definición, su SQL y el motor en un solo reporte. Implementa el ADR-004, con las reglas de MRR del ADR-002 y de ventana de uso del ADR-003.

## ADDED Requirements

### Requirement: comando `analyze` sin build previo

El comando `python -m worky_engine analyze` MUST abrir su propia conexión, registrar las tablas crudas y correr staging, marts y análisis sin depender de una corrida previa de `build`. El comando MUST declarar el motor DuckDB 1.5.5, MUST escribir un CSV por consulta más `outputs/analysis/report.md` bajo `outputs/analysis/`, y MUST terminar con el mismo patrón de códigos de salida que `build` (cero en éxito, distinto de cero con un mensaje en español si falta una base o una dependencia).

#### Scenario: corrida sin build previo

- Dado un repositorio recién clonado, sin haber corrido `python -m worky_engine build`
- Cuando alguien corre `python -m worky_engine analyze --data-dir ... --out-dir outputs/analysis`
- Entonces el comando termina en 0 y `outputs/analysis/` contiene un CSV por consulta más `report.md`

#### Scenario: dos corridas idénticas

- Dado la misma entrada sin cambios
- Cuando alguien corre `analyze` dos veces seguidas
- Entonces todos los archivos bajo `outputs/analysis/` de la segunda corrida son idénticos byte por byte a los de la primera

#### Scenario: falta una dependencia o una base de datos

- Dado que falta DuckDB o una de las tres bases SQLite de origen
- Cuando alguien corre `analyze`
- Entonces el comando termina con código distinto de cero y un mensaje en español que nombra lo que falta, sin escribir salidas parciales

### Requirement: A1.1, MRR activo por segmento e industria

La consulta MUST agrupar por `segment` e `industry` las empresas con `churn_date` nulo, MUST mostrar dos columnas de MRR (el que reporta el CRM y el total con valores imputados del ADR-002) y MUST incluir una fila de totales.

#### Scenario: tabla segmentada con dos totales

- Dado `mart_master_dataset` con sus columnas de `mrr_mxn` y `mrr_source`
- Cuando la consulta agrupa por `segment` e `industry` filtrando `churn_date IS NULL`
- Entonces cada fila trae el MRR solo del CRM y el MRR total con imputados, y la fila de totales suma ambas columnas

#### Scenario: el total imputado coincide con la sábana

- Dado el total de la columna de MRR con imputados en la fila de totales de A1.1
- Cuando se compara contra la suma de `mrr_mxn` de las empresas activas en `master_dataset`
- Entonces ambos valores son iguales

### Requirement: A1.2, caída relativa de uso al churn

La consulta MUST calcular, por cuenta con churn y `account_id`, el promedio de `active_users` en los tres meses calendario anteriores al mes de baja (excluyendo ese mes) contra el promedio de los primeros tres meses con uso de la cuenta, MUST ordenar por caída relativa descendente, y MUST marcar `windows_overlap` en `true` para las cuentas con menos de seis meses de uso.

#### Scenario: mes de baja excluido de la ventana

- Dado una cuenta con churn y su serie mensual de `active_users`
- Cuando la consulta construye la ventana de los tres meses previos a la baja
- Entonces el mes calendario del churn no entra al promedio de esa ventana

#### Scenario: 89 cuentas en el dataset real

- Dado el dataset real de `product_db.product_usage` y las cuentas con churn
- Cuando se corre la consulta completa
- Entonces el resultado tiene 89 filas, ordenadas por caída relativa descendente

#### Scenario: ventanas traslapadas marcadas

- Dado una cuenta con menos de seis meses de uso hasta su baja
- Cuando la consulta calcula sus dos promedios
- Entonces `windows_overlap` es `true` para esa cuenta

#### Scenario: cuenta con churn sin filas de uso

- Dado una cuenta con `churn_date` no nulo que no tiene ninguna fila en `product_usage`
- Cuando se corre la consulta completa
- Entonces la cuenta aparece en el resultado con los dos promedios en nulo, en vez de quedar fuera de la tabla

### Requirement: A1.3, retención por cohorte de alta

La consulta MUST agrupar las cuentas por el mes calendario de `signup_date`, MUST definir "activa en el mes k" como no haber hecho churn k meses después del alta (una cuenta cuyo churn cae exactamente en el mes k ya no cuenta como activa en k), para k en 1, 3, 6 y 12, MUST dejar vacía cualquier celda de cohorte que no alcance k meses al cierre de los datos, y MUST implementarse en una sola consulta con CTEs.

#### Scenario: retención por cohorte y k

- Dado las cuentas agrupadas por mes de `signup_date`
- Cuando la consulta calcula el porcentaje activo en k = 1, 3, 6 y 12
- Entonces cada celda reporta el porcentaje de cuentas de esa cohorte sin churn a k meses de su alta, y el porcentaje nunca sube al pasar de un k al siguiente dentro de la misma cohorte

#### Scenario: celda censurada vacía

- Dado una cohorte de alta reciente que todavía no cumple k meses al cierre de los datos (agosto de 2024)
- Cuando la consulta llega a esa celda
- Entonces la celda queda vacía, sin un porcentaje calculado con dato parcial

### Requirement: A1.4, atribución por primer y último touch

La consulta MUST atribuir cada deal, a nivel deal, a dos canales: el primer touch de su empresa y el último touch anterior al `created_date` del deal, con empate por `touch_id` igual que el motor. MUST definir conversión como etapa `closedwon`, MUST calcular la tasa de conversión por canal para ambos modelos lado a lado, y MUST reportar si el canal ganador cambia entre modelos.

#### Scenario: dos canales por deal

- Dado un deal con su empresa, su `created_date` y los touches de esa empresa
- Cuando la consulta lo atribuye
- Entonces el deal recibe un canal de primer touch y un canal de último touch anterior a su `created_date`, con empate por `touch_id` cuando aplica

#### Scenario: tasas lado a lado y bandera de cambio de ganador

- Dado la tasa de conversión a `closedwon` por canal en ambos modelos
- Cuando se comparan los dos rankings
- Entonces el resultado muestra ambas tasas por canal en la misma tabla y una columna que indica si el canal con la tasa más alta cambia entre modelos

### Requirement: A1.5, deals sin empresa real

La consulta MUST identificar los deals de `crm_hubspot.deals` cuyo `hubspot_id` no existe en ninguna empresa real, equivalente a la cuarentena del motor, y MUST entregarse aunque el motor Python ya aísle esas filas en `quarantine_deals`.

#### Scenario: 35 deals huérfanos

- Dado `crm_hubspot.deals` y las empresas reales de la sábana
- Cuando la consulta busca `hubspot_id` sin correspondencia
- Entonces el resultado tiene 35 filas, todas `closedwon`, con `amount` total 667,251.00 etiquetado como unidades mezcladas

### Requirement: A1.6, tickets con horas de resolución negativas

La consulta MUST listar los tickets con `resolution_hours` negativo, MUST tratar ese valor como nulo para cualquier promedio de tiempo de resolución, MUST conservar esos tickets en los conteos y en el CSAT, y MUST escribir una fila por ticket en `outputs/analysis/analysis_exceptions.csv` con las mismas columnas que `exceptions_log.csv`, sin modificar ninguna salida existente de A0.

#### Scenario: 48 tickets listados y neutralizados en promedios

- Dado los tickets con `resolution_hours` negativo
- Cuando la consulta los agrega para un promedio de tiempo de resolución
- Entonces esos 48 tickets aportan nulo al promedio, y el resultado lista exactamente 48 filas

#### Scenario: tickets conservados en conteos y CSAT

- Dado un ticket con `resolution_hours` negativo
- Cuando la consulta calcula conteos totales y CSAT promedio
- Entonces ese ticket cuenta en ambos cálculos, igual que cualquier otro ticket

#### Scenario: excepción escrita sin tocar el log de A0

- Dado los 48 tickets con horas negativas
- Cuando la consulta termina
- Entonces `outputs/analysis/analysis_exceptions.csv` tiene una fila por ticket con las mismas columnas que `exceptions_log.csv`, y `exceptions_log.csv` de A0 queda sin cambio

### Requirement: A1.7, respuesta de diseño para escalar

A1.7 MUST entregarse como una sección de `report.md` con la respuesta de diseño (particionar el uso por mes y cliente, agregar por adelantado, refrescar solo particiones que cambian) y MAY incluir DDL ilustrativo, MUST NOT entregarse como una consulta ejecutable contra el dataset.

#### Scenario: sección narrativa sin consulta

- Dado el reporte final
- Cuando alguien busca la respuesta de A1.7
- Entonces encuentra una sección de texto con la propuesta de partición y refresco incremental, sin ningún archivo `.sql` asociado a A1.7

### Requirement: reporte de resultados por ítem

`report.md` MUST incluir, por cada ítem de A1.1 a A1.7, la definición del ADR-004, el SQL de la consulta cuando aplica, el nombre del motor y la tabla de resultado, y MUST incluir una justificación de 3 a 4 líneas para la decisión de A1.6.

#### Scenario: sección completa por ítem

- Dado cualquier ítem de A1.1 a A1.6
- Cuando se abre su sección en `report.md`
- Entonces la sección muestra la definición del ADR-004, el SQL, el motor DuckDB 1.5.5 y la tabla de resultado

#### Scenario: justificación de A1.6 en 3 a 4 líneas

- Dado la sección de A1.6 en `report.md`
- Cuando se lee la justificación de la decisión sobre las horas negativas
- Entonces el texto de la justificación tiene entre 3 y 4 líneas

### Requirement: pruebas de comportamiento por consulta

Cada consulta MUST tener una prueba sobre un fixture mínimo que ejerza su regla, y las consultas con un número fijado por el ADR-004 MUST tener además una prueba marcada `dataset` sobre el dataset real.

#### Scenario: prueba de fixture por regla

- Dado un fixture mínimo construido para A1.2 (mes de baja adyacente al último mes de uso)
- Cuando la prueba corre la consulta sobre ese fixture
- Entonces la prueba verifica que el mes de baja queda excluido de la ventana

#### Scenario: prueba marcada dataset con el número real

- Dado el dataset real y la marca `dataset` de pytest
- Cuando la prueba corre A1.2, A1.5 o A1.6 contra ese dataset
- Entonces la prueba compara el resultado contra 89 cuentas, 35 deals por 667,251.00, o 48 tickets negativos, según la consulta
