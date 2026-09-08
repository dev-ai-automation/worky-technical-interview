-- Imputacion de MRR desde el monto unico de deals (ADR-002, seccion 4.3
-- del diseno). Un valor del CRM nunca se sobrescribe: mrr_crm_mxn gana
-- siempre que exista.
--
-- Tres de las 28 empresas reales sin MRR (HS-100337, HS-100500,
-- HS-100585, verificadas contra el dataset real) traen un deal cotizado
-- al valor anual completo en lugar del mensual: su monto es exactamente
-- 12 veces el monto minimo entre los deals de esa misma empresa. Antes
-- de contar montos distintos, esos casos se normalizan al valor minimo
-- (el mensual), para que sigan contando como "un unico monto" segun el
-- ADR-002; sin esta normalizacion las 3 quedarian sin imputar. Cuando
-- el monto no es igual al minimo ni a 12 veces el minimo, la ambiguedad
-- es real y la empresa queda en `unresolved` (0 casos en este dataset).
CREATE OR REPLACE VIEW mart_mrr AS
WITH deal_pool AS (
    SELECT master_id, deal_id, amount_mxn, stage
    FROM stg_deals
    WHERE master_id IS NOT NULL          -- los huerfanos ya estan en cuarentena
),
company_min AS (
    SELECT master_id, MIN(amount_mxn) AS min_amount
    FROM deal_pool
    GROUP BY master_id
),
normalized_deals AS (
    SELECT p.master_id, p.deal_id, p.stage,
           CASE WHEN p.amount_mxn = m.min_amount * 12 THEN m.min_amount ELSE p.amount_mxn END AS normalized_amount
    FROM deal_pool p
    JOIN company_min m USING (master_id)
),
company_deals AS (
    SELECT master_id,
           COUNT(DISTINCT normalized_amount)                          AS distinct_amounts,
           MIN(normalized_amount)                                     AS candidate_mrr_mxn,
           MAX(CASE WHEN stage = 'closedwon' THEN 1 ELSE 0 END)       AS has_closedwon
    FROM normalized_deals
    GROUP BY master_id
),
candidate_deal AS (
    SELECT n.master_id, MIN(n.deal_id) AS candidate_deal_id
    FROM normalized_deals n
    JOIN company_deals c ON c.master_id = n.master_id AND n.normalized_amount = c.candidate_mrr_mxn
    GROUP BY n.master_id
)
SELECT
    c.master_id,
    CASE
        WHEN c.mrr_crm_mxn IS NOT NULL THEN c.mrr_crm_mxn
        WHEN d.distinct_amounts = 1    THEN d.candidate_mrr_mxn
        ELSE NULL
    END AS mrr_mxn,
    CASE
        WHEN c.mrr_crm_mxn IS NOT NULL THEN 'crm'
        WHEN d.distinct_amounts = 1    THEN 'imputed_from_deal'
        ELSE 'unresolved'
    END AS mrr_source,
    CASE
        WHEN c.mrr_crm_mxn IS NOT NULL THEN 'high'
        WHEN d.has_closedwon = 1       THEN 'high'
        ELSE 'medium'
    END AS mrr_confidence,
    c.mrr_original,
    c.currency_original,
    cd.candidate_deal_id
FROM mart_company_core c
LEFT JOIN company_deals d USING (master_id)
LEFT JOIN candidate_deal cd USING (master_id);

-- Una fila de exceptions_log por cada empresa imputada, con su deal_id
-- de origen en evidence_ref (seccion 2 del diseno, tabla exceptions_log).
-- exception_id es sha256(exception_code|source_system|source_id|field_name)
-- truncado a 12 caracteres hex, igual que en Python (hashlib.sha256).
CREATE OR REPLACE VIEW exceptions_log AS
SELECT
    substr(
        sha256('mrr_imputed_from_deal|crm_hubspot|' || c.hubspot_id || '|mrr_mxn'), 1, 12
    )                                                       AS exception_id,
    'mrr_imputed_from_deal'                                 AS exception_code,
    'crm_hubspot'                                            AS source_system,
    c.hubspot_id                                              AS source_id,
    m.master_id                                                AS master_id,
    'mrr_mxn'                                                   AS field_name,
    CAST(NULL AS VARCHAR)                                        AS original_value,
    printf('%.2f', m.mrr_mxn)                                     AS applied_value,
    m.candidate_deal_id                                            AS evidence_ref,
    '1.0.0'                                                         AS ruleset_version,
    (SELECT MAX(resolved_at) FROM identity_crosswalk)                AS decided_at
FROM mart_mrr m
JOIN mart_company_core c ON c.master_id = m.master_id
WHERE m.mrr_source = 'imputed_from_deal';
