# Especificación: resolución de identidad entre sistemas (`identity-resolution`)

## Propósito

Resuelve qué registros de HubSpot, Product DB y Vitally describen a la misma empresa real, les asigna un `master_id` compartido y deja evidencia de cada decisión en `match_audit`, para que ningún reporte posterior mezcle filas clon, deals huérfanos o empresas distintas que comparten un dominio. Implementa el ADR-001.

## ADDED Requirements

### Requirement: deduplicación de filas clon en companies

El sistema MUST identificar las 28 filas clon `HS-9000xx` de la tabla `companies` y MUST moverlas a `quarantine_companies` con un código de razón, sin fusionarlas ni eliminarlas.

#### Scenario: fila clon aislada

- Dado el registro `HS-900001`, clon de `HS-100469`
- Cuando el sistema procesa `companies`
- Entonces `HS-900001` aparece en `quarantine_companies` con un código de razón, y no aparece en el dataset maestro

### Requirement: cascada de niveles de confianza

El sistema MUST evaluar cada registro de origen contra la secuencia fija de niveles de la tabla siguiente, en orden, y MUST detenerse en el primer nivel donde coincide exactamente un candidato. `token_set_ratio`, `partial_ratio` y `WRatio` son puntajes de similitud de nombre de RapidFuzz, de 0 a 100, cada uno con una forma distinta de comparar dos nombres.

| Nivel | Condición | Confianza |
|---|---|---|
| T0 | `hubspot_id` está presente y existe en `companies` ya deduplicada | alta |
| T1 | la etiqueta de dominio coincide exactamente y `token_set_ratio` (similitud insensible al orden de las palabras) es 90 o más | alta |
| T2 | `signup_date` es igual a `created_at`, y el registro es el único candidato del bloque de fecha con `partial_ratio` (similitud por subcadena) de 90 o más | alta |
| T3 | `WRatio` (similitud general ponderada) es 94 o más y supera al segundo mejor candidato por al menos 10 puntos | media |

Un bloque de fecha de T2 puede tener varias empresas con la misma fecha, hasta 4 en la calibración del ADR-001, y el registro igual se resuelve en T2 si solo uno de esos candidatos alcanza `partial_ratio` de 90 o más. Cuando más de un candidato del bloque alcanza ese umbral, el sistema MUST NOT elegir por el orden en que las filas aparecen. El sistema MUST bajar ese registro a T3, o a revisión manual si T3 tampoco resuelve un único candidato.

#### Scenario: cruce por T0

- Dado una cuenta de Product DB con `hubspot_id` presente y existente en `companies`
- Cuando el sistema la evalúa
- Entonces se resuelve en T0 con confianza alta

#### Scenario: cruce por T1

- Dado un cliente de Vitally cuyo dominio coincide con una empresa de HubSpot y cuyo `token_set_ratio` es 92
- Cuando el sistema lo evalúa
- Entonces se resuelve en T1 con confianza alta

#### Scenario: cruce por T2 con candidato único

- Dado una cuenta de Product DB sin `hubspot_id`, con `created_at` igual al `signup_date` de una sola empresa de HubSpot en ese bloque de fecha
- Cuando el sistema la evalúa
- Entonces se resuelve en T2 con confianza alta

#### Scenario: bloque de T2 con más de un candidato

- Dado un bloque de fecha con cuatro empresas candidatas para la misma cuenta
- Cuando el sistema evalúa esa cuenta
- Entonces el sistema no elige por el orden de las filas, y el registro baja a T3, o a revisión manual si T3 tampoco resuelve un único candidato

#### Scenario: cruce por T2, cuenta con nombre truncado

- Dado la cuenta `ACC-2027`, con el nombre truncado `Sanches y Asocia`, en un bloque de fecha de tamaño 2 donde solo ella alcanza `partial_ratio` de 100 contra `HS-100028`
- Cuando el sistema la evalúa
- Entonces se resuelve en T2 con confianza alta, y la evidencia queda registrada en `match_audit`

#### Scenario: cruce por T3

