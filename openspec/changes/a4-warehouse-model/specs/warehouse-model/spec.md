# Especificación: esquema en estrella ejecutable del warehouse (`warehouse-model`)

## Propósito

Envuelve los marts y el crosswalk de A0/A1/A3 en un esquema en estrella de Kimball ejecutable sobre DuckDB: vistas de dimensiones y hechos, `dim_company` con historial SCD tipo 2 sobre plan y CSM, `identity_overrides` como tabla persistida y `fact_health_score_monthly` como snapshot por fecha de corrida. Implementa el ADR-006.

## ADDED Requirements

### Requirement: comando `warehouse` sin build previo

El comando `python -m worky_engine warehouse` MUST correr sin depender de una corrida previa de `build`, `analyze` o `health`. MUST persistir su `.duckdb` bajo `.build/`, ignorado por Git, y MUST terminar en 0 en éxito y distinto de cero con un mensaje en español si falta una base o una dependencia.

#### Scenario: corrida sin build previo

- Dado un repositorio recién clonado, sin haber corrido `build`
- Cuando alguien corre `python -m worky_engine warehouse`
- Entonces el comando termina en 0 y genera su `.duckdb` bajo `.build/`

#### Scenario: falta una dependencia o una base de datos

- Dado que falta DuckDB o una de las tres bases de origen
- Cuando alguien corre `warehouse`
- Entonces el comando termina con código distinto de cero y un mensaje en español que nombra lo que falta

### Requirement: persistencia del `.duckdb` entre corridas

A diferencia de `build`, `analyze` y `health`, que regeneran el suyo en cada corrida (decisión D6 de A0), el `.duckdb` de `warehouse` MUST sobrevivir entre corridas para que el historial SCD2 se pueda observar. Esta persistencia MUST documentarse como excepción explícita a D6, no como una contradicción silenciosa.

#### Scenario: el archivo sobrevive a la segunda corrida

- Dado un `.duckdb` de `warehouse` generado por una primera corrida
- Cuando alguien corre `warehouse` una segunda vez
- Entonces el mismo archivo se reutiliza y conserva las filas cerradas de la primera corrida

#### Scenario: excepción documentada a D6

- Dado el documento de diseño del warehouse
- Cuando alguien busca la decisión de persistencia del `.duckdb`
- Entonces encuentra la excepción a D6 declarada de forma explícita, junto a la razón

### Requirement: vistas de dimensiones y hechos sobre los marts existentes

El sistema MUST exponer `dim_date`, `dim_csm`, `dim_plan` y `map_source_identity` como vistas derivadas de los marts y del crosswalk existentes, y `fact_usage_monthly`, `fact_support_tickets`, `fact_deals` y `fact_marketing_touches` como vistas a su grano nativo. El sistema MUST NOT modificar ningún archivo existente de `worky_engine/sql/staging/` ni de `worky_engine/sql/marts/`.

#### Scenario: dimensiones derivadas sin duplicar lógica

- Dado `mart_company_core` con sus valores de `plan` y `csm_owner`
- Cuando el sistema construye `dim_plan` y `dim_csm`
- Entonces cada tabla contiene los valores distintos leídos del mart, sin una copia paralela de esos datos

#### Scenario: hechos al grano correcto

- Dado `stg_product_usage`, `stg_tickets`, `stg_deals` y `stg_marketing_touches`
- Cuando el sistema construye los hechos correspondientes
- Entonces cada hecho conserva el grano de su fuente: mes por empresa, ticket, deal y touch

#### Scenario: marts y staging sin cambios

- Dado los archivos existentes de `worky_engine/sql/staging/` y `worky_engine/sql/marts/`
- Cuando alguien corre `warehouse`
- Entonces ningún archivo de esas dos carpetas cambia una línea

### Requirement: `fact_revenue_monthly` agregado por fecha de cierre

`fact_revenue_monthly` MUST agregar `fact_deals` por `close_date` a grano (empresa, mes). El sistema MUST NOT presentar esta tabla como una serie mensual de `mrr_mxn`, porque ninguna fuente trae MRR fechado mes a mes (ADR-002).

#### Scenario: agregación por mes de cierre

- Dado un conjunto de deals cerrados en distintos meses para la misma empresa
- Cuando el sistema construye `fact_revenue_monthly`
- Entonces cada fila suma el monto de los deals cerrados en ese mes para esa empresa

#### Scenario: no es una serie de `mrr_mxn`

- Dado la documentación de `fact_revenue_monthly`
- Cuando alguien revisa su definición
- Entonces queda claro que es MRR de deals cerrados por mes, y no una repetición de la columna `mrr_mxn`

### Requirement: `dim_company` con historial SCD tipo 2

`dim_company` MUST mantener una fila vigente por `master_id` más una fila cerrada por cada cambio de `plan` o `csm_owner`, con `company_sk` (surrogate), `master_id`, `effective_from`, `effective_to` e `is_current`. La captura MUST ser hacia adelante, comparando cada corrida contra la última fila vigente.

#### Scenario: primera corrida abre una fila vigente por empresa

- Dado el primer `warehouse` corrido sobre un `.duckdb` vacío
- Cuando el sistema construye `dim_company`
- Entonces cada empresa del crosswalk recibe exactamente una fila con `is_current = true` y `effective_to` vacío

#### Scenario: corrida sin cambios no agrega filas

- Dado un `dim_company` ya poblado y ningún cambio de `plan` ni `csm_owner` en la fuente
- Cuando alguien corre `warehouse` de nuevo
- Entonces el número de filas de `dim_company` no cambia

#### Scenario: un cambio de plan cierra la fila anterior y abre una nueva

