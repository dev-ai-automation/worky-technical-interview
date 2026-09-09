-- dim_csm y dim_plan (seccion 5 del diseno): valores distintos de
-- mart_company_core, solo lectura, sin duplicar la columna en otro
-- lugar. csm_key y plan_key son un hash truncado del valor, la misma
-- convencion de sha256 a 12 hex que ya usan master_id y exception_id.
CREATE OR REPLACE VIEW dim_csm AS
SELECT
    substr(sha256(csm_owner), 1, 12) AS csm_key,
    csm_owner
FROM (SELECT DISTINCT csm_owner FROM mart_company_core WHERE csm_owner IS NOT NULL) t
ORDER BY csm_owner;

CREATE OR REPLACE VIEW dim_plan AS
SELECT
    substr(sha256(plan), 1, 12) AS plan_key,
    plan
FROM (SELECT DISTINCT plan FROM mart_company_core WHERE plan IS NOT NULL) t
ORDER BY plan;
