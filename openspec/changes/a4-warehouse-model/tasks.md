# Tareas: esquema en estrella ejecutable del warehouse y overrides de identidad (`a4-warehouse-model`)

Este documento convierte el diseño en trabajo ejecutable. El corte sigue la sección 10 del diseño: cuatro PR encadenados, cada uno con inicio claro, fin claro y verificación propia. Los goldens bajo `outputs/warehouse/` quedan fuera del conteo de líneas de autoría, pero sí cuentan para la instantánea completa de revisión. Los dieciocho archivos ya versionados de `outputs/` (ocho de A0, ocho de A1, dos de A3) son de solo lectura para este cambio: ninguna tarea los edita, solo verifica su hash.

## Pronóstico de carga de revisión (Review Workload Forecast)

| Field | Value |
|---|---|
| Estimated changed lines | PR1 ~255, PR2 ~380 (más ~1,978 filas de golden fuera del conteo), PR3 ~390 (más ~650 filas de golden fuera del conteo), PR4 ~200. ~1,225 líneas de autoría en total |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR1 → PR2 → PR3 → PR4, encadenados sobre `main` |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Presupuesto por PR de este repositorio: 800 líneas de autoría (`review_budget_lines`, `openspec/config.yaml`). Las cuatro rebanadas quedan entre 25 % y 49 % de ese tope, pero A0 midió `cascade.py` en 466 líneas contra 120 estimadas y A3 midió su PR1 en 991 líneas antes de reducirlo a 798. Con ese precedente, un PR que hoy estima 390 puede acercarse a 700-800. Por eso el riesgo queda en Medium y no en Low, y el diseño ya deja una palanca de reducción documentada para el PR2 y el PR3 (ver sus notas de apertura).

Líneas de control exactas para el guardián automatizado, en el formato literal que exige el skill:

```text
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium
```

Con `auto-chain`, el orquestador procede con la primera rebanada usando `stacked-to-main` ya fijado por el usuario: el PR1 apunta a `main`, y cada PR siguiente apunta a la rama del PR anterior.

### Unidades de trabajo sugeridas

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|---|---|---|---|---|---|
| 1 | Precedencia de `identity_overrides` sobre la cascada en `resolve` y `build` | PR1 | `python -m pytest -q -m "not dataset" tests/test_identity_overrides.py` | `python -m worky_engine build --data-dir data/raw/sistemas --out-dir outputs` sin archivo de overrides, salida idéntica | Eliminar `worky_engine/identity_resolution/overrides.py`, `tests/test_identity_overrides.py`, y revertir el `--overrides` de `cmd_resolve`/`cmd_build` en `cli.py` |
| 2 | Vistas del esquema en estrella, `cmd_warehouse` y el golden de `map_source_identity` | PR2 | `python -m pytest -q -m "not dataset" tests/test_warehouse_star.py` | `python -m worky_engine warehouse --data-dir data/raw/sistemas` | Eliminar `worky_engine/sql/warehouse/`, `worky_engine/warehouse/`, `worky_engine/quality/warehouse_contracts.py`, revertir `cmd_warehouse` de `cli.py`, borrar `outputs/warehouse/` |
| 3 | SCD2 de `dim_company`, `fact_health_score_monthly` y el golden de `dim_company` | PR3 | `python -m pytest -q -m "not dataset" tests/test_warehouse_scd2.py` y `python -m pytest -q -m dataset tests/test_warehouse_idempotency.py` | `python -m worky_engine warehouse --data-dir data/raw/sistemas` corrido dos veces | Revertir el algoritmo de SCD2 y la foto de health en `worky_engine/warehouse/runner.py`, borrar `.build/warehouse.duckdb` y `outputs/warehouse/dim_company.csv` |
| 4 | Documento del modelo, ERD 07 y rutas rápidas | PR4 | N/A: PR de documentación, sin prueba propia; se corre la suite completa en el cierre | N/A: no agrega comportamiento ejecutable | Eliminar `docs/data-model/01-warehouse-model.md`, `docs/diagrams/07-modelo-estrella-warehouse.html` y su fuente, revertir las líneas de `README.md` y `docs/diagrams/README.md` |

