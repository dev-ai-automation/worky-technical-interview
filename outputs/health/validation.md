# Reporte de validación del health score de A3

## Encabezado

| Campo | Valor |
|---|---|
| motor | DuckDB 1.5.5 |
| dataset_asof | 2024-08-31 |
| ruleset_version | 1.0.0 |
| comando | python -m worky_engine health --data-dir <ruta> --out-dir outputs/health |
| empresas evaluadas en este dataset | 650 |
| bajas en este dataset | 89 |
| no detectables (banda 'sin historia') en este dataset | 22 de 89 bajas (4 con 0 meses, 6 con 1 mes, 12 con 2 meses) |
| libro activo con health_score definido en este dataset | 518 |

**Conteo por banda en este dataset:**

| Banda | Empresas |
|---|---|
| riesgo alto | 145 |
| riesgo medio | 78 |
| riesgo bajo | 362 |
| sin historia | 65 |

**Mes de referencia y mes de corte:** el mes de referencia es el mes de `churn_date` para una empresa dada de baja, o el cierre de los datos (`dataset_asof`) para una activa. El mes de corte es el mes de referencia menos dos meses, con el mismo desplazamiento para las dos poblaciónes en este dataset (ADR-003, ADR-005).

## Fórmula y pesos

En voz alta: el `health_score` es 0.35 veces el momentum de uso, más 0.20 veces el cambio mes a mes, más 0.15 veces la caída desde el mejor promedio de tres meses, más 0.30 veces la antigüedad. Cada subpuntaje ya está normalizado de 0 a 100 por rango percentil dentro de la población evaluada, con 100 como el valor más sano (ADR-005).

| Subpuntaje | Peso | Definición |
|---|---|---|
| Momentum de uso | 0.35 | EWMA de 3 meses contra EWMA de 9 meses, en el mes de corte |
| Cambio mes a mes | 0.20 | active_users del último mes contra el mes anterior, en el mes de corte |
| Caída desde el mejor promedio | 0.15 | promedio de los últimos 3 meses contra el mejor promedio movil de 3 meses |
| Antigüedad | 0.30 | meses desde signup_date hasta el mes de corte, recortado a cero |

Una empresa con menos de tres meses de uso al mes de corte no recibe los tres subpuntajes de uso ni `health_score`: cae en la banda 'sin historia' y cuenta en el denominador del recall general como no detectable, aunque si recibe su subpuntaje de antigüedad (ADR-003, ADR-005).

**Resguardo de fuga:** ninguna fila de uso fechada despues del mes de corte entra a ningún subpuntaje; los tickets se leen de una ventana de tres meses que termina en el mes de corte (`mart_support_asof`, distinta de `mart_support`), y los primeros tres meses de activacion solo cuentan si el tercero cae en el mes de corte o antes.

## AUC por señal, en este dataset

AUC es la probabilidad de que una empresa dada de baja muestre peor señal que una activa; 0.5 es una moneda al aire. Se mide a k = 2, el mes de corte principal.

| Señal | AUC (k = 2, en este dataset) | Peso en la fórmula |
|---|---|---|
| Momentum de uso (EWMA span 3 contra span 9) | 1.000 | 0.35 |
| Cambio mes a mes de active_users | 0.979 | 0.20 |
| Caída desde el mejor promedio de 3 meses | 0.832 | 0.15 |
| Antigüedad al mes de corte | 0.762 | 0.30 |
| Tickets totales en la ventana de 3 meses | 0.465 | 0.00 |
| Tickets urgentes en la ventana de 3 meses | 0.508 | 0.00 |
| CSAT promedio en la ventana de 3 meses | 0.498 | 0.00 |
| Activacion en los primeros 3 meses de uso | 0.588 | 0.00 |

Las señales de soporte (tickets totales, urgentes y CSAT en la ventana de tres meses) y la activacion de los primeros tres meses se miden y se publican, pero pesan cero en la fórmula: en este dataset ninguna separa tan bien como las cuatro señales que si entran al score, y se muestran aquí para que nadie tenga que creer que no sirven en vez de verlo medido (ADR-005).

