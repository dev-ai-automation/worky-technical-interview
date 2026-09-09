# Propuesta: tablero ejecutivo de riesgo real para el VP de Customer Success

## Intención

A5 pide el wireframe de un tablero que muestre qué cuentas están en riesgo real, priorizadas por impacto en MRR, y que responda si dos cuentas con el mismo health score pero MRR de $3,000 y $45,000 se tratan igual. Hoy ese documento no existe y la banda `riesgo alto` de `health_scores.csv` (145 filas) mezcla 78 cuentas activas con 67 que ya hicieron churn, evaluadas solo para medir recall (ADR-005). Un tablero que lea esa banda sin filtrar `churned` le pondría al VP cuentas que ya no existen en la cola de trabajo.

Éxito: abrir el mockup y ver las 78 cuentas accionables, los $2,216,115 MXN en riesgo (13.7 % del MRR activo de $16,223,225.50) y la cuenta grande arriba de la chica con el mismo score; y que una prueba falle si esas cifras se desincronizan de los goldens.

## Alcance

### Dentro

- `docs/dashboard/01-dashboard-vp-cs.md`: secciones obligatorias (KPIs de encabezado, cola de prioridad, cohorte de onboarding, carga por CSM, panel de evidencia del modelo, drill-down por cuenta), cada widget con métrica, definición, fuente, filtro y acción.
- Regla de la cola de trabajo: `flagged_15 = True AND churned = False` (78 cuentas), ordenada por `mrr_mxn` descendente.
- Segundo eje de severidad por tramo de MRR sobre el libro activo: menos de $5k (131), de $5k a $20k (250), más de $20k (180).
- Respuesta explícita a la pregunta de $3,000 contra $45,000, con HS-100065 ($2,947) y HS-100507 ($46,340) como evidencia del CSV.
- Panel separado de evidencia del modelo para las 67 cuentas ya churneadas, nunca mezcladas con la cola.
- `docs/dashboard/02-mockup-vp-cs.html`: autocontenido, sin JS ni recursos externos, barras SVG en línea, lenguaje llano sin nombres de columnas técnicas.
- `tests/test_dashboard_figures.py`: prueba marcada `dataset` que fija 78 cuentas, $2,216,115, 13.7 %, 65 = 22 + 43 y el conteo por CSM contra `outputs/health/health_scores.csv` y `outputs/master_dataset.csv`.
- Una fila con la liga a `docs/dashboard/` en la tabla de entregables del README.

### Fuera

- Generador Python (`worky_engine dashboard`): trabajo futuro documentado, no implementado aquí.
- Vista de tendencia con dato real: `fact_health_score_monthly` hoy tiene una sola fecha de corrida; se documenta como camino del warehouse, no se dibuja con datos inventados.
- Cambios en `worky_engine/`, en `outputs/`, en cualquier golden de A0, A1, A3 y A4, y en la sección de pasos de corrida del README.

## Capacidades

### Nuevas

- `executive-dashboard`: secciones obligatorias del documento, la regla de la cola (`flagged_15 AND churned=False` por MRR descendente), los tramos de MRR, la respuesta a la pregunta de $3,000 contra $45,000, la trazabilidad de cada cifra a `health_scores.csv` y `master_dataset.csv`, la restricción de HTML autocontenido, el lenguaje llano del mockup y la prueba que ancla las cifras a los goldens.

### Modificadas

- Ninguna. Este cambio no toca el comportamiento del motor.

## Enfoque

El documento Markdown es la especificación por secciones que pide el caso; el HTML es la misma especificación renderizada con las cifras reales de este dataset, en un solo archivo que abre en GitHub o en el navegador sin servidor. La prueba `dataset` recalcula desde los CSV las cifras citadas en ambos archivos y las compara contra los valores escritos, de modo que el documento no puede quedarse atrás del dato y la Parte B puede citar los mismos números. Cada tabla del documento nombra la columna fuente y el filtro; el mockup solo muestra lenguaje de negocio.

## Áreas afectadas

| Área | Impacto | Descripción |
|---|---|---|
| `docs/dashboard/01-dashboard-vp-cs.md` | Nueva | Wireframe por secciones, regla de la cola, tramos de MRR y la respuesta de A5 |
| `docs/dashboard/02-mockup-vp-cs.html` | Nueva | Mockup autocontenido con las cifras reales |
| `tests/test_dashboard_figures.py` | Nueva | Prueba `dataset` que ancla las cifras citadas a los goldens |
| `docs/decisions/ADR-007-executive-dashboard.md` | Nueva | Registro de las cinco decisiones de producto ya confirmadas |
| `README.md` | Modificado | Una fila en la tabla de entregables |
| `worky_engine/`, `outputs/`, goldens de A0, A1, A3 y A4 | Sin cambio | A5 solo lee |

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Las cifras del HTML se congelan y se desincronizan del CSV | Alta | `tests/test_dashboard_figures.py` falla si cualquiera de las cifras citadas deja de cuadrar |
| Confundir `risk_band` con `flagged_15` al escribir un widget | Media | Cada tabla del documento declara el filtro `churned = False` explícito |
| Conflicto con A6, que corre en el árbol principal | Media | A5 se implementa en un worktree aislado y no toca `worky_engine/`, `outputs/` ni los pasos de corrida del README |
| Lenguaje técnico en el mockup frente a un VP no técnico | Media | Los nombres de columnas viven solo en la tabla de especificación del Markdown |
| Rebasar las 800 líneas de autoría del corte | Baja | Sin código de motor; el mockup se acota a las seis secciones acordadas |

## Plan de reversión

`git revert` del merge del PR. Los tres archivos son nuevos y la única línea modificada es la fila del README, así que revertir deja el repositorio idéntico al estado posterior a A4. No hay migración de datos ni artefactos generados que borrar a mano.

## Dependencias

A1 (`outputs/master_dataset.csv`), A3 (`outputs/health/health_scores.csv` y `validation.md`) y A4 (`docs/data-model/01-warehouse-model.md` para el camino de la tendencia), ya entregados. ADR-005, ADR-006 y ADR-007. pytest, ya fijado en `pyproject.toml`.

## Criterios de éxito

- [ ] El documento cubre las seis secciones y responde por escrito la pregunta de $3,000 contra $45,000.
- [ ] La cola de prioridad lista 78 cuentas y la cuenta de MRR más alto aparece primero.
- [ ] El mockup abre sin conexión y sin recursos externos, y no muestra ningún nombre de columna técnica.
- [ ] `pytest tests/test_dashboard_figures.py` pasa con el dataset real y falla si se altera cualquier cifra citada.
- [ ] Las 67 cuentas ya churneadas aparecen solo en el panel de evidencia del modelo.
- [ ] `git status` no reporta cambios en `worky_engine/`, `outputs/` ni en los goldens.