## PR1: precedencia de `identity_overrides` en `resolve` y `build`

Rama: `feat/a4-pr1-identity-overrides`, base `main`. Líneas de autoría estimadas: ~255. Qué revisa primero el revisor: que sin archivo de overrides las salidas de `resolve` y `build` queden idénticas byte a byte, y que una fila inválida detenga la corrida antes de escribir nada.

- [ ] 1.1 Crear `worky_engine/identity_resolution/overrides.py` con `load_overrides(path)`: lee el CSV en UTF-8 con `dtype=str`, valida las seis columnas exactas (`source_system`, `source_id`, `master_id`, `decided_by`, `decided_at`, `reason`), que `source_system` sea `product_db` o `vitally`, que `decided_by`/`decided_at`/`reason` no vengan vacíos, que `decided_at` sea fecha ISO, y que `source_id` no se repita entre filas. D14, D17. Requisito "precedencia de overrides sobre la cascada" (spec `identity-resolution`).
- [ ] 1.2 Agregar `apply_overrides(...)` a `worky_engine/identity_resolution/overrides.py`: valida que cada `master_id` exista en `identity_crosswalk` y que cada `source_id` exista en su tabla cruda de origen; para una fila válida fija la columna del crosswalk con nivel `O`, recalcula `confidence_tier`, agrega la fila `O` a `match_audit` con la evidencia del archivo, y marca `needs_review = false` con `superseded_by` en la fila `M` sustituida. Ante cualquier fila inválida, lanza antes de escribir nada. D15, D16, D17.
- [ ] 1.3 Modificar `worky_engine/cli.py`: agregar `--overrides` (opcional, por omisión `data/identity_overrides.csv`) a los subparsers `resolve` y `build`, extender `_import_resolve_dependency`/`_import_build_dependencies` para importar `load_overrides`/`apply_overrides`, y llamarlos en `cmd_resolve` y `cmd_build` justo después de la cascada y antes de escribir, solo si el archivo existe. D15.
- [ ] 1.4 Crear `tests/test_identity_overrides.py` con fixture mínimo propio (no extiende `tests/fixtures/mini_dataset.py`). Escenarios: "override fija el master_id y sale de revisión manual", "override con master_id inexistente se rechaza", "source_id duplicado entre overrides se rechaza", "override con source_id desconocido se rechaza", "sin archivo de overrides, la salida de A0 no cambia". Prueba: `python -m pytest -q -m "not dataset" tests/test_identity_overrides.py`.
- [ ] 1.5 Cerrar PR1: correr `python -m pytest -q -m "not dataset" tests/test_identity_overrides.py`, correr `python -m pytest -q` (suite completa tal como existe en este punto), confirmar con `git status --short outputs` que ningún golden existente de A0, A1 o A3 cambió, y preparar el commit convencional (sin atribución de IA, sin coautor).

## PR2: vistas del esquema en estrella, `cmd_warehouse` y golden de `map_source_identity`

Rama: `feat/a4-pr2-warehouse-star`, base `feat/a4-pr1-identity-overrides`. Líneas de autoría estimadas: ~380, más unas 1,978 filas de golden fuera del conteo de autoría. Qué revisa primero el revisor: que `warehouse` corra en un clon limpio sin `build` previo, y que ningún archivo de `worky_engine/sql/staging/` ni `worky_engine/sql/marts/` haya cambiado. Salvaguarda si este PR se acerca a 800 líneas: mover `fact_marketing_touches` y `fact_support_tickets` al documento como parte del modelo sin materializarlas (unas 60 líneas de SQL y 40 de prueba) y recortar `test_warehouse_star.py` a los dos hechos que alimentan A5.

