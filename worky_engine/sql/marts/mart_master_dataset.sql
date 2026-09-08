-- Ensambla las columnas disponibles en este PR: identidad, atributos
-- comerciales, MRR con su trazabilidad y el estatus de baja. Las
-- columnas de uso, soporte y comercial llegan en el PR 4 (seccion 8 del
-- diseno); este SELECT queda listo para agregarlas con un JOIN mas,
-- sin tocar ninguna de las columnas que ya arma este PR.
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
    c.segment,
    c.industry,
    c.plan,
    c.state,
    c.csm_owner,
    strftime(c.signup_date, '%Y-%m-%d')                                       AS signup_date,
    printf('%.2f', m.mrr_mxn)                                                 AS mrr_mxn,
    m.mrr_source,
    m.mrr_confidence,
    printf('%.2f', m.mrr_original)                                           AS mrr_original,
    m.currency_original,
    strftime(c.churn_date, '%Y-%m-%d')                                        AS churn_date,
    c.churn_status,
    CASE WHEN c.churn_date IS NOT NULL THEN strftime(c.churn_date, '%Y-%m')
         ELSE (SELECT MAX(month) FROM stg_product_usage) END                  AS reference_month
FROM mart_company_core c
JOIN mart_mrr m ON m.master_id = c.master_id;
