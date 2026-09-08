-- Canal de adquisicion y revenue cerrado (seccion 4.5 del diseno).
--
-- El canal usa el primer touch de marketing_touches por touch_date y
-- desempate por touch_id (ambos estables y unicos en la fuente, asi que
-- el desempate es reproducible); cuando la empresa no tiene ningun
-- touch, se usa el lead_source de su primer deal por created_date y
-- desempate por deal_id; si tampoco hay deals, el valor es 'unknown'.
-- El perfil del dataset real indica que las 650 empresas tienen al
-- menos un touch, asi que el respaldo deberia quedar en cero filas.
--
-- closed_revenue_mxn suma, por empresa, el amount_mxn ya normalizado a
-- valor mensual (mart_deal_normalized, la misma regla 12x del ADR-002
-- que usa mart_mrr) de los deals en closedwon; los deals huerfanos ya
-- quedaron fuera de stg_deals.master_id y por tanto de
-- mart_deal_normalized, asi que no entran a esta suma.
CREATE OR REPLACE VIEW mart_first_touch AS
SELECT master_id, channel AS first_touch_channel
FROM (
    SELECT master_id, channel,
           ROW_NUMBER() OVER (PARTITION BY master_id ORDER BY touch_date, touch_id) AS rn
    FROM stg_marketing_touches
    WHERE master_id IS NOT NULL
) ranked
WHERE rn = 1;

CREATE OR REPLACE VIEW mart_first_deal AS
SELECT master_id, lead_source AS first_deal_lead_source
FROM (
    SELECT master_id, lead_source,
           ROW_NUMBER() OVER (PARTITION BY master_id ORDER BY created_date, deal_id) AS rn
    FROM stg_deals
    WHERE master_id IS NOT NULL
) ranked
WHERE rn = 1;

CREATE OR REPLACE VIEW mart_commercial AS
SELECT
    c.master_id,
    COALESCE(ft.first_touch_channel, fd.first_deal_lead_source, 'unknown')  AS acquisition_channel,
    printf('%.2f', COALESCE(r.closed_revenue_mxn, 0))                       AS closed_revenue_mxn
FROM mart_company_core c
LEFT JOIN mart_first_touch ft ON ft.master_id = c.master_id
LEFT JOIN mart_first_deal fd ON fd.master_id = c.master_id
LEFT JOIN (
    SELECT master_id, SUM(normalized_amount) AS closed_revenue_mxn
    FROM mart_deal_normalized
    WHERE stage = 'closedwon'
    GROUP BY master_id
) r ON r.master_id = c.master_id;