## Métricas de validación contra churn_date, en este dataset

AUC del `health_score` en este dataset: 0.997.

| Tasa de marcado | Marcadas | Precisión | Recall general | Recall detectable | Recall ponderado por MRR |
|---|---|---|---|---|---|
| 10 % | 119 | 0.563 | 0.753 | 1.000 | 0.608 |
| 15 % | 145 | 0.462 | 0.753 | 1.000 | 0.608 |
| 20 % | 171 | 0.392 | 0.753 | 1.000 | 0.608 |
| corte fijo (score < 40) | 154 | 0.435 | 0.753 | no aplica | no aplica |

El 15 % es el umbral operativo: reparte el trabajo del libro activo entre los CSM. El corte fijo de referencia se reporta aparte, solo como dato adicional, sin sustituir al umbral operativo (ADR-005).

## Matriz de confusión al 15 %, en este dataset

| Celda | Empresas |
|---|---|
| Verdaderos positivos | 67 |
| Falsos positivos | 78 |
| Falsos negativos | 22 (de los cuales 22 son no detectables por falta de historia) |
| Verdaderos negativos | 483 |

## Empresas no detectables, en este dataset

22 de las 89 bajas de este dataset (24.7 %) caen en la banda 'sin historia': tienen menos de tres meses de uso al mes de corte, así que nunca reciben `health_score` y nunca pueden marcarse, sin importar el peso de ningún subpuntaje. Cuentan en el denominador del recall general porque son bajas reales, aunque el modelo por diseño no pueda verlas todavía (ADR-005, Adenda 1). Desglose por meses de uso al mes de corte: 4 con 0 meses de uso, 6 con 1 mes de uso, 12 con 2 meses de uso.

## Detección temprana en k = 3, en este dataset

De las bajas marcadas al 15 % con el mes de corte principal (k = 2), 56 tenian suficiente historia de uso para tener `health_score` también en k = 3, y de esas, 52 ya estaban marcadas un mes antes (0.929 de las que se pudieron evaluar): se habrian detectado con un mes extra de anticipacion.

## Sensibilidades, en este dataset

| Corrida | AUC | Recall al 20 % | Qué cambia |
|---|---|---|---|
| k = 3 (un mes de corte más atras) | 0.955 | 0.607 | El AUC y el recall bajan frente a k = 2: con un mes menos de datos, menos empresas llegan a los tres meses de historia que exige el score de uso. |
| Lectura literal (activas en su mes más reciente) | 0.995 | 0.753 | Compara recencia y no salud: las activas se evaluan con datos más frescos que las bajas, y por eso se reporta solo como sensibilidad, nunca como regla principal. |
| Pesos iguales (0.25 cada subpuntaje) | 0.991 | 0.753 | El AUC y el recall casi no cambian frente a los pesos del ADR-005: las cuatro señales de uso ya separan bien por si solas, y el reparto exacto de pesos entre ellas importa menos que juntarlas. |
| Convencion del harness (percentil sobre la población completa) | 0.997 | 0.753 | Usa el mismo `health_score`, pero el umbral sale del percentil de bajas y activas juntas en vez del libro activo: sirve para comparar contra measurements.md, no como regla operativa (D16). |

## Capacidad por CSM, en este dataset (7 CSM)

| Tasa de marcado | Libro activo con score | Marcadas | Marcadas por CSM |
|---|---|---|---|
| 10 % | 518 | 52 | 7.4 |
| 15 % | 518 | 78 | 11.1 |
| 20 % | 518 | 104 | 14.9 |

## Respuesta a A3.4: qué error cuesta más, en este dataset

Un falso positivo (marcar una cuenta sana como riesgo) cuesta horas de un CSM revisando una cuenta que en realidad está bien: es un costo real, pero acotado y recuperable. Muchos falsos positivos significan un umbral demasiado estricto, precisión baja y horas de CSM gastadas en cuentas sanas.

