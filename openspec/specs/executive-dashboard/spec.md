# Especificación: tablero ejecutivo de riesgo real para el VP de Customer Success (`executive-dashboard`)

## Propósito

Define el wireframe por secciones y el mockup autocontenido que responden la pregunta de A5: qué cuentas están en riesgo real, priorizadas por impacto en MRR, y si dos cuentas con el mismo health score pero MRR muy distinto reciben el mismo trato. Implementa el ADR-007.

## ADDED Requirements

### Requirement: Secciones obligatorias del documento de wireframe

`docs/dashboard/01-dashboard-vp-cs.md` MUST cubrir seis secciones (KPIs de encabezado, cola de prioridad, cohorte de onboarding, carga por CSM, panel de evidencia del modelo, drill-down por cuenta), cada una con su métrica, definición, columna fuente exacta, filtro y acción esperada del CSM o del VP.

#### Scenario: el documento cubre las seis secciones obligatorias

- Dado el documento `01-dashboard-vp-cs.md`
- Cuando alguien revisa su índice
- Entonces encuentra las seis secciones (KPIs, cola de prioridad, onboarding, carga por CSM, evidencia del modelo, drill-down)

#### Scenario: cada sección declara su fuente y su filtro

- Dado cualquiera de las seis secciones obligatorias
- Cuando alguien busca de dónde sale cada widget
- Entonces la tabla de esa sección nombra la columna fuente exacta y el filtro aplicado, sin dejarlo implícito

#### Scenario: la vista de tendencia se documenta como camino a futuro, no como dato inventado

- Dado que `fact_health_score_monthly` tiene una sola fecha de corrida
- Cuando alguien busca la sección de tendencia en el tiempo
- Entonces el documento la describe como camino del warehouse pendiente de dos o más corridas, sin dibujar una serie con datos inventados

#### Scenario: el README enlaza el entregable

- Dado el README del proyecto
- Cuando alguien revisa la tabla de entregables
- Entonces encuentra una fila con la liga a `docs/dashboard/`

### Requirement: Regla de la cola de prioridad del CSM

La cola de prioridad MUST incluir únicamente cuentas con `flagged_15 = True AND churned = False`, ordenadas por `mrr_mxn` descendente. El sistema MUST NOT usar `risk_band = 'riesgo alto'` sola como filtro de la cola.

#### Scenario: la cola lista las 78 cuentas accionables

- Dado `outputs/health/health_scores.csv`
- Cuando alguien construye la cola de prioridad con el filtro `flagged_15 = True AND churned = False`
- Entonces la cola contiene exactamente 78 cuentas activas
- Y una cuenta con `flagged_15 = True` pero `churned = True` queda excluida, sin importar su `risk_band`

#### Scenario: la cuenta de mayor MRR aparece primero

- Dado dos cuentas marcadas con el mismo nivel de riesgo
- Cuando el sistema ordena la cola
- Entonces la cuenta con `mrr_mxn` más alto aparece antes que la de `mrr_mxn` más bajo

#### Scenario: un empate de health score se rompe por MRR

- Dado dos cuentas activas marcadas con el mismo `health_score`
- Cuando el sistema resuelve el orden dentro de la cola
- Entonces la cuenta de mayor `mrr_mxn` queda arriba de la de menor `mrr_mxn`

### Requirement: Segundo eje visual por tramos de MRR

La cola de prioridad MUST mostrar un segundo eje de severidad por tramo de MRR sobre el libro activo: menos de $5,000 (131 cuentas), de $5,000 a $20,000 (250 cuentas) y más de $20,000 (180 cuentas).

#### Scenario: cada cuenta de la cola muestra su tramo de MRR

- Dado una cuenta listada en la cola de prioridad
- Cuando alguien revisa su fila
- Entonces la fila muestra el tramo de MRR al que pertenece esa cuenta, y la suma de cuentas activas por tramo coincide con 131, 250 y 180

### Requirement: Respuesta explícita a la pregunta de $3,000 contra $45,000

El documento MUST responder por escrito que dos cuentas con el mismo health score y MRR distinto no reciben el mismo trato, y MUST sustentarlo con los tres mecanismos combinados: orden por MRR, KPI que agrega MRR por cuenta y tramo de MRR como segundo eje.

#### Scenario: el documento nombra los tres mecanismos de trato distinto

- Dado la sección que responde la pregunta de A5
- Cuando alguien la lee
- Entonces encuentra los tres mecanismos (orden, KPI agregado, tramo de MRR) explicados como la respuesta

#### Scenario: HS-100065 y HS-100507 quedan como evidencia viva de la respuesta

- Dado HS-100065 (MRR $2,947) y HS-100507 (MRR $46,340), ambas en la misma banda de riesgo
- Cuando alguien revisa el ejemplo citado en el documento
- Entonces ve que HS-100507 queda arriba de HS-100065 en la cola y pesa más en el KPI de MRR en riesgo, pese al score parecido

### Requirement: Panel de evidencia del modelo para cuentas ya churneadas

El documento MUST separar en un panel propio de "evidencia del modelo" a las 67 cuentas con `risk_band = 'riesgo alto'` y `churned = True`, y MUST NOT mezclarlas con la cola de prioridad de cuentas activas.

#### Scenario: el panel de evidencia lista las 67 cuentas ya churneadas