- [ ] 2.1 Crear `worky_engine/sql/warehouse/w1_dim_date.sql`: vista `dim_date`, un día de calendario de `MIN(signup_date)` a `dataset_asof`, `date_key` entero `YYYYMMDD`. D10.
- [ ] 2.2 Crear `worky_engine/sql/warehouse/w2_dim_csm_plan.sql`: vistas `dim_csm` y `dim_plan` sobre los valores distintos de `mart_company_core` (read-only). Requisito "vistas de dimensiones y hechos sobre los marts existentes", escenario "dimensiones derivadas sin duplicar lógica".
- [ ] 2.3 Crear `worky_engine/sql/warehouse/w3_map_source_identity.sql`: vista `map_source_identity`, `identity_crosswalk` (read-only) desdoblado más `identity_overrides`, con `link_source` (`cascade`/`override`). Requisito "identity_overrides como tabla persistida leída por el warehouse", escenario "override reflejado en map_source_identity".
- [ ] 2.4 Crear `worky_engine/sql/warehouse/w4_company_snapshot.sql`: vista de la foto de empresa con `attributes_hash` (D6), entrada del SCD2 del PR3.
- [ ] 2.5 Crear `worky_engine/sql/warehouse/w5_facts.sql`: `fact_usage_monthly`, `fact_support_tickets`, `fact_deals`, `fact_revenue_monthly` (agregado por `close_date`, D11) y `fact_marketing_touches`, cada uno unido contra la banda vigente de `dim_company` en su fecha (D13). Requisito "fact_revenue_monthly agregado por fecha de cierre" (ambos escenarios) y "vistas de dimensiones y hechos...", escenario "hechos al grano correcto".
- [ ] 2.6 Crear `worky_engine/warehouse/__init__.py` y `worky_engine/warehouse/db.py` con `open_warehouse_connection`: misma configuración de extensiones apagadas de A0, sin borrar el archivo. D2.
- [ ] 2.7 Crear `worky_engine/warehouse/runner.py` (esqueleto): `WAREHOUSE_FILES` en el orden fijo de la sección 1 del diseño, DDL para crear `identity_overrides` si no existe y materializar las filas leídas con `load_overrides`, y el punto de entrada `run_warehouse(con, ...)` que regresa un `WarehouseResult` (el algoritmo de SCD2 propio llega en el PR3). D9.
- [ ] 2.8 Crear `worky_engine/quality/warehouse_contracts.py` con `assert_map_source_identity_unique` y `assert_overrides_are_reflected`, usando el mismo `ContractViolation` de A0.
- [ ] 2.9 Modificar `worky_engine/cli.py`: agregar `_import_warehouse_dependencies`, `cmd_warehouse` (D1: mismo orden de `cmd_analyze`/`cmd_health`; D3: `--run-date` o `dataset_asof` por omisión) y su parser `--data-dir --out-dir --db-path --run-date --overrides` (D20), reutilizando `apply_overrides` del PR1. Requisito "comando warehouse sin build previo" (ambos escenarios).
- [ ] 2.10 Crear `tests/test_warehouse_star.py` con fixture mínimo propio. Escenarios: "corrida sin build previo", "falta una dependencia o una base de datos", "dimensiones derivadas sin duplicar lógica", "hechos al grano correcto", "marts y staging sin cambios", "agregación por mes de cierre", "no es una serie de mrr_mxn", "un hecho se une contra la versión vigente en su fecha", "dos hechos de fechas distintas ven CSM distinto", "tabla con las columnas del contrato", "override reflejado en map_source_identity". Prueba: `python -m pytest -q -m "not dataset" tests/test_warehouse_star.py`.
- [ ] 2.11 Generar y commitear `outputs/warehouse/map_source_identity.csv` (golden, fuera del conteo de autoría), ordenado por `source_system` y luego `source_id`.
- [ ] 2.12 Cerrar PR2: correr `python -m pytest -q -m "not dataset" tests/test_identity_overrides.py tests/test_warehouse_star.py`, correr `python -m pytest -q` (suite completa tal como existe en este punto), correr `python -m worky_engine warehouse --data-dir data/raw/sistemas` (read-only) y confirmar que ningún archivo de `worky_engine/sql/staging/` (read-only) ni `worky_engine/sql/marts/` (read-only) cambió, confirmar con `git status --short outputs` que solo aparece `outputs/warehouse/`, y preparar el commit convencional.