Un falso negativo (no marcar una cuenta que si se va) cuesta el MRR completo de esa cuenta cuando hace churn sin que nadie haya intervenido antes: el equipo pierde el ingreso y la oportunidad de retenerla. Muchos falsos negativos significan un umbral demasiado laxo y MRR perdido sin alerta previa.

En este dataset, el error más caro para Worky es un falso negativo en una cuenta grande: perder una cuenta de MRR alto sin ninguna alerta previa cuesta más que las horas de varios CSM revisando cuentas sanas. Por eso el umbral operativo se sesga hacia recall aunque baje la precisión, y la métrica que mejor lo mide es el recall ponderado por MRR, no el recall simple: ahi una cuenta grande que se detecta pesa más que diez cuentas pequenas.

**Hallazgo de onboarding, para la Parte B (ADR-005, Adenda 1):** casi una cuarta parte de las bajas de este dataset ocurre antes de que la cuenta acumule tres meses de uso, así que el health score, por diseño, todavía no las puede ver. Esto no se corrige con otro reparto de pesos: las cuentas en su primer trimestre necesitan su propia señal o su propio playbook de onboarding, aparte del health score, para que el riesgo de baja temprana no quede invisible hasta que ya sea tarde para actuar.

## Contexto comercial, fuera del score, en este dataset

`acquisition_channel` y `segment` se miden y se publican como factores de riesgo comerciales, pero no entran a la fórmula del `health_score`: en este dataset explican churn a nivel de portafolio, no a nivel de cuenta individual, así que se reportan aparte (ADR-005).

**Por canal de adquisición:**

| acquisition_channel | n | Tasa de baja | Tasa de marcado al 15 % |
|---|---|---|---|
| Evento | 108 | 8.3 % | 17.6 % |
| Organic | 92 | 19.6 % | 18.5 % |
| Outbound SDR | 90 | 14.4 % | 25.6 % |
| Paid Search | 86 | 12.8 % | 22.1 % |
| Partner | 85 | 15.3 % | 23.5 % |
| Referral | 100 | 12.0 % | 25.0 % |
| Webinar | 89 | 14.6 % | 24.7 % |

**Por segmento:**

| segment | n | Tasa de baja | Tasa de marcado al 15 % |
|---|---|---|---|
| Enterprise | 86 | 2.3 % | 12.8 % |
| Mid-Market | 206 | 13.1 % | 20.9 % |
| SMB | 358 | 16.8 % | 25.4 % |

## Referencias

- ADR-003: ventana de tendencia de uso y resguardo de fuga (`docs/decisións/ADR-003-usage-trend-and-leakage-guard.md`).
- ADR-004: definiciónes de las consultas de A1 (`docs/decisións/ADR-004-sql-analysis-definitions.md`).
- ADR-005: el modelo del health score, sus pesos y la Adenda 1 sobre el techo del recall (`docs/decisións/ADR-005-health-score-model.md`).

## Apéndice: SQL de las vistas de health, tal como está en cada archivo

### `h1_company_asof.sql`

