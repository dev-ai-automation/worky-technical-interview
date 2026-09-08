-- Supervivencia por atributo (seccion 3.7 del diseno). identity_crosswalk
-- ya solo trae empresas reales (HS-1xxxxx): la deduplicacion de clones ya
-- corrio en Python (worky_engine.identity_resolution.quarantine), asi que
-- este join solo adjunta los atributos comerciales de la fila sobreviviente.
--
-- `ruleset_version` y `resolved_at` (que se expone como `dataset_asof`
-- en mart_master_dataset) salen tal cual del crosswalk: son la misma
-- version de reglas y la misma fecha maxima de los datos que ya calculo
-- identity_resolution (seccion 7 del diseno), asi que este mart solo
-- las pasa de largo en vez de recalcularlas.
CREATE OR REPLACE VIEW mart_company_core AS
SELECT
    x.master_id,
    x.hubspot_id,
    x.account_id,
    x.vitally_id,
    x.confidence_tier,
    x.ruleset_version,
    x.resolved_at,
    c.company_name,
    c.domain,
    c.domain_label,
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