## PR3: SCD2 de `dim_company`, `fact_health_score_monthly` y golden de `dim_company`

Rama: `feat/a4-pr3-warehouse-scd2-health`, base `feat/a4-pr2-warehouse-star`. Líneas de autoría estimadas: ~390, más unas 650 filas de golden fuera del conteo de autoría. Qué revisa primero el revisor: que dos corridas sin cambios no escriban nada, y que un cambio de plan cierre la banda anterior con `is_current = False`. Misma salvaguarda del PR2 declarada de antemano: si este PR se acerca a 800 líneas, mover `fact_marketing_touches` y `fact_support_tickets` al documento sin materializarlas y recortar las pruebas de esos dos hechos.

- [ ] 3.1 Modificar `worky_engine/warehouse/runner.py`: agregar el DDL de `dim_company` (veinte columnas, sección 3 del diseño) y las cuatro sentencias fijas del SCD2 (reemplazo del mismo día, cierre, apertura, tipo 1), parametrizadas por la fecha de corrida. D4, D5, D6, D7, D8. Requisito "dim_company con historial SCD tipo 2".
- [ ] 3.2 Modificar `worky_engine/warehouse/runner.py`: agregar el DDL de `fact_health_score_monthly` y el paso que llama `run_health(con)` de A3 en proceso, con borrado e inserción para la misma `run_date` (idempotente). D12. Requisito "fact_health_score_monthly como snapshot por fecha de corrida".
- [ ] 3.3 Modificar `worky_engine/cli.py`: validar que `--run-date` sea ISO y nunca anterior al `effective_from` máximo de las filas vigentes, terminando con código 1 en caso contrario.
- [ ] 3.4 Modificar `worky_engine/quality/warehouse_contracts.py`: agregar `assert_dim_company_one_current_per_master`, `assert_dim_company_sk_unique`, `assert_dim_company_bands_are_contiguous`, `assert_dim_company_tracked_attributes_change`, `assert_health_snapshot_unique` y `assert_warehouse_row_order`.
- [ ] 3.5 Crear `tests/test_warehouse_scd2.py` con fixture mínimo propio. Escenarios: "el archivo sobrevive a la segunda corrida", "primera corrida abre una fila vigente por empresa", "corrida sin cambios no agrega filas", "un cambio de plan cierra la fila anterior y abre una nueva", "una empresa que desaparece de las fuentes conserva su fila", "cada corrida de health agrega un snapshot", "snapshot idempotente para la misma fecha", más los casos de tipo 1 y reemplazo del mismo día de la sección 3 del diseño. Prueba: `python -m pytest -q -m "not dataset" tests/test_warehouse_scd2.py`.
- [ ] 3.6 Crear `tests/test_warehouse_idempotency.py`, marca `dataset`. Escenarios: "dos corridas sin cambios dan resultados idénticos", "las llaves no dependen del orden de ejecución", "goldens generados en cada corrida", "goldens de A0, A1 y A3 sin cambio", "warehouse no depende de esas salidas". Verifica que `--out-dir` quede con exactamente dos archivos y que el sha256 de los dieciocho archivos ya versionados de `outputs/` (read-only) sea igual antes y después. Prueba: `python -m pytest -q -m dataset tests/test_warehouse_idempotency.py`.
- [ ] 3.7 Verificar que `openspec/changes/a4-warehouse-model/design.md` (read-only) documenta la excepción a la decisión D6 de A0, junto a la razón (decisión D2 de este diseño), satisfaciendo por inspección el escenario "excepción documentada a D6" sin escribir código.
- [ ] 3.8 Generar y commitear `outputs/warehouse/dim_company.csv` (golden, fuera del conteo de autoría), ordenado por `master_id` y luego `effective_from`.
- [ ] 3.9 Cerrar PR3: correr `python -m pytest -q -m "not dataset" tests/test_identity_overrides.py tests/test_warehouse_star.py tests/test_warehouse_scd2.py`, correr `python -m pytest -q -m dataset tests/test_warehouse_idempotency.py`, correr `python -m pytest -q` (suite completa con el dataset real), correr `python -m worky_engine warehouse --data-dir data/raw/sistemas` (read-only) dos veces seguidas y confirmar que los dos goldens salen idénticos byte a byte, confirmar que los dieciocho archivos existentes de `outputs/` (read-only) no cambiaron, y preparar el commit convencional.

