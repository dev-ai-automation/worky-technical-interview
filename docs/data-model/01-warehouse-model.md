# Modelo de warehouse: esquema en estrella ejecutable (A4)

Este documento responde las cuatro preguntas de A4 sobre el modelo de warehouse: qué hechos y dimensiones hay, dónde viven las llaves que reconcilian `hubspot_id`, `account_id` y `vitally_id`, cómo se guarda el historial de cambios y cómo el trabajo manual de resolución de identidad de A0 nunca se repite. El comando `python -m worky_engine warehouse` (ADR-006) envuelve los marts y el crosswalk que ya construyeron A0, A1 y A3, sin modificarlos, y materializa ese envoltorio como un esquema en estrella de Kimball sobre DuckDB (ADR-001, ADR-002, ADR-003).

Está escrito para dos lectores distintos: un analista junior que necesita correr el comando y entender qué tabla leer para cada pregunta, y una dirección que quiere verificar que el historial de cambios es honesto sobre lo que el dataset del caso sí y no permite demostrar. La sección 3 es la que un lector escéptico debe revisar primero: ahí se dice sin rodeos que el historial de este dataset se captura hacia adelante, no hacia atrás.

## Cómo correrlo

```bash
python -m worky_engine warehouse --data-dir fundation-docs --out-dir outputs/warehouse
```

No necesita una corrida previa de `build`, igual que `analyze` y `health`. Genera su propia base `.build/warehouse.duckdb` y escribe dos archivos en `outputs/warehouse/`:

| Archivo | Contenido |
|---|---|
| `dim_company.csv` | 650 empresas vigentes, una fila por banda de SCD2 |
| `map_source_identity.csv` | Un vínculo por sistema origen, `cascade` u `override` |

Sobre el dataset del caso, cada hecho trae este número de filas: `fact_usage_monthly` 9,793, `fact_support_tickets` 1,888, `fact_deals` 962, `fact_revenue_monthly` 125 y `fact_marketing_touches` 1,635. `fact_health_score_monthly` guarda 650 filas por cada fecha de corrida distinta. Ninguno de los cinco hechos ni `fact_health_score_monthly` se versiona como golden: los cinco hechos son vistas que se recalculan desde marts que ya tienen su propio golden, y `fact_health_score_monthly` crece con cada fecha de corrida, así que su contenido no es estable por diseño.

El diagrama [`07-modelo-estrella-warehouse.html`](../diagrams/07-modelo-estrella-warehouse.html) muestra las llaves reales de cada tabla de esta sección, extendiendo el diagrama [`03-modelo-relacional-objetivo.html`](../diagrams/03-modelo-relacional-objetivo.html) en vez de repetirlo.

Banderas del comando, todas opcionales salvo `--data-dir`:

| Bandera | Por omisión | Qué hace |
|---|---|---|
| `--data-dir` | (obligatoria) | Ruta a las tres bases origen o al zip del caso |
| `--out-dir` | `outputs/warehouse` | Dónde escribir los dos goldens |
| `--db-path` | `.build/warehouse.duckdb` | Dónde persiste la base entre corridas |
| `--run-date` | `dataset_asof` del dataset | Fecha de corrida en formato ISO |
| `--overrides` | `data/identity_overrides.csv` | Ruta del archivo de decisiones humanas (sección 2) |

Códigos de salida, iguales a los de `build`, `analyze` y `health`: `0` si todo corrió bien; `1` si un contrato se violó, el archivo de overrides trae una fila inválida, o `--run-date` no es una fecha ISO o queda antes del `effective_from` vigente más reciente; `2` si falta un argumento o una de las tres bases origen.

Dos corridas de `warehouse` sobre el mismo dataset producen los dos goldens idénticos byte a byte, incluso en dos máquinas distintas. Ninguna llave depende del orden de ejecución (ver la sección 1), la fecha de corrida nunca sale del reloj (sale de `dataset_asof` o de `--run-date`), y cada vista ordena sus filas de forma explícita antes de escribirse. `git status --short outputs` confirma, en cada corrida, que ningún archivo fuera de `outputs/warehouse/` cambia.

## 1. Qué hechos y dimensiones tiene el warehouse