- Dado una empresa cuyo `plan` cambió desde la última corrida
- Cuando alguien corre `warehouse`
- Entonces la fila anterior queda con `is_current = false` y `effective_to` igual a la fecha de esta corrida, y una fila nueva queda con `is_current = true`

#### Scenario: una empresa que desaparece de las fuentes conserva su fila

- Dado una empresa presente en una corrida anterior y ausente de las fuentes en la corrida actual
- Cuando alguien corre `warehouse`
- Entonces su última fila vigente permanece en `dim_company` sin cerrarse ni eliminarse

### Requirement: uniones históricas contra la versión vigente en la fecha del hecho

Cualquier hecho histórico (uso, soporte, deals) MUST unirse contra la fila de `dim_company` vigente en la fecha del hecho, nunca contra la fila actual (ADR-003).

#### Scenario: un hecho se une contra la versión vigente en su fecha

- Dado una empresa que cambió de CSM entre la fecha de un ticket antiguo y hoy
- Cuando el sistema une ese ticket contra `dim_company`
- Entonces el ticket queda asociado al CSM que era vigente en la fecha del ticket, no al CSM actual

#### Scenario: dos hechos de fechas distintas ven CSM distinto

- Dado una empresa con dos hechos, uno antes y otro después de un cambio de CSM
- Cuando el sistema resuelve ambas uniones
- Entonces cada hecho queda asociado al CSM vigente en su propia fecha

### Requirement: `identity_overrides` como tabla persistida leída por el warehouse

`identity_overrides` MUST existir como tabla persistida con las columnas `source_system`, `source_id`, `master_id`, `decided_by`, `decided_at` y `reason`. El warehouse MUST leer los overrides ya aplicados al crosswalk y reflejarlos en `map_source_identity`.

#### Scenario: tabla con las columnas del contrato

- Dado el esquema del `.duckdb` de `warehouse`
- Cuando alguien inspecciona `identity_overrides`
- Entonces la tabla tiene las seis columnas del contrato

#### Scenario: override reflejado en `map_source_identity`

- Dado un `source_id` cuyo `master_id` fue fijado por un override ya aplicado al crosswalk
- Cuando el sistema construye `map_source_identity`
- Entonces esa fila muestra el `master_id` del override

### Requirement: `fact_health_score_monthly` como snapshot por fecha de corrida

`fact_health_score_monthly` MUST guardar una fila por (`company_sk`, `run_date`) con la salida del comando `health` de esa corrida. Una corrida repetida con la misma `run_date` MUST ser idempotente y MUST NOT duplicar filas.

#### Scenario: cada corrida de health agrega un snapshot

- Dado el comando `health` corrido en una fecha
- Cuando el sistema construye `fact_health_score_monthly`
- Entonces existe una fila por empresa con esa `run_date`

#### Scenario: snapshot idempotente para la misma fecha

- Dado un snapshot ya guardado para una `run_date`
- Cuando alguien corre `health` otra vez en la misma fecha
- Entonces el número de filas de esa `run_date` no cambia

### Requirement: determinismo de llaves surrogate y goldens byte-idénticos

Las llaves surrogate (`company_sk`, `date_key`, entre otras) MUST generarse de forma determinista, nunca por el orden de ejecución. Dos corridas de `warehouse` sin cambios en las fuentes MUST producir salidas byte-idénticas.

#### Scenario: dos corridas sin cambios dan resultados idénticos

- Dado un `.duckdb` de `warehouse` recién construido
- Cuando alguien corre `warehouse` dos veces seguidas sin cambiar las fuentes
- Entonces los archivos de la segunda corrida son idénticos byte por byte a los de la primera

#### Scenario: las llaves no dependen del orden de ejecución

- Dado el mismo conjunto de empresas procesado en dos órdenes distintos
- Cuando el sistema genera sus llaves surrogate
- Entonces cada empresa recibe la misma llave sin importar el orden en que se procesó

### Requirement: goldens versionados del warehouse

El sistema MUST versionar `outputs/warehouse/dim_company.csv` y `outputs/warehouse/map_source_identity.csv` como goldens.

#### Scenario: goldens generados en cada corrida

- Dado una corrida exitosa de `warehouse`
- Cuando alguien revisa `outputs/warehouse/`
- Entonces encuentra `dim_company.csv` y `map_source_identity.csv`

### Requirement: aislamiento respecto a los goldens de A0, A1 y A3

El comando `warehouse` MUST NOT leer ni modificar ninguna salida existente bajo `outputs/` de A0, A1 o A3.

#### Scenario: goldens de A0, A1 y A3 sin cambio

- Dado los goldens existentes de A0, A1 y A3
- Cuando alguien corre `warehouse`
- Entonces ningún archivo fuera de `outputs/warehouse/` cambia

#### Scenario: warehouse no depende de esas salidas

- Dado un repositorio sin ninguna salida previa bajo `outputs/`
- Cuando alguien corre `warehouse`
- Entonces el comando corre sin error, sin leer ningún archivo de `outputs/` de A0, A1 o A3

### Requirement: contrato de la marca de agua incremental

El sistema SHOULD procesar, para el cruce de identidad, solo los `source_id` que no estén todavía en el crosswalk, dejando intactos los vínculos ya resueltos. Si se implementa, cada vínculo existente en `identity_crosswalk` MUST sobrevivir sin recalcularse.

#### Scenario: contrato documentado

- Dado el documento de diseño del warehouse
- Cuando alguien busca el contrato de la marca de agua incremental
- Entonces encuentra qué `source_id` se considera "ya visto" y cuáles se procesan de nuevo

#### Scenario: vínculos existentes sobreviven si se implementa

- Dado un crosswalk con vínculos ya resueltos y una marca de agua implementada
- Cuando llega un `source_id` nuevo
- Entonces solo ese `source_id` se evalúa, y los vínculos existentes no cambian
