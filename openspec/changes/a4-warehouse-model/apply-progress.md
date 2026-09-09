# Apply progress: `a4-warehouse-model`

**Batch**: PR1, tareas 1.1 a 1.5 (precedencia de `identity_overrides` en `resolve` y `build`)
**Modo**: Standard (strict_tdd: false)
**Rama**: `feat/a4-pr1-identity-overrides`, base `main`

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

## Remaining Tasks

- [ ] 2.1 a 2.12 (PR2: vistas del esquema en estrella, `cmd_warehouse`, golden de `map_source_identity`)
- [ ] 3.1 a 3.9 (PR3: SCD2 de `dim_company`, `fact_health_score_monthly`, golden de `dim_company`)
- [ ] 4.1 a 4.6 (PR4: documento del modelo, ERD 07, rutas rápidas)

## Workload / PR Boundary

- Mode: stacked PR slice (`auto-chain`, `stacked-to-main`)
- Current work unit: Unit 1 — precedencia de `identity_overrides` sobre la cascada en `resolve` y `build`
- Boundary: arranca en `main` (sin `worky_engine/identity_resolution/overrides.py` ni `--overrides` en el CLI) y termina con las tareas 1.1 a 1.5 completas, PR1 listo para abrir contra `main`
- Estimated review budget impact: 529 líneas de autoría, dentro del presupuesto de 800 por PR; el revisor ve primero que sin archivo de overrides las salidas de A0 quedan idénticas y que una fila inválida detiene la corrida antes de escribir

## Prepared Conventional Commit Message

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

## Status

5/32 tasks complete (PR1 done, PR2 to PR4 pending). Ready for next batch (PR2).
