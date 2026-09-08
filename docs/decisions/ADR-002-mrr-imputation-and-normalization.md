# ADR-002: estimar el MRR faltante a partir del monto de los deals, marcado y nunca oculto

- Estado: Aceptado (2026-09-07)
- Alcance: A0 (dataset maestro), A1.1 (MRR activo), A5 (tablero), A6 (script de limpieza)
- Decisores: candidato (responsable)

De las 678 filas de empresa en HubSpot, 56 no tienen registrado un valor de MRR (monthly recurring revenue, el monto que un cliente paga cada mes). La mitad de ellas, 28 filas, son las filas duplicadas HS-9000xx que el ADR-001 ya deja aparte en cuarentena, así que se quedan intactas y sin llenar. Las otras 28 son empresas reales (ids HS-1xxxxx) que simplemente no tienen un valor de MRR en el CRM. Esta decisión llena un valor de MRR para esas 28 empresas reales, estimado a partir del monto de sus propios deals, en lugar de dejar el campo vacío, para que cualquier tablero o reporte de ingresos que ordene o totalice clientes por MRR pueda incluirlas. Esto le importa a cualquiera que lea un número de MRR, un analista que escribe una consulta de ingresos o un director que lee el tablero de A5, porque hoy una empresa sin valor de MRR simplemente desaparece de un reporte ordenado por MRR, aunque sea un cliente real que sí paga.

## Ruta rápida

1. Revisar si la empresa ya tiene un valor de MRR del CRM. Si lo tiene, se conserva: un valor imputado nunca sobrescribe un valor del CRM.
2. Si el MRR falta y la fila es uno de los 28 clones HS-9000xx, se deja como está; el ADR-001 ya pone esa fila en cuarentena.
3. Si el MRR falta y la fila es una empresa real, se revisan sus deals y se toma el monto que comparten (cada una de las 28 empresas tiene un único monto distinto entre todos sus deals).
4. Se convierte el monto a MXN si la empresa cobra en USD, usando un tipo de cambio fijo de 18.5 MXN por USD, y se registra de dónde salió el valor y qué tanto confiar en él.
5. Se escribe una fila en la bitácora de excepciones que nombra el deal origen, y se conserva la moneda y el monto originales junto con el valor convertido para que la estimación siempre se pueda rastrear.

## El problema en números

| Hallazgo | Qué encontramos |
|---|---|
| MRR faltante en general | 56 de 678 filas de empresa tienen un valor mrr NULL |
| Ya resuelto por el ADR-001 | 28 de esas 56 son las filas duplicadas HS-9000xx, en cuarentena y nunca imputadas |
| Empresas reales sin MRR | Las otras 28 son empresas reales (ids HS-1xxxxx) sin MRR en el CRM |
| Mezcla de monedas | 22 de las 650 empresas reales cobran en USD; esta decisión fija el tipo de cambio en 18.5 MXN por USD |
| Cobertura de deals | Las 650 empresas reales tienen al menos un deal |
| Qué tan bien predice el MRR el monto del deal | Al unir los deals con su empresa, el monto del deal es igual al MRR de la empresa en 655 de 962 casos (68%); la mediana de monto dividido entre MRR es 1.00 en los tres pipelines (New Business, Renewal, Upsell) |
| Consistencia dentro de las 28 empresas sin MRR | Cada una de las 28 tiene un único monto de deal distinto entre todos sus deals |
| Etapa de los deals de las 28 | 4 de las 28 tienen un deal en closedwon; las otras 24 solo tienen deals abiertos o perdidos |

## Cómo llenamos un valor faltante

El monto del deal no es idéntico al MRR, pero lo sigue de cerca: el monto del deal es igual al MRR de la empresa en el 68% de los casos comparables, y la mediana de monto dividido entre MRR es 1.00 en los tres pipelines. Dentro de las 28 empresas sin MRR, cada una tiene un único monto de deal distinto entre todos sus deals, así que no hay ambigüedad sobre qué número usar para esa empresa.

El dataset maestro guarda cuatro columnas para llevar tanto el valor como qué tanto se puede confiar en él:

| Columna | Qué contiene |
|---|---|
| mrr_mxn | El valor de MRR en MXN, el número que debe usar cualquier otro reporte |
| mrr_source | crm (vino directamente de HubSpot) o imputed_from_deal (estimado a partir del monto de un deal) |
| mrr_confidence | high, cuando la empresa tiene un deal en closedwon (4 de las 28), o medium, cuando solo tiene deals abiertos o perdidos (24 de las 28) |
| mrr_original, currency_original | el valor y la moneda del CRM exactamente como llegaron, conservados para no perder nada sobre el origen |

