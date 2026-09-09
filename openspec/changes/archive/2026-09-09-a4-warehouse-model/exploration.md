# Exploración: a4-warehouse-model (modelo de warehouse para RevOps)

## Texto literal de la sección A4 del caso

"A4. Modelado de datos. Diseña (diagrama o descripción textual) el modelo de warehouse que serviría de base para lo anterior, ahora que sabes que la información entra desde 3 sistemas distintos y desincronizados. Indica: qué tablas de hechos y dimensiones propones, dónde vivirían las llaves de reconciliación entre hubspot_id/account_id/vitally_id (¿una tabla de mapeo persistente? ¿un proceso que la recalcule?), cómo manejarías el historial de cambios (ej. una cuenta que cambia de CSM o de plan), y cómo evitarías que el trabajo manual de reconciliación de A0 se tenga que repetir cada vez que llega un dato nuevo."

## Contexto

A0 (motor del dataset maestro), A1 (SQL) y A3 (health score) ya están archivados como código real, probado y corriendo. El ADR-001 ya prometió, en su tabla "qué cambia en las secciones siguientes": "A4 recibe un crosswalk persistente y las tablas de auditoría como parte de su modelo, que es justo lo que evita que el equipo repita el trabajo de cruce manual cada vez que el warehouse se reconstruye". Esa promesa ya es cierta hoy en el código: `identity_crosswalk.csv` y `match_audit.csv` existen y se reutilizan entre corridas. El trabajo de A4 no es inventar el mapeo desde cero: es formalizarlo como modelo de warehouse, nombrar sus huecos reales y decidir qué tanto de eso se vuelve código ejecutable.

## Estado actual

### Lo que ya existe y A4 puede reusar directo

- `identity_crosswalk.csv`: una fila por empresa real, con `master_id`, `hubspot_id`, `account_id`, `vitally_id`, `confidence_tier`, `resolved_at`, `ruleset_version`. Ya es, en los hechos, la tabla de mapeo persistente que pide la pregunta A4, y `map_source_identity(source_system, source_id, company_key, confidence_tier, matched_at)` de `docs/research/01-bi-revops-data-architecture.md` es casi una renombrada de lo mismo.
- `match_audit.csv`: una fila por registro de origen procesado (companies, accounts, customers), con nivel, puntaje, evidencia y `needs_review`. Es la bitácora de auditoría del cruce.
- `worky_engine/cli.py` (`cmd_build`, función `_load_existing_crosswalk`) ya reutiliza el `identity_crosswalk.csv` de la corrida anterior: `keys.resolve_master_id` busca el `master_id` existente por `hubspot_id` antes de generar uno nuevo por hash. Esto es lo que hace que el proceso sea idempotente entre corridas, tal como describe el ADR-001.
- Capas ya separadas en `worky_engine/sql/staging/` (una vista `stg_*` por tabla origen) y `worky_engine/sql/marts/` (`mart_company_core`, `mart_mrr`, `mart_usage`, `mart_support`, `mart_commercial`, `mart_deal_normalized`, `mart_coverage`, `mart_master_dataset`). Esto ya ES, sin nombrarlo así, la mitad de un esquema de Kimball: staging normalizado más marts de presentación.
- `quarantine_companies.csv` y `quarantine_deals.csv` ya cumplen el papel de tablas de excepción para lo que nunca debe entrar al modelo dimensional.
- El diagrama `docs/diagrams/03-modelo-relacional-objetivo.html` ya dibuja `master_dataset` al centro con `identity_crosswalk`, `match_audit` y las cuarentenas alrededor. A4 no repite ese diagrama: lo extiende hacia un esquema en estrella.

### Lo que existe pero tiene un hueco real

