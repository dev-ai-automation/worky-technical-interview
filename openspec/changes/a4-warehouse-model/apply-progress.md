# Apply progress: `a4-warehouse-model`

## PR1: precedencia de `identity_overrides` en `resolve` y `build`

**Batch**: PR1, tareas 1.1 a 1.5 (precedencia de `identity_overrides` en `resolve` y `build`)
**Modo**: Standard (strict_tdd: false)
**Rama**: `feat/a4-pr1-identity-overrides`, base `main`

**Corrección post-revisión (native review, un ciclo acotado):** la revisión nativa de PR1 exigió una corrección acotada, aplicada en el commit `fcf56d6`. R3-001: un override que re-apunta un `source_id` ya vinculado por la cascada (o por un override anterior del mismo archivo) ahora limpia al titular anterior en el crosswalk (`account_id`/`account_match_tier` o `vitally_id`/`vitally_match_tier` y `confidence_tier` recalculado), evitando que dos filas del crosswalk carguen el mismo `source_id`. R3-002: un archivo de overrides vacío o con una fila mal formada (columnas de más, coma sin comillas) ahora se rechaza con `OverrideError` en vez de dejar pasar la traza cruda de `pandas.errors`. El commit agregó +99 líneas (dos pruebas nuevas: `test_override_que_repunta_source_id_ya_vinculado_limpia_el_master_anterior`, `test_archivo_vacio_se_rechaza_con_override_error`, `test_fila_mal_formada_se_rechaza_con_override_error`) y dejó la suite completa en 226 pruebas pasando (223 + 3). El PR1 completo, corrección incluida, ya está commiteado en la rama base de este PR2 (`feat/a4-pr1-identity-overrides`); ver `git log` para el detalle de commits (`54e6663`, `fcf56d6`, `22343e6`, `9835533`).

## Completed Tasks

- [x] 1.1 `worky_engine/identity_resolution/overrides.py`: `load_overrides(path)` con las validaciones de forma del archivo (columnas exactas, `source_system`, campos obligatorios, fecha ISO, `source_id` no repetido).
- [x] 1.2 `apply_overrides(...)` en el mismo archivo: valida referencias cruzadas (master_id en el crosswalk, source_id en su tabla de origen) para todas las filas antes de tocar cualquier salida; fija la columna del crosswalk con nivel `O`, recalcula `confidence_tier`, agrega la fila `O` a `match_audit` y marca `needs_review = false` con `superseded_by` en la fila sustituida.
- [x] 1.3 `worky_engine/cli.py`: `--overrides` en `resolve` y `build` (por omisión `data/identity_overrides.csv`), `_import_resolve_dependency`/`_import_build_dependencies` extendidos, y `_apply_overrides_if_present` nuevo, llamado justo después de la cascada y antes de escribir en ambos comandos.
- [x] 1.4 `tests/test_identity_overrides.py`: fixture mínimo propio (dos empresas, una cuenta sin vínculo claro que cae en M), diez pruebas cubriendo los cinco escenarios del requisito más la forma del archivo (columnas, `source_system`, campo vacío, fecha no ISO).
- [x] 1.5 Cierre de PR1: pruebas focalizadas, suite completa (`not dataset` y completa con dataset real), `build` sin overrides confirmado byte idéntico, commit convencional preparado (ver abajo).

## Files Changed

| File | Action | What Was Done |
|------|--------|----------------|
| `worky_engine/identity_resolution/overrides.py` | Created | `load_overrides` y `apply_overrides`, D14 a D17 |
| `tests/test_identity_overrides.py` | Created | Diez pruebas, fixture mínimo propio |
| `worky_engine/cli.py` | Modified | `--overrides` en `resolve`/`build`, `_apply_overrides_if_present`, imports diferidos extendidos |

Ningún archivo bajo `worky_engine/identity_resolution/` existente (`cascade.py`, `keys.py`, `blocking.py`, `scoring.py`, `veto.py`, `quarantine.py`, `__init__.py`), `worky_engine/sql/`, `worky_engine/quality/contracts.py` ni `outputs/` se tocó.

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and result | `python -m pytest -q -m "not dataset" tests/test_identity_overrides.py` → 10 passed |
| Runtime harness command/scenario and result | `python -m worky_engine build --data-dir data/raw/sistemas --out-dir outputs` (sin overrides) → `git status --short outputs` vacío (byte idéntico); `resolve` con un CSV de overrides válido en un `--out-dir` temporal muestra la fila `O` en `match_audit.csv` con `decided_by` del archivo; `resolve` con un `master_id` inexistente termina con código 1 y el `--out-dir` sin archivos |
| Rollback boundary | Eliminar `worky_engine/identity_resolution/overrides.py` y `tests/test_identity_overrides.py`, y revertir en `worky_engine/cli.py`: `DEFAULT_OVERRIDES_PATH`, la extensión de `_import_resolve_dependency`/`_import_build_dependencies`, `_apply_overrides_if_present`, las dos llamadas en `cmd_resolve`/`cmd_build`, los dos `--overrides` de los subparsers y la línea añadida al docstring del módulo |

## Verification (foreground, exact results)

1. `python -m pytest -q -m "not dataset" tests/test_identity_overrides.py` → `10 passed in 1.13s`
2. `python -m pytest -q` (suite completa, incluye pruebas `dataset`) → `223 passed in 126.41s` (línea base de A3 era 213; se agregaron 10 pruebas nuevas, todas en verde)
3. `python -m worky_engine build --data-dir data/raw/sistemas --out-dir outputs` → `build: 650 empresas ensambladas en outputs`, exit 0. `git status --short outputs` → vacío (sin cambios). `git status --short` → solo `M worky_engine/cli.py`, `?? tests/test_identity_overrides.py`, `?? worky_engine/identity_resolution/overrides.py`
4. `python -m worky_engine resolve --help` → muestra `--overrides OVERRIDES` con su ayuda. `resolve` con un CSV de overrides válido (`product_db,ACC-2000,b5e018ec0013,ana.reyes,2024-08-15,confirmado manualmente por el CSM`) sobre el dataset real, `--out-dir` en el scratchpad → exit 0, `match_audit.csv` trae la fila `O` con `decided_by=ana.reyes`, `blocking_rule=override`, junto a la fila `T2` original con `needs_review=False`. `resolve` con una fila inválida (`master_id` inexistente) → `resolve: identity_overrides: fila 1 referencia master_id 'no-existe-master-id' que no existe en identity_crosswalk`, exit 1, `--out-dir` queda vacío (sin escritura parcial)
5. Conteo de líneas de autoría: `git diff --numstat -- worky_engine/cli.py` → `67  8` (75 líneas). `wc -l` de los archivos nuevos: `overrides.py` 234, `test_identity_overrides.py` 220. **Total autoría: 529 líneas** (estimado del diseño: ~255; medido: 529, dentro del presupuesto de 800 líneas por PR de `openspec/config.yaml`, sin necesidad de `size:exception`)

## Deviations from Design

Ninguna decisión de diseño se cambió. Dos ajustes de implementación no cubiertos explícitamente por D14 a D17, documentados aquí por transparencia:

- La deduplicación de `source_id` en `load_overrides` se implementó sobre el par `(source_system, source_id)`, siguiendo la tabla de validación de la sección 4 del diseño ("El mismo par `source_system` y `source_id` aparece en dos filas del archivo"), no sobre `source_id` en solitario. La redacción del requisito de la spec y de la tarea 1.4 dice "source_id duplicado entre filas" sin nombrar el par explícitamente; se siguió el diseño por ser la fuente más precisa, y el escenario de prueba (dos filas con el mismo `source_system` y el mismo `source_id`) es indistinguible entre ambas lecturas, así que no hay conflicto observable.
- `_apply_overrides_if_present` (privada, en `cli.py`) encapsula "sin archivo, no tocar nada" y "fila inválida, código 1 y mensaje" para no duplicar ese bloque en `cmd_resolve` y `cmd_build`; no está nombrada en las tareas pero implementa literalmente lo que piden 1.3 y el requisito de la spec.

## Issues Found

Ninguno. La suite completa (223 pruebas) corrió en verde sin fallas ambientales.

### PR1 Workload / PR Boundary

- Mode: stacked PR slice (`auto-chain`, `stacked-to-main`)
- Current work unit: Unit 1 — precedencia de `identity_overrides` sobre la cascada en `resolve` y `build`
- Boundary: arranca en `main` (sin `worky_engine/identity_resolution/overrides.py` ni `--overrides` en el CLI) y termina con las tareas 1.1 a 1.5 completas, PR1 listo para abrir contra `main`
- Estimated review budget impact: 529 líneas de autoría, dentro del presupuesto de 800 por PR; el revisor ve primero que sin archivo de overrides las salidas de A0 quedan idénticas y que una fila inválida detiene la corrida antes de escribir

### PR1 Prepared Conventional Commit Message

```
feat(identity): apply identity_overrides after the cascade in resolve and build

Add worky_engine/identity_resolution/overrides.py with load_overrides
and apply_overrides: validates the six-column CSV, that master_id
exists in the crosswalk and source_id exists in its origin table,
before touching any output. A valid row sets the crosswalk link with
tier O, recomputes confidence_tier, adds an O row to match_audit, and
marks the superseded row out of manual review. An invalid row stops
the command with exit code 1 and no partial write.

Wire --overrides into resolve and build (default
data/identity_overrides.csv, applied only when present, right after
the cascade and before writing). Without the file, outputs stay
byte-identical to before this change.
```

## PR2: vistas del esquema en estrella, `cmd_warehouse` y golden de `map_source_identity`

**Batch**: PR2, tareas 2.1 a 2.12
**Modo**: Standard (strict_tdd: false)
**Rama**: `feat/a4-pr2-warehouse-star`, base `feat/a4-pr1-identity-overrides`