| Objeto | Tipo | Grano | Llave | Fuente |
|---|---|---|---|---|
| `dim_company` | Tabla | una banda de vigencia por empresa | `company_sk` | `mart_company_core` más el historial acumulado |
| `dim_date` | Vista | un día de calendario | `date_key` (`YYYYMMDD`) | `generate_series` de `MIN(signup_date)` a `dataset_asof` |
| `dim_csm` | Vista | un CSM | `csm_key` (hash del valor) | valores distintos de `csm_owner` |
| `dim_plan` | Vista | un plan | `plan_key` (hash del valor) | valores distintos de `plan` |
| `map_source_identity` | Vista | un vínculo de origen | `source_system`, `source_id` | `identity_crosswalk` desdoblado más `identity_overrides` |
| `identity_overrides` | Tabla | una decisión humana | `source_system`, `source_id` | `data/identity_overrides.csv` |
| `fact_usage_monthly` | Vista | (empresa, mes) | `company_sk`, `date_key` | `stg_product_usage` vía `account_id` |
| `fact_support_tickets` | Vista | un ticket | `ticket_id` | `stg_tickets` vía `vitally_id` |
| `fact_deals` | Vista | un deal | `deal_id` | `stg_deals` más `mart_deal_normalized` |
| `fact_revenue_monthly` | Vista | (empresa, mes) | `company_sk`, `date_key` | `fact_deals` en `closedwon`, agregado por mes de `close_date` |
| `fact_marketing_touches` | Vista | un touch | `touch_id` | `stg_marketing_touches` |
| `fact_health_score_monthly` | Tabla | (empresa, fecha de corrida) | `master_id`, `run_date` | `run_health(con)` de A3, sobre la misma conexión |

Solo tres objetos guardan algo que no se puede recalcular desde las fuentes: `dim_company`, `identity_overrides` y `fact_health_score_monthly`. Todo lo demás es una vista que se vuelve a crear en cada corrida, así que nunca queda una segunda copia de los datos desincronizada de los marts de A1.

Todas las llaves sustitutas se generan con `sha256` truncado a 12 caracteres hexadecimales sobre columnas de negocio (`company_sk = sha256(master_id, effective_from)`, `csm_key = sha256(csm_owner)`), nunca con un contador. Un contador dependería del orden en que DuckDB procesa las filas, y ese orden puede cambiar entre corridas o entre máquinas; el hash determinista da la misma llave a la misma empresa sin importar el orden de ejecución, y es la misma convención que ya usan `master_id` y `exception_id` en A0.

`dim_date` tiene grano de un día de calendario, no de un mes, aunque `fact_usage_monthly` y `fact_revenue_monthly` son mensuales. El grano diario es el que necesitan `fact_deals` y `fact_support_tickets`, que ocurren en cualquier día del mes; los dos hechos mensuales simplemente apuntan al último día de su mes al resolver `date_key`. El rango de fechas sale de los datos (`MIN(signup_date)` hasta `dataset_asof`), así que se mueve solo si el dataset cambia, en vez de quedar fijo a mano en el código.

`fact_revenue_monthly` merece una aclaración explícita: agrega `fact_deals` filtrado a `closedwon` por mes de `close_date`, no repite la columna `mrr_mxn` mes a mes. Ninguna fuente del caso trae MRR con fecha (ADR-002), así que una serie de `mrr_mxn` sería un dato inventado. Lo que esta tabla mide es ingreso de deals cerrados por mes, un concepto distinto de una suscripción recurrente que se factura todos los meses.

## 2. Dónde viven las llaves de reconciliación entre `hubspot_id`, `account_id` y `vitally_id`

La respuesta tiene dos partes, porque el caso pregunta por una tabla o un proceso como si fueran alternativas, y en este motor son las dos cosas a la vez.

**La tabla.** `identity_crosswalk` es la tabla persistente que guarda un `master_id` por empresa junto con sus tres identificadores de origen (ADR-001). Se reutiliza entre builds: el `master_id` de una empresa no cambia de una corrida a otra, así que cualquier tabla que lo use como llave foránea sigue siendo válida después de un rebuild. `match_audit` guarda, para cada registro de origen, el nivel de confianza, el puntaje y la evidencia exacta que produjo ese vínculo o la falta de uno.

