-- Motor: DuckDB 1.5.5. A1.2, caida relativa de uso al churn (ADR-004,
-- formula literal del caso, ADR-003 sobre el resguardo del mes de baja).
-- Promedio de active_users en los tres meses calendario anteriores al
-- mes de baja (ese mes queda fuera) contra el promedio de los primeros
-- tres meses con uso de la cuenta. windows_overlap marca a las cuentas
-- con menos de seis meses de uso, donde las dos ventanas pueden
-- compartir al menos un mes.
CREATE OR REPLACE VIEW analysis_a1_02_usage_drop AS
WITH churned AS (
    SELECT master_id, hubspot_id, company_name, account_id, churn_date,
           substr(churn_date, 1, 7) AS churn_month
    FROM mart_master_dataset
    WHERE churn_status = 'churned' AND account_id IS NOT NULL
),
series AS (
    SELECT c.master_id, u.month, u.active_users,
           ROW_NUMBER() OVER (PARTITION BY c.master_id ORDER BY u.month) AS month_rank
    FROM churned c
    JOIN stg_product_usage u ON u.account_id = c.account_id
),
-- primeros tres meses con uso por orden calendario, no los tres meses
-- siguientes al signup_date: la cuenta de producto puede arrancar despues
first_window AS (
    SELECT master_id, AVG(active_users) AS avg_first
    FROM series WHERE month_rank <= 3 GROUP BY master_id
),
-- los tres meses calendario anteriores al mes de baja; el mes de baja
-- queda fuera (ADR-003, misma razon que el resguardo de trend_usage)
last_window AS (
    SELECT s.master_id, AVG(s.active_users) AS avg_last
    FROM series s
    JOIN churned c ON c.master_id = s.master_id
    WHERE s.month < c.churn_month
      AND s.month >= strftime(CAST(c.churn_month || '-01' AS DATE) - INTERVAL 3 MONTH, '%Y-%m')
    GROUP BY s.master_id
),
totals AS (SELECT master_id, COUNT(*) AS usage_months FROM series GROUP BY master_id)
SELECT
    c.master_id, c.hubspot_id, c.company_name, c.account_id, c.churn_date, c.churn_month,
    COALESCE(t.usage_months, 0)                                   AS usage_months,
    printf('%.2f', f.avg_first)                                   AS avg_users_first_3,
    printf('%.2f', l.avg_last)                                    AS avg_users_last_3_before_churn,
    CASE WHEN t.usage_months IS NULL OR l.avg_last IS NULL OR f.avg_first = 0 THEN NULL
         ELSE printf('%.6f', (f.avg_first - l.avg_last) / f.avg_first) END AS drop_relative,
    CASE WHEN t.usage_months IS NULL THEN 'no_usage'
         WHEN l.avg_last IS NULL     THEN 'final_window_empty'
         WHEN f.avg_first = 0        THEN 'initial_avg_zero'
         ELSE 'computed' END                                       AS drop_status,
    (COALESCE(t.usage_months, 0) < 6)                              AS windows_overlap
FROM churned c
LEFT JOIN totals t       ON t.master_id = c.master_id
LEFT JOIN first_window f ON f.master_id = c.master_id
LEFT JOIN last_window l  ON l.master_id = c.master_id
ORDER BY drop_relative DESC NULLS LAST, master_id;