**Corrección post-revisión (native review, un ciclo acotado):** la revisión nativa de PR2 exigió una corrección acotada, aplicada en el commit `73b44b9`: la prueba de "marts y staging sin cambios" (`test_marts_y_staging_sin_cambios`) ahora corre `warehouse` entre sus dos instantáneas de hash, en vez de solo tomar el hash antes y después sin ejecutar nada real en medio, para que la comparación pueda fallar de verdad si algún archivo de `sql/staging/` o `sql/marts/` cambiara. PR2 cerró bajo `size:exception`, con 967 líneas de autoría medidas contra el presupuesto de 800 (ver Verification #6 y la sección "PR2 Workload / PR Boundary" más abajo para el detalle ya registrado de esa decisión).

### PR2 Completed Tasks

- [x] 2.1 `worky_engine/sql/warehouse/w1_dim_date.sql`: vista `dim_date`, `generate_series` de `MIN(signup_date)` a `dataset_asof`, `date_key` entero `YYYYMMDD`.
- [x] 2.2 `worky_engine/sql/warehouse/w2_dim_csm_plan.sql`: `dim_csm` y `dim_plan`, valores distintos de `mart_company_core`.
- [x] 2.3 `worky_engine/sql/warehouse/w3_map_source_identity.sql`: `identity_crosswalk` desdoblado (una fila por sistema vinculado) más `identity_overrides`, `link_source` `cascade`/`override`.
- [x] 2.4 `worky_engine/sql/warehouse/w4_company_snapshot.sql`: vista `warehouse_company_snapshot` con `attributes_hash` sobre `plan`/`csm_owner`, entrada del SCD2 del PR3.
- [x] 2.5 `worky_engine/sql/warehouse/w5_facts.sql`: `fact_usage_monthly`, `fact_deals`, `fact_revenue_monthly` (agregado por mes de `close_date`), `fact_support_tickets` (grano de un ticket, `stg_tickets` vía `vitally_id`) y `fact_marketing_touches` (grano de un touch, `stg_marketing_touches`), cada uno unido contra la banda vigente de `dim_company` en su fecha. **Palanca de reducción revertida por decisión del usuario, después del cierre original de este PR:** los dos hechos que se habían dejado fuera para caber en el presupuesto de 800 líneas se restauraron; el usuario aceptó `size:exception` para esta versión de PR2. Ver sección "Deviations from Design" abajo.
- [x] 2.6 `worky_engine/warehouse/__init__.py` y `worky_engine/warehouse/db.py`: `open_warehouse_connection`, misma configuración de extensiones apagadas de A0, sin borrar el archivo entre corridas (D2, excepción a D6 de A0).
- [x] 2.7 `worky_engine/warehouse/runner.py` (esqueleto): `WAREHOUSE_FILES` en el orden fijo, DDL de `dim_company` (veinte columnas, vacía) e `identity_overrides`, `run_warehouse(con, overrides)` que regresa `WarehouseResult` con `map_source_identity` materializada. El DDL vacío de `dim_company` es necesario para que `w4`/`w5` puedan crearse sin que DuckDB rechace la vista por un objeto ausente; PR3 solo agrega el algoritmo de SCD2 sobre esta misma tabla, sin tocar ningún archivo `.sql`.
- [x] 2.8 `worky_engine/quality/warehouse_contracts.py`: `assert_map_source_identity_unique` y `assert_overrides_are_reflected`, mismo `ContractViolation` de A0.
- [x] 2.9 `worky_engine/cli.py`: `_import_warehouse_dependencies`, `cmd_warehouse` (mismo orden que `cmd_analyze`/`cmd_health`) y su parser `--data-dir --out-dir --db-path --run-date --overrides`. `--run-date` queda aceptado y sin efecto hasta el PR3.
- [x] 2.10 `tests/test_warehouse_star.py`: fixture mínimo propio, diez pruebas. Ver Work Unit Evidence.
- [x] 2.11 `outputs/warehouse/map_source_identity.csv` generado (1950 filas, ordenado por `source_system` y luego `source_id`); no commiteado en este batch (persistencia queda para el commit de cierre del PR, fuera de lo que hace `sdd-apply`).
- [x] 2.12 Cierre de PR2: pruebas focalizadas, suite completa, `warehouse` corrido sobre el dataset real dos veces adicionales (determinismo byte a byte confirmado), `git status --short outputs` confirmado con solo `outputs/warehouse/` nuevo, commit convencional preparado (ver abajo).

### PR2 Files Changed

| File | Action | What Was Done |
|------|--------|----------------|
| `worky_engine/sql/warehouse/w1_dim_date.sql` | Created | `dim_date`, 16 líneas |
| `worky_engine/sql/warehouse/w2_dim_csm_plan.sql` | Created | `dim_csm`, `dim_plan`, 17 líneas |
| `worky_engine/sql/warehouse/w3_map_source_identity.sql` | Created | `map_source_identity`, 44 líneas |
| `worky_engine/sql/warehouse/w4_company_snapshot.sql` | Created | `warehouse_company_snapshot`, 25 líneas |
| `worky_engine/sql/warehouse/w5_facts.sql` | Created/Modified | `fact_usage_monthly`, `fact_deals`, `fact_revenue_monthly`, `fact_support_tickets`, `fact_marketing_touches`, 150 líneas |
| `worky_engine/warehouse/__init__.py` | Created | Reexporta `open_warehouse_connection`, `run_warehouse`, 13 líneas |
| `worky_engine/warehouse/db.py` | Created | `open_warehouse_connection`, 29 líneas |
| `worky_engine/warehouse/runner.py` | Created | `WAREHOUSE_FILES`, DDL de `dim_company`/`identity_overrides`, `run_warehouse`, 134 líneas |
| `worky_engine/quality/warehouse_contracts.py` | Created | Dos contratos de `map_source_identity`, 52 líneas |
| `tests/test_warehouse_star.py` | Created/Modified | Trece pruebas, fixture mínimo propio, 366 líneas |
| `worky_engine/cli.py` | Modified | `_import_warehouse_dependencies`, `cmd_warehouse`, parser `warehouse`, 121 líneas (solo adiciones) |
| `outputs/warehouse/map_source_identity.csv` | Created (golden) | 1950 filas, fuera del conteo de autoría |

Ningún archivo bajo `worky_engine/sql/staging/`, `worky_engine/sql/marts/`, `worky_engine/identity_resolution/` (incluido `overrides.py`, ya cerrado en PR1), `worky_engine/quality/contracts.py` ni los goldens existentes de `outputs/` (los dieciocho de A0/A1/A3) se tocó.

### PR2 Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and result | `python -m pytest -q -m "not dataset" tests/test_warehouse_star.py` → `13 passed` (tres pruebas nuevas: grano de `fact_support_tickets`, grano de `fact_marketing_touches`, CSM distinto por banda para ambos); `python -m pytest -q -m "not dataset" tests/test_identity_overrides.py tests/test_warehouse_star.py` → `24 passed` |
| Runtime harness command/scenario and result | `python -m worky_engine warehouse --data-dir data/raw/sistemas` (sin `--out-dir`, usa el default `outputs/warehouse`) sobre un `.build/` limpio → `warehouse: 1950 vinculos en outputs\warehouse`, exit 0, `.build/warehouse.duckdb` creado. Corrido tres veces seguidas sobre el mismo `.build/warehouse.duckdb`: `outputs/warehouse/map_source_identity.csv` sale con el mismo sha256 (`29d11f7c...`) en las tres corridas, idéntico al golden ya existente antes de restaurar los dos hechos. Los dieciocho archivos ya versionados de `outputs/` (A0/A1/A3) confirmados con el mismo sha256 antes y después. `git status --short outputs` → solo `?? outputs/warehouse/`. `fact_support_tickets` y `fact_marketing_touches` consultados en el mismo proceso que corre `run_warehouse` sobre el dataset real: `0` filas cada uno, igual que los otros tres hechos (`fact_usage_monthly`, `fact_deals`, `fact_revenue_monthly`), porque `dim_company` sigue vacía hasta el algoritmo de SCD2 del PR3; `stg_tickets` trae 1,888 filas y `stg_marketing_touches` 1,635, confirmando que la fuente sí tiene datos y que el cero es por la unión pendiente, no por un error de los hechos nuevos |
| Rollback boundary | Eliminar `worky_engine/sql/warehouse/`, `worky_engine/warehouse/`, `worky_engine/quality/warehouse_contracts.py`, `tests/test_warehouse_star.py`, `outputs/warehouse/`, y revertir en `worky_engine/cli.py`: `DEFAULT_WAREHOUSE_DB_PATH`, `DEFAULT_WAREHOUSE_OUT_DIR`, `_import_warehouse_dependencies`, `cmd_warehouse`, el subparser `warehouse` y la línea añadida al docstring del módulo |

### PR2 Verification (foreground, exact results)

1. `python -m pytest -q -m "not dataset" tests/test_warehouse_star.py` → `13 passed in ~16s`
2. `python -m pytest -q` (suite completa, incluye pruebas `dataset`) → `239 passed in 133.76s` (línea base al cierre de PR2 original: 236; se agregaron 3 pruebas nuevas al restaurar los dos hechos, todas en verde)
3. Aislamiento de goldens: sha256 de los 18 archivos versionados de `outputs/` calculado antes de correr `warehouse` sobre un `.build/` limpio (`.build/warehouse.duckdb` no existía). Después de correr `python -m worky_engine warehouse --data-dir data/raw/sistemas`, los 18 hashes salen iguales y solo aparece `outputs/warehouse/` en `git status --short outputs`, con exactamente un archivo nuevo (`map_source_identity.csv`)
4. Determinismo: `warehouse` corrido dos veces más sobre el mismo `.build/warehouse.duckdb` ya existente → `outputs/warehouse/map_source_identity.csv` con el mismo sha256 `29d11f7ceb7022d03edb8e64a37c97f426d8159f55ecb624ca1e1feeac20ad90` en las tres corridas, idéntico al golden ya existente antes de esta actualización (restaurar los dos hechos no cambia `map_source_identity.csv`, que no depende de ellos)
5. `python -m worky_engine warehouse --help` → muestra `--data-dir`, `--out-dir`, `--db-path`, `--run-date`, `--overrides` con su ayuda
6. Conteo de líneas de autoría: `git diff --numstat -- worky_engine/cli.py` → `121  0` (121 líneas, sin cambios en esta actualización). `wc -l` de los archivos nuevos: `w1_dim_date.sql` 16, `w2_dim_csm_plan.sql` 17, `w3_map_source_identity.sql` 44, `w4_company_snapshot.sql` 25, `w5_facts.sql` 150 (era 92, +58 al restaurar los dos hechos), `warehouse/__init__.py` 13, `warehouse/db.py` 29, `warehouse/runner.py` 134, `quality/warehouse_contracts.py` 52, `tests/test_warehouse_star.py` 366 (era 301, +65 al agregar las tres pruebas nuevas). **Total autoría: 967 líneas** (medición anterior tras la palanca de reducción: 844; medido ahora, después de revertirla: 967, sobre el presupuesto de 800 por PR de `openspec/config.yaml`; el usuario aceptó `size:exception` para esta versión de PR2). `outputs/warehouse/map_source_identity.csv` (1950 filas) excluido del conteo por ser golden.

### Deviations from Design (PR2)

1. **Palanca de reducción revertida (decisión del usuario, después del cierre original de este PR):** `fact_support_tickets` y `fact_marketing_touches` se restauraron como vistas en `w5_facts.sql`, con el mismo patrón de unión a `dim_company` que las otras tres (`fact_support_tickets` resuelve `master_id` contra `mart_company_core` por `vitally_id`, igual que `mart_support.sql`; `fact_marketing_touches` reusa el `master_id` que ya resuelve `stg_marketing_touches.sql`). La spec `warehouse-model` (requisito "vistas de dimensiones y hechos sobre los marts existentes") ya no queda en desviación: las cinco vistas MUST están materializadas. Ya no queda pendiente sincronizar la spec por este motivo antes de archivar.
2. **Conteo de autoría por encima del presupuesto, ahora también después de revertir la palanca:** 844 líneas medidas con la palanca aplicada; 967 líneas medidas después de restaurarla (ver Verification #6 arriba). El usuario aceptó explícitamente `size:exception` para esta versión de PR2 en vez de mantener el recorte o dividir el PR en una rebanada adicional. No se comprimió ni se restiló código para caber en el número original, y las dos vistas restauradas y las tres pruebas nuevas siguen el mismo patrón que ya usaban las tres vistas y las diez pruebas existentes.
3. **`dim_company` con DDL vacío en este PR, no mencionado explícitamente en la tarea 2.7:** la tarea 2.7 solo nombra el DDL de `identity_overrides`, pero `w4_company_snapshot.sql` y `w5_facts.sql` (tareas 2.4 y 2.5, ya asignadas a este PR) necesitan que `dim_company` exista como objeto para poder crearse sin que DuckDB rechace la vista. Se agregó el DDL vacío (veinte columnas, sección 3 del diseño) al esqueleto de `runner.py`, dejando que el PR3 solo agregue el algoritmo de SCD2 sobre esta misma tabla sin tener que volver a tocar ningún archivo `.sql`. Esto no contradice la tarea 3.1 (que sigue siendo quien agrega el algoritmo), solo adelanta la forma vacía de la tabla.
4. **Mensaje final de `cmd_warehouse` distinto al de la sección 2 del diseño:** el diseño dice `warehouse: <n> empresas vigentes y <m> vinculos en <out-dir>`; este PR imprime solo `warehouse: <m> vinculos en <out-dir>`, porque `dim_company` todavía no tiene filas (el algoritmo de SCD2 llega en el PR3) y no hay `<n>` que reportar honestamente. El PR3 debe extender el mensaje.

### Issues Found (PR2)

Ninguno inesperado. La suite completa (236 pruebas) corrió en verde sin fallas ambientales. La única sorpresa fue el conteo de autoría (ver Deviations #2), ya cubierta por la salvaguarda que el propio diseño anticipó.

## PR3: SCD2 de `dim_company`, `fact_health_score_monthly` y golden de `dim_company`

**Batch**: PR3, tareas 3.1 a 3.9
**Modo**: Standard (strict_tdd: false)
**Rama**: `feat/a4-pr3-warehouse-scd2-health`, base `feat/a4-pr2-warehouse-star`

**Corrección post-revisión (native review, un ciclo acotado):** la revisión nativa de PR3 exigió una corrección acotada, aplicada en el commit `e7e465f`: una prueba nueva que demuestra, con datos reales del dataset, que la primera banda de cada empresa se abre hacia atrás y que los cinco hechos traen filas contra el dataset completo (`fact_usage_monthly` 9,793, `fact_support_tickets` 1,888, `fact_deals` 962, `fact_revenue_monthly` 125, `fact_marketing_touches` 1,635), en vez de dejar esa evidencia solo en la narrativa de "Corrección necesaria..." de más abajo. PR3 cerró bajo `size:exception`, con 873 líneas de autoría medidas contra el presupuesto de 800 (ver Verification #5 y la sección "PR3 Workload / PR Boundary" más abajo).

### PR3 Completed Tasks

- [x] 3.1 `worky_engine/warehouse/runner.py`: DDL de `dim_company` (sin cambio de forma, ya la tenía PR2 vacía) y las cuatro sentencias fijas del SCD2 (`_SCD2_REPLACE_SAME_DAY_SQL`, `_SCD2_CLOSE_SQL`, `_SCD2_OPEN_SQL`, `_SCD2_TYPE1_SQL`), parametrizadas por `run_date`, corridas en `_run_scd2` entre `w4` y `w5` de `WAREHOUSE_FILES`.
- [x] 3.2 `worky_engine/warehouse/runner.py`: DDL de `fact_health_score_monthly` (diez columnas) y `_snapshot_health`, que llama `run_health(con)` de A3 en proceso, borra las filas de la `run_date` actual e inserta de nuevo (idempotente), resolviendo `company_sk` contra la fila vigente de `dim_company` para cada `master_id`.
- [x] 3.3 `worky_engine/cli.py`: `cmd_warehouse` valida `--run-date` (formato ISO con `date.fromisoformat`, y nunca anterior al `effective_from` vigente más reciente ya persistido, consultado por `information_schema.tables` antes de asumir que `dim_company` existe); ambos casos inválidos terminan en código 1 sin tocar `assemble_master_dataset` ni `run_warehouse`.
- [x] 3.4 `worky_engine/quality/warehouse_contracts.py`: `assert_dim_company_one_current_per_master`, `assert_dim_company_sk_unique`, `assert_dim_company_bands_are_contiguous`, `assert_dim_company_tracked_attributes_change`, `assert_health_snapshot_unique` y `assert_warehouse_row_order`, más la extensión de `assert_map_source_identity_unique` (ahora recibe `dim_company` y valida que todo `master_id` exista ahí). `run_warehouse_contracts` corre los ocho contratos en el orden de la sección 8 del diseño.
- [x] 3.5 `tests/test_warehouse_scd2.py`: fixture mínimo propio (compañías más las cinco tablas secundarias vacías con sus columnas reales, mismo patrón que `tests/test_identity_overrides.py`). Diez pruebas: persistencia del archivo entre conexiones, primera corrida abre una fila vigente por empresa, corrida sin cambios no agrega filas, cambio de plan cierra y abre banda, empresa que desaparece conserva su fila, cada corrida de health agrega un snapshot, snapshot idempotente para la misma fecha, llaves no dependen del orden de ejecución, atributo no rastreado (tipo 1) actualiza en sitio, y reemplazo de banda del mismo día.
- [x] 3.6 `tests/test_warehouse_idempotency.py`, marca `dataset`. Dos pruebas: dos corridas de `warehouse` sobre el dataset real dan `dim_company.csv` y `map_source_identity.csv` idénticos entre sí y contra el golden commiteado, con el hash de los dieciocho archivos ya versionados de `outputs/` (A0, A1, A3) sin cambio; y `--out-dir` queda con exactamente esos dos archivos.
- [x] 3.7 Verificado por inspección: D2 del diseño de este cambio ya documenta la excepción a D6 de A0 y su razón; `worky_engine/warehouse/db.py` repite la misma declaración. Sin cambios de código.
- [x] 3.8 `outputs/warehouse/dim_company.csv` generado sobre el dataset real (650 filas, ordenado por `master_id` y `effective_from`), hash confirmado idéntico en tres corridas seguidas más una cuarta con `--run-date` explícito igual al de las anteriores. No commiteado en este batch (mismo patrón que `map_source_identity.csv` en PR2; instrucción explícita del orquestador de no commitear ni stagear).
- [x] 3.9 Cierre de PR3: ver Verification y Work Unit Evidence más abajo para los resultados exactos de cada comando.

### Corrección necesaria fuera de las tareas literales: los cinco hechos no unían nada contra el dataset real

Al correr `warehouse` sobre el dataset real con `dim_company` ya poblada (algoritmo de SCD2 de este PR), `fact_support_tickets`, `fact_deals` y `fact_marketing_touches` seguían en cero filas, y `fact_revenue_monthly` solo traía una. La causa: el único run por omisión usa `run_date = dataset_asof` (D3), que en este dataset es `2024-08-31`, el último día del dataset; la primera (y única) banda de cada empresa abre exactamente en esa fecha (D7). El join de la sección 5 del diseño (`f.event_date >= d.effective_from`) exige que el hecho sea posterior o igual a esa apertura, pero deals, tickets y touches del caso están fechados antes de esa fecha por construcción (son historia, no eventos futuros): ningún hecho histórico podía satisfacer esa condición contra la única banda que existe.

Se agregó la vista `dim_company_open_bands` en `worky_engine/sql/warehouse/w5_facts.sql`, que calcula `join_effective_from`: `DATE '0001-01-01'` para la banda más antigua de cada empresa (no hay una banda anterior con la que comparar: es la primera vez que se observó a la empresa, no un hueco de datos) y el propio `effective_from` para cualquier banda posterior (abierta por un cambio real de plan o csm_owner, que si debe respetar su fecha de apertura). Los cinco `JOIN` de `w5_facts.sql` ahora usan `dim_company_open_bands`/`join_effective_from` en vez de `dim_company`/`effective_from` directamente. Esto no cambia el resultado de ninguna prueba existente (las bandas más antiguas de los fixtures de prueba ya son anteriores a todos sus eventos), pero sí cambia el resultado sobre el dataset real: `fact_usage_monthly` 9,793 filas, `fact_support_tickets` 1,888 (coincide con el total de `stg_tickets`), `fact_deals` 962, `fact_revenue_monthly` 125, `fact_marketing_touches` 1,635 (coincide con el total de `stg_marketing_touches`), confirmado antes de generar el golden final. Esta corrección no estaba nombrada en ninguna tarea de 3.1 a 3.9, pero la instrucción de esta rebanada pedía explícitamente asegurar que los cinco hechos trajeran filas sobre el dataset real, y la causa vivía en `w5_facts.sql`, un archivo ya asignado a este PR (no está en la lista de archivos de solo lectura).

### PR3 Files Changed

| File | Action | What Was Done |
|------|--------|----------------|
| `worky_engine/warehouse/runner.py` | Modified | Algoritmo de SCD2 (`_run_scd2` y sus cuatro sentencias), `_resolve_run_date`, DDL y snapshot de `fact_health_score_monthly` (`_snapshot_health`), `WarehouseResult` con `dim_company` y `fact_health_score_monthly` agregados, `run_warehouse` con parámetro `run_date` |
| `worky_engine/quality/warehouse_contracts.py` | Modified | Seis contratos nuevos de `dim_company`/health, extensión de `assert_map_source_identity_unique`, `run_warehouse_contracts` con firma de cuatro parámetros |
| `worky_engine/cli.py` | Modified | Validación de `--run-date` en `cmd_warehouse`, `write_csv` de `dim_company.csv`, mensaje final con el conteo de empresas vigentes, ayuda del argumento `--run-date` actualizada |
| `worky_engine/sql/warehouse/w5_facts.sql` | Modified | Vista `dim_company_open_bands` y los cinco `JOIN` reescritos para usarla (ver sección de corrección arriba) |
| `tests/test_warehouse_star.py` | Modified | Fixture `warehouse_setup` reemplazado: dos corridas reales de `run_warehouse` con un cambio de `csm_owner` en vez de sembrar bandas a mano (`_seed_dim_company_bands` eliminada); `test_dimensiones_derivadas_sin_duplicar_logica` actualizada a tres CSM distintos |
| `tests/test_warehouse_scd2.py` | Created | Diez pruebas, fixture mínimo propio |
| `tests/test_warehouse_idempotency.py` | Created | Dos pruebas, marca `dataset` |
| `outputs/warehouse/dim_company.csv` | Created (golden) | 650 filas, fuera del conteo de autoría |

Ningún archivo bajo `worky_engine/sql/staging/`, `worky_engine/sql/marts/`, `worky_engine/identity_resolution/`, `worky_engine/quality/contracts.py`, `w1_dim_date.sql`, `w2_dim_csm_plan.sql`, `w3_map_source_identity.sql`, `w4_company_snapshot.sql`, ni los dieciocho goldens existentes de `outputs/` (A0/A1/A3) se tocó. Los cambios en `cli.py` quedaron dentro de `cmd_warehouse` y su parser.

### PR3 Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and result | `python -m pytest -q -m "not dataset" tests/test_warehouse_scd2.py tests/test_warehouse_star.py` → `23 passed`; `python -m pytest -q -m "not dataset" tests/test_warehouse_scd2.py tests/test_warehouse_star.py tests/test_identity_overrides.py` → `36 passed` |
| Runtime harness command/scenario and result | `python -m worky_engine warehouse --data-dir data/raw/sistemas` (default `--out-dir outputs/warehouse`), tres corridas seguidas sobre `.build/warehouse.duckdb` recién borrado: `650 empresas vigentes y 1950 vinculos`, sha256 de `dim_company.csv` (`eaaf60bf...`) y `map_source_identity.csv` (`29d11f7c...`) idénticos en las tres. Cuarta corrida con `--run-date 2024-08-31` (mismo run date que las anteriores): mismos conteos (650/650), mismos hashes, cero filas nuevas en `dim_company` ni en `fact_health_score_monthly`. `--run-date 2020-01-01` (anterior al vigente): código 1, `dim_company` sin cambio (650 filas antes y después). `--run-date not-a-date`: código 1, mismo mensaje de formato ISO |
| Rollback boundary | Revertir el algoritmo de SCD2 y la foto de health en `worky_engine/warehouse/runner.py` (volver a la versión del PR2, sin `_run_scd2`/`_snapshot_health`/`_resolve_run_date`), revertir los seis contratos nuevos y la extensión de `assert_map_source_identity_unique` en `worky_engine/quality/warehouse_contracts.py`, revertir la validación de `--run-date` y el segundo `write_csv` en `cmd_warehouse`, revertir `dim_company_open_bands` en `w5_facts.sql`, borrar `tests/test_warehouse_scd2.py` y `tests/test_warehouse_idempotency.py`, revertir el fixture de `tests/test_warehouse_star.py` a `_seed_dim_company_bands`, borrar `.build/warehouse.duckdb` y `outputs/warehouse/dim_company.csv` |

### PR3 Verification (foreground, exact results)

1. `python -m pytest -q -m "not dataset" tests/test_warehouse_scd2.py tests/test_warehouse_star.py` → `23 passed` (9 de `test_warehouse_scd2.py` en la primera corrida, luego 10 tras agregar la prueba de orden de ejecución, más 13 de `test_warehouse_star.py`, ya con el fixture reescrito y `dim_csm` con tres CSM)
2. `python -m pytest -q` (suite completa, incluye pruebas `dataset`) → `251 passed in 2227.27s` (línea base al cierre de PR2: 239; se agregaron 12 pruebas nuevas: 10 de `test_warehouse_scd2.py` y 2 de `test_warehouse_idempotency.py`, todas en verde)
3. Aislamiento y determinismo de goldens: `.build/warehouse.duckdb` borrado, tres corridas seguidas de `python -m worky_engine warehouse --data-dir data/raw/sistemas`. `git status --short outputs` → solo `outputs/warehouse/dim_company.csv` nuevo (`map_source_identity.csv` ya estaba commiteado desde PR2 y salió sin cambios). Conteos sobre el dataset real: `dim_company WHERE is_current` 650, `fact_usage_monthly` 9793, `fact_support_tickets` 1888, `fact_deals` 962, `fact_revenue_monthly` 125, `fact_marketing_touches` 1635, `fact_health_score_monthly` 650
4. Captura hacia adelante del SCD2: `tests/test_warehouse_scd2.py::test_cambio_de_plan_cierra_la_fila_anterior_y_abre_una_nueva` (dos corridas, cambio de plan, la banda anterior cierra en la fecha de la segunda corrida y la nueva queda vigente) y `test_reemplazo_de_banda_del_mismo_dia` (dos corridas con la misma `run_date` y un cambio real de por medio, la banda se reemplaza en vez de duplicarse) pasan, ver punto 1. Además, una cuarta corrida real sobre el dataset con el mismo `--run-date` que las tres anteriores agrega cero filas a `dim_company` (650 antes y después) y cero filas a `fact_health_score_monthly` (650 antes y después), con los dos goldens saliendo con el mismo sha256
5. Conteo de líneas de autoría: `git diff --numstat` sobre los archivos modificados → `tests/test_warehouse_star.py` 27+23=50, `worky_engine/cli.py` 53+13=66, `worky_engine/quality/warehouse_contracts.py` 110+13=123, `worky_engine/sql/warehouse/w5_facts.sql` 34+14=48, `worky_engine/warehouse/runner.py` 204+29=233; `wc -l` de los archivos nuevos: `tests/test_warehouse_idempotency.py` 95, `tests/test_warehouse_scd2.py` 258. **Total autoría: 873 líneas** (estimado del diseño: ~390; medido: 873, sobre el presupuesto de 800 de `openspec/config.yaml`). `outputs/warehouse/dim_company.csv` (650 filas) excluido del conteo por ser golden

### Deviations from Design (PR3)

1. **Presupuesto de autoría superado (873 contra 800), salvaguarda de la sección 10 del diseño no aplicada:** la salvaguarda declarada de antemano en tasks.md y en el diseño para este PR es la misma del PR2 (mover `fact_support_tickets`/`fact_marketing_touches` al documento sin materializarlos y recortar sus pruebas). Esa palanca ya no aplica: el PR2 la revirtió por decisión explícita del usuario, que aceptó `size:exception` para dejar esos dos hechos materializados de forma permanente; ambos son parte activa del esquema en estrella que este PR extiende (`dim_company_open_bands` los alcanza igual que a los otros tres). Volver a quitarlos ahora desharía esa decisión ya aceptada, así que no se aplicó. El exceso medido (873 vs 800) sigue el mismo patrón que PR1 (529 vs 255 estimadas) y PR2 (967 vs 380 estimadas, `size:exception` aceptado): se recomienda `size:exception` también para esta rebanada, sin comprimir ni recortar pruebas para forzar el número.
2. **Vista `dim_company_open_bands` no nombrada en ninguna tarea de 3.1 a 3.9:** necesaria para que los cinco hechos trajeran filas sobre el dataset real, tal como pedía explícitamente esta rebanada; ver la sección "Corrección necesaria..." arriba para el detalle completo. No cambia el contrato de `dim_company` ni ningún golden ya commiteado; solo cambia cómo los hechos (vistas derivadas, sin su propio golden) resuelven su unión histórica contra la primera banda de cada empresa.
3. **`fact_health_score_monthly` resuelve `company_sk` contra la fila vigente (`is_current = true`) de `dim_company`, no contra una unión temporal como D13:** el diseño no especifica explícitamente esta unión para la foto de health (D12 solo dice "de dónde sale", no cómo se une a `dim_company`). Se usó `is_current` porque la foto de health se toma en el momento de la corrida (`run_date`), que es exactamente cuando `dim_company` queda actualizada por el propio algoritmo de SCD2 de esa misma corrida: la fila vigente en ese instante es, por construcción, la vigente en `run_date`.

### Issues Found (PR3)

Ninguno inesperado, aparte de la corrección de `w5_facts.sql` ya documentada arriba (encontrada por instrucción explícita de esta rebanada, no por accidente). La suite completa (251 pruebas) corrió en verde sin fallas ambientales.

## Remaining Tasks

Ninguna. Las 32 tareas de las cuatro rebanadas (PR1 a PR4) están completas.

- [x] Seguimiento resuelto: la desviación de `fact_support_tickets`/`fact_marketing_touches` (Deviations #1 de PR2) ya no aplica, los dos hechos se restauraron por decisión del usuario; no queda pendiente sincronizar la spec por este motivo
- [x] Seguimiento resuelto: PR3 ya asegura que los cinco hechos traen filas sobre el dataset real (ver "Corrección necesaria..." arriba); no queda pendiente para PR4

## PR4: documento del modelo, ERD 07 y rutas rápidas

**Batch**: PR4, tareas 4.1 a 4.6
**Modo**: Standard (strict_tdd: false), receipt-driven review apagado para esta rebanada de documentación (instrucción explícita del orquestador)
**Rama**: `feat/a4-pr4-warehouse-docs`, base `feat/a4-pr3-warehouse-scd2-health`

Este PR no toca código de producción: solo documentación y el diagrama 07, entregado con `archify` siguiendo el mismo flujo Node que los diagramas 02 y 03 (`erDiagram` de Mermaid, tipo `erd`).

### PR4 Completed Tasks

- [x] 4.1 `docs/data-model/01-warehouse-model.md` creado (153 líneas): responde las cuatro preguntas de A4 en secciones nombradas ("1. Qué hechos y dimensiones tiene el warehouse", "2. Dónde viven las llaves de reconciliación...", "3. Cómo se guarda el historial de cambios", "4. Cómo el trabajo manual de A0 nunca se repite"), declara el historial como hacia adelante, documenta el ejemplo de las seis columnas de `identity_overrides.csv` y el contrato exacto de la marca de agua incremental (D18).
- [x] 4.2 `docs/diagrams/src/07-modelo-estrella-warehouse.mmd` (119 líneas) y `docs/diagrams/src/07-modelo-estrella-warehouse.erd.json` creados: catorce entidades (`dim_company`, `dim_date`, `dim_csm`, `dim_plan`, `map_source_identity`, `identity_overrides`, los cinco hechos, `fact_health_score_monthly`, `identity_crosswalk`, `match_audit`), con las llaves reales de cada tabla, extendiendo el diagrama 03 sin repetirlo.
- [x] 4.3 `docs/diagrams/07-modelo-estrella-warehouse.html` entregado con `archify`: `validate erd` con 11/11 checks en verde y 0 errores de composición, luego `deliver erd` (artefacto de 67,307 bytes, sha256 `843501d9...`). `grep -c "https://"` da 0.
- [x] 4.4 `docs/diagrams/README.md` modificado: fila 07 agregada a la tabla del índice con `docs/data-model/01-warehouse-model.md` como documento de origen, el conteo "Los siete diagramas" corregido a "Los ocho diagramas", y el comando de regeneración de 07 agregado a la sección "Cómo regenerar cada diagrama" para mantener la convención ya establecida por 00 a 06 en el mismo archivo.
- [x] 4.5 `README.md` modificado: paso 6 de "Ruta rápida" con el comando de `warehouse`, y dos filas nuevas en "Qué produce" (`warehouse/dim_company.csv`, `warehouse/map_source_identity.csv`).
- [x] 4.6 Cierre de PR4: ver Verification más abajo para los resultados exactos.

### Qué satisface cada escenario de spec asignado a PR4

| Escenario | Dónde queda satisfecho |
|---|---|
| "contrato documentado" (marca de agua incremental) | `docs/data-model/01-warehouse-model.md`, sección 2, subsección "Contrato de la marca de agua incremental (documentado, no implementado)"; también en `design.md` sección 6 |
| "excepción documentada a D6" | `docs/data-model/01-warehouse-model.md`, sección 4, subsección "Excepción documentada a la decisión D6 de A0"; ya satisfecho también por `design.md` D2 y por `worky_engine/warehouse/db.py` (verificado por PR3, tarea 3.7) |
| "no es una serie de mrr_mxn" | `docs/data-model/01-warehouse-model.md`, sección 1, párrafo sobre `fact_revenue_monthly`: agrega `fact_deals` por mes de `close_date`, nunca repite `mrr_mxn` |

### PR4 Files Changed

| File | Action | What Was Done |
|------|--------|----------------|
| `docs/data-model/01-warehouse-model.md` | Created | Documento de A4, 153 líneas |
| `docs/diagrams/src/07-modelo-estrella-warehouse.mmd` | Created | Fuente Mermaid `erDiagram`, 119 líneas |
| `docs/diagrams/src/07-modelo-estrella-warehouse.erd.json` | Created | Entrada de `archify`, 9 líneas |
| `docs/diagrams/07-modelo-estrella-warehouse.html` | Created (generado por `archify deliver`) | 67,307 bytes, 0 referencias a `https://` |
| `docs/diagrams/README.md` | Modified | Fila 07, conteo corregido, comando de regeneración |
| `README.md` | Modified | Paso 6 de "Ruta rápida", dos filas en "Qué produce" |

Ningún archivo de `worky_engine/`, `tests/` ni `outputs/` se tocó en este PR.

### PR4 Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and result | N/A: PR de documentación sin comportamiento ejecutable propio, según lo declarado en tasks.md. Se corrió la suite rápida como red de seguridad: `python -m pytest -q -m "not dataset"` → `211 passed, 41 deselected in 522.10s` |
| Runtime harness command/scenario and result | `node bin/archify.mjs validate erd docs/diagrams/src/07-modelo-estrella-warehouse.erd.json --json` → `"ok": true`, 11 checks en verde, `composition.status: "pass"`, 0 errores y 0 advertencias; `node bin/archify.mjs deliver erd ... --json` → `"ok": true`, artefacto de 67,307 bytes |
| Rollback boundary | Eliminar `docs/data-model/01-warehouse-model.md`, `docs/diagrams/07-modelo-estrella-warehouse.html` y su fuente en `docs/diagrams/src/`, revertir la fila 07 y el comando de regeneración en `docs/diagrams/README.md`, y revertir el paso 6 y las dos filas nuevas en `README.md` |

### PR4 Verification (foreground, exact results)

1. `python -m pytest -q -m "not dataset"` → `211 passed, 41 deselected in 522.10s (0:08:42)`. Sin cambios de código en este PR, la línea base se mantiene (211 = 251 de PR3 menos las pruebas marcadas `dataset`, que esta rebanada no reejecuta por no haber tocado ningún archivo bajo `worky_engine/` ni `tests/`)
2. `git status --short` → `M README.md`, `M docs/diagrams/README.md`, `M openspec/changes/a4-warehouse-model/tasks.md`, `?? docs/data-model/01-warehouse-model.md`, `?? docs/diagrams/07-modelo-estrella-warehouse.html`, `?? docs/diagrams/src/07-modelo-estrella-warehouse.erd.json`, `?? docs/diagrams/src/07-modelo-estrella-warehouse.mmd`. Ningún archivo de `outputs/` cambió
3. `docs/diagrams/07-modelo-estrella-warehouse.html` existe, 67,307 bytes. `grep -c "dim_company"`, `grep -c "fact_health_score_monthly"` y `grep -c "identity_overrides"` dan 1, 0 y 1 respectivamente porque el SVG queda incrustado en una sola línea larga; contados con `grep -o ... | wc -l` (conteo de ocurrencias, no de líneas) dan 13, 4 y 5 ocurrencias reales
4. `grep -c "—" docs/data-model/01-warehouse-model.md` → `0`. `wc -l docs/data-model/01-warehouse-model.md` → `153`
5. Conteo de líneas de autoría: `wc -l` del nuevo markdown (`docs/data-model/01-warehouse-model.md`) → **153 líneas**, dentro del rango objetivo de 150 a 220 y muy por debajo del presupuesto de 800 por PR. Los archivos de fuente del diagrama (`07-modelo-estrella-warehouse.mmd` 119 líneas, `07-modelo-estrella-warehouse.erd.json` 9 líneas) y el HTML generado (67,307 bytes) quedan fuera de este conteo, igual que los goldens de PR2 y PR3 quedaron fuera del suyo

### Deviations from Design (PR4)

Ninguna decisión de diseño se cambió. Dos ajustes de documentación no nombrados de forma literal en las tareas 4.1 a 4.6, hechos por transparencia con el lector del documento:

1. `docs/data-model/01-warehouse-model.md` agrega una tabla de los ocho contratos de calidad de `worky_engine/quality/warehouse_contracts.py` (sección 3) y una tabla de las cinco banderas del comando más sus códigos de salida (sección "Cómo correrlo"). Ninguna de las dos tablas está pedida de forma literal por la tarea 4.1, pero ambas responden directamente la pregunta "cómo se guarda el historial" con la evidencia de que el motor lo protege, no solo lo declara.
2. `docs/diagrams/README.md` corrige "Los siete diagramas" a "Los ocho diagramas" y agrega el comando de regeneración de 07 a la sección ya existente "Cómo regenerar cada diagrama". La tarea 4.4 solo pide agregar la fila 07 a la tabla del índice; se hicieron estos dos ajustes adicionales, acotados al mismo archivo ya asignado a esta tarea, para que el archivo no quede con un conteo desactualizado ni con un diagrama fuera de su propia guía de regeneración.

### Issues Found (PR4)

Ninguno. La suite `not dataset` corrió en verde (211 pruebas) sin fallas ambientales, y `archify validate`/`deliver` pasaron en el primer intento sin necesitar ninguna corrección de geometría.

## PR4 Workload / PR Boundary

- Mode: stacked PR slice (`auto-chain`, `stacked-to-main`), dentro del presupuesto de 800 líneas de autoría (153 medidas, ver Verification #5)
- Current work unit: Unit 4 — documento del modelo, ERD 07 y rutas rápidas
- Boundary: arranca en `feat/a4-pr3-warehouse-scd2-health` (sin `docs/data-model/01-warehouse-model.md`, sin diagrama 07, sin la corrida de `warehouse` documentada en `README.md`) y termina con las tareas 4.1 a 4.6 completas, PR4 listo para abrir contra `feat/a4-pr3-warehouse-scd2-health`
- Estimated review budget impact: 153 líneas de autoría del documento nuevo, dentro del presupuesto; el revisor ve primero que el documento responde las cuatro preguntas de A4 en el orden que pide el caso y que la sección 3 dice sin rodeos que el historial es hacia adelante

## PR4 Prepared Conventional Commit Message

```
docs(warehouse): add the A4 warehouse model document and its ERD

Add docs/data-model/01-warehouse-model.md, answering the four A4
questions in named sections: which fact and dimension tables exist,
where the hubspot_id/account_id/vitally_id reconciliation keys live,
how change history is captured, and how A0's manual identity review
never repeats. States plainly that the dataset is a single snapshot
and the SCD2 evidence is a two-run test, not reconstructed history.
Documents the identity_overrides.csv example, the incremental
watermark contract, the eight quality contracts, and real row counts
from the case dataset.

Add docs/diagrams/07-modelo-estrella-warehouse.html with archify
(erd type), extending diagram 03 with the star schema: dim_company
with its SCD2 keys, map_source_identity, identity_overrides, the five
facts and fact_health_score_monthly. Register it in
docs/diagrams/README.md alongside its regeneration command.

Add the warehouse command to README.md's quick path and outputs
table, matching the existing analyze and health sections. No
production code changed in this PR.
```

## PR3 Workload / PR Boundary

- Mode: stacked PR slice (`auto-chain`, `stacked-to-main`); presupuesto superado (873 líneas medidas contra 800), se recomienda `size:exception` para esta rebanada, igual que se aceptó para PR2 (967 líneas)
- Current work unit: Unit 3 — SCD2 de `dim_company`, `fact_health_score_monthly` y golden de `dim_company`
- Boundary: arranca en `feat/a4-pr2-warehouse-star` (sin algoritmo de SCD2, `dim_company` vacía, sin `fact_health_score_monthly`) y termina con las tareas 3.1 a 3.9 completas, PR3 listo para abrir contra `feat/a4-pr2-warehouse-star` una vez que el usuario confirme el `size:exception`
- Estimated review budget impact: 873 líneas de autoría, 73 sobre el presupuesto de 800; el revisor ve primero que dos corridas sin cambios no escriben nada y que un cambio de plan cierra la banda anterior con `is_current = False`

## PR3 Prepared Conventional Commit Message

```
feat(warehouse): add the dim_company SCD2 algorithm, the health score snapshot and its golden

Add the four fixed SCD2 statements to warehouse/runner.py (same-day
replace, close, open, type-1 update), parameterized by run_date:
dim_company now keeps one current band per company plus a closed band
per real plan or csm_owner change, captured forward from each run.

Add the fact_health_score_monthly DDL and snapshot step, calling A3's
run_health(con) in process and resolving company_sk against the
current dim_company row; a rerun with the same run_date is idempotent.

Wire --run-date validation into cmd_warehouse (ISO format, never
earlier than the most recent persisted current effective_from) and
write dim_company.csv alongside map_source_identity.csv. Add the six
new dim_company/health contracts and extend
assert_map_source_identity_unique to check every master_id exists in
dim_company.

Add dim_company_open_bands in w5_facts.sql so the five facts resolve
against a company's earliest known band even for events older than
its first snapshot date, instead of silently dropping them: on the
real dataset this takes fact_support_tickets, fact_deals and
fact_marketing_touches from zero rows to their real counts.

Replace test_warehouse_star.py's hand-seeded dim_company bands with
two real SCD2 runs, and add test_warehouse_scd2.py and
test_warehouse_idempotency.py. Commit dim_company.csv, generated on
the real dataset and confirmed byte-identical across three consecutive
runs plus a fourth with an explicit matching run-date, with the
eighteen existing outputs/ files untouched.
```

## PR2 Workload / PR Boundary

- Mode: stacked PR slice (`auto-chain`, `stacked-to-main`), `size:exception` aceptado por el usuario (967 líneas medidas contra 800 de presupuesto, después de revertir la palanca de reducción y restaurar `fact_support_tickets`/`fact_marketing_touches`)
- Current work unit: Unit 2 — vistas del esquema en estrella, `cmd_warehouse` y golden de `map_source_identity`
- Boundary: arranca en `feat/a4-pr1-identity-overrides` (sin `worky_engine/sql/warehouse/`, `worky_engine/warehouse/`, `cmd_warehouse`) y termina con las tareas 2.1 a 2.12 completas, más las dos vistas restauradas y sus tres pruebas, PR2 listo para abrir contra `feat/a4-pr1-identity-overrides`
- Estimated review budget impact: 967 líneas de autoría, 167 sobre el presupuesto de 800 (`size:exception` ya aceptado); el revisor ve primero que `warehouse` corre en un clon limpio sin `build` previo y que ningún archivo de `sql/staging/` ni `sql/marts/` cambió

## PR2 Prepared Conventional Commit Message

```
feat(warehouse): add the star schema views, the warehouse command and its map_source_identity golden

Add worky_engine/sql/warehouse/ with dim_date, dim_csm, dim_plan,
map_source_identity and the five facts (fact_usage_monthly,
fact_deals, fact_revenue_monthly, fact_support_tickets and
fact_marketing_touches), each fact joined against the dim_company band
current on its own event date.

Add worky_engine/warehouse/ (open_warehouse_connection, which keeps
its .duckdb file between runs, and the runner skeleton with the fixed
WAREHOUSE_FILES order and the dim_company/identity_overrides DDL) and
worky_engine/quality/warehouse_contracts.py with the two contracts
available at this point.

Wire cmd_warehouse into cli.py, same order as analyze and health: no
build required first, own persisted connection, and one CSV written
(map_source_identity.csv). Commit its golden, generated on the real
dataset and confirmed byte-identical across three consecutive runs,
with the eighteen existing outputs/ files untouched.
```

## Status

32/32 tasks complete (PR1, PR2, PR3 y PR4 hechos). Ready for verify. PR1 mide 529 líneas de autoría, dentro del presupuesto de 800. PR2 mide 967 líneas de autoría contra el presupuesto de 800 (`size:exception` ya aceptado por el usuario). PR3 mide 873 líneas de autoría contra el presupuesto de 800, con la revisión nativa exigiendo una corrección acotada (commit `e7e465f`); se recomienda `size:exception` también para PR3, igual que se aceptó para PR2, pendiente de confirmación del usuario antes de abrir el PR contra `feat/a4-pr2-warehouse-star`. PR4 mide 153 líneas de autoría en su documento nuevo, dentro del presupuesto de 800, sin código de producción tocado.

Ninguna tarea queda pendiente de las 32 originales. El único punto abierto es administrativo, no de implementación: confirmar `size:exception` para PR2 y PR3 antes de abrir esos dos PR contra GitHub (PR1 y PR4 no lo necesitan, ambos caben dentro del presupuesto de 800).
