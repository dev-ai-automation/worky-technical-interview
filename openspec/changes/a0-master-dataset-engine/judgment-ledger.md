# Judgment Day: ledger congelado del motor A0

- Blanco: commit `92b5bb85f978a7bcc4fc445eff6b9f69d620a1d0` (tree `cbf97ed2`), worktree detached de solo lectura
- target_identity: `sha256:43fd96db24709f5efc8df502f698fe0ba585a93ae8210636a016fdd717bf436d`
- Alcance: `worky_engine/**`, `tests/**`, `pyproject.toml` (59 archivos, 4,855 líneas); referencias: design.md, specs, ADR-001/002/003, outputs/
- Jueces: `jd-judge-a` y `jd-judge-b` (modelo sonnet), prompt idéntico, sin refutador
- Skill resolution: none (el registro no tiene skill de Python, SQL ni datos)
- Ronda: 1 (sin corrección todavía)

## Verificación del orquestador sobre el dataset real

| Comprobación | Resultado |
|---|---|
| Deals cuyo `hubspot_id` apunta a un clon HS-9000xx | 0 de 997 |
| Accounts de product_db con `hubspot_id` repetido | 0 de 650 (54 sin `hubspot_id`) |
| `master_id` repetido dentro de una misma fuente en `match_audit.csv` | 0 en crm_hubspot, product_db y vitally |

Los dos hallazgos compartidos son reales en el código y no cambian ninguna salida con este dataset.

## Hallazgos

| ID | Ubicación | Juez A | Juez B | Estado | Resumen |
|---|---|---|---|---|---|
| JD-01 | `worky_engine/identity_resolution/cascade.py:137-151` | WARNING | CRITICAL | confirmado por ambos, severidad en desacuerdo | Si dos accounts o dos customers resuelven al mismo `master_id`, el crosswalk conserva solo el último (`account_id`/`vitally_id` se sobrescriben sin aviso ni marca en `match_audit`). No hay guardia equivalente a `assert_unique_master_ids` en esta dirección. Dormido en este dataset. |
| JD-02 | `identity_resolution/quarantine.py:77-100`, `cascade.py:80-81`, `sql/staging/stg_deals.sql:20`, `sql/marts/mart_deal_normalized.sql:11` | WARNING | CRITICAL | confirmado por ambos, severidad en desacuerdo | Un deal cuyo `hubspot_id` apunta a un clon en cuarentena no se marca huérfano (el conjunto de ids se arma antes de deduplicar) ni se remapea al sobreviviente como pide design.md 3.8 caso 2; `mart_deal_normalized` lo descarta por `master_id IS NOT NULL` y desaparece sin rastro en cuarentena, excepciones ni cobertura. Dormido en este dataset (0 deals). |
| JD-03 | `cascade.py:108,145-151,205-232` | no reportado | WARNING | sospecha (un solo juez) | `vetoed_ids` solo marca la fila S de la empresa; `_resolve_customer` no saca al candidato vetado del bloque de dominio como describe design.md 3.4. Dormido: T1 = 650 exactos. |
| JD-04 | `worky_engine/cli.py:90-91` | no reportado | WARNING | sospecha (un solo juez) | `ZipFile.extractall` sin `filter="data"`: un zip con rutas `..` podría escribir fuera del directorio de extracción (zip-slip). Solo aplica al zip local del caso. |
| JD-05 | `sql/marts/mart_usage.sql:44-64`, `quality/contracts.py:175-185` | WARNING | no reportado | sospecha (un solo juez) | La forma cerrada del EWMA pondera por distancia calendario al `trend_asof_month`; equivale a `ewm(adjust=True)` solo si la serie llega hasta ese mes. El contrato revisa huecos internos pero no que la serie alcance el mes de corte. ADR-001 documenta que el invariante se cumple en este dataset. |
| JD-06 | `identity_resolution/keys.py:21-31`, `cascade.py:378-379` | no reportado | SUGGESTION | info | design.md 3.6 pide comparar `ruleset_version` antes de reutilizar un `master_id` del crosswalk; el código reutiliza sin comparar. Inofensivo mientras la versión sea la constante 1.0.0. |

## Conteos

- Confirmados por ambos: 2 (JD-01, JD-02), con desacuerdo de severidad (A: WARNING, B: CRITICAL)
- Sospechas de un solo juez: 3 (JD-03, JD-04, JD-05)
- Info: 1 (JD-06)
- Contradicciones sobre la existencia de un defecto: 0

## Decisión pendiente

La regla de Judgment Day corrige solo hallazgos severos confirmados por ambos jueces y exige preguntar antes de la ronda 1. Los jueces coinciden en que JD-01 y JD-02 existen, pero no en que sean severos; esa diferencia se escala a decisión humana.
