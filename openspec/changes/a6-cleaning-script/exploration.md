# Exploración: a6-cleaning-script (script de limpieza automática de companies.csv)

## Texto literal de la sección A6 del caso

"A6. Automatización. Escribe un script (Python real, no pseudocódigo) que tome companies.csv y detecte automáticamente: nulos en mrr, cuentas en currency = USD, y fechas en formato DD/MM/YYYY mezcladas con YYYY-MM-DD, y que las normalice, dejando un log de cuántos registros de cada tipo corrigió." Evaluación "Plus valioso" (opcional, menor prioridad que A0 a A4, ya archivados y corriendo).

## Estado actual

`data/raw/sistemas/crm_hubspot__companies.csv`, 678 filas. Encabezado confirmado: `hubspot_id,name,domain,segment,industry,mrr,currency,signup_date,csm_owner,plan,state,churn_date`.

Conteos verificados con grep directo sobre el CSV (no solo el perfil de docs):

- `mrr` nulo: 56 filas (patrón `,,(MXN|USD),`). De esas, 28 corresponden a los clones `HS-9000\d\d` (regex confirmada, 28 coincidencias) y 28 a empresas reales `HS-1xxxxx`.
- `currency = USD`: 22 filas (patrón `,USD,`).
- `signup_date` en DD/MM/YYYY: 31 filas (patrón `,\d{2}/\d{2}/\d{4},`).
- `churn_date` (última columna): 0 filas en DD/MM/YYYY (patrón de fin de línea, 0 coincidencias). Solo `signup_date` mezcla formatos; `churn_date` no necesita normalización de formato.

Piezas reutilizables ya existentes:

- `worky_engine/normalization/dates.py::normalize_date` acepta ISO o DD/MM/YYYY, valida que la terna sea una fecha calendario real, y devuelve `None` si no calza con ninguno de los dos formatos o si es inválida. Ya se usa en `stg_companies.sql`, `cascade.py` y `assemble.py`: la normalización de fecha ya corre río arriba en A0, lo que confirma la fila de A6 en el ADR-001 ("la normalización de fechas se mueve río arriba, hacia A0, como paso obligatorio").
- `worky_engine/normalization/currency.py::to_mxn(amount, currency)` con tasa fija 18.5 (ADR-002), devuelve `ConvertedAmount(mxn, original_amount, original_currency)`, lanza `ValueError` para monedas no soportadas.
- `worky_engine/cli.py` establece el patrón: subcomandos con importación diferida (para capturar `ImportError` como mensaje claro), `_resolve_data_dir` (extrae el zip si hace falta), `_reconfigure_streams_to_utf8` (necesario en Windows), `write_csv`/`write_markdown` deterministas (UTF-8 sin BOM, `\n`, sin índice, `na_rep=""`), y códigos de salida consistentes (0 éxito, 1 violación de contrato o validación de negocio, 2 dependencia o archivo faltante).
- `tests/test_normalization.py` ya cubre `normalize_date`/`to_mxn` por tabla de casos parametrizados e idempotencia por registro; `tests/fixtures/mini_dataset.py` es el patrón de fixture sintética a reusar.

Hallazgo que cambia el alcance del caso: el ADR-002 (ya aceptado) declara su alcance como "A0, A1.1, A5, A6" y en su tabla "Qué cambia en las secciones siguientes" dice literal: "A6 (script de limpieza): Registra conteos por tipo de corrección: cuántos nulos se imputaron, cuántos montos en USD se convirtieron, cuántas fechas se normalizaron." La Adenda 1 (2026-09-08) agrega que "el script de A6 debe registrar cada deal anualizado como una corrección más en su log." Es decir, este ADR ya comprometió a A6 a imputar mrr desde deals, no solo a marcarlo como nulo. La regla de imputación (monto único entre los deals de la empresa, anualización cuando un monto es exactamente 12x otro, confianza `high`/`medium` según haya un deal `closedwon`) solo existe hoy como SQL en `worky_engine/sql/marts/mart_mrr.sql`, no como función Python reutilizable.

