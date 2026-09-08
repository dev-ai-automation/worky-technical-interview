# ADR-001: una identidad compartida para cada cliente en tres sistemas que no coinciden entre sí

- Estado: Aceptado (2026-09-07)
- Alcance: sección A0 del caso (dataset maestro), con consecuencias para A1, A3, A4 y A6
- Decisores: candidato (responsable)

HubSpot, la base de datos de producto (Product DB) y Vitally llevan cada uno su propia lista de clientes, y nada obliga a que las tres coincidan. Esta decisión coloca un proceso automático frente a los tres sistemas: compara sus registros, decide cuáles describen a la misma empresa y le asigna a esa empresa un identificador único compartido. A la fila que conservamos como la verdad sobre una empresa la llamamos registro dorado (golden record). El proceso beneficia a cualquiera que construya un número a partir de este dataset, desde un analista que corre una consulta hasta un director que lee el tablero de ingresos, porque los totales de hoy mezclan filas duplicadas y huérfanas, y este proceso quita esa mezcla conservando la evidencia detrás de cada cruce.

## Ruta rápida

1. Limpiar el registro: normalizar sus fechas, dominio y nombre de empresa para que las diferencias de formato (acentos, subdominios, orden de la fecha, razones sociales) no parezcan diferencias reales.
2. Compararlo contra los otros sistemas nivel por nivel, empezando con la evidencia más fuerte disponible (un id ya compartido entre sistemas) y recurriendo a la similitud de nombre y dominio solo cuando es necesario.
3. Revisar si aplica un veto: una regla que anula un puntaje de similitud alto cuando otra evidencia indica que los dos registros son en realidad empresas distintas, y mantiene los registros separados, cada uno con su propio master_id, en lugar de fusionarlos. A revisión manual solo va lo que ningún nivel logra resolver.
4. Asignarle un master_id: reutilizar el id que ya tiene si ya está en el crosswalk (la tabla que mapea el id propio de cada sistema al id compartido), o generar uno nuevo si pertenece a un registro dorado nuevo.
5. Registrar la decisión en match_audit, anotando qué nivel coincidió, el puntaje y cada señal que contribuyó, para poder revisar el cruce después.

## El problema en números

| Hallazgo | Qué encontramos |
|---|---|
| Las cuentas de Product DB a menudo no tienen un id de HubSpot | accounts.hubspot_id está lleno en 596 de 650 cuentas; a las otras 54 les falta, y 10 de esas tienen nombres de empresa truncados |
| Los clientes de Vitally no tienen ningún id compartido con HubSpot | el cruce por dominio exacto funciona para 573 de 650; el resto falla por subdominios como app., por .mx contra .com.mx, o por caracteres acentuados |
| HubSpot tiene filas de empresa duplicadas | 28 filas (ids HS-9000xx) son clones en mayúsculas o con razón social distinta de filas HS-1xxxxx existentes; su mrr es NULL y ningún otro sistema las referencia |
| HubSpot tiene deals huérfanos | 35 deals apuntan a ids que no existen en companies (HS-9900xx); todos están en closedwon, y suman 667,251 |
| El dominio solo no es una regla de identidad segura | después de quitar las 28 filas clon, 4 dominios todavía son compartidos por 9 empresas distintas, con nombres, planes, MRR y fechas de alta diferentes; cruzar solo por dominio fusionaría, por ejemplo, una cuenta con 47,414 de MRR con otra de 7,947 de MRR en una sola |
| Un puntaje de similitud solo tampoco es una regla de identidad segura | en los 596 pares donde ya conocemos la respuesta correcta, el mejor candidato incorrecto igual obtuvo 100 de 100, así que un puntaje por sí solo no distingue un cruce correcto de uno incorrecto |

## Cómo se decide un cruce

El proceso revisa un registro contra una secuencia fija de niveles, de la evidencia más fuerte a la más débil, y se detiene en el primer nivel donde coincide exactamente un candidato.

Antes de cualquier comparación, el proceso limpia cada registro para que las diferencias de formato no parezcan diferencias reales:

- Fechas: los valores en formato DD/MM/YYYY se convierten a formato ISO antes de comparar cualquier cosa. Cuatro de las 54 cuentas sin hubspot_id solo lograron un cruce después de este paso.
- Dominio: se pasa a minúsculas, se quitan los acentos, se eliminan los subdominios www, app, mail o portal, y se conserva solo la etiqueta registrable, de modo que cordero501.mx y app.cordero501.com.mx terminan siendo cordero501.
- Nombre de empresa: se quitan los acentos, se pasa a minúsculas, se eliminan la puntuación y las razones sociales como SA de CV, S.A., S.C., A.C., y Asociados o e Hijos, y se colapsan los espacios en blanco extra.