- Dado una cuenta cuya fecha de alta no coincide con la de ninguna empresa, y cuyo `WRatio` es 94 o más con un margen de al menos 10 puntos sobre el segundo mejor candidato
- Cuando el sistema la evalúa
- Entonces se resuelve en T3 con confianza media

### Requirement: regla de veto

El sistema MUST tratar dos registros como empresas distintas, cada una con su propio `master_id`, cuando comparten la etiqueta de dominio, su similitud de nombre es menor a 70, sus fechas de alta son distintas, y ambos registros tienen un valor de MRR. El sistema MUST registrar el veto en `match_audit`.

#### Scenario: dominio compartido club290.com.mx

- Dado dos empresas que comparten el dominio `club290.com.mx`, con nombres distintos, fechas de alta distintas y MRR en ambas
- Cuando el sistema las evalúa
- Entonces cada empresa conserva su propio `master_id`, y el veto queda registrado en `match_audit`

### Requirement: revisión manual

El sistema MUST enviar a revisión manual, con confianza baja, cualquier registro que ningún nivel T0 a T3 resuelva y al que no aplique el veto.

#### Scenario: registro sin cruce resuelto

- Dado un registro que no cumple ninguna condición de T0 a T3 y al que no aplica el veto
- Cuando el sistema lo evalúa
- Entonces el registro queda marcado para revisión manual con confianza baja

### Requirement: master_id idempotente

El sistema MUST reutilizar el `master_id` ya existente en `identity_crosswalk` para cualquier id de origen que ya esté ahí. Para un registro dorado nuevo, el sistema MUST generar el id como el hash sha256 de la etiqueta de dominio concatenada con el nombre normalizado, truncado a 12 caracteres hexadecimales.

#### Scenario: id de origen ya en el crosswalk

- Dado un `hubspot_id` que ya tiene un `master_id` asignado en `identity_crosswalk`
- Cuando el sistema procesa ese registro otra vez
- Entonces recibe el mismo `master_id`, sin generar uno nuevo

#### Scenario: registro dorado nuevo

- Dado un registro dorado que aún no existe en `identity_crosswalk`
- Cuando el sistema le asigna un `master_id`
- Entonces el id es el hash sha256 de su etiqueta de dominio y su nombre normalizado, truncado a 12 caracteres hexadecimales

### Requirement: tabla identity_crosswalk

El sistema MUST mantener `identity_crosswalk` con las columnas `master_id`, `hubspot_id`, `account_id`, `vitally_id`, `confidence_tier` y `resolved_at`.

#### Scenario: fila completa de crosswalk

- Dado una empresa resuelta en los tres sistemas
- Cuando el sistema escribe su fila en `identity_crosswalk`
- Entonces la fila incluye su `master_id`, los tres ids de origen, el nivel de confianza y la fecha de resolución

### Requirement: tabla match_audit

El sistema MUST escribir en `match_audit` exactamente una fila por registro de origen procesado, con las columnas `source_system`, `source_id`, `master_id`, `tier`, `score`, `evidence_json`, `ruleset_version`, `decided_by` y `decided_at`.

#### Scenario: una fila por registro de origen

- Dado los 650 registros de `accounts`, los 678 de `companies` y los 650 de `customers`
- Cuando el sistema termina de resolver identidad
- Entonces `match_audit` tiene exactamente una fila por cada registro de origen procesado

### Requirement: cuarentena de deals huérfanos

El sistema MUST mover a `quarantine_deals` los 35 deals `HS-9900xx` cuyo `hubspot_id` no existe en `companies`, MUST conservar el monto de cada uno, y MUST NOT eliminarlos.

#### Scenario: deals huérfanos aislados

- Dado los 35 deals con `hubspot_id` inexistente en `companies`
- Cuando el sistema procesa `deals`
- Entonces los 35 aparecen en `quarantine_deals` con su monto, y ninguno entra al cálculo de revenue del dataset maestro

### Requirement: remapeo de deals que apuntan a un clon

