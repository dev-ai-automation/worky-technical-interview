# Especificación: limpieza automática de datos (`data-cleaning`)

## Propósito

Este dominio cubre el comando que toma `companies.csv` y `deals.csv`, detecta y corrige nulos en `mrr`, montos en USD y fechas DD/MM/YYYY, imputa el `mrr` faltante desde los deals de cada empresa según el ADR-002, y deja un log auditable de cada corrección. Implementa la sección A6 del caso y el compromiso de imputación del ADR-002 (incluida su adenda 1 sobre anualización).

## ADDED Requirements

### Requirement: comando `clean` y wrapper equivalentes

El subcomando `python -m worky_engine clean` y el wrapper `python scripts/clean_companies.py` MUST producir exactamente el mismo resultado, porque el segundo únicamente invoca al primero. El comando MUST terminar en 0 cuando la corrida es exitosa, en 1 cuando detecta una violación de contrato o de regla de negocio, y en 2 cuando falta un archivo o una dependencia, con un mensaje en español que nombra lo que falta.

#### Scenario: corrida exitosa desde ambas rutas

- Dado companies.csv y deals.csv presentes en el directorio de datos
- Cuando alguien corre el subcomando y, por separado, el wrapper
- Entonces ambas rutas generan las mismas salidas en outputs/clean/ y ambas terminan en 0

#### Scenario: falta companies.csv

- Dado que companies.csv no existe en el directorio de datos
- Cuando alguien corre clean
- Entonces el comando termina con código 2 y un mensaje en español que nombra el archivo faltante

#### Scenario: falta una dependencia

- Dado que pandas no está instalado en el entorno
- Cuando alguien corre clean
- Entonces el comando termina con código 2 y un mensaje en español que nombra la dependencia faltante

### Requirement: entradas requeridas companies.csv y deals.csv

El comando MUST leer companies.csv como entrada obligatoria para toda corrida, y MUST leer deals.csv como entrada obligatoria para la imputación de mrr. Si deals.csv falta, el comando MUST terminar en código 2 con un mensaje en español que nombre el archivo faltante, sin escribir ninguna salida parcial.

#### Scenario: ambos archivos presentes

- Dado companies.csv y deals.csv en el directorio de datos
- Cuando alguien corre clean
- Entonces el comando lee ambos archivos y corre las tres detecciones más la imputación

#### Scenario: falta deals.csv

- Dado que deals.csv no existe
- Cuando alguien corre clean
- Entonces el comando termina con código 2, sin escribir companies_clean.csv, y el mensaje nombra deals.csv

### Requirement: detección de mrr nulo con exclusión de clones

El comando MUST detectar exactamente 56 filas con mrr nulo sobre las 678 filas del dataset, MUST separar de esas 56 las 28 filas clon `HS-9000xx` como excluidas de la imputación, y MUST contar las 28 restantes como empresas reales imputables.

#### Scenario: conteo exacto sobre el dataset

- Dado companies.csv con 678 filas
- Cuando el comando corre la detección de mrr nulo
- Entonces reporta 56 filas con mrr nulo, de las cuales 28 son clones `HS-9000xx` y 28 son empresas reales imputables

#### Scenario: un clon no se imputa

- Dado una fila clon `HS-9000xx` con mrr nulo
- Cuando el comando corre la imputación
- Entonces esa fila queda con mrr nulo sin imputar, y se reporta aparte en el log como excluida por cuarentena

### Requirement: detección de moneda USD

El comando MUST detectar exactamente 22 filas con currency igual a USD sobre las 678 filas del dataset.

#### Scenario: conteo exacto de USD

- Dado companies.csv con 678 filas
- Cuando el comando corre la detección de moneda
- Entonces reporta exactamente 22 filas en USD

### Requirement: detección y normalización de signup_date

El comando MUST detectar exactamente 31 filas con signup_date en formato DD/MM/YYYY, MUST reportar aparte cuántas de esas 31 son ambiguas por día menor o igual a 12 (donde DD/MM y MM/DD serían ambas fechas válidas), deben ser 12, MUST normalizarlas a ISO siguiendo la convención DD/MM del ADR-001 incluso en el caso ambiguo, MUST rechazar sin normalizar cualquier fecha que no sea un calendario válido, y MUST reportar 0 filas con formato mezclado en churn_date.

#### Scenario: conteo y normalización de signup_date

- Dado companies.csv con 678 filas
- Cuando el comando corre la detección y normalización de fechas
- Entonces reporta 31 fechas DD/MM/YYYY normalizadas a ISO, y de esas 12 quedan marcadas aparte como ambiguas por día menor o igual a 12

#### Scenario: fecha calendario imposible

- Dado una fila con signup_date igual a 31/02/2023
- Cuando el comando intenta normalizarla
- Entonces la fecha no se normaliza a ningún valor, la fila queda registrada como excepción, y el proceso no aborta la corrida completa

#### Scenario: churn_date sin mezcla de formatos

- Dado companies.csv con 678 filas
- Cuando el comando corre la detección de fechas sobre churn_date
- Entonces reporta 0 filas en formato DD/MM/YYYY

### Requirement: conversión de moneda USD a MXN

El comando MUST convertir cada monto en USD a MXN usando el tipo de cambio fijo de 18.5 (ADR-002), MUST escribir el resultado en mrr_mxn, y MUST conservar el monto y la moneda originales sin cambios en mrr_original y currency_original para cada fila, esté o no en USD.

#### Scenario: monto en USD

- Dado una fila con mrr igual a 1000 y currency igual a USD
- Cuando el comando convierte la moneda
- Entonces mrr_mxn queda en 18500, mrr_original en 1000 y currency_original en USD

#### Scenario: monto ya en MXN