- **Sin historial en ningún lado.** Revisé `docs/data-model/00-as-is-schema-profile.md` y `worky_engine/sql/staging/stg_companies.sql`: `companies` trae `csm_owner`, `plan`, `segment`, `state` como columnas de valor único, sin fecha de vigencia ni tabla de bitácora de cambios. Los tres sistemas de origen son extracciones del estado actual, no un log de eventos. Y en el propio motor, la decisión D6 del diseño de A0 dice explícito: el archivo `.duckdb` "se regenera en `.build/` y se ignora en Git" en cada build, así que tampoco hay una foto guardada de corrida a corrida. Conclusión dura: no existe ningún historial de plan o CSM en ninguna parte del sistema hoy, ni para reconstruir hacia atrás ni para comparar entre corridas pasadas. Solo se puede empezar a capturar historial hacia adelante, desde la primera vez que alguien corra el warehouse de A4 más de una vez.
- **El cruce se recalcula completo cada build, no de forma incremental.** `worky_engine/identity_resolution/cascade.py` (`resolve_identity`) vuelve a evaluar los 650+650+678 registros de origen en cada corrida; solo el `master_id` se reutiliza vía el crosswalk existente (`existing_lookup`), pero el resto de la cascada (T0 a T3, veto, bloque de fecha) se repite completo. Con 1,978 registros esto es barato, pero no es lo que describe la pregunta A4 ("solo llega un dato nuevo"): hoy no hay una marca de agua que distinga "registros ya vistos" de "registros nuevos".
- **Las decisiones de revisión manual no se guardan en ningún lado para reutilizarse.** Un registro en nivel M (`needs_review = true`, `master_id = None`) no tiene ninguna tabla donde una persona pueda escribir "este `account_id` en realidad es la empresa `master_id = X`". Revisé `worky_engine/sql/marts/mart_coverage.sql`, `mart_mrr.sql` y todo `cascade.py`: la palabra `override` no aparece en ningún archivo del motor. Como el algoritmo es determinista, correr `build` otra vez sobre los mismos datos vuelve a mandar exactamente ese mismo registro a revisión manual. Hoy no hay manera de que una decisión humana sobreviva a un rebuild.
- **MRR y health score tampoco tienen grano temporal real.** `mart_mrr.sql` calcula un solo valor "actual" de MRR por empresa (del CRM o imputado), no una serie mensual: no existe ninguna fuente con MRR fechado mes a mes. Lo mismo con el health score: el comando `health` (`openspec/specs/health-score/spec.md`) calcula un puntaje en el momento de la corrida, sin guardarlo con fecha para comparar corridas futuras.

### Lo que no existe todavía

- Ningún esquema en estrella nombrado como tal (dimensiones y hechos con esos nombres).
- `dim_date`, `dim_csm`, `dim_plan`: hoy `csm_owner` y `plan` son columnas de texto planas en `mart_company_core`.
- Cualquier mecanismo de SCD tipo 2.
- Cualquier tabla de `overrides` para decisiones de revisión manual.
- Cualquier marca de agua (`watermark`) para procesar solo registros nuevos.

## Áreas afectadas

- `docs/data-model/00-as-is-schema-profile.md` — esquema origen real: columnas, tipos, llaves implícitas, sin ninguna de historial.
- `docs/decisions/ADR-001-identity-resolution-scorecard.md` — la promesa de crosswalk persistente que A4 debe cumplir.
- `docs/research/01-bi-revops-data-architecture.md`, sección 2 — el esquema en estrella recomendado (Kimball, SCD2, `map_source_identity`, incremental con marca de agua).
- `worky_engine/identity_resolution/cascade.py`, `keys.py` — cómo se mintan y reutilizan hoy los `master_id`; base real para el diseño de "solo nuevos ids".
- `worky_engine/master_dataset/assemble.py`, `worky_engine/cli.py` — capas staging/marts existentes y el patrón de comando (`build`, `analyze`, `health`) que un comando `warehouse` nuevo replicaría.
- `worky_engine/sql/marts/*.sql` — fuente real de cada dimensión y hecho propuesto; ningún archivo existente se modifica, A4 solo los lee y los envuelve.
- `openspec/specs/identity-resolution/spec.md`, `master-dataset-assembly/spec.md` — contrato actual de crosswalk, match_audit y columnas del dataset maestro que A4 hereda tal cual.
- `docs/diagrams/03-modelo-relacional-objetivo.html` y `docs/diagrams/README.md` — el diagrama que A4 extiende, con la skill `archify` (tipo `erd` o `dataflow`) disponible para el nuevo diagrama.
- Ningún archivo de `outputs/` ni ningún golden de A0/A1/A3 se toca.

