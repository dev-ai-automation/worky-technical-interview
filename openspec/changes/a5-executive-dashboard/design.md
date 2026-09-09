# Diseño: tablero ejecutivo de riesgo real para el VP de Customer Success (A5)

Este documento decide cómo se construyen los tres archivos que el ADR-007 ya fijó: el wireframe por secciones, el mockup HTML autocontenido y la prueba que ancla las cifras a los goldens. El ADR-005 fijó el modelo del health score, sus bandas y el umbral operativo `flagged_15`; el ADR-006 fijó el esquema en estrella que alimentará la vista de tendencia cuando existan dos corridas; el ADR-007 fijó la regla de la cola (`flagged_15 AND churned = False`), el orden por MRR y el panel separado de evidencia del modelo. Aquí se define el orden de lectura del documento, la técnica exacta del HTML, la codificación visual, el formato literal de cada cifra y la forma de la prueba.

A5 solo lee. No toca `worky_engine/`, `outputs/`, ningún golden de A0, A1, A3 y A4, ni la sección de pasos de corrida del README. La implementación corre en un worktree aislado mientras A6 avanza en el árbol principal.

## Resumen de decisiones

| # | Decisión | Elegido | Rechazado | Por qué |
|---|---|---|---|---|
| D1 | Orden de lectura del Markdown | Ocho secciones en orden de decisión del VP: KPIs de encabezado, cola de prioridad, la respuesta a $3,000 contra $45,000 como subsección 2.1, cohorte de onboarding, carga por CSM, evidencia del modelo, tendencia como camino futuro, drill-down por cuenta, y al cierre "lo que este tablero no muestra" | Orden por fuente de datos, o la respuesta del caso al final como conclusión | El VP entra por el monto en riesgo y sale con una lista de trabajo. La respuesta a la pregunta del caso va pegada a la cola porque el orden por MRR es el mecanismo que la contesta; ponerla al final obliga a reconstruir el argumento |
| D2 | Forma de cada sección | Un bloque de layout en ASCII más una tabla de widgets con seis columnas fijas: métrica, definición en lenguaje llano, columna o consulta fuente, filtro, acción del CSM, cadencia | Solo prosa, o solo el bloque ASCII | El caso pide "boceto o descripción por secciones". Las seis columnas hacen que cada widget se pueda rastrear hasta el archivo que lo alimenta sin leer el resto del documento |
| D3 | Cómo entran las cifras al HTML | Escritas a mano una sola vez a partir de un snippet de pandas documentado, con el snippet completo en el apéndice del Markdown para que cualquiera lo vuelva a correr | Generador Python en este corte, o cifras escritas sin dejar el snippet | El generador es trabajo futuro por ADR-007 y compite con A6. Sin el snippet, nadie puede recomputar las cifras sin rederivarlas; con él, la recomputación es un copiar y pegar. La prueba es la guardia real, el snippet es la ruta humana |
| D4 | Técnica del HTML | Un solo archivo, sin JavaScript, sin recursos externos, sin fuentes remotas; variables CSS con `prefers-color-scheme` para claro y oscuro, y un bloque `@media print` | El script de tema del diagrama 05, o un lector de CSV en el navegador | El requisito es abrir sin conexión y sin servidor. `prefers-color-scheme` da los dos temas sin una línea de JS. Un lector de CSV rompería la apertura desde GitHub y agregaría una dependencia de red |
| D5 | Cómo se dibujan las barras | SVG en línea con `<rect>` de ancho fijo escrito a mano | Barras con `background-color` sobre un `div` | El navegador descarta los fondos CSS al imprimir salvo que se fuerce `print-color-adjust`; un `<rect>` de SVG es contenido y siempre imprime. Es también lo que la propuesta comprometió |
| D6 | Codificación visual | El color codifica solo el nivel de riesgo, con tres pasos; el tramo de MRR se codifica con una insignia de texto y un tamaño de tipografía, nunca con color | Color para riesgo y para MRR a la vez, o burbujas de tamaño variable | Es el principio preatencional de la sección 5 de la investigación: dos escalas de color en la misma tabla compiten y ninguna gana. Con insignia de texto la tabla sigue siendo legible en blanco y negro y para daltonismo |
| D7 | Contraste | Todo texto contra su fondo cumple 4.5:1 en los dos temas, y ningún dato se comunica solo por color: cada celda coloreada lleva además su etiqueta escrita | Confiar en la paleta del diagrama 05 sin verificar | El entregable se imprime y se proyecta. Una etiqueta escrita junto al color es la única versión que sobrevive a una fotocopia |
| D8 | Tramos de MRR | `mrr_mxn < 5000`, `5000 <= mrr_mxn < 20000`, `mrr_mxn >= 20000`, sobre las 561 cuentas activas: 131, 250 y 180 | Cortes por percentil calculados en el momento | Los umbrales redondos se explican solos frente a un VP. La prueba recalcula los tres conteos con este predicado exacto, así que la convención queda verificada y no supuesta |
| D9 | De dónde sale el nombre del CSM | `master_dataset.csv` unido a `health_scores.csv` por `master_id` | Leer `csm_owner` de `health_scores.csv`, o de `dim_company.csv` | `health_scores.csv` no tiene `csm_owner`: sus 23 columnas terminan en las tres marcas. `dim_company.csv` sí lo tiene, pero ataría A5 a haber corrido `warehouse`, y el ADR-007 ya eligió los CSV de A1 y A3 como fuente |
| D10 | Ortografía de los nombres | Tal como vienen en `master_dataset.csv`: Jorge Ibarra, Ana Ruiz, Diego Ortega, Luis Peña, Carla Nuñez, Fernanda Solís, Marta Díaz | La grafía corregida "Carla Núñez" que usa el ADR-007 | La prueba compara contra los valores del CSV. Corregir la ortografía en el documento rompe la coincidencia literal y, peor, inventa un dato que el sistema origen no tiene. La divergencia queda anotada en el apéndice del documento |
| D11 | Formato literal de las cifras | Cadenas exactas, sin `&nbsp;` ni variantes: `$2,216,115`, `13.7 %`, `$16,223,225.50`, `92.9 %`, `$2,947`, `$46,340`, `35.56`, `27.68` | Formato libre por archivo, o `&nbsp;` antes del signo de porcentaje | La prueba busca estas cadenas dentro del Markdown y del HTML. Un espacio duro se ve igual y falla la comparación, así que queda prohibido dentro de una cifra anclada |
| D12 | Línea de capacidad por CSM | 12 cuentas por CSM, declarada en el documento como línea de referencia operativa, no como dato medido | Presentar 12 como si saliera del dataset | `validation.md` mide 11.1 cuentas por CSM al 15 % y 14.9 al 20 %, nunca 12. La barra de referencia es una decisión de operación; el documento lo dice con esas palabras y la prueba no la ancla contra ningún CSV |
| D13 | Vista de tendencia | Un bloque ASCII vacío con la explicación escrita de qué la llenará (`fact_health_score_monthly` con dos o más corridas) | Dibujar una serie de ejemplo | `fact_health_score_monthly` hoy tiene una sola fecha de corrida. Una serie inventada en un entregable que presume de cifras reales es exactamente el error que este proyecto evita |
| D14 | Marca de la prueba | `@pytest.mark.dataset`, igual que `test_health_idempotency.py` | Sin marca, para que corra en el camino rápido | Las aserciones son sobre el dataset del caso, no sobre lógica pura. La marca las agrupa con las demás pruebas ancladas a datos reales y mantiene verde el camino `-m "not dataset"` en un clon sin las tres bases |

