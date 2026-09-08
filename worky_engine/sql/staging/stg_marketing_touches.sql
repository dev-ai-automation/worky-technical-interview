-- Staging de marketing_touches: tipa la fecha, recorta espacios y
-- adjunta el master_id que ya resolvio identity_resolution, para que
-- mart_commercial (canal de adquisicion, PR 4b) no repita ese join.
CREATE OR REPLACE VIEW stg_marketing_touches AS
SELECT
    trim(t.touch_id)                                    AS touch_id,
    trim(t.hubspot_id)                                   AS hubspot_id,
    x.master_id                                          AS master_id,
    trim(t.channel)                                        AS channel,
    CAST(t.touch_date AS DATE)                             AS touch_date,
    trim(t.campaign)                                        AS campaign
FROM raw_marketing_touches t
LEFT JOIN identity_crosswalk x ON x.hubspot_id = t.hubspot_id;
