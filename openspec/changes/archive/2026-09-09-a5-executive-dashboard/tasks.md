# Tareas: tablero ejecutivo de riesgo real para el VP de Customer Success (`a5-executive-dashboard`)

A5 solo lee. Ningún archivo bajo `worky_engine/` o `outputs/` cambia; las tareas solo crean `docs/dashboard/01-dashboard-vp-cs.md`, `docs/dashboard/02-mockup-vp-cs.html`, `tests/test_dashboard_figures.py` y agregan una fila a la tabla "Dónde está cada cosa" de `README.md`. Todo se implementa en un worktree aislado mientras A6 corre en el árbol principal, rama `feat/a5-pr1-dashboard` sobre `main`.

## Pronóstico de carga de revisión (Review Workload Forecast)

| Field | Value |
|---|---|
| Estimated changed lines | 630 a 730 líneas de autoría (unas 230 de Markdown, unas 100 de prueba, un renglón de README, entre 300 y 400 de HTML escrito a mano) |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Un solo PR |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Presupuesto por PR de este repositorio: 800 líneas de autoría. La estimación de 630 a 730 ya se acerca a ese tope y este repositorio suele medir el doble de lo estimado (A0 midió `cascade.py` en 466 contra 120, A3 midió su PR1 en 991 antes de recortarlo a 798). Por eso el riesgo queda en Medium. La palanca de reducción ya está documentada en el diseño: si el PR se acerca al presupuesto, la cola de prioridad del mockup baja de 20 a 10 renglones sin tocar ninguna cifra agregada.

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: stacked-to-main
400-line budget risk: Medium
```

Con `auto-chain`, el orquestador procede directo con este PR único.

### Unidad de trabajo sugerida

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|---|---|---|---|---|---|
| 1 | Wireframe, mockup y prueba de anclaje del tablero del VP de CS | PR 1 | `python -m pytest -q tests/test_dashboard_figures.py` | Abrir `docs/dashboard/02-mockup-vp-cs.html` con doble clic, sin red; `python -m pytest -q -m "not dataset"` debe seguir en verde | Eliminar `docs/dashboard/01-dashboard-vp-cs.md`, `docs/dashboard/02-mockup-vp-cs.html`, `tests/test_dashboard_figures.py` y revertir el renglón agregado en `README.md` |

## PR1: wireframe, mockup y prueba de anclaje

Rama: `feat/a5-pr1-dashboard`, base `main`. Qué revisa primero el revisor: que las cifras del documento y del mockup coincidan con la prueba, y que la cola de prioridad nunca mezcle cuentas churneadas.

### Fase 1: cifras y prueba (RED antes de escribir los documentos)

- [x] 1.1 Crear `tests/test_dashboard_figures.py`: cargar `outputs/health/health_scores.csv` (read-only) y `outputs/master_dataset.csv` (read-only) con pandas, unir por `master_id`, sin marca `@pytest.mark.dataset` (D14). Rutas resueltas con `Path(__file__).resolve().parent.parent`, igual que `test_health_idempotency.py`.
- [x] 1.2 Agregar la fase 1 de la prueba: recalcular y afirmar 78 cuentas en la cola, MRR en riesgo 2216115.0, MRR activo 16223225.5, proporción 13.7, `risk_alto` 145/78/67, `sin historia` 65/22/43, tramos de MRR activas 131/250/180, conteo por `csm_owner` (Jorge Ibarra 21, Ana Ruiz 15, Diego Ortega 10, Luis Peña 10, Carla Nuñez 9, Fernanda Solís 8, Marta Díaz 5), y HS-100065 (MRR 2947.0, score 35.56) y HS-100507 (MRR 46340.0, score 27.68). Escenarios: "la cola lista las 78 cuentas accionables", "la cuenta de mayor MRR aparece primero", "un empate de health score se rompe por MRR", "cada cuenta de la cola muestra su tramo de MRR", "HS-100065 y HS-100507 quedan como evidencia viva de la respuesta", "el panel de evidencia lista las 67 cuentas ya churneadas", "el panel reporta la detección temprana del modelo", "la cohorte de onboarding lista las 43 cuentas activas nuevas", "el conteo por CSM coincide con las cifras verificadas".
- [x] 1.3 Agregar la fase 2 de la prueba: leer `docs/dashboard/01-dashboard-vp-cs.md` y `docs/dashboard/02-mockup-vp-cs.html` como texto UTF-8 y exigir que las cadenas literales de D11 (`$2,216,115`, `13.7 %`, `$16,223,225.50`, `92.9 %`, `$2,947`, `$46,340`, `35.56`, `27.68`), los siete conteos por CSM y los tres conteos de tramo aparezcan en ambos archivos, sin `&nbsp;`. Escenarios: "la prueba dataset recalcula las cifras y coincide", "la prueba falla si un golden regenerado cambia una cifra citada".
- [x] 1.4 Correr `python -m pytest -q tests/test_dashboard_figures.py` y confirmar que falla porque los dos documentos todavía no existen (RED esperado antes de la fase 2).

### Fase 2: documento Markdown por secciones

- [x] 2.1 Crear `docs/dashboard/01-dashboard-vp-cs.md` con el índice de las ocho secciones de D1 (KPIs, cola de prioridad, subsección 2.1, onboarding, carga por CSM, evidencia del modelo, tendencia, drill-down, cierre) y el bloque de layout ASCII de muestra más la tabla de widgets de seis columnas (métrica, definición en lenguaje llano, columna o consulta fuente, filtro, acción del CSM o VP, cadencia) de D2. Requisito "Secciones obligatorias del documento de wireframe". Escenarios: "el documento cubre las seis secciones obligatorias", "cada sección declara su fuente y su filtro".
- [x] 2.2 Escribir la sección 1 "KPIs de encabezado" con su tabla de widgets: MRR en riesgo ($2,216,115, 13.7 %), cuentas por atender (78 de 518), carga por CSM (11.1, referencia 12), aviso anticipado (92.9 %), agregados sobre `flagged_15=True AND churned=False` más `validation.md` (read-only). Cita `docs/decisions/ADR-007-executive-dashboard.md` (read-only) como origen de la regla de la cola.
- [x] 2.3 Escribir la sección 2 "Cola de prioridad": tabla de widgets con el filtro `flagged_15=True AND churned=False`, orden `mrr_mxn` descendente, y la columna de tramo de MRR por fila (131/250/180 sobre activas). Requisitos "Regla de la cola de prioridad del CSM" y "Segundo eje visual por tramos de MRR".
- [x] 2.4 Escribir la subsección 2.1 "Respuesta a $3,000 contra $45,000" nombrando los tres mecanismos (orden por MRR, KPI agregado, tramo de MRR) y el ejemplo HS-100507 ($46,340, score 27.68) contra HS-100065 ($2,947, score 35.56). Requisito "Respuesta explícita a la pregunta de $3,000 contra $45,000". Escenarios: "el documento nombra los tres mecanismos de trato distinto", "HS-100065 y HS-100507 quedan como evidencia viva de la respuesta".
- [x] 2.5 Escribir la sección 3 "Cohorte de onboarding" con el filtro `risk_band='sin historia' AND churned=False` (43 cuentas), etiquetada "sin historia de uso suficiente" y nunca "sana", con la nota 65 = 22 bajas reales + 43 activas nuevas. Cita `docs/decisions/ADR-005-health-score-model.md` (read-only) como origen de la banda "sin historia". Requisito "Cohorte de onboarding sin historia". Escenarios: "la cohorte de onboarding lista las 43 cuentas activas nuevas", "la cohorte nunca se etiqueta como sana".
- [x] 2.6 Escribir la sección 4 "Carga por CSM" con los siete conteos, la línea de referencia de 12 (D12, declarada como referencia operativa) y la marca "sobre capacidad" en Jorge Ibarra y Ana Ruiz. Requisito "Carga de trabajo por CSM". Escenarios: "el conteo por CSM coincide con las cifras verificadas", "un CSM por encima de su capacidad queda señalado".
- [x] 2.7 Escribir la sección 5 "Evidencia del modelo" con las 67 cuentas de `risk_band='riesgo alto' AND churned=True`, separadas de la cola, citando 92.9 % (52 de 56 evaluables) desde `outputs/health/validation.md` (read-only). Requisito "Panel de evidencia del modelo para cuentas ya churneadas". Escenarios: "el panel de evidencia lista las 67 cuentas ya churneadas", "el panel reporta la detección temprana del modelo".
- [x] 2.8 Escribir la sección 6 "Tendencia en el tiempo" como bloque ASCII vacío con la explicación de que `fact_health_score_monthly` necesita dos o más corridas del comando `warehouse` antes de dibujar una serie (D13). Escenario: "la vista de tendencia se documenta como camino a futuro, no como dato inventado".
- [x] 2.9 Escribir la sección 7 "Drill-down por cuenta" con los cuatro subpuntajes (`score_momentum`, `score_mom`, `score_drawdown`, `score_tenure`) y `usage_months_asof`, usando HS-100507 como ejemplo.
- [x] 2.10 Escribir la sección 8 "Lo que este tablero no muestra": la historia real del score, las 22 bajas no detectables y el aviso de que el score no es la única alerta temprana.
- [x] 2.11 Agregar la tabla de lenguaje llano (mapa de columna interna a texto de negocio) y el apéndice con el snippet de pandas que recalcula todas las cifras citadas (D3), nombrando la columna y el filtro exacto de cada una. Escenario: "cada cifra citada nombra su columna fuente".

### Fase 3: mockup HTML por widget

- [x] 3.1 Crear `docs/dashboard/02-mockup-vp-cs.html`: un solo archivo sin `<script>`, sin hoja de estilo ni fuente externa, sin llamada de red; variables CSS con `prefers-color-scheme` para modo claro y oscuro (D4) y un bloque `@media print`; estructura base con las secciones vacías y el pie de procedencia como marcador. Escenarios: "el mockup no depende de ningún recurso externo", "el mockup se lee en modo claro y en modo oscuro".
- [x] 3.2 Agregar las cuatro tarjetas de KPI (MRR en riesgo, cuentas por atender, carga por CSM, aviso anticipado) con las cifras literales de D11, en lenguaje de negocio, sin nombres de columna. Requisito "Mockup HTML autocontenido y en lenguaje llano". Escenario: "el mockup usa lenguaje de negocio, no nombres de columna".
- [x] 3.3 Agregar la tabla de la cola de prioridad: 20 de las 78 filas (cuenta, segmento, responsable, MRR, tramo, nivel) con cuatro mini barras SVG en línea por los subpuntajes (D5, `<rect>` de ancho fijo). Palanca de reducción: si el PR se acerca al presupuesto de 800 líneas, bajar a 10 filas sin cambiar ninguna cifra agregada.
- [x] 3.4 Agregar la matriz de tramo por nivel de riesgo: nueve celdas con número de cuentas y MRR por celda, insignia de texto para el tramo y color solo para el nivel de riesgo (D6).
- [x] 3.5 Agregar la lista de la cohorte de onboarding: 43 cuentas activas con meses de uso y fecha de alta.
- [x] 3.6 Agregar las barras de carga por CSM: siete barras SVG contra la línea de referencia de 12, con la etiqueta de texto "sobre capacidad" en Jorge Ibarra y Ana Ruiz, distinguidas por texto y nunca por color (D6, D12).
- [x] 3.7 Agregar el panel de evidencia del modelo: 67 cuentas ya dadas de baja que el modelo había marcado, más el 92.9 % a k = 3.
- [x] 3.8 Agregar el pie de procedencia: los dos CSV fuente, `dataset_asof` 2024-08-31, `ruleset_version` 1.0.0 y la fecha de cálculo de las cifras.
- [x] 3.9 Verificar a mano que todo texto contra su fondo cumple 4.5:1 en los dos temas y que ninguna celda comunica un dato solo por color; cada celda coloreada lleva además su etiqueta escrita (D7).

### Fase 4: renglón del README y cierre

- [x] 4.1 Modificar `README.md`: agregar un renglón con la liga a `docs/dashboard/` en la tabla "Dónde está cada cosa", sin tocar la sección de pasos de corrida. Escenario: "el README enlaza el entregable".
- [x] 4.2 Correr `python -m pytest -q tests/test_dashboard_figures.py` y confirmar verde; correr `python -m pytest -q -m "not dataset"` y confirmar que la suite completa sigue en verde; abrir `docs/dashboard/02-mockup-vp-cs.html` con doble clic sin red y mandarlo a vista previa de impresión.
- [x] 4.3 Confirmar con `grep -Ec "<script src|<link|http://|https://" docs/dashboard/02-mockup-vp-cs.html` que el conteo es 0, confirmar con `git status --short` que solo aparecen los cuatro paths de este cambio, y preparar el mensaje de commit convencional sin atribución de IA.