## 1. Secciones del documento y su fuente

| # | Sección | Filtro exacto | Cifra de encabezado |
|---|---|---|---|
| 1 | KPIs de encabezado | agregados sobre `flagged_15 = True AND churned = False` | $2,216,115 MXN, 13.7 %, 78 cuentas, 92.9 % de detección temprana |
| 2 | Cola de prioridad | `flagged_15 = True AND churned = False`, orden `mrr_mxn` descendente | 78 cuentas, 20 visibles en el mockup |
| 2.1 | Respuesta a $3,000 contra $45,000 | HS-100507 ($46,340, score 27.68) contra HS-100065 ($2,947, score 35.56) | tres mecanismos: orden, KPI agregado y tramo |
| 3 | Cohorte de onboarding | `risk_band = 'sin historia' AND churned = False` | 43 cuentas activas, separadas de las 22 bajas |
| 4 | Carga por CSM | `csm_owner` de `master_dataset.csv` cruzado con la cola | 7 CSM, de 5 a 21 cuentas, referencia de 12 |
| 5 | Evidencia del modelo | `risk_band = 'riesgo alto' AND churned = True` | 67 cuentas detectadas, 92.9 % con un mes de anticipación |
| 6 | Tendencia en el tiempo | `fact_health_score_monthly`, hoy una sola fecha | camino futuro, sin serie dibujada |
| 7 | Drill-down por cuenta | los cuatro subpuntajes más `usage_months_asof` | ejemplo con HS-100507 |
| 8 | Lo que este tablero no muestra | historia real de score, las 22 bajas no detectables, el score como única alerta temprana | honestidad declarada |

Bloque ASCII de muestra, con la forma que repiten las ocho secciones:

