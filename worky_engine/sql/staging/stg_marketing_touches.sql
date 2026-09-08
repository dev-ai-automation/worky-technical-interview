-- Staging de marketing_touches: tipa la fecha y recorta espacios. Sin
-- join a otro sistema, tal como fija la seccion 4.2 del diseno.
CREATE OR REPLACE VIEW stg_marketing_touches AS
SELECT
    trim(touch_id)                                      AS touch_id,
    trim(hubspot_id)                                     AS hubspot_id,
    trim(channel)                                        AS channel,
    CAST(touch_date AS DATE)                             AS touch_date,
    trim(campaign)                                        AS campaign
FROM raw_marketing_touches;