**El proceso.** La cascada de A0 (niveles T0 a T3, más el nivel M de revisión manual) sigue siendo quien resuelve esos vínculos. Lo que agrega A4 es la tabla `identity_overrides`, que se aplica justo después de la cascada y antes de escribir el crosswalk y la auditoría. Un override es una decisión humana sobre un registro que cayó en revisión manual: fija la columna del crosswalk correspondiente (`account_id` o `vitally_id`), recalcula `confidence_tier`, agrega una fila con nivel `O` a `match_audit`, y saca ese registro de la cola de revisión sin borrar lo que el algoritmo había decidido antes. El archivo tiene seis columnas:

```csv
source_system,source_id,master_id,decided_by,decided_at,reason
product_db,ACC-2000,b5e018ec0013,ana.reyes,2024-08-15,confirmado manualmente por el CSM
```

Sin ese archivo, `resolve`, `build` y `warehouse` producen las mismas salidas que antes de este cambio, byte por byte. Una fila con un `master_id` inexistente, un `source_id` que no está en su tabla de origen, o un `source_id` repetido entre filas, detiene el comando con código de salida distinto de cero antes de escribir nada.

`map_source_identity` publica siete columnas: `source_system`, `source_id`, `master_id`, `confidence_tier`, `link_source` (`cascade` u `override`), `decided_by` y `matched_at`. Ahí es donde un vínculo hecho por una persona se distingue de uno hecho por el algoritmo: `link_source = 'override'` marca la fila y `decided_by` trae el nombre de quien lo decidió. Una consecuencia declarada: el reporte `mart_coverage_by_tier` de A0 solo cuenta los cinco niveles del algoritmo (`T0` a `T3` y `M`), así que las filas con override no aparecen ahí. Sí se ven en `map_source_identity` y en la baja de la cola de revisión manual.

**Contrato de la marca de agua incremental (documentado, no implementado).** La cascada hoy revisa los 1,978 registros de origen en cada build, aunque solo el `master_id` se reutiliza. El contrato exacto para procesar solo lo nuevo, si se implementa en un cambio posterior, es este:

- No hace falta una columna nueva: el conjunto de pares `(source_system, source_id)` ya vinculados es exactamente `map_source_identity`.
- Un registro cuenta como "ya visto" cuando su par `(source_system, source_id)` ya aparece en esa vista. Un registro es nuevo cuando su par no aparece ahí.
- La cascada de niveles T0 a T3 corre solo sobre los registros nuevos. Los vínculos existentes sobreviven sin reevaluarse, la misma garantía que ya da la reutilización del `master_id`.
- Una corrida reportaría cuántos registros omitió por sistema origen; ese conteo sería la evidencia de que el trabajo no se repitió.
- El dataset del caso no trae un campo de fecha de carga, así que la marca de agua es por identidad del par, no por tiempo.

No se implementó en este corte porque, con 1,978 registros, saltarse la reevaluación no cambia ningún número medible del dataset actual. Queda como trabajo futuro (ver la sección final).

## 3. Cómo se guarda el historial de cambios

`dim_company` aplica SCD tipo 2 sobre dos atributos: `plan` y `csm_owner`. Cada banda de vigencia tiene `company_sk` (llave sustituta), `effective_from` inclusivo, `effective_to` exclusivo (vacío en la fila vigente) e `is_current`. Los demás atributos de la empresa (nombre, industria, estado, fechas de alta y baja) se actualizan en la fila vigente sin abrir una banda nueva, porque el caso no nombra ninguna pregunta de negocio que necesite versionarlos.

El algoritmo corre en cuatro pasos fijos en cada corrida, parametrizados por la fecha de corrida (`--run-date`, por omisión `dataset_asof`):

| Paso | Qué hace |
|---|---|
| 1. Reemplazo del mismo día | Borra la fila vigente si ya se abrió justo en esta `run_date` pero sus atributos volvieron a cambiar, para que el paso 3 la reabra sin dejar una banda duplicada |
| 2. Cierre | Marca `is_current = false` y fija `effective_to = run_date` en la fila vigente cuyo `plan` o `csm_owner` ya no coincide con la foto actual |
| 3. Apertura | Inserta una fila nueva, con `company_sk` derivado de `master_id` y `run_date`, para cada empresa que se quedó sin fila vigente (nueva, recién cerrada, o recién borrada por el paso 1) |
| 4. Actualización tipo 1 | Sobrescribe en sitio los atributos no rastreados (nombre, industria, estado, fechas) de la fila vigente que sobrevivió, sin abrir banda |

