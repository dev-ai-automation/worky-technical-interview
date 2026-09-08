-- Staging de deals: tipa el monto, lo convierte a MXN con la moneda que
-- el deal hereda de su empresa (la tabla deals no trae columna de
-- moneda propia, seccion 4.5 del diseno) y adjunta el master_id que ya
-- resolvio identity_resolution, para que mart_mrr no repita ese join.
CREATE OR REPLACE VIEW stg_deals AS
SELECT
    trim(d.deal_id)                                     AS deal_id,
    trim(d.hubspot_id)                                   AS hubspot_id,
    x.master_id                                          AS master_id,
    trim(d.stage)                                        AS stage,
    CAST(d.amount AS DECIMAL(14,2))                      AS amount,
    CASE WHEN c.currency_original = 'USD'
         THEN CAST(d.amount AS DECIMAL(14,2)) * 18.5
         ELSE CAST(d.amount AS DECIMAL(14,2)) END          AS amount_mxn,
    CAST(d.created_date AS DATE)                          AS created_date,
    CAST(d.close_date AS DATE)                            AS close_date,
    trim(d.pipeline)                                       AS pipeline,
    trim(d.lead_source)                                    AS lead_source
FROM raw_deals d
LEFT JOIN identity_crosswalk x ON x.hubspot_id = d.hubspot_id
LEFT JOIN stg_companies c ON c.hubspot_id = d.hubspot_id;