```sql
-- Motor: DuckDB 1.5.5. Identidad, mes de referencia y mes de corte por
-- empresa (ADR-003 y ADR-005, decisiones D6 y D7 del diseno de A3).
--
-- El desplazamiento sale de `health_params`, que el corredor crea con
-- una sola fila antes de este archivo (`CROSS JOIN health_params p`):
-- `k_months` aplica a las empresas con baja y `active_offset` a las
-- activas. En la corrida principal ambos valen 2, con el mismo
-- desplazamiento para las dos poblaciones (requirement "mes de corte
-- igual para bajas y activas"). La lectura literal del caso (activas
-- evaluadas en su propio mes de referencia) pone `active_offset` en 0
-- y solo corre como sensibilidad (decision D8), nunca como regla
-- principal.
--
-- `reference_month` es el mes de `churn_date` para una empresa con
-- baja, o el cierre de los datos derivado de la sabana para una
-- activa (decision D6): nunca una constante escrita a mano, porque
-- `dataset_asof` sale de los datos y cambia si el dataset cambia.
CREATE OR REPLACE VIEW health_company_asof AS
WITH dataset_end AS (
    -- Cierre de los datos: la fecha maxima de dataset_asof, que ya es
    -- la misma fecha para toda la sabana (identity_resolution la fija
    -- una sola vez para las siete tablas de origen).
    SELECT substr(MAX(dataset_asof), 1, 7) AS end_month FROM mart_master_dataset
),
reference AS (
    SELECT
        m.master_id, m.hubspot_id, m.account_id, m.vitally_id,
        m.segment, m.acquisition_channel, m.mrr_mxn, m.signup_date,
        (m.churn_status = 'churned') AS churned,
        CASE WHEN m.churn_status = 'churned' THEN substr(m.churn_date, 1, 7)
             ELSE e.end_month END AS reference_month,
        CASE WHEN m.churn_status = 'churned' THEN p.k_months
             ELSE p.active_offset END AS offset_months
    FROM mart_master_dataset m
    CROSS JOIN dataset_end e
    CROSS JOIN health_params p
)
SELECT *,
       strftime(
           CAST(reference_month || '-01' AS DATE) - INTERVAL (offset_months) MONTH, '%Y-%m'
       ) AS asof_month
FROM reference
ORDER BY master_id;
```

### `h2_usage_signals.sql`

```sql
-- Motor: DuckDB 1.5.5. Las tres senales de uso del ADR-003 y del
-- ADR-005, recalculadas en `asof_month` de `health_company_asof` (h1):
-- distinto de `trend_asof_month` de `mart_usage`, que aplica k = 2 fijo
-- a bajas y activas con su propia formula (`mart_usage.sql` queda
-- intacta). Reusa la misma forma cerrada de EWMA que ya documenta
-- `mart_usage.sql` (alpha = 2 / (span + 1), pesos (1 - alpha) ^ k
-- normalizados por su propia suma), verificada contra `pandas.Series
-- .ewm(span=s, adjust=True).mean()` en tests/test_usage_trend.py y, en
-- este paquete, en tests/test_health_equivalence.py contra `_features`
-- del harness.
--
-- Resguardo de fuga (decision D11): `usage_window` solo admite filas
-- con `u.month <= a.asof_month`. `per_company` agrega desde
-- `usage_window`, y la SELECT final parte de `health_company_asof`
-- (LEFT JOIN) para que toda empresa reciba una fila, incluidas las que
-- no tienen ninguna fila de uso hasta el corte (usage_months_asof = 0).
--
-- Denominadores degenerados (decision D15), definidos en 0.0 en vez de
-- NULL: `ewma_9 = 0`, el mes previo en cero, o el mejor promedio movil
-- de 3 meses en cero. Con `usage_months_asof >= 3` las tres senales
-- siempre quedan definidas.
CREATE OR REPLACE VIEW health_usage_signals AS
WITH usage_window AS (
    SELECT
        a.master_id, u.month, u.active_users,
        datediff(
            'month', CAST(u.month || '-01' AS DATE), CAST(a.asof_month || '-01' AS DATE)
        ) AS k
    FROM health_company_asof a
    JOIN stg_product_usage u ON u.account_id = a.account_id AND u.month <= a.asof_month
),
positioned AS (
    -- Posicion cronologica por empresa, igual que `_features` del
    -- harness (`values[-1]`, `values[-2]`, `values[-3:]`, y el mejor
    -- promedio movil de 3 meses via `rolling(3).mean().max()`).
    SELECT
        master_id, active_users, k,
        LAG(active_users) OVER (PARTITION BY master_id ORDER BY month) AS prev_month,
        row_number() OVER (PARTITION BY master_id ORDER BY month DESC) AS rank_desc,
        AVG(active_users) OVER (
            PARTITION BY master_id ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS rolling_avg_3,
        COUNT(*) OVER (
            PARTITION BY master_id ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS rolling_count
    FROM usage_window
),
per_company AS (
    SELECT
        master_id,
        COUNT(*) AS usage_months_asof,
        SUM(active_users * pow(1 - 2.0 / (3 + 1), k)) / SUM(pow(1 - 2.0 / (3 + 1), k)) AS ewma_3,
        SUM(active_users * pow(1 - 2.0 / (9 + 1), k)) / SUM(pow(1 - 2.0 / (9 + 1), k)) AS ewma_9,
        MAX(CASE WHEN rank_desc = 1 THEN active_users END) AS last_month,
        MAX(CASE WHEN rank_desc = 1 THEN prev_month END) AS prev_of_last,
        AVG(CASE WHEN rank_desc <= 3 THEN active_users END) AS avg_last3,
        MAX(CASE WHEN rolling_count = 3 THEN rolling_avg_3 END) AS best_avg_3
    FROM positioned
    GROUP BY master_id
)
SELECT
    a.master_id,
    COALESCE(p.usage_months_asof, 0) AS usage_months_asof,
    CASE WHEN COALESCE(p.usage_months_asof, 0) < 3 THEN NULL
         WHEN p.ewma_9 = 0 THEN 0.0
         ELSE p.ewma_3 / p.ewma_9 - 1 END AS sig_momentum,
    CASE WHEN COALESCE(p.usage_months_asof, 0) < 3 THEN NULL
         WHEN p.prev_of_last = 0 THEN 0.0
         ELSE p.last_month / p.prev_of_last - 1 END AS sig_mom,
    CASE WHEN COALESCE(p.usage_months_asof, 0) < 3 THEN NULL
         WHEN p.best_avg_3 = 0 THEN 0.0
         ELSE p.avg_last3 / p.best_avg_3 - 1 END AS sig_drawdown
FROM health_company_asof a
LEFT JOIN per_company p ON p.master_id = a.master_id;
```

