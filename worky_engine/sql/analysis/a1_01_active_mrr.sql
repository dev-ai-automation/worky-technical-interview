-- Motor: DuckDB 1.5.5. A1.1, MRR activo por segmento e industria (ADR-004).
-- Activa significa churn_date nulo. Dos columnas de MRR: la que reporta
-- el CRM (mrr_source = 'crm') y el total con valores imputados del
-- ADR-002 (mrr_source in 'crm' o 'imputed_from_deal'), mas una fila de
-- totales via GROUPING SETS. row_type ordena la fila de totales al
-- final porque 'segment' es menor que 'total' en orden alfabetico.
CREATE OR REPLACE VIEW analysis_a1_01_active_mrr AS
WITH active AS (
    SELECT segment, industry, mrr_source,
           CAST(NULLIF(mrr_mxn, '') AS DECIMAL(14,2)) AS mrr_mxn
    FROM mart_master_dataset
    WHERE churn_date IS NULL
),
grouped AS (
    SELECT segment, industry,
           GROUPING(segment, industry)                                  AS grouping_id,
           COUNT(*)                                                     AS companies_active,
           CAST(SUM(CASE WHEN mrr_source = 'imputed_from_deal' THEN 1 ELSE 0 END) AS BIGINT) AS companies_imputed,
           CAST(SUM(CASE WHEN mrr_source = 'unresolved' THEN 1 ELSE 0 END) AS BIGINT) AS companies_unresolved,
           SUM(CASE WHEN mrr_source = 'crm' THEN mrr_mxn ELSE 0 END)     AS mrr_crm_mxn,
           SUM(COALESCE(mrr_mxn, 0))                                     AS mrr_total_mxn
    FROM active
    GROUP BY GROUPING SETS ((segment, industry), ())
)
SELECT
    CASE WHEN grouping_id = 3 THEN 'TOTAL' ELSE segment END              AS segment,
    CASE WHEN grouping_id = 3 THEN '' ELSE COALESCE(industry, '') END    AS industry,
    companies_active, companies_imputed, companies_unresolved,
    printf('%.2f', mrr_crm_mxn)                                          AS mrr_crm_mxn,
    printf('%.2f', mrr_total_mxn)                                        AS mrr_total_mxn,
    CASE WHEN grouping_id = 3 THEN 'total' ELSE 'segment' END             AS row_type
FROM grouped
ORDER BY row_type, segment, industry;