Hallazgo que hace viable cumplir el ADR-002 sin duplicar identity_resolution: `deals.csv` liga a `companies.csv` por `hubspot_id` crudo, una FK directa que no depende del crosswalk. Un script standalone puede reproducir la regla del ADR-002 en pandas puro leyendo `companies.csv` + `deals.csv`, sin importar el módulo de identidad ni el ensamblaje del dataset maestro.

## Áreas afectadas

- `data/raw/sistemas/crm_hubspot__companies.csv`, `crm_hubspot__deals.csv` (esta segunda solo si se decide cumplir el ADR-002): entradas del script.
- `worky_engine/normalization/dates.py`, `currency.py`: funciones puras a importar, sin modificar.
- `worky_engine/cli.py`: patrón de subcomando (`resolve`, `build`, `analyze`, `health`, `warehouse`) que un subcomando `clean` replicaría.
- `worky_engine/sql/marts/mart_mrr.sql`: única fuente de verdad de la regla de imputación del ADR-002, a portar (no a ejecutar vía DuckDB) si se elige imputar.
- `docs/decisions/ADR-002-mrr-imputation-and-normalization.md`, `ADR-001-identity-resolution-scorecard.md`: compromisos ya aceptados que A6 debe cumplir o documentar explícitamente por qué no.
- `worky_engine/writers.py`: `write_csv`/`write_markdown` deterministas a reusar para el log.
- `tests/test_normalization.py`, `tests/fixtures/mini_dataset.py`: patrón de pruebas a extender.
- Ningún archivo de `outputs/` ni golden de A0/A1/A3/A4 se toca.

## Opciones

1. **Script standalone puro**: `scripts/clean_companies.py` con su propio `argparse`, importa `worky_engine.normalization` pero no toca `cli.py`.
   - A favor: calza literal con "escribe un script"; cero acoplamiento con el CLI existente; defensa en vivo trivial (un archivo, un comando).
   - En contra: rompe el patrón de subcomandos que siguen A0 a A4; duplica boilerplate ya resuelto en `cli.py` (UTF-8, `_resolve_data_dir`, exit codes).
   - Esfuerzo: ~300 a 350 líneas de autoría (código + pruebas).

2. **Subcomando `clean` en `cli.py` + wrapper delgado** (recomendada): `cmd_clean` con el mismo patrón que `resolve`/`health` (importación diferida, `_resolve_data_dir`, `write_csv`), más `scripts/clean_companies.py` que solo invoca `main(["clean", ...])`.
   - A favor: consistente con el resto del motor (mismo estilo de contratos, exit codes, UTF-8); el revisor igual corre un archivo literal para la defensa; reusa infraestructura ya probada.
   - En contra: algo más de código que la opción 1; toca `cli.py`, un archivo compartido con los demás comandos (riesgo bajo, es aditivo).
   - Esfuerzo: ~350 a 450 líneas de autoría.

3. **Solo subcomando, sin wrapper**: igual a la opción 2 sin el archivo en `scripts/`.
   - A favor: menos código.
   - En contra: no entrega literalmente "un script" para la defensa en vivo; el caso pide explícitamente Python real ejecutable como script, y solo un subcomando dentro de un CLI más grande diluye esa lectura literal.
   - Esfuerzo: ~250 a 300 líneas de autoría.

## Recomendación

Opción 2: subcomando `clean` siguiendo el patrón ya establecido por `resolve`/`build`/`analyze`/`health`/`warehouse`, más un wrapper delgado `scripts/clean_companies.py` que solo llama a ese subcomando. Esto mantiene la consistencia arquitectónica del motor (mismo manejo de UTF-8, exit codes, contratos y escritura determinista) sin sacrificar la lectura literal del caso ("escribe un script"), porque la defensa en vivo sigue siendo correr un único archivo.

## Decisiones de producto pendientes

