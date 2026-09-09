# Exploración: a3-health-score (health score con validación real)

Fase `sdd-explore` ejecutada el 2026-09-08 por el agente explorador (sin herramienta de ejecución en esa fase); persistida por el orquestador. Las mediciones de señales nuevas que la exploración dejó pendientes se corrieron después en modo solo lectura y se resumen en la sección final. Referencia en Engram: `sdd/a3-health-score/explore`.

## Texto literal de la sección A3 del caso

"A3. Health Score, con validación real. Esta vez sí tienes el ground truth: la columna churn_date.

1. Propón un modelo de Health Score (fórmula, variables de product_usage y tickets, pesos) para predecir riesgo de churn.
2. Calcula el score histórico de cada cuenta 2-3 meses antes de su fecha de referencia (para las que churnearon, antes de churn_date; para las activas, en el mes más reciente).
3. Valida: de las cuentas que tu modelo marcó como riesgo alto, ¿qué % efectivamente churneó? De las que churnearon, ¿qué % tu modelo detectó a tiempo? (Esto es, en esencia, calcular precisión y recall de tu propio score; no necesitas ML formal, un umbral simple basta, pero sí necesitas medir qué tan bueno es).
4. ¿Qué harías distinto si tu Health Score tuviera muchos falsos positivos (marca cuentas sanas como en riesgo) vs. muchos falsos negativos (no detecta a tiempo cuentas que sí se van)? ¿Cuál error es más costoso para Worky y por qué?"

## Estado actual

### Lo que ya existe y A3 puede reusar directo

- `docs/decisions/ADR-003-usage-trend-and-leakage-guard.md` ya decidió, para A3, tres subpuntajes de uso: momentum (tendencia), mes contra mes (choque) y caída desde el mejor promedio de 3 meses (nivel). Los tres ya están implementados y medidos en `worky_engine/harness/backtest.py`.
- `outputs/backtest_report.md` ya reporta el AUC de esos tres, en k = 2 y k = 3, sobre el dataset real:

| Subpuntaje | AUC k = 2 | AUC k = 3 |
|---|---|---|
| Momentum (EWMA 3 contra 9) | 1.000 | 0.894 |
| Mes contra mes anterior | 0.978 | 0.903 |
| Caída desde el mejor promedio de 3 meses | 0.845 | 0.620 |

- `worky_engine/sql/marts/mart_usage.sql` ya calcula `trend_usage`, `trend_asof_month` y `trend_status` con el resguardo de fuga.
- `worky_engine/analysis/runner.py` y `worky_engine/cli.py` (`analyze`) fijan el patrón que A3 debe copiar para un comando `health`: conexión propia, identidad y ensamblaje en memoria, lista declarada de archivos SQL, vistas materializadas a CSV en orden fijo, contratos antes de escribir, y un reporte armado desde los DataFrames ya materializados.

### Lo que existe pero tiene un hueco

- `worky_engine/sql/marts/mart_support.sql` agrega todos los tickets de la vida de la cuenta, sin filtro por mes de corte. Si A3 reusa esa vista tal cual para el subpuntaje de soporte, mete tickets ocurridos después del mes de corte al puntaje que se supone debe predecir la baja. Es un hueco de fuga que ya existe en el repositorio para este uso; el dataset maestro lo usa como agregado descriptivo, no como predictor. A3 debe cerrarlo con una vista de soporte ventanada.
- `docs/decisions/ADR-004-sql-analysis-definitions.md` fijó que las señales de soporte para A3 son conteos y CSAT, no tiempo de resolución, hasta que A6 corrija el signo de los 48 tickets negativos.
- Hallazgo ya medido en A0: el soporte no anticipa churn en este dataset (cuentas con baja: 2.64 tickets y CSAT 3.10; activas: 2.95 y 2.89). El canal de adquisición sí separa (Evento 8.3 % de churn contra Organic 19.6 %), pero es contexto comercial, no una señal de producto.

### Lo que no existe todavía

- Ninguna vista usa `payroll_runs_completed`, `features_used` ni `logins`. La pregunta abierta 1 del ADR-003 (señal de fase de onboarding) no tiene vista ni medición.
- El harness no calcula recall ponderado por MRR ni detección temprana (si la cuenta ya estaba marcada en k = 3). Es la pregunta abierta 2 del ADR-003.
- No existe combinación de subpuntajes en un score único, ni umbral, ni matriz de confusión: eso es lo que pide A3.

