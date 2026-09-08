-- Ensambla el contrato completo del dataset maestro (seccion 2 del
-- diseno): identidad, atributos comerciales, MRR con su trazabilidad,
-- el estatus de baja, la tendencia de uso (`mart_usage`, PR 4a) y,
-- desde el PR 4b, soporte (`mart_support`) y comercial (`mart_commercial`).
-- `domain_label`, `ruleset_version` y `dataset_asof` cierran el PR 4b:
-- las dos ultimas salen tal cual del crosswalk via mart_company_core,
-- sin recalcularlas.
--
-- Fechas y montos salen como texto ya formateado (`strftime`, `printf`)
-- para que el CSV nunca dependa de como pandas imprima un Timestamp o
-- un flotante (decision D8 del diseno).
CREATE OR REPLACE VIEW mart_master_dataset AS
SELECT
    c.master_id,
    c.hubspot_id,
    c.account_id,
    c.vitally_id,
    c.confidence_tier,
    c.company_name,
    c.domain,
    c.domain_label,
    c.segment,
    c.industry,
    c.plan,
    c.state,
    c.csm_owner,
    strftime(c.signup_date, '%Y-%m-%d')                                       AS signup_date,
    COALESCE(printf('%.2f', m.mrr_mxn), '')                                  AS mrr_mxn,
    m.mrr_source,
    m.mrr_confidence,
    printf('%.2f', m.mrr_original)                                           AS mrr_original,
    m.currency_original,
    strftime(c.churn_date, '%Y-%m-%d')                                        AS churn_date,
    c.churn_status,
    CASE WHEN c.churn_date IS NOT NULL THEN strftime(c.churn_date, '%Y-%m')
         ELSE (SELECT MAX(month) FROM stg_product_usage) END                  AS reference_month,
    u.active_users_latest,
    u.active_users_avg,
    u.usage_months,
    u.trend_usage,
    u.trend_asof_month,
    u.trend_status,
    s.tickets_total,
    s.tickets_urgent,
    s.csat_avg,
    ci.acquisition_channel,
    ci.closed_revenue_mxn,
    c.ruleset_version,
    strftime(CAST(c.resolved_at AS DATE), '%Y-%m-%d')                          AS dataset_asof
FROM mart_company_core c
JOIN mart_mrr m ON m.master_id = c.master_id
JOIN mart_usage u ON u.master_id = c.master_id
JOIN mart_support s ON s.master_id = c.master_id
JOIN mart_commercial ci ON ci.master_id = c.master_id;
