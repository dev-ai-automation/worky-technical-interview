-- Motor: DuckDB 1.5.5. A1.3, retencion por cohorte de alta (ADR-004).
-- Cohorte por mes calendario de signup_date. Una cuenta sigue activa en
-- el mes k si no ha hecho churn k meses despues del alta: la empresa
-- que hace churn exactamente en el mes k (months_to_churn = k) ya no
-- cuenta como activa en k, por eso la comparacion es months_to_churn
-- estrictamente mayor a k. Las celdas de cohortes que todavia no
-- cumplen k meses al cierre de los datos quedan censoradas y vacias,
-- nunca calculadas con dato parcial. Formato largo: una fila por
-- cohorte y por k (D8); report.py la pivotea a matriz en el PR 3.
-- Una sola consulta con CTEs, tal como exige el ADR-004.
CREATE OR REPLACE VIEW analysis_a1_03_cohort_retention AS
WITH dataset_end AS (
    -- cierre de los datos derivado de la sabana, nunca escrito como
    -- constante: dataset_asof es la fecha maxima presente en las siete
    -- tablas (D9) y en este dataset da 2024-08-31
    SELECT substr(MAX(dataset_asof), 1, 7) AS end_month FROM mart_master_dataset
),
cohorts AS (
    SELECT substr(signup_date, 1, 7) AS cohort_month,
           CASE WHEN churn_date IS NULL THEN NULL
                ELSE datediff('month', CAST(signup_date AS DATE), CAST(churn_date AS DATE))
           END AS months_to_churn
    FROM mart_master_dataset
),
cohort_size AS (
    SELECT c.cohort_month, COUNT(*) AS cohort_size,
           datediff('month', CAST(c.cohort_month || '-01' AS DATE),
                             CAST(e.end_month || '-01' AS DATE)) AS months_elapsed
    FROM cohorts c CROSS JOIN dataset_end e
    GROUP BY c.cohort_month, months_elapsed
),
horizons AS (SELECT unnest([1, 3, 6, 12]) AS k),
cells AS (
    SELECT s.cohort_month, h.k, s.cohort_size, s.months_elapsed,
           SUM(CASE WHEN c.months_to_churn IS NULL OR c.months_to_churn > h.k
                    THEN 1 ELSE 0 END) AS retained
    FROM cohort_size s
    JOIN cohorts c ON c.cohort_month = s.cohort_month
    CROSS JOIN horizons h
    GROUP BY s.cohort_month, h.k, s.cohort_size, s.months_elapsed
)
SELECT cohort_month, k, cohort_size,
       -- texto para que el golden no muestre 23.0 cuando hay celdas censuradas nulas
       CASE WHEN months_elapsed < k THEN NULL ELSE CAST(retained AS VARCHAR) END AS retained,
       CASE WHEN months_elapsed < k THEN NULL
            ELSE printf('%.2f', 100.0 * retained / cohort_size) END AS retention_pct,
       CASE WHEN months_elapsed < k THEN 'censored' ELSE 'computed' END AS cell_status
FROM cells
ORDER BY cohort_month, k;
