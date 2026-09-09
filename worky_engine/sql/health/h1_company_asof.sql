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
