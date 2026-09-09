# Especificación: ensamblaje del dataset maestro (`master-dataset-assembly`)

## Propósito

Ensambla la fila final de cada empresa real a partir de `identity_crosswalk` y de las fuentes normalizadas, aplicando la supervivencia de atributos, la imputación de MRR y los agregados de uso, soporte y comercial. Implementa la parte de ensamblaje del ADR-002 y del ADR-003.

## ADDED Requirements

### Requirement: una fila por empresa real

El sistema MUST producir exactamente 650 filas en el dataset maestro, una por cada `master_id` de una empresa real, sin duplicados y sin ninguna de las filas en cuarentena.

#### Scenario: conteo final de filas

- Dado el crosswalk con sus 650 empresas reales resueltas
- Cuando el sistema ensambla el dataset maestro
- Entonces el resultado tiene exactamente 650 filas, cada una con un `master_id` único

### Requirement: columnas mínimas del dataset maestro

El dataset maestro MUST incluir, para cada fila, `master_id`, `confidence_tier` y las columnas de la tabla siguiente.

| Columna | Contenido |
|---|---|
| `segment`, `industry`, `plan` | atributos comerciales de la empresa |
| `mrr_mxn` | MRR normalizado a MXN |
| `mrr_source`, `mrr_confidence`, `mrr_original`, `currency_original` | origen y trazabilidad del valor de MRR |
| `csm_owner` | responsable de la cuenta |
| `active_users_latest`, `active_users_avg` | usuarios activos más recientes y su promedio |
| `trend_usage`, `trend_asof_month`, `trend_status` | tendencia de uso y su mes de corte |
| `tickets_total`, `tickets_urgent`, `csat_avg` | agregados de soporte |
| `closed_revenue_mxn` | revenue cerrado |
| `acquisition_channel` | canal de adquisición |
| `churn_status` | estatus de baja |

`tickets_urgent` cuenta los tickets de la empresa con `priority = 'Urgent'`. Los valores aceptados en `priority` son exactamente `Low`, `Medium`, `High` y `Urgent`.

#### Scenario: fila con todas las columnas

- Dado una empresa cualquiera del dataset maestro
- Cuando el sistema construye su fila
- Entonces la fila incluye todas las columnas listadas, sin ninguna vacía de forma silenciosa

### Requirement: imputación de MRR desde el monto del deal

Para una empresa real sin valor de MRR en el CRM que tiene exactamente un monto mensual normalizado entre sus deals, el sistema MUST imputar `mrr_mxn` a partir de ese monto, MUST marcar `mrr_confidence` en `high` cuando la empresa tiene un deal en `closedwon` (deal cerrado y ganado), y MUST marcarlo en `medium` cuando no lo tiene. El sistema MUST NOT sobrescribir nunca un valor de MRR que ya viene del CRM. El dominio completo de `mrr_confidence`, incluido el valor `none` para los casos que no se pueden imputar, se define en el requisito de MRR sin resolver.

#### Scenario: imputación con deal closedwon

- Dado una de las 4 empresas reales sin MRR que tiene un deal en `closedwon`
- Cuando el sistema imputa su MRR
- Entonces `mrr_source` es `imputed_from_deal` y `mrr_confidence` es `high`

#### Scenario: imputación sin deal closedwon

- Dado una de las 24 empresas reales sin MRR que solo tiene deals abiertos o perdidos
- Cuando el sistema imputa su MRR
- Entonces `mrr_source` es `imputed_from_deal` y `mrr_confidence` es `medium`

#### Scenario: empresa con valor de CRM

- Dado una empresa que ya tiene un valor de MRR en HubSpot
- Cuando el sistema ensambla su fila
- Entonces `mrr_mxn` conserva el valor del CRM, y `mrr_source` es `crm`

### Requirement: MRR sin resolver

El sistema MUST usar el dominio `{high, medium, none}` para `mrr_confidence`. El sistema MUST marcar `mrr_confidence` en `none` si y solo si `mrr_source` es `unresolved`, y MUST dejar `mrr_mxn` vacío si y solo si `mrr_source` es `unresolved`. Una empresa real sin MRR en el CRM queda en `unresolved` cuando tiene más de un monto mensual normalizado distinto entre sus deals, o cuando no tiene ningún deal. El sistema MUST NOT fallar la construcción por una fila en `unresolved`, pero MUST contar esas filas y MUST reportarlas.

