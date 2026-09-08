# Especificación: normalización de fuentes de origen (`source-normalization`)

## Propósito

Este dominio limpia los valores crudos de fecha, dominio, nombre de empresa y monto antes de que cualquier otro módulo los compare o los ensamble, para que una diferencia de formato (acentos, subdominios, orden de la fecha, razón social, moneda) nunca se lea como una diferencia real entre dos registros. Lo usan `identity-resolution` para comparar registros entre sistemas y `master-dataset-assembly` para calcular `mrr_mxn`. Implementa la sección de limpieza previa del ADR-001 y la conversión de moneda del ADR-002.

## Requisitos

### Requisito: normalización de fecha

El sistema MUST convertir cada fecha en formato DD/MM/YYYY al formato ISO (YYYY-MM-DD) antes de cualquier comparación. Una fecha que ya llega en formato ISO MUST conservarse sin cambios.

#### Escenario: fecha ya en formato ISO

- Dado un valor de fecha en formato ISO, por ejemplo `2023-05-14`
- Cuando el sistema lo normaliza
- Entonces el valor de salida es idéntico al de entrada

#### Escenario: fecha en formato DD/MM/YYYY

- Dado un valor de fecha en formato DD/MM/YYYY, por ejemplo `14/05/2023`
- Cuando el sistema lo normaliza
- Entonces el valor de salida es `2023-05-14`

### Requisito: etiqueta de dominio

El sistema MUST convertir cada dominio a minúsculas, MUST quitarle los acentos, MUST eliminar los subdominios `www`, `app`, `mail` y `portal`, y MUST conservar solo la etiqueta registrable: el nombre de la organización, sin el subdominio y sin el sufijo de país o de tipo de sitio.

#### Escenario: mismo negocio con y sin subdominio

- Dado los dominios `app.cordero501.com.mx` y `cordero501.mx`
- Cuando el sistema normaliza ambos
- Entonces los dos producen la etiqueta `cordero501`

### Requisito: nombre normalizado de empresa

El sistema MUST aplicar descomposición NFKD y quitar los acentos, MUST convertir a minúsculas, MUST quitar la puntuación, MUST eliminar las razones sociales `sa de cv`, `s a de c v`, `sa`, `sc`, `ac`, `y asociados` y `e hijos` (comparadas ya en minúsculas y sin puntuación), y MUST colapsar los espacios en blanco repetidos a uno solo. La variante `s a de c v` es la forma que resulta de `S.A. de C.V.` después de quitar la puntuación; 80 nombres del dataset la traen así.

#### Escenario: nombre con razón social y acentos

- Dado el nombre `Gaitán y Asociados, S.A. de C.V.`
- Cuando el sistema lo normaliza
- Entonces el valor de salida es `gaitan`

### Requisito: conversión de moneda a MXN

El sistema MUST convertir cualquier monto en USD a MXN usando el tipo de cambio fijo de 18.5 MXN por USD, y MUST conservar el valor original junto con la moneda original, además del valor convertido.

#### Escenario: monto en USD

- Dado un monto de 1000 USD
- Cuando el sistema lo convierte
- Entonces el valor convertido es 18500 MXN, y el valor original (1000) junto con la moneda original (USD) siguen disponibles sin cambios

#### Escenario: monto ya en MXN

- Dado un monto de 5000 MXN
- Cuando el sistema lo procesa
- Entonces el valor convertido es igual al valor original, y la moneda original (MXN) sigue disponible sin cambios

### Requisito: idempotencia de la normalización

El sistema MUST producir el mismo resultado cuando una fecha, un dominio, un nombre o un monto ya normalizado se normaliza otra vez.

#### Escenario: segunda normalización

- Dado un valor ya normalizado, por ejemplo la etiqueta de dominio `cordero501`
- Cuando el sistema lo normaliza de nuevo
- Entonces el resultado es idéntico al valor de entrada

### Requisito: codificación explícita de archivos

El sistema MUST abrir cada archivo de origen con la codificación UTF-8 declarada de forma explícita, para que un carácter acentuado en un nombre o en un dominio (por ejemplo `gaitán115.com.mx`) nunca se decodifique de forma incorrecta.

#### Escenario: archivo con caracteres acentuados

- Dado un archivo CSV en UTF-8 con nombres y dominios acentuados
- Cuando el sistema lo lee declarando la codificación UTF-8
- Entonces cada carácter acentuado se conserva igual que en el archivo de origen