## Pregunta 1: forma del entregable

| Opción | Qué incluye | A favor | En contra | Líneas autoría estimadas | Presupuesto (800/cambio) |
|---|---|---|---|---|---|
| a. Solo documento + ERD | `design.md` con el esquema en estrella, tabla de dimensiones/hechos, mecanismo de SCD2 y de reconciliación descritos en prosa, más un diagrama `erd` con `archify` | Es exactamente lo que pide el texto del caso ("diagrama o descripción textual"); cero riesgo de presupuesto; dejaría más tiempo para A5, A6 y la Parte B | Rompe el patrón de A0/A1/A3 (los tres se entregaron como código corriendo); nada demuestra que el mecanismo de SCD2 o el de "solo ids nuevos" funciona de verdad | ~0 | Sin riesgo |
| b. Documento + ERD + DDL ejecutable (recomendada) | Lo de (a), más un comando nuevo `python -m worky_engine warehouse` que materializa las vistas/tablas del esquema en estrella sobre DuckDB a partir de los marts y el crosswalk ya existentes, con una tabla persistida para el historial SCD2 de `dim_company` y otra para `overrides` de revisión manual, probado con pytest simulando dos corridas seguidas con un cambio de plan o de CSM | Sigue el mismo patrón que A0/A1/A3 (código real, probado); demuestra con una prueba que el SCD2 y los overrides funcionan, aunque el dataset real no tenga historial que mostrar; reusa marts existentes, casi no duplica lógica | Agrega alcance nuevo no pedido literal por el caso; hay que ser disciplinado para no rebasar el presupuesto | ~400 a 650 (DDL + comando + pruebas; sin duplicar los marts existentes) | Dentro de 800, similar de tamaño a A0 completo |
| c. (b) más una capa raw estilo Data Vault ligero | Hubs de empresa/contacto y satélites por fuente debajo del mart de Kimball, como preparación explícita para una cuarta fuente futura | Punto extra de "innovador" que menciona la investigación (`docs/research/01...md`, sección 2, recomendación 5) | El propio research dice "presentarla como preparación para el crecimiento... sin convertirla en el entregable principal"; agrega joins y código que nadie más de A1/A3/A5 va a consumir; sube el riesgo de rebasar el presupuesto de la PR y de comerse tiempo de A5/A6/Parte B | ~600 a 900 adicionales | Riesgo medio-alto de exceder 800 o necesitar una segunda PR encadenada |

Recomiendo (b), con la capa Data Vault de (c) mencionada solo como "trabajo futuro" dentro del propio `design.md`, tal como ya sugiere la investigación, sin escribir el código.

## Pregunta 2: tablas de hechos y dimensiones

