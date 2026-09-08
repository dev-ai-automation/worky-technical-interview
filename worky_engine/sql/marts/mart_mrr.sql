-- Imputacion de MRR desde el monto unico de deals (ADR-002, seccion 4.3
-- del diseno). Un valor del CRM nunca se sobrescribe: mrr_crm_mxn gana
-- siempre que exista.
--
-- Tres de las 28 empresas reales sin MRR (HS-100337, HS-100500,
-- HS-100585, verificadas contra el dataset real) traen un deal cotizado
-- al valor anual completo en lugar del mensual: su monto es exactamente
-- 12 veces el monto minimo entre los deals de esa misma empresa. La
-- normalizacion de unidad vive en `mart_deal_normalized` (compartida con
-- `mart_commercial`), asi que esos casos ya llegan aqui con un unico
-- monto normalizado, tal como pide el ADR-002; sin ella las 3 quedarian
-- sin imputar. Cuando el monto no es igual al minimo ni a 12 veces el
-- minimo, la ambiguedad es real y la empresa queda en `unresolved`
-- (0 casos reales, 2 en el fixture sintetico) con `mrr_confidence = 'none'`:
-- no hay MRR que confiar.
CREATE OR REPLACE VIEW mart_mrr AS
WITH normalized_deals AS (
    SELECT master_id, deal_id, stage, original_amount, normalized_amount
    FROM mart_deal_normalized
),
company_deals AS (
    SELECT master_id,
           COUNT(DISTINCT normalized_amount)                          AS distinct_amounts,
           MIN(normalized_amount)                                     AS candidate_mrr_mxn,
           MAX(CASE WHEN stage = 'closedwon' THEN 1 ELSE 0 END)       AS has_closedwon
    FROM normalized_deals
    GROUP BY master_id
),
-- El deal de evidencia (evidence_ref) prefiere, entre los que calzan con
-- el monto imputado, el que ya trae ese monto crudo (sin haber pasado
-- por la normalizacion 12x): en los tres casos anuales (HS-100337,
-- HS-100500, HS-100585) evidence_ref queda apuntando al deal mensual y
-- no al anual, para que quien audite la fila vea el monto que coincide
-- con applied_value sin tener que rehacer la normalizacion.
candidate_deal AS (
    SELECT master_id, deal_id AS candidate_deal_id
    FROM (
        SELECT n.master_id, n.deal_id,
               ROW_NUMBER() OVER (
                   PARTITION BY n.master_id
                   ORDER BY (n.original_amount <> c.candidate_mrr_mxn), n.deal_id
               ) AS rn
        FROM normalized_deals n
        JOIN company_deals c ON c.master_id = n.master_id AND n.normalized_amount = c.candidate_mrr_mxn
    ) ranked
    WHERE rn = 1
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
        WHEN c.mrr_crm_mxn IS NOT NULL              THEN 'high'
        WHEN d.distinct_amounts = 1 AND d.has_closedwon = 1 THEN 'high'
        WHEN d.distinct_amounts = 1                  THEN 'medium'
        ELSE 'none'          -- unresolved: ningun MRR que confiar
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
WHERE m.mrr_source = 'imputed_from_deal'

UNION ALL

-- Una fila de exceptions_log por cada deal remapeado de un clon en
-- cuarentena a su sobreviviente (design.md 3.8 caso 2): stg_deals ya
-- resuelve ese master_id con quarantine_companies.survivor_master_id,
-- esta fila es solo la evidencia de que ese remapeo ocurrio.
SELECT
    substr(
        sha256('deal_remapped_from_clone|crm_hubspot|' || d.deal_id || '|hubspot_id'), 1, 12
    )                                                       AS exception_id,
    'deal_remapped_from_clone'                              AS exception_code,
    'crm_hubspot'                                            AS source_system,
    d.deal_id                                                 AS source_id,
    q.survivor_master_id                                       AS master_id,
    'hubspot_id'                                                AS field_name,
    q.hubspot_id                                                 AS original_value,
    q.survivor_hubspot_id                                         AS applied_value,
    q.hubspot_id                                                   AS evidence_ref,
    '1.0.0'                                                         AS ruleset_version,
    (SELECT MAX(resolved_at) FROM identity_crosswalk)                AS decided_at
FROM stg_deals d
JOIN quarantine_companies q ON q.hubspot_id = d.hubspot_id;
