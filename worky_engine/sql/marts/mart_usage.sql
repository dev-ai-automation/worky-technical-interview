-- Tendencia de uso y resguardo contra fuga de datos (ADR-003, seccion 4.4
-- del diseno). El mes de referencia se recalcula aqui con la misma
-- formula que usa `mart_master_dataset` (mes de `churn_date` para una
-- empresa con baja, `MAX(month)` de `stg_product_usage` para una activa):
-- la duplicacion es intencional, porque `mart_master_dataset` va a
-- consumir esta vista y un ciclo entre las dos no es posible.
--
-- `trend_asof_month` es el mes de referencia menos 2 meses (k = 2). Solo
-- entran al calculo de `trend_usage` las filas de uso con
-- `month <= trend_asof_month`: ese filtro, en `usage_window`, es el
-- resguardo contra fuga de datos completo.
--
-- DuckDB no trae una funcion de promedio movil exponencialmente
-- ponderado, asi que se calcula con su forma cerrada: alpha = 2/(span+1),
-- pesos (1-alpha)^k normalizados por su propia suma, con k la distancia
-- en meses hacia atras desde `trend_asof_month`. Esa forma cerrada es
-- exactamente lo que produce `pandas.Series.ewm(span=s, adjust=True)
-- .mean()` en su ultimo punto, siempre que la serie no tenga huecos
-- internos (contrato `assert_usage_months_no_internal_gaps`, tarea 3.12).
--
-- `active_users_latest` y `active_users_avg` describen el mes de
-- referencia y la serie completa hasta el (no hasta `trend_asof_month`):
-- son columnas descriptivas y no llevan el resguardo de 2 meses, tal
-- como fija la seccion 2 del diseno.
CREATE OR REPLACE VIEW mart_usage AS
WITH company_reference AS (
    SELECT
        c.master_id,
        c.account_id,
        CASE WHEN c.churn_date IS NOT NULL THEN strftime(c.churn_date, '%Y-%m')
             ELSE (SELECT MAX(month) FROM stg_product_usage) END AS reference_month
    FROM mart_company_core c
),
company_asof AS (
    SELECT
        master_id,
        account_id,
        reference_month,
        strftime(
            CAST(reference_month || '-01' AS DATE) - INTERVAL 2 MONTH, '%Y-%m'
        ) AS trend_asof_month
    FROM company_reference
),
usage_window AS (
    -- Resguardo contra fuga de datos: ninguna fila con `month` posterior
    -- a `trend_asof_month` entra aqui.
    SELECT
        a.master_id,
        u.active_users,
        datediff(
            'month',
            CAST(u.month || '-01' AS DATE),
            CAST(a.trend_asof_month || '-01' AS DATE)
        ) AS k
    FROM company_asof a
    JOIN stg_product_usage u ON u.account_id = a.account_id AND u.month <= a.trend_asof_month
),
ewma AS (
    SELECT
        master_id,
        COUNT(*) AS usage_months,
        SUM(active_users * pow(1 - 2.0 / (3 + 1), k)) / SUM(pow(1 - 2.0 / (3 + 1), k)) AS ewma_3,
        SUM(active_users * pow(1 - 2.0 / (9 + 1), k)) / SUM(pow(1 - 2.0 / (9 + 1), k)) AS ewma_9
    FROM usage_window
    GROUP BY master_id
),
reference_window AS (
    -- Serie completa hasta el mes de referencia (sin el resguardo de 2
    -- meses), solo para las dos columnas descriptivas.
    SELECT a.master_id, u.month, u.active_users
    FROM company_asof a
    JOIN stg_product_usage u ON u.account_id = a.account_id AND u.month <= a.reference_month
),
descriptive_totals AS (
    SELECT master_id, MAX(month) AS latest_month, AVG(active_users) AS active_users_avg
    FROM reference_window
    GROUP BY master_id
),
descriptive AS (
    SELECT t.master_id, w.active_users AS active_users_latest, t.active_users_avg
    FROM descriptive_totals t
    JOIN reference_window w ON w.master_id = t.master_id AND w.month = t.latest_month
)
SELECT
    ca.master_id,
    ca.trend_asof_month,
    COALESCE(e.usage_months, 0) AS usage_months,
    d.active_users_latest,
    printf('%.2f', d.active_users_avg) AS active_users_avg,
    CASE
        WHEN COALESCE(e.usage_months, 0) = 0 THEN 'no_usage'
        WHEN e.usage_months < 3 THEN 'insufficient_history'
        ELSE 'computed'
    END AS trend_status,
    CASE
        WHEN COALESCE(e.usage_months, 0) < 3 THEN NULL
        WHEN e.ewma_9 = 0 THEN '0.000000'
        ELSE printf('%.6f', e.ewma_3 / e.ewma_9 - 1)
    END AS trend_usage
FROM company_asof ca
LEFT JOIN ewma e ON e.master_id = ca.master_id
LEFT JOIN descriptive d ON d.master_id = ca.master_id;