| Tabla | Grano | Llave | Fuente real | Estado hoy |
|---|---|---|---|---|
| `dim_company` | una fila vigente por `master_id`, más una fila cerrada por cada cambio de plan o CSM (SCD2) | `company_sk` (nueva, surrogate), `master_id` (llave de negocio) | `identity_crosswalk` + `mart_company_core` (segment, industry, plan, state, csm_owner, signup_date, churn_date) | Existe sin SCD2; hoy es una sola fila "actual" por empresa |
| `dim_date` | un día del calendario | `date_key` | generada, cubriendo desde el `signup_date` mínimo hasta `dataset_asof` (2024-08-31) | No existe |
| `dim_csm` | un CSM | `csm_key` | valores distintos de `companies.csm_owner` / `customers.csm_email` (las mismas 7 personas, según el ADR-001) | No existe como tabla; hoy es texto plano en la fila de empresa |
| `dim_plan` | un plan | `plan_key` | valores distintos de `companies.plan` (relación 1:1 con `segment` según el perfil de esquema) | No existe como tabla |
| `map_source_identity` (= `identity_crosswalk` + `match_audit`, formalizados) | una fila por vínculo de origen a `master_id` | `source_system`, `source_id` | ya existe, sin ese nombre | Existe, solo falta encuadrarlo como artefacto de dimensión de primera clase |
| `fact_usage_monthly` | (empresa, mes) | `company_sk`, `date_key` | `stg_product_usage` (9,793 filas, 24 meses reales) | Grano correcto ya existe en staging; falta envolverlo como hecho con FK a las dimensiones |
| `fact_support_tickets` | un ticket | `ticket_id` | `stg_tickets` (1,888 filas) | Existe como agregado (`mart_support`); falta el hecho a grano ticket |
| `fact_deals` | un deal | `deal_id` | `stg_deals` / `mart_deal_normalized` (997 reales + 35 huérfanos en cuarentena) | Existe a nivel agregado (`mart_commercial`); falta el hecho a grano deal |
| `fact_revenue_monthly` | (empresa, mes) | `company_sk`, `date_key` | agregación de `fact_deals` por `close_date`, no una repetición del MRR actual | No existe. Importante: no hay ninguna fuente con MRR fechado mes a mes; `mrr_mxn` es un valor único "actual" por empresa. Un hecho mensual honesto solo puede construirse agregando deals por fecha, no fingiendo una serie de MRR que los datos no tienen |
| `fact_marketing_touches` | un touch | `touch_id` | `stg_marketing_touches` (1,635 filas) | Existe como agregado (primer touch en `mart_commercial`); falta el hecho a grano touch |
| `fact_health_score_monthly` | (empresa, fecha de corrida) | `company_sk`, `run_date` | salida del comando `health` (A3), con fecha de corrida agregada | No existe. El health score de hoy es un punto en el tiempo, sin historial entre corridas |

## Pregunta 3: dónde viven las llaves de reconciliación

Ya viven en una tabla de mapeo persistente, no en un proceso que la recalcule desde cero: `identity_crosswalk.csv`, reutilizada build tras build vía `_load_existing_crosswalk` y `keys.resolve_master_id`. Eso ya resuelve la pregunta literal del caso ("¿una tabla de mapeo persistente?") con evidencia real, no con una propuesta.

Lo que falta, y que A4 debe agregar al modelo:

1. **Una marca de agua real por sistema origen**, para procesar solo registros con `source_id` no visto antes contra el crosswalk existente, en vez de volver a correr T0-T3 sobre los 1,978 registros cada vez. Con el volumen de este caso no cambia ningún número, pero es la respuesta correcta a "cómo evitarías repetir el trabajo cuando llega un dato nuevo", y hoy no existe.
2. **Una tabla de `identity_overrides`** (`source_system`, `source_id`, `master_id`, `decided_by`, `decided_at`, `reason`) que el proceso de resolución consulte antes de correr la cascada. Hoy, un registro en revisión manual (nivel M) no tiene ningún lugar donde una persona escriba su decisión; sin esta tabla, cada rebuild vuelve a mandarlo a la cola manual, sin importar que alguien ya lo haya revisado ayer. Esto conecta con la pregunta 5.

## Pregunta 4: historial de cambios

No hay ningún historial que reconstruir hacia atrás: los tres sistemas origen son fotografías del estado actual (confirmado en `docs/data-model/00-as-is-schema-profile.md` y en `stg_companies.sql`, columna por columna), y el propio motor borra su `.duckdb` en cada build (decisión D6 del diseño de A0). Esto significa que el SCD2 de `dim_company` para `plan` y `csm_owner` solo puede capturarse **hacia adelante**, a partir de la primera vez que alguien corra el warehouse de A4 más de una vez, comparando la fila nueva contra la última fila vigente y cerrando/abriendo según corresponda (`effective_from`, `effective_to`, `is_current`). Con el dataset del caso, que es una sola foto, no va a haber ninguna fila histórica real que mostrar el día de la defensa; lo defendible es una prueba unitaria que simula dos corridas seguidas con un cambio de plan o de CSM y verifica que el mecanismo cierra la fila vieja y abre la nueva correctamente. Esto se dice de forma explícita y honesta en el modelo, en vez de sugerir que existe historial donde no lo hay.

