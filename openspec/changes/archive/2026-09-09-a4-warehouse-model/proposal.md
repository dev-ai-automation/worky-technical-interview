# Propuesta: esquema en estrella ejecutable para el warehouse de A4

## Intención

A4 pide el modelo de warehouse: hechos y dimensiones, dónde viven las llaves de reconciliación, cómo se guarda el historial y cómo no repetir el cruce manual de A0. El ADR-006 ya lo fijó y falta el código: hoy no hay esquema en estrella, ninguna fila tiene vigencia, y una decisión humana sobre un registro en revisión manual se pierde en el siguiente rebuild.

Éxito: correr `warehouse` dos veces con un cambio de plan en medio y ver la fila anterior cerrada y la nueva vigente, sin tocar ningún mart ni golden de A0, A1 y A3; y correr `build` con una fila de override y ver ese registro fuera de la cola de revisión manual.

## Alcance

### Dentro

- Comando `python -m worky_engine warehouse` sobre un `.duckdb` persistido en `.build/`, ignorado por Git.
- Vistas sobre los marts existentes: `dim_date`, `dim_csm`, `dim_plan`, `map_source_identity` y los cinco hechos del ADR-006, con `fact_revenue_monthly` agregado por `close_date`.
- Tablas persistidas: `dim_company` con SCD tipo 2 sobre `plan` y `csm_owner`, `identity_overrides` y `fact_health_score_monthly` por fecha de corrida. Llaves surrogate por hash determinista.
- Precedencia de overrides en la resolución de identidad: `resolve` y `build` aplican `identity_overrides` después de la cascada, en un archivo nuevo dentro de `identity_resolution` y una llamada desde el CLI. Sin archivo de overrides, la salida es idéntica byte a byte.
- `docs/data-model/01-warehouse-model.md`, ERD con `archify`, y el contrato de la marca de agua documentado, implementado solo si sobra presupuesto.
- Goldens versionados: solo `outputs/warehouse/dim_company.csv` y `map_source_identity.csv`.

### Fuera

- Modificar archivos existentes de staging, marts o `identity_resolution`, o cualquier golden de A0, A1 y A3.
- Reconstruir historial hacia atrás: ninguna fuente lo trae.
- Data Vault ligero y el tablero de A5, documentados como trabajo posterior.
- Leer `fact_revenue_monthly` como serie de `mrr_mxn` (ADR-002).

## Capacidades

### Nuevas

- `warehouse-model`: vistas de hechos y dimensiones, `dim_company` con SCD2, `identity_overrides` como tabla y su lectura desde el warehouse, `fact_health_score_monthly`, el comando `warehouse`, la persistencia del `.duckdb`, el determinismo de llaves y el contrato de la marca de agua.

### Modificadas

- `identity-resolution`: requisito agregado de precedencia de overrides. Una fila de `identity_overrides` fija el `master_id` de un registro de origen después de la cascada, lo saca de la revisión manual y deja evidencia en `match_audit`; una fila que apunta a un `master_id` inexistente, un `source_id` repetido o un `source_id` que no existe en su tabla de origen detiene la corrida con un error visible que nombra la fila y el motivo, sin escribir ninguna salida (`exceptions_log` es una vista de `mart_mrr.sql`, que este cambio no toca). Los requisitos existentes sobre cascada, revisión manual, crosswalk y `match_audit` siguen vigentes; sin archivo de overrides, sus goldens no cambian.

## Enfoque

`worky_engine/sql/warehouse/` define las vistas sobre los marts y el DDL de las tres tablas persistidas. `worky_engine/warehouse/` corre el comando, resuelve identidad en memoria con la misma cascada y los mismos overrides que `build`, cierra y abre las bandas SCD2 y llena `identity_overrides` y `map_source_identity`. `worky_engine/identity_resolution/overrides.py` (archivo nuevo) aplica las filas de override sobre el crosswalk y la auditoría; `cli.py` lo llama en `resolve` y `build` cuando el archivo existe. Cada hecho histórico se une contra la fila de `dim_company` vigente en su fecha (ADR-003).

## Áreas afectadas

| Área | Impacto | Descripción |
|---|---|---|
| `worky_engine/sql/warehouse/`, `worky_engine/warehouse/`, `tests/test_warehouse_*.py` | Nueva | DDL, corredor, SCD2, lectura de overrides y pruebas |
| `worky_engine/identity_resolution/overrides.py`, `tests/test_identity_overrides.py` | Nueva | Precedencia de overrides después de la cascada, validación y evidencia en `match_audit` |
| `docs/data-model/01-warehouse-model.md`, `docs/diagrams/07-*.html` | Nueva | Documento del caso y ERD |
| `worky_engine/cli.py`, `README.md`, `docs/diagrams/README.md` | Modificado | Subcomando `warehouse`, llamada a overrides en `resolve` y `build`, cómo correrlo |
| Archivos existentes de marts, `identity_resolution` y goldens de A0, A1 y A3 | Sin cambio | Verificado por prueba |

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Un override apunta a un `master_id` que no existe o repite un `source_id` | Media | Validación al cargar: la corrida se detiene con un error en `stderr` que nombra la fila y el motivo, código de salida 1 y ninguna escritura parcial |
| No hay historial real que mostrar | Alta | La prueba de dos corridas, declarada sintética |
| El `.duckdb` persistido contradice la decisión D6 de A0 | Media | Excepción documentada en el diseño |
| Rebasar las 800 líneas de autoría | Media | La marca de agua va al final; PRs encadenados |

## Plan de reversión

`git revert` del merge de cada PR. Todo es archivo nuevo más una rama del parser y una llamada aditiva en `resolve` y `build` que solo actúa si existe el archivo de overrides, así que `build`, `analyze` y `health` quedan intactos. Se borran a mano `.build/warehouse.duckdb` y `outputs/warehouse/`.

## Dependencias

DuckDB y pandas, ya fijados en `pyproject.toml`. Node v24 solo para el ERD. ADR-001, ADR-002, ADR-003 y ADR-006.

## Criterios de éxito

- [ ] `warehouse` corre sin `build` previo y termina en 0.
- [ ] Dos corridas sin cambios dan goldens idénticos byte a byte.
- [ ] Un cambio de plan cierra la fila anterior (`is_current = false`) y abre la nueva.
- [ ] Una fila de `identity_overrides` fija el `master_id` en el crosswalk, saca el registro de la cola manual de `match_audit` en `build` y se refleja en `map_source_identity`.
- [ ] Sin archivo de overrides, los goldens de A0, A1 y A3 quedan idénticos, verificado por prueba.
- [ ] El documento y el ERD responden las cuatro preguntas de A4.
