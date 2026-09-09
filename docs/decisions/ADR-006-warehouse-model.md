# ADR-006: un esquema en estrella que envuelve los marts existentes y hace que el trabajo manual de A0 nunca se repita

- Estado: Aceptado (2026-09-09)
- Alcance: A4 (modelo de warehouse), con efectos en A5 (tablero) y Parte B (playbook de retención)
- Decisores: candidato (responsable)

El caso pide el modelo de warehouse que serviría de base para lo que ya existe, ahora que la información entra desde tres sistemas desincronizados: qué hechos y dimensiones, dónde viven las llaves de reconciliación, cómo se maneja el historial de cambios y cómo se evita repetir el cruce manual de A0. El ADR-001 ya prometió que A4 recibiría "un crosswalk persistente y las tablas de auditoría como parte de su modelo"; esa promesa ya es código real hoy, corriendo en cada build de A0. Lo que falta es formalizarla como esquema en estrella, agregar SCD tipo 2 donde el caso lo pide, y sumar la única pieza que hace falta para que una decisión humana sobreviva a un rebuild. Resultado: un esquema en estrella de Kimball que envuelve los marts de A0/A1/A3 sin tocarlos, un comando `warehouse` que lo materializa sobre DuckDB, y una tabla de overrides que hace que revisar un registro una vez sea revisarlo para siempre.

La investigación (`docs/research/01-bi-revops-data-architecture.md`, sección 2) recomienda un esquema en estrella de Kimball para la capa de presentación, con dimensiones conformadas y SCD tipo 2, y deja Data Vault como preparación para cuando aparezca una cuarta fuente. Esta decisión sigue esa recomendación: los tres sistemas de hoy no justifican el costo de joins adicionales que traería Data Vault en producción.

## Ruta rápida

1. `python -m worky_engine warehouse` toma los marts y el crosswalk que ya existen de A0/A1/A3 y los envuelve en vistas SQL de un esquema en estrella, sin modificar ningún archivo de esos módulos.
2. El `.duckdb` de este comando persiste entre corridas, a diferencia de `build`, `analyze` y `health`, que siguen regenerando el suyo (decisión D6 de A0). Es una excepción documentada, no una contradicción silenciosa.
3. `dim_company` aplica SCD tipo 2 sobre `plan` y `csm_owner`, con `effective_from`, `effective_to`, `is_current` y una llave surrogate `company_sk`. La captura es hacia adelante, desde la primera vez que el comando corre más de una vez.
4. `identity_overrides` guarda la decisión de una persona sobre un registro que cayó en revisión manual (nivel M), y el proceso de resolución la aplica antes de correr la cascada de A0, sin modificar ese módulo. Es la pieza que faltaba para que ese trabajo humano no se pierda en cada rebuild.
5. `fact_health_score_monthly` guarda cada corrida del comando `health` por fecha, con el mismo mecanismo de snapshot que `dim_company`.
6. La marca de agua incremental por sistema origen queda documentada con su contrato exacto; se implementa solo si el presupuesto de líneas alcanza después de cubrir dim_company, SCD2 y overrides.
7. El ERD que acompaña este documento extiende `docs/diagrams/03-modelo-relacional-objetivo.html` hacia el esquema en estrella, con la skill `archify` (tipo `erd`), en lugar de repetirlo desde cero.

## Qué ya existe y qué proponemos

`identity_crosswalk.csv` y `match_audit.csv`, prometidos en el ADR-001, ya son código real hoy:

| Pieza | Estado hoy |
|---|---|
| Crosswalk persistente | `identity_crosswalk.csv` se reutiliza entre builds vía `_load_existing_crosswalk` y `keys.resolve_master_id` |
| Bitácora de auditoría | `match_audit.csv` tiene una fila por registro origen, con nivel, puntaje y evidencia |
| Capas staging y marts | `worky_engine/sql/staging/` y `worky_engine/sql/marts/` ya funcionan como staging más presentación de Kimball, sin ese nombre |
| Historial de plan o CSM | No existe en ningún sistema origen ni en el motor; el `.duckdb` de `build` se borra en cada corrida (D6 de A0) |
| Cruce incremental | No existe; `cascade.py` reevalúa los 1,978 registros de origen en cada build, aunque solo el `master_id` se reutiliza |
| Decisiones de revisión manual | No se guardan en ningún lado; un registro en nivel M vuelve a la cola en cada rebuild |
| MRR y health score con grano temporal | No existen; `mart_mrr` da un valor actual por empresa y `health` no guarda fecha de corrida |

Los hechos y dimensiones nuevos leen esas piezas tal como están, sin duplicar ninguna:

| Tabla | Grano | Llave | Fuente real |
|---|---|---|---|
| `dim_company` | una fila vigente por `master_id`, más una fila cerrada por cada cambio de plan o CSM | `company_sk` (surrogate), `master_id` | `identity_crosswalk` + `mart_company_core` |
| `dim_date` | un día de calendario | `date_key` | generada desde el `signup_date` mínimo hasta 2024-08-31 |
| `dim_csm` | un CSM | `csm_key` | valores distintos de `csm_owner` / `csm_email` |
| `dim_plan` | un plan | `plan_key` | valores distintos de `companies.plan` |
| `map_source_identity` | una fila por vínculo de origen a `master_id` | `source_system`, `source_id` | `identity_crosswalk` + `match_audit`, formalizados con ese nombre |
| `fact_usage_monthly` | (empresa, mes) | `company_sk`, `date_key` | `stg_product_usage` |
| `fact_support_tickets` | un ticket | `ticket_id` | `stg_tickets` |
| `fact_deals` | un deal | `deal_id` | `stg_deals` / `mart_deal_normalized` |
| `fact_revenue_monthly` | (empresa, mes) | `company_sk`, `date_key` | `fact_deals` agregado por `close_date` |
| `fact_marketing_touches` | un touch | `touch_id` | `stg_marketing_touches` |
| `fact_health_score_monthly` | (empresa, fecha de corrida) | `company_sk`, `run_date` | salida del comando `health` |

## Qué decidimos

| Tema | Decisión | Por qué |
|---|---|---|
| Forma del entregable | Documento + ERD + DDL ejecutable acotado (opción b): comando `warehouse` que materializa el esquema en estrella sobre DuckDB envolviendo marts y crosswalk existentes | Mantiene el patrón de A0/A1/A3 (código real, probado) y demuestra SCD2 y overrides con una prueba; la opción a no prueba nada y la opción c cuesta 600 a 900 líneas más por algo que la propia investigación recomienda dejar como trabajo futuro |
| Dónde viven las llaves de reconciliación (pregunta A4 del caso) | Las dos cosas a la vez: `identity_crosswalk` sigue siendo la tabla de mapeo persistente, y la cascada de A0 sigue siendo el proceso que la resuelve, consultando primero `identity_overrides` y, con presupuesto disponible, una marca de agua que solo procese `source_id` no vistos | El caso pregunta si es tabla o proceso como si fueran alternativas; ya son las dos cosas hoy, y elegir solo una perdería la mitad de la respuesta real |
| Historial de cambios (pregunta A4 del caso) | SCD tipo 2 en `dim_company` sobre `plan` y `csm_owner`, capturado hacia adelante desde la primera corrida repetida de `warehouse` | Ningún sistema origen ni el motor guardan una foto anterior que reconstruir hacia atrás: los tres sistemas son fotografías del estado actual y el `.duckdb` de `build` se borra cada corrida (D6 de A0) |
| Nunca repetir el trabajo manual de A0 (pregunta A4 del caso) | Cuatro piezas: crosswalk persistente, `master_id` idempotente y `match_audit` ya existen; se agrega `identity_overrides` (source_system, source_id, master_id, decided_by, decided_at, reason), consultada antes de la cascada | Hoy un registro en nivel M vuelve a la cola de revisión en cada rebuild aunque una persona ya lo haya resuelto ayer; overrides es la única pieza de las cuatro que faltaba |
| Persistencia del `.duckdb` de `warehouse` | Se conserva entre corridas, bajo `.build/` e ignorado por Git; `build`, `analyze` y `health` siguen regenerando el suyo | Es indispensable para observar el SCD2 en más de una corrida; se documenta como excepción a la decisión D6 de A0, no como contradicción silenciosa |
| `fact_health_score_monthly` | Se incluye, con el mismo mecanismo de snapshot por fecha de corrida que `dim_company` | Extiende el mismo patrón de captura hacia adelante; hoy `health` calcula un puntaje sin guardar fecha para comparar entre corridas |
| Marca de agua incremental | Se documenta con su contrato exacto (procesar solo `source_id` no vistos contra el crosswalk; los vínculos existentes sobreviven); se implementa solo si sobra presupuesto de líneas después de dim_company, SCD2 y overrides | Con 650 empresas no cambia ningún número medible hoy; es rigor de ingeniería, no una necesidad del dataset |
| `fact_revenue_monthly` | Agrega `fact_deals` por `close_date`; nunca se presenta como una serie mensual de `mrr_mxn` | No existe ninguna fuente con MRR fechado mes a mes (ADR-002); mostrar esa serie sería inventar un dato que el dataset no tiene |
| Llaves surrogate | Se generan de forma determinista (hash o secuencia estable), nunca por orden de ejecución | Preserva la idempotencia byte a byte que ya exige la especificación de build-cli |
| Relación con los marts existentes | El esquema en estrella envuelve `mart_company_core`, `mart_usage`, `mart_deal_normalized`, `mart_support` y `stg_marketing_touches` como vistas SQL; ningún archivo de A1 o A3 cambia una línea | A5 puede leer el esquema nuevo o los marts de siempre; ambos caminos quedan abiertos |
| Uniones históricas | Cualquier hecho histórico se une contra la versión de `dim_company` vigente en la fecha del hecho, no contra la fila actual | Resguardo contra fuga de datos (ADR-003): un análisis de churn debe preguntar qué CSM tenía la cuenta cuando se fue, no cuál tiene hoy |

## Opciones que consideramos

