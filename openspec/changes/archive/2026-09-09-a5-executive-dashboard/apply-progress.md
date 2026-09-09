# Apply progress: a5-executive-dashboard (PR1: wireframe, mockup y prueba de anclaje)

**Mode**: Standard (strict_tdd: false), pero fase 1 se implementó como RED antes de escribir los documentos (tasks 1.1-1.4), siguiendo la fase 1/fase 2 que pide el diseño.

## Work Unit Evidence

| Evidencia | Valor |
|---|---|
| Comando de prueba enfocado y resultado exacto | `python -m pytest -q tests/test_dashboard_figures.py` → `18 passed` |
| Comando/escenario de arnés en tiempo real y resultado exacto | `python -m pytest -q -m "not dataset"` → `229 passed, 41 deselected in 561.72s`; apertura del mockup validada con `html.parser` (0 errores de parseo, `<!doctype html>` presente, 0 etiquetas `<script`) como sustituto de abrir con doble clic en un navegador real, no disponible en este entorno de shell |
| Límite de reversión | Eliminar `docs/dashboard/01-dashboard-vp-cs.md`, `docs/dashboard/02-mockup-vp-cs.html`, `tests/test_dashboard_figures.py` y revertir el renglón agregado en `README.md`; ningún otro archivo cambió |

## TDD Cycle Evidence (fase 1 del diseño, tasks 1.1-1.4)

| Fase | Acción | Resultado |
|---|---|---|
| RED | `tests/test_dashboard_figures.py` creado con las fases 1 y 2; corrido antes de escribir los documentos | `12 passed` (fase 1, cifras contra los CSV), `6 errors` (fase 2, `FileNotFoundError` porque los documentos no existían) |
| GREEN | `docs/dashboard/01-dashboard-vp-cs.md` y `docs/dashboard/02-mockup-vp-cs.html` escritos con las cifras literales de D11 | `18 passed` |
| REFACTOR | Ajuste único: se agregó la línea "Total por tramo" al mockup porque la fase 2 detectó que faltaban los tres conteos de tramo (131/250/180) como texto literal | `18 passed` se mantiene |

## Completed Tasks

Las 27 tareas de `tasks.md` quedan marcadas `[x]`:

- [x] 1.1-1.4: prueba `tests/test_dashboard_figures.py` (fase 1 y 2), corrida RED confirmada antes de escribir los documentos.
- [x] 2.1-2.11: `docs/dashboard/01-dashboard-vp-cs.md`, ocho secciones, tabla de lenguaje llano y apéndice con el snippet de pandas.
- [x] 3.1-3.9: `docs/dashboard/02-mockup-vp-cs.html`, autocontenido, siete widgets, verificación manual de contraste y de que ningún dato se comunica solo por color.
- [x] 4.1-4.3: renglón del README, corrida verde de ambas pruebas, `grep` de referencias externas en 0 y `git status` limpio fuera de los archivos de este cambio.

## Files Changed

| Archivo | Acción | Qué se hizo |
|---|---|---|
| `tests/test_dashboard_figures.py` | Creado | 231 líneas. Dos clases: `TestFase1CifrasDesdeLosGoldens` (11 pruebas que recalculan desde los dos CSV) y `TestFase2CifrasEnLosDocumentos` (7 pruebas que leen los dos documentos como texto UTF-8 y exigen las cadenas literales de D11, los 7 conteos por CSM y los 3 conteos de tramo). Sin marca `@pytest.mark.dataset` (D14): solo lee `outputs/health/health_scores.csv` y `outputs/master_dataset.csv`, ya versionados |
| `docs/dashboard/01-dashboard-vp-cs.md` | Creado | 209 líneas. Ocho secciones (D1), tabla de seis columnas por sección (D2), tabla de lenguaje llano y apéndice con el snippet de pandas documentado (D3) |
| `docs/dashboard/02-mockup-vp-cs.html` | Creado | 242 líneas, 24,989 bytes. Un solo archivo, sin `<script>`, `<link>`, `@import` ni referencias `http(s)://` (verificado en 0 con `grep`), variables CSS con `prefers-color-scheme` para modo claro/oscuro y bloque `@media print`, barras `<rect>` de SVG en línea |
| `README.md` | Modificado | +1 línea en la tabla "Dónde está cada cosa" con la liga a `docs/dashboard/` |
| `openspec/changes/a5-executive-dashboard/tasks.md` | Modificado | Las 27 tareas marcadas `[x]` |

## Deviations from Design

Ninguna deviación material. Un solo ajuste durante GREEN: el mockup no traía inicialmente las tres cadenas literales de conteo por tramo ("131 cuentas", "250 cuentas", "180 cuentas") como texto aparte de la matriz por celda; se agregó una línea de resumen bajo la matriz de tramo por nivel de riesgo para satisfacer la fase 2 de la prueba sin cambiar ninguna cifra.

## Issues Found

Ninguno. Todas las cifras recalculadas con pandas coincidieron exactamente con las citadas en el ADR-007 y en el diseño (78 cuentas, $2,216,115, 13.7 %, $16,223,225.50, 145/78/67, 65/22/43, tramos 131/250/180, conteo por CSM y HS-100065/HS-100507).

## Measured Authored Line Count

| Archivo | Líneas |
|---|---|
| `tests/test_dashboard_figures.py` | 231 |
| `docs/dashboard/01-dashboard-vp-cs.md` | 209 |
| `docs/dashboard/02-mockup-vp-cs.html` | 242 |
| `README.md` (renglón agregado) | 1 |
| **Total autoría** | **683** |

Dentro del presupuesto de 800 líneas por PR de este repositorio. No fue necesario usar la palanca de reducción (cola del mockup de 20 a 10 filas).

## Workload / PR Boundary

- Mode: single PR (`auto-chain`, `stacked-to-main`, sin decisión pendiente: `Decision needed before apply: No`)
- Unidad de trabajo: PR1 completa (única unidad definida en `tasks.md`)
- Boundary: empieza en la prueba RED (1.1) y termina en la confirmación de `git status` limpio (4.3); las 27 tareas quedan cerradas en este mismo lote
- Estimated review budget impact: 683 líneas de autoría contra el presupuesto de 800; el pronóstico original estimaba 630-730, dentro de rango

## Conventional Commit Message Prepared (no staged, no committed)

```
docs(dashboard): add A5 executive dashboard wireframe, self-contained mockup and figures-anchoring test

Add docs/dashboard/01-dashboard-vp-cs.md (eight-section wireframe), docs/dashboard/02-mockup-vp-cs.html
(self-contained HTML mockup with the real dataset figures) and tests/test_dashboard_figures.py (anchors
every cited figure to outputs/health/health_scores.csv and outputs/master_dataset.csv). Adds one row to
the README "Donde esta cada cosa" table. Implements ADR-007: the CSM priority queue filters
flagged_15=True AND churned=False (78 accounts), ordered by mrr_mxn descending, so a $45,000 account
never weighs the same as a $3,000 one at the same risk level.
```

## Status

27/27 tasks complete. Ready for verify.