## PR4: documento del modelo, ERD 07 y rutas rápidas

Rama: `feat/a4-pr4-warehouse-docs`, base `feat/a4-pr3-warehouse-scd2-health`. Líneas de autoría estimadas: ~200. Qué revisa primero el revisor: que el documento responda las cuatro preguntas de A4 y diga sin rodeos que el historial es hacia adelante.

- [ ] 4.1 Crear `docs/data-model/01-warehouse-model.md`: responde las cuatro preguntas de A4 (hechos y dimensiones, dónde viven las llaves de reconciliación, cómo se guarda el historial, cómo no se repite el cruce manual de A0), declara que el historial se captura hacia adelante y sin reconstrucción hacia atrás, documenta el ejemplo de las seis columnas de `identity_overrides.csv` (D14) y el contrato exacto de la marca de agua incremental (D18: qué `source_id` cuenta como "ya visto" y cuáles se reprocesan). Requisito "contrato de la marca de agua incremental", escenario "contrato documentado".
- [ ] 4.2 Crear `docs/diagrams/src/07-modelo-estrella-warehouse.mmd` y `docs/diagrams/src/07-modelo-estrella-warehouse.erd.json`: extiende el diagrama 03 (read-only) con el esquema en estrella (dimensiones, hechos e `identity_overrides`), tipo `erd` según D21.
- [ ] 4.3 Entregar `docs/diagrams/07-modelo-estrella-warehouse.html` con `archify` (`node bin/archify.mjs validate erd docs/diagrams/src/07-modelo-estrella-warehouse.erd.json --json` y luego `deliver erd ... --json`), confirmando `grep -c "https://"` en 0.
- [ ] 4.4 Modificar `docs/diagrams/README.md`: agregar la fila 07 a la tabla del índice, con `docs/data-model/01-warehouse-model.md` como documento de origen.
- [ ] 4.5 Modificar `README.md`: agregar la corrida de `warehouse` a "Ruta rápida" y una fila de `outputs/warehouse/` en "Qué produce".
- [ ] 4.6 Cerrar PR4: correr `python -m pytest -q` (suite completa con el dataset real), correr `grep -c "https://" docs/diagrams/07-modelo-estrella-warehouse.html` confirmando 0, confirmar con `git status --short outputs` que no hay cambios fuera de `outputs/warehouse/` en las cuatro rebanadas combinadas, y preparar el commit convencional.

## Marca de agua incremental: no es una tarea

La marca de agua incremental (D18) queda documentada como contrato en la tarea 4.1, no implementada en este corte. Sería una quinta rebanada opcional, solo si las rebanadas 1 a 3 cierran dentro de su presupuesto y sobra tiempo de calendario. El escenario "vínculos existentes sobreviven si se implementa" es condicional (SHOULD, "si se implementa") y no aplica mientras la marca de agua no se implemente.