### `h3_tenure.sql`

```sql
-- Motor: DuckDB 1.5.5. Antiguedad en meses desde `signup_date` hasta
-- `asof_month` (h1): la unica de las cuatro senales con cobertura
-- total (requirement "los cuatro subpuntajes normalizados por
-- percentil", escenario "antiguedad con cobertura total"), incluidas
-- las empresas que caen en la banda "sin historia" por falta de uso.
--
-- `GREATEST(..., 0)` recorta a cero una empresa dada de alta despues
-- de su propio mes de corte: sin este recorte, una alta muy reciente
-- entregaria un `datediff` negativo, que ninguna otra senal del score
-- puede producir.
CREATE OR REPLACE VIEW health_tenure AS
SELECT
    master_id,
    GREATEST(datediff('month', CAST(signup_date AS DATE), CAST(asof_month || '-01' AS DATE)), 0) AS sig_tenure
FROM health_company_asof;
```

### `h4_support_asof.sql`

```sql
-- Motor: DuckDB 1.5.5. Ventana de soporte de tres meses terminando en
-- `asof_month` (h1), distinta de `mart_support` (que agrega toda la
-- vida de la cuenta): `mart_support.sql` queda intacta, y esta vista
-- vive en `sql/health/` aunque conserva el prefijo `mart_` porque su
-- grano y su forma son las de un mart (decision D10 del diseno).
--
-- Resguardo de fuga (decision D11): `created_date` es una fecha, no un
-- mes, asi que el corte es por dia. El limite inferior es el primer
-- dia de los tres meses que terminan en `asof_month`
-- (`asof_month - 2 meses`), y el limite superior se escribe como
-- "antes del primer dia del mes siguiente al corte" para no depender
-- de cuantos dias tiene cada mes. Solo `priority = 'Urgent'` cuenta
-- como urgente; `csat_window_avg` promedia unicamente los tickets que
-- trajeron puntaje, igual que `mart_support.sql`.
CREATE OR REPLACE VIEW mart_support_asof AS
SELECT
    a.master_id,
    COUNT(t.ticket_id) AS tickets_window_total,
    -- CAST a BIGINT: SUM() de un CASE INTEGER da HUGEINT (mismo resguardo que mart_support.sql).
    CAST(SUM(CASE WHEN t.priority = 'Urgent' THEN 1 ELSE 0 END) AS BIGINT) AS tickets_window_urgent,
    CASE WHEN COUNT(t.csat_score) = 0 THEN NULL
         ELSE printf('%.2f', AVG(t.csat_score)) END AS csat_window_avg
FROM health_company_asof a
LEFT JOIN stg_tickets t
    ON t.vitally_id = a.vitally_id
   AND t.created_date >= CAST(a.asof_month || '-01' AS DATE) - INTERVAL 2 MONTH
   AND t.created_date < CAST(a.asof_month || '-01' AS DATE) + INTERVAL 1 MONTH
GROUP BY a.master_id;
```