Un deal cuyo `hubspot_id` es el de un clon en cuarentena no es huérfano. El sistema MUST asignarle el `master_id` del sobreviviente de ese clon, MUST incluirlo en el cálculo de revenue y de MRR de esa empresa, y MUST escribir en `exceptions_log` una fila `deal_remapped_from_clone` por cada deal remapeado, con el `hubspot_id` del clon como valor original y el del sobreviviente como valor aplicado. Un deal cuyo `hubspot_id` es el de una empresa real MUST NOT generar esa fila.

#### Scenario: deal de un clon llega al sobreviviente

- Dado un clon `HS-900060` en `quarantine_companies` con sobreviviente `HS-600001`, y un deal `D-6001` con `hubspot_id = HS-900060`
- Cuando el sistema ensambla el dataset maestro
- Entonces `D-6001` suma al revenue de `HS-600001`, no aparece en `quarantine_deals`, y `exceptions_log` tiene exactamente una fila `deal_remapped_from_clone` con `source_id = D-6001`

#### Scenario: deal de una empresa real no deja evidencia de remapeo

- Dado un deal cuyo `hubspot_id` es el de una empresa real presente en `identity_crosswalk`
- Cuando el sistema ensambla el dataset maestro
- Entonces `exceptions_log` no tiene ninguna fila `deal_remapped_from_clone` para ese deal

### Requirement: contención de vínculos duplicados de una fuente

`identity_crosswalk` tiene una sola fila por empresa. Si dos accounts de Product DB o dos customers de Vitally resuelven al mismo `master_id`, el sistema MUST conservar el primero por orden de entrada, MUST NOT sobrescribirlo ni detener la corrida, MUST marcar la fila de `match_audit` del segundo con `needs_review = true` y la clave `duplicate_link` en `evidence_json` (id conservado, id descartado y campo), y MUST escribir exactamente una fila `duplicate_source_link` en `exceptions_log` por cada id descartado, con `exception_id` único. El mismo id repetido MUST NOT contar como duplicado.

#### Scenario: dos accounts para la misma empresa

- Dado dos accounts `ACC-700001` y `ACC-700002` con el mismo `hubspot_id = HS-700001`
- Cuando el sistema resuelve la identidad y ensambla el dataset maestro
- Entonces el crosswalk de `HS-700001` conserva `ACC-700001`, la fila de `match_audit` de `ACC-700002` tiene `needs_review = true` y `duplicate_link`, `exceptions_log` tiene exactamente una fila `duplicate_source_link` con `original_value = ACC-700002` y `applied_value = ACC-700001`, la cola de revisión manual del reporte de cobertura cuenta 1, y el dataset maestro sigue teniendo una sola fila para `HS-700001`

#### Scenario: el mismo id descartado aparece dos veces

- Dado los accounts `ACC-700001`, `ACC-700002` y otra vez `ACC-700002`, los tres con `hubspot_id = HS-700001`
- Cuando el sistema resuelve la identidad y ensambla el dataset maestro
- Entonces las dos filas de `match_audit` de `ACC-700002` quedan con `needs_review = true`, `exceptions_log` tiene exactamente una fila `duplicate_source_link`, y ningún `exception_id` se repite

#### Scenario: el mismo account repetido no es un duplicado

- Dado el account `ACC-700001` que aparece dos veces en `accounts` con el mismo `hubspot_id`
- Cuando el sistema resuelve la identidad
- Entonces ninguna fila de `match_audit` lleva `needs_review` ni `duplicate_link`, y `exceptions_log` no tiene filas `duplicate_source_link`

### Requirement: supervivencia de atributos

Cuando dos sistemas discrepan sobre el mismo `master_id`, el sistema MUST resolver el valor final según la tabla siguiente.

| Atributo | Fuente que gana |
|---|---|
| nombre canónico | la ortografía de la fila `HS-1xxxxx` |
| atributos comerciales (`mrr`, `currency`, `plan`, `segment`, `industry`, `state`, `csm`) | el registro de HubSpot que tenga el valor de MRR |
| `churn_date` | HubSpot, después de quitar las filas clon |
| conflicto entre un clon y su original (por ejemplo `HS-900001` en MXN contra `HS-100469` en USD) | revisión manual, con el impacto de cada opción medido |