Sobre el resguardo contra fuga de datos (ADR-003): cualquier hecho histórico (uso, soporte, deals) debe unirse contra la versión de `dim_company` que era vigente en la fecha del hecho, no contra la fila actual. Esto es la razón real de tener SCD2 y no solo una columna de texto: sin él, un análisis de churn preguntaría "qué CSM tenía la cuenta hoy" en vez de "qué CSM tenía la cuenta cuando se fue".

## Pregunta 5: nunca repetir el trabajo manual de A0

Cuatro piezas, tres ya existen y una falta:

1. Crosswalk persistente y reutilizado entre builds (ya existe).
2. `master_id` idempotente, por hash o por reutilización del existente (ya existe, `keys.py`).
3. Bitácora de auditoría completa por decisión (`match_audit`, ya existe).
4. **Tabla de `identity_overrides` para decisiones humanas** (no existe, ver pregunta 3). Sin ella, las tres piezas anteriores garantizan que el algoritmo nunca cambia de opinión solo, pero no garantizan que una corrección humana sobreviva a un rebuild. Esta es la pieza que de verdad responde "cómo evitarías repetir el trabajo manual", porque hoy ese trabajo se puede perder.

## Pregunta 6: relación con las capas ya existentes

`worky_engine/sql/staging/` y `worky_engine/sql/marts/` ya son, en los hechos, una capa de staging más una capa de presentación intermedia, aunque sin ese nombre. A4 no debe reemplazar los marts existentes: debe envolverlos. Los hechos y dimensiones nuevos son vistas SQL que leen `mart_company_core`, `mart_usage`, `mart_deal_normalized`, `mart_support` y `stg_marketing_touches` tal como están, más las dos tablas nuevas (historial SCD2 y overrides) que si necesitan persistencia real entre corridas. A1 y A3 no deberían tener que cambiar ni una línea: siguen leyendo los mismos marts de siempre. A5, cuando llegue, puede elegir leer directo del esquema en estrella nuevo o seguir leyendo los marts; ambos caminos quedan abiertos.

## Pregunta 7: riesgos

- **Sobreingeniería del alcance.** El caso pide "diagrama o descripción textual"; construir DDL ejecutable es una decisión de producto, no un mandato del caso. Ver la pregunta 1 y la sección de decisiones pendientes.
- **Historial que no se puede demostrar con datos reales.** Cualquier fila de SCD2 mostrada el día de la defensa sale de una prueba sintética, no del dataset del caso. Hay que decirlo así, sin dar a entender que existe historial real.
- **`fact_revenue_monthly` puede confundirse con una serie de MRR.** Debe quedar claro en el nombre y en la documentación que es MRR de deals cerrados por mes, no una serie temporal de `mrr_mxn` (que no existe).
- **UTF-8 en Windows**, mismo riesgo ya conocido de A0: nombres de CSM y de empresa con acentos: cualquier archivo nuevo necesita `encoding="utf-8"` explícito.
- **Determinismo de las llaves surrogate** (`company_sk`, `date_key`, etc.): deben generarse de forma determinista (hash o secuencia estable), nunca con un contador dependiente del orden de ejecución, para no romper la idempotencia byte a byte que ya exige `build-cli`.
- **Pruebas de DDL sobre DuckDB con pytest**: mismo patrón ya usado en `tests/test_build_idempotency.py` y `tests/test_health_idempotency.py`; no hace falta un framework nuevo.
- **Presupuesto de PR (400 líneas) dentro del presupuesto de cambio (800 líneas)**: con la opción (b) acotada, el DDL más el comando más las pruebas caben en una sola PR o en dos encadenadas cortas, sin necesidad de una tercera.

## Recomendación

