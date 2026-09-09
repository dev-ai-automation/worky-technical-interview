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