Dos corridas seguidas sin cambios en las fuentes no agregan ninguna fila, y por eso los dos goldens salen idénticos byte a byte entre corridas repetidas. Una empresa que desaparece de las fuentes de un día a otro conserva su última fila vigente sin cerrarla: una extracción incompleta no es evidencia de que algo cambió en el negocio.

**Honestidad sobre el historial real.** El dataset del caso es una sola fotografía tomada el 2024-08-31. No existe ninguna banda cerrada real en este repositorio, porque nunca hubo una segunda extracción de los tres sistemas origen. La evidencia de que el algoritmo funciona son dos pruebas que simulan dos corridas seguidas con un cambio real de `plan` o de `csm_owner` de por medio (`tests/test_warehouse_scd2.py`), no un historial reconstruido a partir de datos que el caso nunca entregó. La captura es hacia adelante desde la primera vez que alguien corre `warehouse` más de una vez.

**Por qué la primera banda de cada empresa se abre hacia atrás.** La fecha de corrida por omisión es `dataset_asof`, el último día del dataset. Eso significa que la primera banda de cada empresa abre justo ese día. Una unión literal contra `effective_from` habría dejado fuera todo el uso, los tickets, los deals y los touches anteriores a esa fecha, que es la mayoría de la historia comercial del caso. Para evitarlo, la primera banda de cada empresa se trata como vigente hacia atrás, sin límite inferior: no existe ninguna versión anterior de esa empresa que el warehouse conozca y haya perdido, es simplemente la primera vez que se observó. Cualquier banda posterior, abierta por un cambio real de plan o de CSM, sí respeta su propia fecha de apertura.

**Uniones históricas contra la versión vigente en la fecha del hecho.** Es el resguardo del ADR-003 aplicado a la dimensión: cualquier hecho (uso, ticket, deal, touch) se une contra la banda de `dim_company` vigente en la fecha del propio hecho, nunca contra la fila actual. Un análisis de una cuenta que hizo churn debe poder preguntar qué CSM tenía asignado cuando se fue, no cuál CSM tiene hoy una cuenta que ya no existe en el sistema.

**Contratos que protegen el historial.** Ocho reglas corren después de cada corrida y detienen el comando si alguna falla, con el mismo mecanismo de `ContractViolation` que ya usa A0:

| Contrato | Qué protege |
|---|---|
| `assert_dim_company_one_current_per_master` | Exactamente una fila `is_current = true` por empresa |
| `assert_dim_company_sk_unique` | `company_sk` nunca se repite |
| `assert_dim_company_bands_are_contiguous` | El `effective_to` de una banda coincide con el `effective_from` de la siguiente, y solo la última queda abierta |
| `assert_dim_company_tracked_attributes_change` | Dos bandas seguidas de la misma empresa difieren en `plan` o en `csm_owner`, nunca en otro atributo |
| `assert_map_source_identity_unique` | El par `source_system` y `source_id` no se repite, y todo `master_id` existe en `dim_company` |
| `assert_overrides_are_reflected` | Cada fila de `identity_overrides` aparece en `map_source_identity` con `link_source = 'override'` |
| `assert_health_snapshot_unique` | El par `master_id` y `run_date` no se repite en `fact_health_score_monthly` |
| `assert_warehouse_row_order` | Los dos goldens salen con el orden de columnas y de filas ya declarado |

## 4. Cómo el trabajo manual de A0 nunca se repite

Cuatro piezas hacen que revisar un registro una vez sea revisarlo para siempre:

1. **Crosswalk persistente.** `identity_crosswalk.csv` se reutiliza entre builds; el motor no vuelve a resolver desde cero un vínculo que ya existía.
2. **`master_id` idempotente.** El mismo conjunto de identificadores de origen produce siempre el mismo `master_id`, sin importar cuántas veces se rebuild el dataset.
3. **`match_audit`.** Guarda la evidencia de cada decisión (nivel, puntaje, regla de bloqueo) para que nadie tenga que reconstruir por qué un registro cayó en tal nivel.
4. **`identity_overrides`.** La pieza que faltaba antes de A4: una decisión humana sobre un registro en revisión manual ahora sobrevive a un rebuild, en vez de volver a la cola cada vez.