| Opción | Por qué se rechazó o se eligió |
|---|---|
| a. Solo documento + ERD | Rechazada: es la lectura literal del caso, pero rompe el patrón de A0/A1/A3, que se entregaron como código corriendo, y no prueba que el SCD2 o los overrides funcionan |
| b. Documento + ERD + DDL ejecutable acotado (elegida) | Elegida: sigue el mismo patrón, demuestra SCD2 y overrides con una prueba, envuelve los marts existentes sin duplicar lógica, cabe en 400 a 650 líneas de autoría dentro del presupuesto de 800 |
| c. (b) más una capa raw estilo Data Vault ejecutada | Rechazada: 600 a 900 líneas adicionales; la propia investigación recomienda presentarla solo como preparación para el crecimiento, no como entregable ejecutado; queda documentada como trabajo futuro |
| Marca de agua incremental implementada desde el inicio | Rechazada como prioridad: con 650 empresas no cambia ningún resultado medible; se documenta su contrato y se implementa solo si sobra presupuesto |
| Reconstruir el historial de plan o CSM hacia atrás | Rechazada: no existe ninguna fuente con una foto anterior de esos atributos; reconstruir algo que no está en los datos sería inventarlo |

## Qué cambia en las secciones siguientes

| Sección | Efecto |
|---|---|
| A5 | El tablero puede leer el esquema en estrella nuevo (dim_company con su banda SCD2, fact_health_score_monthly) o seguir leyendo los marts de siempre; ambos caminos quedan abiertos. |
| A6 | Si el script de A6 corrige alguna columna de origen, el efecto llega solo a través de los marts que A4 ya envuelve; A4 no necesita cambios propios para reflejarlo. |
| Parte B | El playbook de retención puede citar `identity_overrides` como evidencia de que una decisión de CSM sobre una cuenta ambigua queda registrada y no se pierde en el siguiente rebuild. |

## Riesgos y cómo los manejamos

| Riesgo | Mitigación |
|---|---|
| Sobreingeniería de alcance: el caso solo pide diagrama o descripción textual | El documento de diseño y el ERD ya cumplen la pregunta literal; el DDL ejecutable es una decisión de producto declarada aparte, acotada a 400 a 650 líneas |
| Historial que no se puede demostrar con datos reales | Se dice de forma explícita que el dataset del caso es una sola foto; la evidencia de SCD2 es una prueba con dos corridas simuladas, nunca datos reales presentados como historial |
| `fact_revenue_monthly` puede confundirse con una serie de MRR | El nombre y la documentación dejan claro que es MRR de deals cerrados por mes, agregado desde `fact_deals`, no una repetición de `mrr_mxn` |
| UTF-8 en Windows con nombres de CSM y de empresa acentuados | Mismo resguardo que A0: todo archivo nuevo abre con `encoding="utf-8"` explícito |
| Presupuesto de la PR (400 líneas) dentro del presupuesto del cambio (800 líneas) | La opción b queda acotada desde el diseño; la marca de agua incremental se implementa solo si sobra presupuesto después de dim_company, SCD2 y overrides |
| `identity_overrides` toca un módulo que A0 ya cerró y archivó | Es una extensión aditiva: ningún archivo existente de `identity_resolution` cambia, la tabla y sus pruebas viven en archivos nuevos, y el proceso de resolución la aplica antes de correr la cascada |

## Lista de verificación para el revisor

- [ ] `identity_crosswalk.csv` y `match_audit.csv` no cambian, ni ningún archivo existente de `identity_resolution`; `identity_overrides` es una tabla nueva y aditiva.
- [ ] El comando `warehouse` no modifica ningún archivo de `worky_engine/sql/staging/` ni de `worky_engine/sql/marts/`; solo los lee.
- [ ] La prueba de SCD2 simula dos corridas con un cambio de plan o de CSM y verifica que la fila vieja cierra (`effective_to`, `is_current = false`) y la fila nueva abre correctamente.
- [ ] `fact_revenue_monthly` se documenta y se nombra como agregación de deals por fecha de cierre, nunca como serie de `mrr_mxn`.
- [ ] El `.duckdb` de `warehouse` vive en `.build/`, está ignorado por Git, y su persistencia entre corridas queda documentada como excepción a la decisión D6 de A0.
- [ ] Ningún archivo de `outputs/` ni ningún golden de A0/A1/A3 se toca.
- [ ] El ERD extiende `docs/diagrams/03-modelo-relacional-objetivo.html` en lugar de reemplazarlo o duplicarlo.

## Preguntas abiertas

1. Si se implementa la marca de agua incremental, con qué granularidad de timestamp se marca "visto" cada `source_id`, dado que el dataset del caso no trae un campo de carga explícito.
2. Para producción: cuántas corridas reales del comando `warehouse` hacen falta para que el historial de SCD2 dé cobertura útil, más allá de la prueba sintética.
3. Si A5 termina leyendo el esquema en estrella nuevo en vez de los marts, si conviene exponer también `dim_csm` y `dim_plan` como filtros del tablero, o dejarlos solo como soporte interno de `dim_company`.
