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

## Remaining Tasks

- [ ] 3.1 a 3.9 (PR3: SCD2 de `dim_company`, `fact_health_score_monthly`, golden de `dim_company`)
- [ ] 4.1 a 4.6 (PR4: documento del modelo, ERD 07, rutas rápidas)
- [x] Seguimiento resuelto: la desviación de `fact_support_tickets`/`fact_marketing_touches` (Deviations #1) ya no aplica, los dos hechos se restauraron por decisión del usuario; no queda pendiente sincronizar la spec por este motivo

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

17/32 tasks complete (PR1 y PR2 hechos; PR3 y PR4 pendientes). Ready for next batch (PR3). PR2 mide 967 líneas de autoría contra el presupuesto de 800, después de que el usuario pidió revertir la palanca de reducción y restaurar `fact_support_tickets`/`fact_marketing_touches`; `size:exception` ya aceptado por el usuario para esta versión de PR2.