```
+----------------------+----------------------+----------------------+----------------------+
| MRR en riesgo        | Cuentas por atender  | Carga por CSM        | Aviso anticipado     |
| $2,216,115 MXN       | 78                   | 11.1 (ref. 12)       | 92.9 % con 1 mes     |
| 13.7 % del activo    | de 518 con puntaje   | 7 personas           | 52 de 56 evaluables  |
+----------------------+----------------------+----------------------+----------------------+
| Cuenta   | Segmento | Responsable | MRR mensual | Tramo | Nivel | Por que esta marcada |
| HS-1005..| Enterpr. | Ana Ruiz    | $46,340     | Alto  | Alto  | [##  ][#   ][####][# ]|
```

## 2. Flujo de datos

```
outputs/master_dataset.csv ──┐
                             ├──> snippet de pandas (una corrida, apendice) ──> cifras
outputs/health/health_scores.csv ─┘                                              │
outputs/health/validation.md ────────> 92.9 %, 22 no detectables ────────────────┤
                                                                                 v
                              docs/dashboard/01-dashboard-vp-cs.md  <────────── escritas a mano
                              docs/dashboard/02-mockup-vp-cs.html   <────────── escritas a mano
                                                 ^                    ^
                                                 │                    │
        tests/test_dashboard_figures.py ─── recalcula de los CSV y busca las cadenas literales
```

La prueba no genera nada: recalcula desde los dos CSV y compara contra el texto de los dos documentos. Si alguien edita una cifra a mano o el golden cambia, la comparación falla.

## 3. Widgets del mockup

| Widget | Contenido | Fuente |
|---|---|---|
| Cuatro tarjetas de KPI | MRR en riesgo, cuentas por atender, carga por CSM, aviso anticipado | agregados de la cola más `validation.md` |
| Cola de prioridad | 20 filas de las 78, con cuenta, segmento, responsable, MRR, tramo, nivel y cuatro mini barras SVG de los subpuntajes | `health_scores.csv` unido a `master_dataset.csv` |
| Matriz de tramo por nivel de riesgo | nueve celdas con número de cuentas y MRR por celda | cola completa, cruzada por tramo y banda |
| Cohorte de onboarding | 43 cuentas activas sin tres meses de uso, con meses de uso y fecha de alta | `risk_band = 'sin historia' AND churned = False` |
| Carga por CSM | 7 barras SVG contra la línea de referencia de 12 | conteo por `csm_owner` sobre la cola |
| Evidencia del modelo | 67 cuentas ya dadas de baja que el modelo había marcado, más el 92.9 % a k = 3 | `risk_band = 'riesgo alto' AND churned = True`, `validation.md` |
| Pie de procedencia | los dos CSV, `dataset_asof` 2024-08-31, `ruleset_version` 1.0.0 y la fecha en que se calcularon las cifras | encabezado de `validation.md` |

## 4. Lenguaje llano

Esta tabla vive completa en el Markdown y ninguna de sus columnas de la izquierda aparece en el HTML.

| Columna interna | Cómo se lee en el tablero |
|---|---|
| `flagged_15 = True` | En la lista de esta semana |
| `churned = False` | Cuenta viva |
| `risk_band` | Nivel de riesgo |
| `health_score` | Puntaje de salud (0 a 100, más alto es mejor) |
| `score_momentum` | Tendencia de uso |
| `score_mom` | Cambio contra el mes pasado |
| `score_drawdown` | Caída desde su mejor mes |
| `score_tenure` | Antigüedad de la cuenta |
| `usage_months_asof` | Meses de uso acumulados |
| `mrr_mxn` | MRR mensual |
| `csm_owner` | Responsable de la cuenta |
| `risk_band = 'sin historia'` | Cuenta nueva, todavía sin puntaje |

## 5. La prueba `tests/test_dashboard_figures.py`

Entre 80 y 120 líneas, marcada `dataset`, en dos fases y sin dependencias nuevas.

Fase 1, recalcular con pandas desde `outputs/health/health_scores.csv` y `outputs/master_dataset.csv` unidos por `master_id`:

| Aserción | Valor esperado |
|---|---|
| Cuentas en la cola | 78 |
| MRR en riesgo | 2216115.0 |
| MRR activo total | 16223225.5 |
| Proporción en riesgo, a un decimal | 13.7 |
| `risk_band = 'riesgo alto'`: total, activas, churneadas | 145, 78, 67 |
| `sin historia`: total, churneadas, activas | 65, 22, 43 |
| Conteo por `csm_owner` sobre la cola | Jorge Ibarra 21, Ana Ruiz 15, Diego Ortega 10, Luis Peña 10, Carla Nuñez 9, Fernanda Solís 8, Marta Díaz 5 |
| Tramos de MRR sobre activas | 131, 250, 180 |
| HS-100065 | MRR 2947.0, score 35.56, `flagged_15` verdadero |
| HS-100507 | MRR 46340.0, score 27.68, `flagged_15` verdadero |

