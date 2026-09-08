-- Staging de companies: tipa columnas, recorta espacios y convierte el
-- MRR del CRM a MXN con el tipo de cambio fijo de 18.5 del ADR-002. Las
-- fechas ya llegan en ISO porque assemble.py las normaliza una sola vez
-- (con worky_engine.normalization.normalize_date) antes de registrar el
-- DataFrame en DuckDB, asi que aqui solo hace falta tipar con CAST.
-- `domain_label` llega igual de precalculado, con la misma funcion
-- pura de `worky_engine.normalization.domain_label` que usa
-- identity_resolution, para no reimplementar el recorte de acentos y
-- subdominios en SQL.
CREATE OR REPLACE VIEW stg_companies AS
SELECT
    trim(hubspot_id)                                    AS hubspot_id,
    trim(name)                                           AS company_name,
    trim(domain)                                         AS domain,
    domain_label                                          AS domain_label,
    trim(segment)                                        AS segment,
    trim(industry)                                       AS industry,
    trim(plan)                                            AS plan,
    trim(state)                                           AS state,
    trim(csm_owner)                                       AS csm_owner,
    CAST(signup_date AS DATE)                             AS signup_date,
    CAST(churn_date AS DATE)                              AS churn_date,
    CAST(mrr AS DECIMAL(12,2))                            AS mrr_original,
    trim(currency)                                        AS currency_original,
    CASE WHEN trim(currency) = 'USD'
         THEN CAST(mrr AS DECIMAL(12,2)) * 18.5
         ELSE CAST(mrr AS DECIMAL(12,2)) END               AS mrr_crm_mxn
FROM raw_companies;