## Regla del mes de corte: la tensión central

`mart_usage.sql` y el ADR-003 aplican el mismo desplazamiento k a los dos grupos: mes de referencia (mes de `churn_date` para bajas, 2024-08 para activas) menos k meses. Así ambos grupos se evalúan con la misma recencia.

El caso pide "2-3 meses antes de churn_date" para las bajas y "en el mes más reciente" para las activas. Leído literal, compara una baja evaluada con datos de hace 2 o 3 meses contra una activa evaluada con datos de hoy. No es fuga de la etiqueta, pero sí es una asimetría de recencia: la activa luce mejor por tener datos frescos, no por estar más sana, y eso puede inflar el AUC sin que el modelo sea mejor.

## Áreas afectadas

- `worky_engine/sql/marts/mart_usage.sql`: fuente de los tres subpuntajes de uso; A3 la lee, no la modifica.
- Vista nueva de soporte ventanada (por ejemplo `mart_support_asof`) que respete el mes de corte; `mart_support.sql` queda para lo que ya consume.
- `worky_engine/harness/backtest.py`: candidato a extender con recall ponderado por MRR y detección temprana, o base de un módulo nuevo `worky_engine/health/`.
- `worky_engine/analysis/runner.py` y `worky_engine/cli.py`: patrón a espejear para el comando `health`.
- `tests/test_usage_trend.py` y `tests/test_support_commercial.py`: patrón de pruebas.
- Ninguna fuente cruda ni golden de A0 o A1 se modifica.

## Opciones

### Forma del score

1. Suma ponderada de subpuntajes normalizados (0 a 100), pesos por juicio verificados con el harness. Es el patrón de Vitally y Gainsight (`docs/research/01-bi-revops-data-architecture.md`) y lo que el ADR-003 adelantó. Interpretable línea por línea; no depende de tener muchos eventos de churn; cada peso se justifica con el AUC individual. Costo: los pesos son juicio, no aprendidos.
2. Pesos ajustados con una regresión logística simple. Pesos "óptimos" sobre este dataset, pero con 90 eventos de churn (78 con uso) el sobreajuste es probable, el caso dice que no hace falta ML formal, y el score deja de explicarse en una oración.
3. Reglas por niveles (un solo subpuntaje en el peor decil dispara riesgo alto). Captura caídas brutales que un promedio diluye, pero es más difícil de auditar con precisión y recall y no se compara limpio contra el harness.

### Política de umbral

- Corte fijo (por ejemplo score menor a 40): simple y estable, pero ignora cuántas cuentas puede atender el equipo.
- Top-N por capacidad de CSM (7 CSM por un tamaño de cartera manejable): conecta el umbral con una restricción real; es la pregunta abierta 2 del ADR-003.
- Punto sobre la curva de precisión y recall: más "óptimo" en papel, pero el más difícil de explicar y el más inestable con 90 eventos.

## Recomendación

Espejear el patrón `analyze` con un comando `health` (`python -m worky_engine health --data-dir ... --out-dir outputs/health`), reusar `mart_usage` para los tres subpuntajes de uso, agregar una vista de soporte ventanada, y sumar un subpuntaje de onboarding solo si la medición confirma que separa el churn temprano (la mitad del churn ocurre en los primeros meses). Forma del score: suma ponderada con pesos por juicio verificados con el harness. Umbral: reportar un corte fijo como referencia y un top-N ligado a la capacidad de los 7 CSM como el que se usaría en producción, con sensibilidad en k = 3. Mes de corte: el mismo k para bajas y activas (regla del ADR-003), documentando qué cambia con la lectura literal, como hizo el ADR-004.

Sobre A3.4: un falso positivo cuesta horas de CSM en una cuenta sana; un falso negativo cuesta el MRR completo de la cuenta que se va. Con 7 CSM y el recall ponderado por MRR como métrica, el error más caro es el falso negativo en una cuenta grande, y el umbral debe sesgarse hacia recall aunque baje la precisión.

## Riesgos y preguntas de producto

