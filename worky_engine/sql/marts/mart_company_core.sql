-- Supervivencia por atributo (seccion 3.7 del diseno). identity_crosswalk
-- ya solo trae empresas reales (HS-1xxxxx): la deduplicacion de clones ya
-- corrio en Python (worky_engine.identity_resolution.quarantine), asi que
-- este join solo adjunta los atributos comerciales de la fila sobreviviente.
CREATE OR REPLACE VIEW mart_company_core AS
SELECT
    x.master_id,
    x.hubspot_id,
    x.account_id,
    x.vitally_id,
    x.confidence_tier,
    c.company_name,
    c.domain,
    c.segment,
    c.industry,
    c.plan,
    c.state,
    c.csm_owner,
    c.signup_date,
    c.churn_date,
    CASE WHEN c.churn_date IS NULL THEN 'active' ELSE 'churned' END AS churn_status,
    c.mrr_original,
    c.currency_original,
    c.mrr_crm_mxn
FROM identity_crosswalk x
JOIN stg_companies c ON c.hubspot_id = x.hubspot_id;