**Qué recalcula un rebuild y qué no.** Un rebuild completo (`build`, `resolve` o `warehouse`) vuelve a correr la cascada de A0 sobre las tres bases origen, pero el `master_id` de cada empresa no cambia porque el crosswalk existente ya lo fija. Lo que sí se recalcula en cada corrida son las vistas del esquema en estrella (`dim_date`, `dim_csm`, `dim_plan`, `map_source_identity` y los cinco hechos), porque son ventanas sobre los marts y no guardan estado propio. Lo que no se recalcula, si hay un archivo de overrides presente, es la decisión humana ya tomada: se vuelve a aplicar, con el mismo efecto, en cada corrida.

**Formato del archivo de overrides y su modo de falla.** Seis columnas exactas (`source_system`, `source_id`, `master_id`, `decided_by`, `decided_at`, `reason`), leídas como texto plano, nunca como código. `source_system` solo acepta `product_db` o `vitally`, porque en `crm_hubspot` el `master_id` se genera, no se vincula. Cualquier fila inválida falla cerrada: el comando termina con código de salida distinto de cero, un mensaje en `stderr` que nombra el contrato y la fila, y ninguna escritura parcial en `outputs/`.

**Excepción documentada a la decisión D6 de A0.** `build`, `analyze` y `health` borran su archivo `.duckdb` en cada corrida (decisión D6 del diseño de A0), así que nunca acumulan estado entre ejecuciones. El `.duckdb` de `warehouse` es la única excepción: persiste bajo `.build/`, ignorado por Git, porque sin esa persistencia no habría manera de observar el historial de SCD2 en más de una corrida. Es una excepción declarada de forma explícita en el diseño de este cambio, no una contradicción silenciosa con el resto del motor. Borrar `.build/warehouse.duckdb` reinicia el modelo desde una primera corrida, y es también el efecto normal de correrlo por primera vez en otra máquina.

## Migración y reversión

Este cambio no mueve ningún dato existente. Todo lo que produce es código nuevo (cinco archivos SQL, un paquete de Python y un archivo dentro de `identity_resolution`) más lo que ese código genera dentro de `.build/` y `outputs/warehouse/`. Revertir los cuatro PR de este cambio deja los goldens de A0, A1 y A3 intactos y la suite completa en verde; el único paso manual es borrar `.build/warehouse.duckdb` y `outputs/warehouse/`. Borrar ese archivo `.duckdb` en cualquier momento reinicia el modelo desde una primera corrida, sin afectar ningún otro comando del motor.

## Trabajo futuro

- **Capa raw ligera al estilo Data Vault.** La investigación (`docs/research/01-bi-revops-data-architecture.md`, sección 2) la recomienda como preparación para cuando aparezca una cuarta fuente, no como entregable de este corte: con tres sistemas, el costo de los joins adicionales que trae Data Vault no se justifica todavía.
- **Implementar la marca de agua incremental.** El contrato ya está fijado en la sección 2 de este documento; falta la sentencia SQL o de Python que filtre por pares no vistos antes de correr la cascada.
- **Aplicar `identity_overrides` en `analyze` y `health`.** Hoy solo se aplica en `resolve`, `build` y `warehouse`. Sin archivo de overrides no hay ninguna diferencia observable, pero con un archivo presente, `analyze` y `health` seguirían leyendo la resolución sin la corrección humana hasta que se extienda esa capa.
- **Exponer `dim_csm` y `dim_plan` en un tablero (A5).** Si el tablero de A5 termina leyendo este esquema en estrella en vez de los marts de siempre, queda pendiente decidir si esas dos dimensiones se exponen como filtros para quien usa el tablero o si se quedan como soporte interno de `dim_company`, sin superficie propia.
- **Definir cuántas corridas reales hacen falta para un historial útil.** La prueba con dos corridas simuladas demuestra que el mecanismo de SCD2 funciona, pero no dice cuántas corridas reales de `warehouse` en producción hacen falta para que el historial de plan y CSM tenga cobertura suficiente para un análisis de retención serio.

## Documentos relacionados

`docs/decisions/ADR-006-warehouse-model.md` trae la decisión completa con sus alternativas rechazadas y su lista de verificación para el revisor. `docs/data-model/00-as-is-schema-profile.md` describe los tres sistemas origen antes de cualquier cruce. `openspec/changes/a4-warehouse-model/design.md` trae el detalle técnico completo: las veintiuna decisiones numeradas, el SQL exacto de cada vista y el corte en cuatro PR encadenados que produjo este cambio.