| Nivel | Qué tiene que cumplirse | Confianza | Cobertura esperada |
|---|---|---|---|
| T0 | hubspot_id está presente y existe en la tabla companies ya deduplicada | alta | 596 cuentas de producto |
| T1 | el dominio coincide exactamente y la similitud de nombre (token_set_ratio, un puntaje de 0 a 100 que compara dos nombres sin importar el orden de las palabras) es de 90 o más | alta | 650 clientes de Vitally |
| T2 | signup_date es igual a created_at, y el registro es el único candidato de ese grupo de fecha con similitud de nombre (partial_ratio) de 90 o más; si más de uno supera el umbral, baja a T3 o a revisión manual, nunca por orden de filas | alta | 54 cuentas de producto restantes |
| T3 | la similitud de nombre general (WRatio) es de 94 o más y supera al siguiente mejor candidato por al menos 10 puntos | media | lo que quede |
| V (veto) | mismo dominio, similitud de nombre por debajo de 70, fechas de alta distintas, y ambos registros con un valor de MRR | se tratan como dos empresas distintas | 9 empresas en 4 dominios compartidos |
| M | ninguna de las anteriores | confianza baja, se envía a revisión manual | lo que quede |

El veto existe porque un puntaje de similitud alto no basta por sí solo: dos empresas pueden parecer iguales por nombre y dominio y aun así ser negocios distintos. Cuando la evidencia apunta en ese sentido, el proceso se niega a fusionarlas en lugar de adivinar.

De dónde vienen los umbrales: tomamos los 596 pares donde ya conocemos la respuesta correcta (un hubspot_id los conecta), ocultamos ese id, corrimos las reglas de cruce por nombre y medimos qué tan bien funcionaron. El puntaje WRatio eligió el cruce correcto en primer lugar el 99.0% de las veces (590 de 596; los 6 restantes son empates que ninguna métrica de nombre puede resolver, como dos empresas reales llamadas igual, Galindo S. R.L. de C.V., o Rangel S.A. de C.V. contra Rangel y Asociados, que al quitar la razón social quedan idénticas; por eso T1 y T2 corren antes que T3); el puntaje más bajo entre los cruces correctos fue 83, y 93 es el puntaje por debajo del cual cae solo el 5% de los cruces correctos, medidos con la normalización del motor y rapidfuzz 3.14.6. signup_date coincidió exactamente con created_at en el 95.5% de los pares verdaderos, y el grupo de candidatos que comparte una fecha tuvo una mediana de tamaño 1 y un máximo de 4. Los umbrales están versionados (ruleset_version 1.0.0) y se vuelven a revisar con este mismo tipo de prueba cada vez que cambian las reglas.

## Quién gana cuando las fuentes discrepan

La supervivencia de atributos (survivorship) es la regla que decide qué valor, de qué fuente, conservamos cuando dos sistemas discrepan sobre la misma empresa.

| Atributo | Qué fuente gana | Por qué |
|---|---|---|
| nombre canónico | la ortografía de HS-1xxxxx | Vitally coincide con ella en 636 de sus 650 cruces exactos (0 para la ortografía de HS-9), y Product DB coincide en 538 de sus cruces (0 para la ortografía de HS-9) |
| mrr, currency, plan, segment, industry, state, csm | el registro de HubSpot que tenga el valor de MRR | HubSpot es el sistema de registro comercial |
| churn_date | HubSpot, después de quitar las filas duplicadas | se trata como verdad de referencia; las 6 filas clon que tienen churn_date muestran exactamente la misma fecha que su fila original |
| métricas de uso | Product DB | es el único sistema que tiene estos datos |
| métricas de soporte | Vitally | es el único sistema que tiene estos datos |
| valores que entran en conflicto entre una empresa y su clon (por ejemplo HS-900001 en MXN contra HS-100469 en USD) | se envían a revisión manual, con el impacto de cada opción medido | nunca se resuelven de forma automática según qué fila aparezca primero |

## Cómo evitamos repetir este trabajo

El proceso es idempotente: correrlo otra vez sobre la misma entrada da la misma salida, así que nunca tiene que repetir un trabajo que ya hizo, y nunca reabre en silencio un cruce que una persona ya revisó.

master_id es un id generado, almacenado en la tabla crosswalk, y nunca se lee de ningún sistema origen. Cada corrida sigue las mismas dos reglas: reutilizar el master_id existente para cualquier id origen que ya esté en el crosswalk, o, para un registro dorado nuevo, generar uno de forma determinista a partir de sha256(etiqueta de dominio + nombre normalizado), truncado a 12 caracteres hexadecimales. Como el id sale de los datos mismos y no del orden de las filas, correr el proceso dos veces sobre la misma entrada produce una salida idéntica byte por byte, y los datos nuevos nunca reabren un vínculo ya resuelto, salvo que las reglas de cruce mismas cambien (un ruleset_version nuevo).

Tres tablas guardan el registro de qué pasó y por qué:

- match_audit: una fila por registro origen, con el sistema origen, el id origen, el master_id, el nivel, el puntaje, una lista completa de la evidencia que contribuyó a la decisión (incluyendo cualquier veto que se haya activado), el ruleset_version, y quién decidió y cuándo.
- identity_crosswalk: el master_id mapeado a su hubspot_id, account_id y vitally_id, más el nivel de confianza y cuándo se resolvió.
- quarantine_companies y quarantine_deals: guardan las 28 filas de empresa clon y los 35 deals fantasma (667,251 en total), cada uno con un código de razón. Nada se elimina.

Un reporte de cobertura, desglosado por sistema y por nivel, da los números medidos detrás de la pregunta A0.3 del caso.

## Opciones que consideramos

| Opción | Qué hace | Por qué |
|---|---|---|
| A. Cascada determinista | Reglas ordenadas, gana el primer cruce | Rechazada: decisiones binarias, los conflictos se resuelven por el orden de las reglas y no por la evidencia, y no puede reportar una confianza medida |
| B. Cruce probabilístico (Fellegi-Sunter, mediante la librería Splink) | Aprende un peso por campo a partir de los datos y lo compara contra un umbral de probabilidad | Rechazada: sobreingeniería para 650 filas, la estimación de parámetros es difícil de defender en vivo, y es menos explicable para usuarios de negocio |
| C. Scorecard híbrido calibrado (elegida) | Blocking, evidencia ponderada por señal, reglas de veto, una bitácora de auditoría y una llave idempotente | Elegida: más componentes que documentar, pero cada uno responde a una pregunta específica que plantea el caso |

## Qué cambia en las secciones siguientes

| Área | Qué cambia |
|---|---|
| A1.1 (MRR activo) | El MRR total se calcula solo sobre el registro dorado; cualquier valor de MRR imputado o en conflicto se marca y se reporta por separado del total del CRM |
| A3 (health score / análisis de baja de clientes (churn)) | Usa el crosswalk para unir los datos de churn con los datos de uso sin filas duplicadas; sin él, las 28 filas clon aparecerían como clientes sin uso que hicieron churn, cuando en realidad no son cuentas reales |
| A4 (modelo de warehouse) | Recibe un crosswalk persistente y las tablas de auditoría como parte de su modelo, que es justo lo que evita que el equipo repita el trabajo de cruce manual cada vez que el warehouse se reconstruye |
| A6 (script de limpieza) | La normalización de fechas se mueve río arriba, hacia A0, como un paso obligatorio, en lugar de ser un ajuste cosmético final sobre los datos |

Se espera que la cola de revisión manual, el nivel M, se mantenga en un solo dígito, y se reportará de forma abierta en lugar de esconderse dentro de un conteo más grande de "coincidencias".

## Lista de verificación para el revisor

- [ ] Correr el proceso dos veces sobre la misma entrada da el mismo master_id para cada registro
- [ ] Las 28 filas clon HS-9000xx y los 35 deals fantasma aparecen en quarantine_companies y quarantine_deals con un código de razón, sin eliminarse ni fusionarse en silencio
- [ ] match_audit tiene exactamente una fila por registro origen, con nivel, puntaje, evidencia y cualquier veto que se haya activado
- [ ] Las 9 empresas que comparten uno de los 4 dominios duplicados se mantienen como 9 registros separados, no uno solo
- [ ] Cada umbral en la tabla de niveles se puede rastrear hasta los 596 pares etiquetados y lleva ruleset_version 1.0.0
- [ ] Los conteos del reporte de cobertura coinciden con los de este documento (596 en T0, 650 en T1, 54 en T2, y así sucesivamente)

## Preguntas abiertas

1. Resuelta. Ver [ADR-002: estimar el MRR faltante a partir del monto de los deals, marcado y nunca oculto](./ADR-002-mrr-imputation-and-normalization.md) para saber cómo se llena el MRR de las 28 empresas reales que no tienen MRR en el CRM.
2. Política de mes de referencia: resuelta el 2026-09-07. Las cuentas con churn usan su mes de churn como mes de referencia (de las 81 empresas con churn que tienen cuenta de producto, 78 tienen filas de uso, y en las 78 el último mes con uso es el mes de churn; las otras 3 no tienen ninguna fila de uso). Las cuentas activas usan 2024-08, el último mes del dataset, y cada una de las 515 cuentas activas en el CRM que tienen cuenta de producto tiene una fila de uso en ese mes. Las series de uso no tienen huecos internos (0 de 647 cuentas) y el uso cero se guarda como un cero explícito, así que una fila faltante significa que la cuenta no fue cliente ese mes.
3. Resuelta. Ver [ADR-003: medir la tendencia de uso como momentum reciente, nunca en el mes de churn](./ADR-003-usage-trend-and-leakage-guard.md) para la fórmula, la regla de historia mínima y el resguardo contra fuga de datos (leakage guard).