Los montos en USD se convierten a mrr_mxn con un tipo de cambio fijo de 18.5 MXN por USD.

## Quién gana cuando hay más de un valor

Un valor del CRM siempre gana sobre uno imputado. Esta regla es idempotente: en cuanto HubSpot aporta un valor de MRR para una empresa, correr la imputación otra vez ya no toca esa empresa, un valor imputado nunca sobrescribe un valor del CRM. La imputación solo llena un hueco; nunca compite con un valor real.

## Cómo mantenemos la estimación honesta y rastreable

Cada reporte que muestra MRR muestra dos totales lado a lado: el MRR reportado, construido solo con valores del CRM, y el MRR total incluyendo valores imputados, con la proporción imputada indicada junto al número. Quien lo lee siempre sabe cuánto del número es un monto confirmado y facturado, y cuánto es una estimación.

El script de limpieza de A6 escribe una fila en una bitácora de excepciones por cada empresa que imputa, nombrando el deal_id origen que aportó el monto, para que cualquier estimación se pueda rastrear hasta el deal exacto del que salió.

## Opciones que consideramos

| Opción | Qué hace | Por qué |
|---|---|---|
| a. Dejar el MRR como NULL | No hacer nada | Rechazada: subestima el MRR activo de 28 de 650 empresas (4.3% de las cuentas) y las vuelve invisibles en cualquier tablero ordenado por MRR |
| b. Imputar la mediana de MRR del mismo segmento y plan | Llenar el hueco con un valor típico de empresas similares | Rechazada: fácil de calcular, pero oculta cuánto varía en realidad el ingreso entre cuentas, y el número no se puede rastrear hasta un registro real |
| c. Imputar a partir del monto de los deals propios de la empresa (elegida) | Llenar el hueco con el monto que ya existe en los deals propios de esa empresa | Elegida: se puede rastrear hasta un deal_id específico, coincide con el valor del CRM en el 68% de los casos comparables, y queda marcada para que quien la lea pueda excluirla |

## Riesgos y cómo los manejamos

| Riesgo | Cómo lo manejamos |
|---|---|
| En el 32% de los casos comparables, el monto del deal difiere del MRR, así que un valor imputado puede estar equivocado | mrr_source y mrr_confidence marcan cada estimación, cada reporte muestra los dos totales, y un valor real del CRM reemplaza la estimación en el momento en que existe |
| Quien lea el reporte podría actuar sobre un número estimado como si fuera ingreso confirmado, por ejemplo priorizando una cuenta con base en un monto de deal inflado | El tablero de A5 muestra una marca visible en cada fila imputada, así que la estimación nunca se presenta como una cifra confirmada |

## Qué cambia en las secciones siguientes

| Área | Qué cambia |
|---|---|
| A1.1 (MRR activo) | El SQL expone los dos totales: el MRR reportado del CRM y el MRR total incluyendo valores imputados |
| A3 (ingreso en riesgo) | Usa mrr_mxn para las cifras de ingreso en riesgo, llevando consigo las marcas mrr_source y mrr_confidence para que los números sigan siendo rastreables |
| A5 (tablero) | Marca de forma visible cada fila imputada, para que quien lo lea pueda ver cuáles números son estimaciones |
| A6 (script de limpieza) | Registra conteos por tipo de corrección: cuántos nulos se imputaron, cuántos montos en USD se convirtieron, cuántas fechas se normalizaron |

## Lista de verificación para el revisor

- [ ] Cada empresa con un valor de MRR del CRM conserva ese valor exacto; nada se sobrescribe con un número imputado
- [ ] Solo las 28 empresas reales (HS-1xxxxx) reciben un valor imputado; los 28 clones HS-9000xx se quedan en cuarentena e intactos
- [ ] Cada fila imputada lleva mrr_source = imputed_from_deal y el mrr_confidence correcto (high para las 4 empresas con un deal en closedwon, medium para las 24 que solo tienen deals abiertos o perdidos)
- [ ] mrr_original y currency_original siguen presentes y sin cambios en cada fila
- [ ] Los montos en USD se convierten a MXN a 18.5 MXN por USD, de forma consistente
- [ ] Cada reporte que muestra MRR muestra el total reportado y el total incluyendo valores imputados lado a lado, con la proporción imputada indicada
- [ ] La bitácora de excepciones tiene exactamente una fila por empresa imputada, nombrando el deal_id origen