Opción (b): documento de diseño más ERD (skill `archify`, tipo `erd` o `dataflow` según qué tan bien se lea el flujo staging→estrella) más un comando `warehouse` que materialice el esquema en estrella sobre DuckDB, reusando los marts existentes sin tocarlos, con dos tablas nuevas persistidas (`dim_company` con SCD2 y `identity_overrides`), probado con pytest incluyendo una prueba que simule dos corridas para demostrar el SCD2. La capa Data Vault ligera de la opción (c) se documenta como trabajo futuro, sin código. Esto mantiene la continuidad con A0/A1/A3 (código real y probado) sin comerse el presupuesto de líneas ni el tiempo que todavía necesitan A5, A6 y la Parte B.

## Decisiones de producto pendientes

1. **Forma del entregable (pregunta 1).** Opciones (a) solo documento, (b) documento + DDL ejecutable acotado (recomendada), (c) (b) más Data Vault ligero ejecutado. Consecuencia principal: (a) es más rápido y sin riesgo de presupuesto pero rompe el patrón de código real de A0/A1/A3; (c) agrega riesgo de tiempo y de presupuesto por algo que el propio research recomienda no ejecutar. Recomiendo (b).
2. **Si se ejecuta código, ¿el `.duckdb` de `warehouse` se persiste entre corridas (a diferencia de `build`, que lo borra por decisión D6 de A0)?** Es indispensable para demostrar SCD2 con más de una corrida. Consecuencia: agrega un archivo binario versionado o ignorado en `.build/` que hay que documentar aparte de la decisión D6 existente, para no contradecirla en silencio. Recomiendo persistirlo solo para el comando `warehouse`, dejando `build`/`analyze`/`health` como están.
3. **¿Se agrega la tabla `identity_overrides` como parte de A4, o se documenta como hueco para una futura revisión de A0?** Responde de forma directa a "cómo evitar repetir el trabajo manual" (pregunta 5), pero toca el módulo `identity_resolution` que A0 ya cerró y archivó. Recomiendo agregarla en A4, documentando que es una extensión aditiva sobre el módulo de A0, sin modificar ningún archivo existente de esa carpeta.
4. **¿Se construye la marca de agua incremental real (pregunta 3, punto 1), o se documenta el diseño sin implementarla?** Con 650 empresas no cambia ningún resultado medible hoy; implementarla es una demostración de rigor de ingeniería más que una necesidad del dataset. Recomiendo documentarla en el diseño con su contrato exacto, e implementarla solo si el presupuesto de líneas lo permite después de cubrir dim_company/SCD2/overrides.
5. **¿`fact_health_score_monthly` entra en el alcance de A4, dado que hoy A3 no guarda historial entre corridas del health score?** Es una extensión natural del mismo patrón de captura hacia adelante que `dim_company`. Recomiendo incluirla si se elige la opción (b), reusando la misma tabla de snapshots por fecha de corrida.

## Listo para propuesta

Sí, una vez que el usuario confirme las cinco decisiones de producto de arriba. Ninguna cambia la estructura de dimensiones y hechos de la pregunta 2, que ya está fundamentada en columnas reales; solo deciden cuánto de eso se vuelve código ejecutable y cuánto queda en el documento de diseño.

## Referencias

`docs/decisions/ADR-001` (crosswalk persistente, idempotencia), `ADR-002` (MRR sin serie temporal), `ADR-003` (resguardo contra fuga de datos, aplica a las uniones históricas), `docs/data-model/00-as-is-schema-profile.md`, `docs/research/01-bi-revops-data-architecture.md` sección 2, `docs/diagrams/03-modelo-relacional-objetivo.html`, `openspec/specs/identity-resolution/spec.md`, `openspec/specs/master-dataset-assembly/spec.md`, `openspec/specs/health-score/spec.md`, `worky_engine/identity_resolution/cascade.py`, `keys.py`, `worky_engine/master_dataset/assemble.py`, `worky_engine/cli.py`, `worky_engine/sql/marts/*.sql`, `worky_engine/sql/staging/stg_companies.sql`, exploraciones archivadas de a0 y a3 (mismo formato y tono).