- Dado `health_scores.csv` filtrado por `risk_band = 'riesgo alto' AND churned = True`
- Cuando alguien construye el panel de evidencia del modelo
- Entonces el panel muestra exactamente 67 cuentas, ninguna presente en la cola de prioridad

#### Scenario: el panel reporta la detección temprana del modelo

- Dado el panel de evidencia del modelo
- Cuando alguien busca qué tan bien detecta el modelo el riesgo con anticipación
- Entonces el panel cita la cifra de `validation.md`: 92.9 % (52 de 56 cuentas evaluables) ya estaban marcadas un mes antes

### Requirement: Cohorte de onboarding sin historia

El documento MUST mostrar en una vista propia de onboarding a las cuentas con `risk_band = 'sin historia' AND churned = False` (43 cuentas), y MUST NOT presentarlas como cuentas sanas.

#### Scenario: la cohorte de onboarding lista las 43 cuentas activas nuevas

- Dado `health_scores.csv` filtrado por `risk_band = 'sin historia' AND churned = False`
- Cuando alguien construye la cohorte de onboarding
- Entonces la vista muestra exactamente 43 cuentas, separadas de cualquier banda "sana"

#### Scenario: la cohorte nunca se etiqueta como sana

- Dado una cuenta de la cohorte de onboarding
- Cuando alguien revisa su etiqueta en el documento
- Entonces la etiqueta indica "sin historia de uso suficiente", nunca "sana", y aclara que 65 filas totales se dividen en 22 bajas reales y 43 activas nuevas

### Requirement: Carga de trabajo por CSM

La sección de carga por CSM MUST cruzar la cola de prioridad con `csm_owner` y MUST mostrar el conteo de cuentas marcadas por cada CSM frente a su capacidad de referencia de 12 cuentas.

#### Scenario: el conteo por CSM coincide con las cifras verificadas

- Dado la cola de prioridad de 78 cuentas
- Cuando alguien agrupa por `csm_owner`
- Entonces los conteos son Jorge Ibarra 21, Ana Ruiz 15, Diego Ortega 10, Luis Peña 10, Carla Nuñez 9, Fernanda Solís 8 y Marta Díaz 5

#### Scenario: un CSM por encima de su capacidad queda señalado

- Dado un CSM cuyo conteo de cuentas marcadas supera la capacidad de referencia de 12
- Cuando alguien revisa la sección de carga por CSM
- Entonces esa fila queda marcada como sobre capacidad, distinta de las filas dentro del rango

### Requirement: Mockup HTML autocontenido y en lenguaje llano

`docs/dashboard/02-mockup-vp-cs.html` MUST ser un solo archivo sin scripts, hojas de estilo, fuentes ni llamadas de red externas, MUST abrir tanto en local como al previsualizarse en GitHub, MUST ser legible en modo claro y en modo oscuro, y MUST NOT mostrar ningún nombre de columna técnico.

#### Scenario: el mockup no depende de ningún recurso externo

- Dado `02-mockup-vp-cs.html`
- Cuando alguien inspecciona su código
- Entonces no encuentra ninguna etiqueta de script, hoja de estilo, fuente o llamada de red que apunte fuera del propio archivo

#### Scenario: el mockup se lee en modo claro y en modo oscuro

- Dado el mismo archivo `02-mockup-vp-cs.html`
- Cuando alguien lo abre con el tema claro y luego con el tema oscuro del sistema o del navegador
- Entonces el texto y las barras permanecen legibles en ambos modos

#### Scenario: el mockup usa lenguaje de negocio, no nombres de columna

- Dado cualquier widget visible del mockup
- Cuando alguien busca nombres como `flagged_15`, `mrr_mxn` o `risk_band` en el HTML renderizado
- Entonces no los encuentra; los montos aparecen en pesos mexicanos con separador de miles y los nombres de columna solo viven en la tabla de especificación del Markdown

### Requirement: Trazabilidad de cifras y prueba que las ancla a los goldens

Toda cifra citada en el documento y en el mockup MUST ser trazable a `outputs/health/health_scores.csv` o a `outputs/master_dataset.csv`, y `tests/test_dashboard_figures.py` MUST recalcular esas cifras desde los goldens y fallar si el documento se desincroniza de ellos.

#### Scenario: cada cifra citada nombra su columna fuente

- Dado cualquier cifra citada en el documento (78 cuentas, $2,216,115 MXN, 13.7 %, 65 = 22 + 43, 145 = 78 + 67)
- Cuando alguien busca de dónde sale
- Entonces encuentra la columna y el filtro exactos en `health_scores.csv` o `master_dataset.csv`

#### Scenario: la prueba dataset recalcula las cifras y coincide

- Dado el dataset real bajo `outputs/`
- Cuando alguien corre `pytest tests/test_dashboard_figures.py -m dataset`
- Entonces la prueba recalcula las cifras citadas desde los goldens y pasa porque coinciden con las escritas en el documento y en el mockup

#### Scenario: la prueba falla si un golden regenerado cambia una cifra citada

- Dado un golden regenerado con un conteo de cuentas marcadas distinto de 78
- Cuando alguien corre `pytest tests/test_dashboard_figures.py -m dataset`
- Entonces la prueba falla, porque la cifra recalculada ya no coincide con la escrita en el documento