#### Scenario: empresa con dos montos ambiguos

- Dado una empresa real sin MRR en el CRM cuyos deals tienen dos montos mensuales normalizados distintos
- Cuando el sistema intenta imputar su MRR
- Entonces `mrr_source` es `unresolved`, `mrr_confidence` es `none`, y `mrr_mxn` queda vacío

#### Scenario: empresa sin deals

- Dado una empresa real sin MRR en el CRM y sin ningún deal
- Cuando el sistema intenta imputar su MRR
- Entonces `mrr_source` es `unresolved`, `mrr_confidence` es `none`, y `mrr_mxn` queda vacío

### Requirement: bitácora de excepciones de imputación

El sistema MUST escribir en `exceptions_log.csv` exactamente una fila por cada empresa imputada, nombrando su `deal_id` de origen.

#### Scenario: 28 filas de imputación

- Dado las 28 empresas reales sin MRR en el CRM
- Cuando el sistema termina la imputación
- Entonces `exceptions_log.csv` tiene exactamente 28 filas, cada una con su `deal_id`

### Requirement: mes de referencia

El sistema MUST usar el mes de `churn_date` como mes de referencia para una empresa con baja, y MUST usar `2024-08` como mes de referencia para una empresa activa.

#### Scenario: empresa con baja

- Dado una empresa con `churn_date` en un mes conocido
- Cuando el sistema define su mes de referencia
- Entonces el mes de referencia es el mes de `churn_date`

#### Scenario: empresa activa

- Dado una empresa sin `churn_date`
- Cuando el sistema define su mes de referencia
- Entonces el mes de referencia es `2024-08`

### Requirement: cálculo de trend_usage

El sistema MUST calcular `trend_usage` como el EWMA (promedio móvil exponencialmente ponderado) de span 3 dividido entre el EWMA de span 9, menos 1, sobre `active_users`, usando solo los meses hasta el mes de corte, definido como el mes de referencia menos k = 2 meses. El sistema MUST guardar `insufficient_history` cuando la empresa tiene menos de 3 meses de uso hasta ese mes de corte, y MUST guardar `no_usage` cuando no tiene ninguno.

#### Scenario: tendencia calculada

- Dado una empresa con más de 3 meses de uso hasta su mes de corte
- Cuando el sistema calcula su tendencia
- Entonces `trend_usage` tiene un valor numérico y `trend_status` es `computed`

#### Scenario: historia insuficiente

- Dado una empresa con menos de 3 meses de uso hasta su mes de corte
- Cuando el sistema calcula su tendencia
- Entonces `trend_status` es `insufficient_history`

#### Scenario: sin uso

- Dado una empresa sin ninguna fila de uso hasta su mes de corte
- Cuando el sistema calcula su tendencia
- Entonces `trend_status` es `no_usage`

### Requirement: resguardo contra fuga de datos

El sistema MUST NOT incluir en el cálculo de `trend_usage` ninguna fila de uso posterior al mes de corte guardado en `trend_asof_month`.

#### Scenario: fila posterior al mes de corte excluida

- Dado una empresa con filas de uso después de su mes de corte
- Cuando el sistema calcula su tendencia
- Entonces ninguna de esas filas posteriores entra al cálculo de `trend_usage`

### Requirement: canal de adquisición

El sistema MUST definir `acquisition_channel` como el canal del primer registro en `marketing_touches` de la empresa, ordenado por fecha. Cuando la empresa no tiene ningún touch, el sistema MUST usar `lead_source` de su primer deal como respaldo.

#### Scenario: empresa con touches

- Dado una empresa con al menos un registro en `marketing_touches`
- Cuando el sistema define su canal de adquisición
- Entonces el canal es el del primer touch por fecha

#### Scenario: empresa sin touches

- Dado una empresa sin ningún registro en `marketing_touches`
- Cuando el sistema define su canal de adquisición
- Entonces el canal es el `lead_source` de su primer deal

### Requirement: revenue cerrado

El sistema MUST calcular `closed_revenue_mxn` como la suma del `amount` de todos los deals en `closedwon` de la empresa.

#### Scenario: suma de deals cerrados

- Dado una empresa con tres deals en `closedwon` y dos deals abiertos
- Cuando el sistema calcula su revenue cerrado
- Entonces `closed_revenue_mxn` es la suma de los tres deals en `closedwon`, sin incluir los dos abiertos