1. **mrr nulo: marcar o imputar.** (a) alcance literal, solo `companies.csv`, marca los 28 nulos reales como excepción sin inventar un valor; (b) cumplir el ADR-002, leyendo también `deals.csv` (join directo por `hubspot_id`, sin crosswalk), replicando en pandas la regla de monto único + anualización 12x, excluyendo los 28 clones `HS-9000xx` por regex antes de contar. Consecuencia: (b) agrega una segunda entrada no mencionada en el texto literal del caso y ~40 a 60 líneas más, pero cumple una promesa ya aceptada en el ADR-002 (que hoy queda sin código que la respalde); (a) es más simple pero deja esa promesa documentada sin cumplir. Recomiendo (b), dejando explícito en el docstring del comando que es una réplica controlada de la regla en `mart_mrr.sql`, citando el ADR.
2. **Nombres de columna para USD a MXN.** Espejar el patrón ya usado en el motor (`mrr_mxn`, `mrr_original`, `currency_original`) en vez de inventar nombres nuevos para el script. Recomiendo espejar, para que cualquiera que ya conozca el dataset maestro reconozca las columnas.
3. **Detalle por fila en el log.** El caso solo pide conteos por tipo de corrección; agregar un `cleaning_exceptions.csv` a grano fila (mismo shape que `exceptions_log.csv` del motor: `exception_id`, `exception_code`, `source_id`, `field_name`, `original_value`, `applied_value`) es valor extra de bajo costo y mejora auditabilidad. Recomiendo incluirlo si el presupuesto de 400 líneas por PR lo permite después de cubrir la detección y normalización base.
4. **Persistencia como golden.** Si `outputs/clean/*` (CSV limpio + log) se versiona como golden, igual que `outputs/analysis`, `outputs/health` y `outputs/warehouse`. Recomiendo que sí: los conteos son deterministas contra el snapshot fijo del dataset del caso.

## Riesgos

- Ambigüedad DD/MM contra MM/DD: `normalize_date` ya rechaza fechas calendario inválidas (por ejemplo `31/02/2023`); con el dataset real no hay evidencia de colisión real entre DD/MM y MM/DD en las 31 filas mezcladas.
- NaN "truthy" de pandas (lección ya documentada en A4): leer el CSV con `keep_default_na=False, na_values=[""]`, igual que `_load_existing_crosswalk` en `cli.py`, para no dejar que pandas infiera nulos donde no los hay.
- UTF-8 en Windows: reusar `_reconfigure_streams_to_utf8` y `write_csv` tal cual, mismo riesgo ya conocido de A0.
- Presupuesto de PR (400 líneas de foco de revisión, 800 de autoría): la opción recomendada con imputación del ADR-002 se acerca al primer límite; vigilar alcance para no necesitar una segunda PR encadenada para un cambio que el caso marca como opcional.
- Duplicar la regla de `mart_mrr.sql` en pandas crea dos lugares que deben coincidir en el resultado; solo se sostiene por disciplina (una prueba que compare ambos caminos sobre el dataset real ayudaría, pero es alcance adicional a decidir).

## Listo para propuesta

Sí, una vez que el usuario confirme las cuatro decisiones de producto de arriba, en especial la decisión 1 (marcar contra imputar mrr nulo), que determina si el script necesita una segunda entrada (`deals.csv`) y cuánto código adicional entra al presupuesto de la PR.

## Referencias

`data/raw/sistemas/crm_hubspot__companies.csv`, `crm_hubspot__deals.csv`, `docs/data-model/00-as-is-schema-profile.md`, `docs/decisions/ADR-001` (fila de A6), `ADR-002` (imputación, tasa 18.5, adenda 1), `worky_engine/normalization/{dates,currency}.py`, `worky_engine/sql/marts/mart_mrr.sql`, `worky_engine/cli.py`, `worky_engine/writers.py`, `tests/test_normalization.py`, `docs/research/01-bi-revops-data-architecture.md` (secciones 1 y 6), exploración archivada de a0 (recomendación de A6 como cambio pequeño que importa `worky_engine.normalization`).