#### Scenario: conflicto de moneda entre clon y original

- Dado `HS-900001` en cuarentena con MRR en MXN y `HS-100469` con MRR en USD para la misma empresa
- Cuando el sistema detecta el conflicto
- Entonces el caso se envía a revisión manual con el impacto de cada valor medido, y no se resuelve por el orden de las filas

### Requirement: calibración reproducible

El sistema MUST reproducir, sobre los 596 pares donde el `hubspot_id` ya confirma el cruce correcto, una prueba de calibración donde `WRatio` elige el cruce correcto en primer lugar en al menos el 99.0% de los casos (590 de 596 con `ruleset_version` 1.0.0); los 6 restantes son empates que ninguna métrica de nombre puede resolver (dos empresas reales llamadas Galindo S. R.L. de C.V., y Rangel S.A. de C.V. contra Rangel y Asociados, idénticas tras quitar la razón social), y por eso T1 y T2 corren antes que T3. El valor esperado vive en `tests/fixtures/calibration_expectations.json` y se versiona junto con el ruleset.

#### Scenario: prueba de calibración

- Dado los 596 pares etiquetados
- Cuando el sistema corre la prueba de calibración con el `hubspot_id` oculto
- Entonces `WRatio` elige el cruce correcto en primer lugar en al menos el 99.0% de los pares (590 de 596)

### Requirement: precedencia de overrides sobre la cascada

Una fila de `identity_overrides` (`source_system`, `source_id`, `master_id`, `decided_by`, `decided_at`, `reason`) aplicada después de la cascada MUST fijar el `master_id` de ese registro de origen, MUST sacarlo de la cola de revisión manual (`needs_review = false`), y MUST dejar evidencia en `match_audit` que nombre el override. Una fila cuyo `master_id` no existe en `identity_crosswalk`, un `source_id` duplicado entre filas de override, o un `source_id` que no existe en su tabla de origen, MUST rechazarse; el comando MUST terminar con un código de salida distinto de cero y un mensaje de error que nombre la fila y el motivo, y MUST NOT escribir ninguna salida parcial. Sin archivo de overrides, `identity_crosswalk`, `match_audit`, `mart_coverage` y todos los goldens de A0 MUST permanecer idénticos byte a byte.

#### Scenario: override fija el master_id y sale de revisión manual

- Dado un registro en revisión manual (nivel M, `needs_review = true`) y una fila de `identity_overrides` que le asigna un `master_id` existente en el crosswalk
- Cuando el sistema aplica los overrides después de la cascada
- Entonces ese registro queda con el `master_id` del override, `needs_review = false`, y `match_audit` registra el override como evidencia de la decisión

#### Scenario: override con master_id inexistente se rechaza

- Dado una fila de `identity_overrides` cuyo `master_id` no existe en `identity_crosswalk`
- Cuando el sistema procesa los overrides
- Entonces el comando se detiene con un código de salida distinto de cero, el mensaje de error nombra la fila y el motivo, y no se escribe ningún archivo de salida

#### Scenario: source_id duplicado entre overrides se rechaza

- Dado dos filas de `identity_overrides` con el mismo `source_id`
- Cuando el sistema procesa los overrides
- Entonces el comando se detiene con un código de salida distinto de cero, el mensaje de error nombra la fila duplicada y el motivo, y no se escribe ningún archivo de salida

#### Scenario: override con source_id desconocido se rechaza

- Dado una fila de `identity_overrides` cuyo `source_id` no existe en la tabla de origen que indica `source_system`
- Cuando el sistema procesa los overrides
- Entonces el comando se detiene con un código de salida distinto de cero, el mensaje de error nombra la fila y el motivo, y no se escribe ningún archivo de salida

#### Scenario: sin archivo de overrides, la salida de A0 no cambia

- Dado una corrida sin ningún archivo de `identity_overrides`
- Cuando el sistema resuelve identidad y ensambla el dataset maestro
- Entonces `identity_crosswalk`, `match_audit`, `mart_coverage` y todos los goldens de A0 quedan idénticos byte a byte a los de antes de este cambio