### `h5_activation.sql`

```sql
-- Motor: DuckDB 1.5.5. Activacion de los primeros 3 meses de uso,
-- senal de peso cero (ADR-005). El valor crudo es el promedio, sobre
-- esos tres meses, de las cuatro columnas de actividad temprana de
-- measurements.md (payroll_runs_completed, logins, features_used,
-- active_users); mas alto es mas sano, asi que `scoring.py` lo
-- normaliza por percentil sin invertir nada.
--
-- Resguardo de fuga (D11): los primeros 3 meses solo cuentan si el
-- tercero cae en `asof_month` (h1) o antes; si no, o si la cuenta
-- tiene menos de 3 meses de uso en total, `activation_raw` es NULL.
CREATE OR REPLACE VIEW health_activation AS
WITH first_three AS (
    SELECT
        a.master_id,
        u.month,
        u.payroll_runs_completed,
        u.logins,
        u.features_used,
        u.active_users,
        row_number() OVER (PARTITION BY a.master_id ORDER BY u.month ASC) AS month_rank
    FROM health_company_asof a
    JOIN stg_product_usage u ON u.account_id = a.account_id
),
eligible AS (
    SELECT
        master_id,
        MAX(month) AS third_month,
        AVG((payroll_runs_completed + logins + features_used + active_users) / 4.0) AS activation_avg
    FROM first_three
    WHERE month_rank <= 3
    GROUP BY master_id
    HAVING COUNT(*) = 3
)
SELECT
    a.master_id,
    CASE WHEN e.third_month IS NULL OR e.third_month > a.asof_month THEN NULL
         ELSE e.activation_avg END AS activation_raw
FROM health_company_asof a
LEFT JOIN eligible e ON e.master_id = a.master_id;
```

### `h6_asof_inputs.sql`

```sql
-- Motor: DuckDB 1.5.5. Une h1 a h5 en una sola fila por empresa
-- (decision D9 del diseno): la entrada que consume `scoring.py` para
-- calcular percentiles, bandas, marcas y la suma ponderada. Cada join
-- es por `master_id`, y las cinco vistas ya traen exactamente una fila
-- por empresa porque cada una parte de `health_company_asof`.
CREATE OR REPLACE VIEW health_asof_inputs AS
SELECT
    a.master_id, a.hubspot_id, a.account_id, a.vitally_id,
    a.segment, a.acquisition_channel, a.mrr_mxn, a.churned,
    a.signup_date, a.reference_month, a.asof_month,
    u.usage_months_asof, u.sig_momentum, u.sig_mom, u.sig_drawdown,
    t.sig_tenure,
    s.tickets_window_total, s.tickets_window_urgent, s.csat_window_avg,
    v.activation_raw
FROM health_company_asof a
JOIN health_usage_signals u ON u.master_id = a.master_id
JOIN health_tenure t ON t.master_id = a.master_id
JOIN mart_support_asof s ON s.master_id = a.master_id
JOIN health_activation v ON v.master_id = a.master_id
ORDER BY a.master_id;
```