- Dado una fila con mrr igual a 5000 y currency igual a MXN
- Cuando el comando la procesa
- Entonces mrr_mxn es igual a mrr_original (5000) y currency_original queda en MXN

### Requirement: imputación de mrr desde deals con anualización

Para cada empresa real con mrr nulo, el comando MUST buscar sus deals en deals.csv, MUST normalizar a mensual cualquier monto que sea exactamente 12 veces otro monto de la misma empresa y MUST registrar esa normalización como una corrección propia en el log, MUST imputar el monto único resultante con mrr_confidence en high cuando la empresa tiene un deal closedwon y medium en cualquier otro caso, y MUST dejar la empresa sin imputar cuando los montos no se resuelven a un único valor o no existen deals. Cada imputación MUST registrar el deal_id de origen.

#### Scenario: imputación con confianza alta

- Dado una empresa real con mrr nulo, un único monto entre sus deals y al menos un deal closedwon
- Cuando el comando corre la imputación
- Entonces mrr_mxn queda con ese monto, mrr_confidence en high y el log nombra el deal_id de origen

#### Scenario: imputación con confianza media

- Dado una empresa real con mrr nulo, un único monto entre sus deals y ningún deal closedwon
- Cuando el comando corre la imputación
- Entonces mrr_mxn queda con ese monto y mrr_confidence en medium

#### Scenario: empresa sin resolución

- Dado una empresa real con mrr nulo cuyos montos de deals no coinciden ni son 12 veces uno del otro, o que no tiene ningún deal
- Cuando el comando corre la imputación
- Entonces la empresa queda sin mrr imputado y se reporta como unresolved en el log

#### Scenario: anualización contada como corrección propia

- Dado una empresa con dos montos de deal donde el mayor es exactamente 12 veces el menor
- Cuando el comando corre la imputación
- Entonces usa el monto mensual, el menor de los dos, para imputar y registra la anualización como una corrección separada de la imputación en el log

### Requirement: contrato del log de limpieza

El comando MUST escribir cleaning_log.json con el conteo exacto por regla y por columna, incluidos mrr nulo, clones excluidos, USD, fechas normalizadas, fechas ambiguas y deals anualizados, MUST escribir cleaning_log.md con un resumen en español de esos mismos conteos, y MUST escribir cleaning_exceptions.csv con una fila por corrección, con las columnas exception_id, exception_code, source_id, field_name, original_value y applied_value, más confidence y deal_id cuando la corrección es una imputación. El orden de las filas MUST ser determinista entre corridas.

#### Scenario: conteos exactos en json y en md

- Dado una corrida completa de clean sobre el dataset
- Cuando el comando escribe los logs
- Entonces cleaning_log.json trae los conteos exactos, 56, 28, 22, 31 y 12 entre ellos, y cleaning_log.md los resume en español

#### Scenario: fila de excepción por corrección

- Dado una corrección de imputación sobre una empresa
- Cuando el comando escribe cleaning_exceptions.csv
- Entonces esa fila trae exception_id, exception_code, source_id, field_name, original_value, applied_value, confidence y el deal_id de origen

#### Scenario: orden determinista

- Dado dos corridas consecutivas de clean sobre el mismo dataset
- Cuando el comando escribe cleaning_exceptions.csv en cada corrida
- Entonces las filas quedan en el mismo orden en ambas corridas

### Requirement: salida companies_clean.csv

El comando MUST escribir companies_clean.csv con las mismas filas y el mismo orden que companies.csv, MUST conservar todas las columnas originales, y MUST agregar mrr_mxn, mrr_original y currency_original.

#### Scenario: mismas filas y mismo orden

- Dado companies.csv con 678 filas en un orden dado
- Cuando el comando escribe companies_clean.csv
- Entonces trae las mismas 678 filas en el mismo orden

#### Scenario: columnas originales más las nuevas

- Dado el encabezado de companies.csv
- Cuando el comando escribe companies_clean.csv
- Entonces el encabezado conserva todas las columnas originales y agrega mrr_mxn, mrr_original y currency_original

### Requirement: idempotencia de la corrida

El comando MUST reportar cero correcciones de cualquier tipo cuando corre sobre su propia salida companies_clean.csv, y MUST producir companies_clean.csv idéntico byte a byte entre dos corridas consecutivas sobre el mismo dataset de entrada.

#### Scenario: cero correcciones sobre la salida propia

- Dado companies_clean.csv generado por una corrida previa
- Cuando el comando corre clean usando companies_clean.csv como entrada
- Entonces cleaning_log.json reporta cero correcciones en cada regla

#### Scenario: salidas idénticas entre corridas

- Dado dos corridas consecutivas de clean sobre el mismo companies.csv y deals.csv
- Cuando alguien compara companies_clean.csv de ambas corridas
- Entonces los dos archivos son idénticos byte a byte

### Requirement: coincidencia con el motor y goldens sin tocar otras salidas

Las imputaciones que el comando calcula MUST coincidir exactamente con las que produce mart_mrr sobre el dataset real, para las mismas 28 empresas. Las salidas del comando MUST escribirse bajo outputs/clean/ y versionarse como golden, y el comando MUST NOT modificar ningún archivo existente bajo outputs/analysis, outputs/health u outputs/warehouse, ni ningún golden previo de A0 a A4.

#### Scenario: coincidencia con mart_mrr

- Dado las 28 empresas reales con mrr nulo en el dataset real
- Cuando se comparan los valores imputados por clean contra mart_mrr
- Entonces los 28 valores de mrr_mxn coinciden exactamente

#### Scenario: ningún golden previo cambia

- Dado los goldens existentes bajo outputs/analysis, outputs/health y outputs/warehouse
- Cuando alguien corre clean
- Entonces ningún archivo de esas carpetas cambia una línea
