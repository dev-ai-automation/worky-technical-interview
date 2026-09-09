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