Fase 2, leer los dos documentos como texto UTF-8 y exigir que cada cadena de D11 aparezca en los dos archivos, más los siete conteos por CSM y los tres conteos de tramo. Una cifra que se desincronice del CSV rompe la fase 1; una cifra que alguien edite a mano en un documento rompe la fase 2.

Las rutas se resuelven desde `Path(__file__).resolve().parent.parent`, igual que `test_health_idempotency.py`. Los booleanos de `health_scores.csv` llegan como `bool` de pandas porque las tres columnas de marcas nunca vienen vacías, verificado en el CSV.

## 6. Cambios por archivo

| Archivo | Acción | Qué contiene |
|---|---|---|
| `docs/dashboard/01-dashboard-vp-cs.md` | Nuevo | Las ocho secciones, la tabla de lenguaje llano y el apéndice con el snippet de pandas |
| `docs/dashboard/02-mockup-vp-cs.html` | Nuevo | Mockup autocontenido con los siete widgets |
| `tests/test_dashboard_figures.py` | Nuevo | La prueba de dos fases de la sección 5 |
| `README.md` | Modificado | Un renglón en la tabla "Dónde está cada cosa" con `docs/dashboard/` |
| `worky_engine/`, `outputs/`, goldens de A0, A1, A3 y A4, pasos de corrida del README | Sin cambio | A5 solo lee |

## 7. Estrategia de pruebas

| Capa | Qué se prueba | Cómo |
|---|---|---|
| Datos | Las cifras citadas coinciden con los CSV | `pytest tests/test_dashboard_figures.py`, fase 1 |
| Documento | Las cifras escritas coinciden con las recalculadas | misma prueba, fase 2, comparación de cadenas literales |
| Regresión del repositorio | Ningún golden se movió | `git status` limpio fuera de los cuatro archivos, y la suite completa `python -m pytest -q` |
| Manual | El HTML abre sin conexión y se imprime | abrirlo con doble clic sin red y mandar a vista previa de impresión |

No hay capa unitaria ni de extremo a extremo: no se agrega código ejecutable al motor.

## 8. Matriz de amenazas

No aplica. Este cambio agrega dos documentos estáticos y una prueba de lectura. No hay ruteo, comandos de shell, subprocesos, automatización de Git o de pull requests, ni clasificación de archivos ejecutables.

Dos límites quedan fijados como restricción de diseño:

1. El HTML no lleva `<script>`, `<iframe>`, `<link>` externo ni fuente remota, así que abrirlo no genera ninguna petición de red y no ejecuta nada.
2. La prueba solo lee archivos ya versionados dentro del repositorio y no escribe ninguno.

## 9. Migración y reversión

No hay migración. Revertir es borrar los tres archivos nuevos y devolver el renglón del README a su estado anterior, o `git revert` del merge del PR. No queda ningún artefacto generado que limpiar a mano.

Presupuesto estimado de autoría: unas 230 líneas de Markdown, unas 100 de prueba y un renglón del README, más entre 300 y 400 líneas de marcado HTML repetitivo (renglones de tabla y `<rect>` de SVG) que se cuentan como dato generado a mano, con el mismo criterio con que A3 y A4 dejaron los renglones de golden fuera del conteo. Un solo PR.

## 10. Riesgos residuales

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Los tramos de MRR no dan 131, 250 y 180 con el predicado de D8 | Media | La prueba lo detecta en la primera corrida; si pasa, se corrige el predicado documentado en el documento y en el ADR-007, nunca el conteo |
| Una cifra se escribe con `&nbsp;` o con otro formato y la fase 2 falla sin razón obvia | Media | D11 fija las cadenas exactas y el documento las lista juntas en el apéndice |
| El HTML repetitivo empuja el PR hacia el presupuesto de revisión | Media | Los 20 renglones de la cola y las 9 celdas de la matriz son la única parte repetitiva; si el revisor lo pide, la cola baja a 10 renglones sin cambiar ninguna cifra agregada |
| Conflicto con A6 en el árbol principal | Media | Worktree aislado y cuatro archivos tocados, ninguno compartido con A6 |
| Alguien lee la línea de referencia de 12 como un dato medido | Baja | D12 la declara en el documento y en el mockup con la palabra "referencia" |

## 11. Preguntas abiertas

- [ ] ¿La línea de capacidad de 12 cuentas por CSM se queda como referencia declarada o se sustituye por el 11.1 medido en `validation.md`? No bloquea: el documento ya dice cuál de los dos números sale del dato.
- [ ] ¿El generador `worky_engine dashboard` se construye después de A6 y la Parte B, o se queda fuera del caso? Es la pregunta abierta 2 del ADR-007 y sigue igual.
- [ ] ¿La cola del mockup muestra 20 renglones o 10? Se decide al medir el tamaño real del PR.
