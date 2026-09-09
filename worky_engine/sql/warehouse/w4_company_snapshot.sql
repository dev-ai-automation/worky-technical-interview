-- warehouse_company_snapshot (seccion 3 y 5 del diseno): foto actual
-- de cada empresa, con las mismas columnas de dim_company salvo las de
-- vigencia, mas attributes_hash sobre los dos atributos que rastrea el
-- SCD2 del PR3 (plan y csm_owner, D5). Es la entrada de ese algoritmo;
-- este PR solo la deja lista como vista. Un nulo entra a sha256 como
-- cadena vacia (D6).
CREATE OR REPLACE VIEW warehouse_company_snapshot AS
SELECT
    c.master_id,
    c.hubspot_id,
    c.account_id,
    c.vitally_id,
    c.company_name,
    c.domain_label,
    c.segment,
    c.industry,
    c.plan,
    c.csm_owner,
    c.state,
    c.signup_date,
    c.churn_date,
    c.churn_status,
    substr(sha256(COALESCE(c.plan, '') || '|' || COALESCE(c.csm_owner, '')), 1, 12) AS attributes_hash,
    c.ruleset_version
FROM mart_company_core c;