- Mes de corte para las activas: mismo k que las bajas (recomendado) o el mes más reciente (lectura literal).
- Forma del score: suma ponderada con pesos por juicio (recomendado), logística, o reglas.
- Política de umbral: corte fijo, top-N por capacidad de CSM (recomendado reportar ambos), o punto de la curva.
- Cuentas sin historia suficiente: banda aparte "sin historia", nunca "sanas" por default (ADR-003), y contadas en el denominador del recall como no detectables.
- Contexto comercial (canal, segmento): fuera del health score, reportado como factor de riesgo aparte (recomendado), o dentro como subpuntaje.
- `sdd-research`: no necesaria, el documento de research ya cubre los patrones de health score.

## Listo para propuesta

Sí, una vez confirmadas las decisiones anteriores con las mediciones de la sección siguiente.

## Mediciones de señales (solo lectura, corridas por el orquestador después de la exploración)

Tablas completas en `measurements.md` (misma carpeta). Convenciones del harness: mes de referencia = mes de churn para bajas y 2024-08 para activas; mes de corte = referencia menos k; nada fechado después del mes de corte entra a ninguna señal. Denominador del recall: las 89 empresas con churn y cuenta de producto.

Tamaño de los grupos con al menos tres meses de uso al corte: 67 de 89 bajas y 518 de 561 activas en k = 2 (10 bajas sin ningún mes de uso, 18 con uno o dos); 56 de 89 y 492 de 561 en k = 3.

| Señal (k = 2; k = 3 entre paréntesis) | Definida | AUC |
|---|---|---|
| Momentum EWMA 3 contra 9 | 90.0 % | 0.999 (0.901) |
| Cambio mes a mes de `active_users` | 95.4 % | 0.978 (0.898) |
| Caída desde el mejor promedio de 3 meses | 90.0 % | 0.832 (0.630) |
| Tickets en los 3 meses hasta el corte (total, urgentes, proporción urgente) | 91 / 91 / 37 % | 0.462 / 0.509 / 0.535 |
| CSAT promedio en esa ventana | 28.6 % | 0.498 |
| Tickets de toda la vida hasta el corte | 91.2 % | 0.244 |
| Tickets de toda la vida sin importar fecha (lo que hace `mart_support` hoy) | 91.2 % | 0.430 |
| Activación en los primeros 3 meses (nóminas, logins, features, usuarios) | 90.0 % | 0.492 / 0.587 / 0.535 / 0.590 |
| Antigüedad (meses desde el alta al corte) | 100 % | 0.762 (0.762) |
| Canal de adquisición (tasa de churn del canal, leave-one-out) | 100 % | 0.426 |
| MRR (menor es más riesgo) | 100 % | 0.555 |

Lo que dicen estos números: las tres señales de uso separan; el soporte no separa (alrededor de 0.5, una moneda al aire), y contado de toda la vida apunta en dirección contraria (más tickets, menos churn, porque las cuentas viejas acumulan tickets y sobreviven); la activación temprana tampoco separa; la antigüedad sí, y tiene cobertura total, así que ve a las cuentas que ninguna señal de uso puede ver. La fuga de `mart_support` no infla el AUC en este dataset, pero sigue siendo fuga de diseño y se cierra igual.

| Score combinado (k = 2) | AUC | 10 % marcadas: precisión / recall / recall por MRR | 15 % | 20 % |
|---|---|---|---|---|
| (i) Uso con pesos iguales (tres subpuntajes) | 0.970 | 0.952 / 0.663 / 0.526 | 0.720 / 0.753 / 0.839 | 0.540 / 0.753 / 0.839 |
| (ii) Uso 70 % + antigüedad 15 % + activación 15 % | 0.953 | 0.662 / 0.483 / 0.260 | 0.724 / 0.798 / 0.843 | 0.631 / 0.921 / 0.900 |
| (iii) Uso 80 % + soporte 20 % | 0.904 | 0.846 / 0.618 / 0.521 | 0.673 / 0.742 / 0.576 | 0.538 / 0.787 / 0.850 |

Con el score (i) al 15 %, 67 bajas quedan marcadas en k = 2; 56 de ellas también tenían historia en k = 3 y 29 (52 %) ya estaban marcadas un mes antes. Diez de las 89 bajas (11 %) no se pueden detectar en k = 2 por falta de historia de uso; el recall las cuenta en el denominador. Capacidad: marcar el 10, 15 o 20 % de las 541 activas con score definido son 54, 81 o 108 cuentas, es decir 7.7, 11.6 o 15.4 por cada uno de los 7 CSM.
