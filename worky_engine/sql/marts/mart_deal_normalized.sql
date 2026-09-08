-- Normalizacion de unidad de los montos de deal a valor mensual (ADR-002,
-- Adenda 1): el monto minimo de cada empresa es el mensual, y un monto
-- que es exactamente 12 veces ese minimo esta cotizado al ano, asi que
-- se lleva al valor del minimo. `mart_mrr` (imputacion de MRR) y
-- `mart_commercial` (closed_revenue_mxn) comparten esta vista para no
-- repetir la regla en dos archivos.
CREATE OR REPLACE VIEW mart_deal_normalized AS
WITH deal_pool AS (
    SELECT master_id, deal_id, amount_mxn, stage
    FROM stg_deals
    WHERE master_id IS NOT NULL          -- stg_deals ya remapea los clones al master_id
                                          -- del sobreviviente; lo que queda en NULL aqui
                                          -- son los huerfanos, ya en quarantine_deals
),
company_min AS (
    SELECT master_id, MIN(amount_mxn) AS min_amount
    FROM deal_pool
    GROUP BY master_id
)
SELECT
    p.master_id,
    p.deal_id,
    p.stage,
    p.amount_mxn AS original_amount,
    CASE WHEN p.amount_mxn = m.min_amount * 12 THEN m.min_amount ELSE p.amount_mxn END AS normalized_amount
FROM deal_pool p
JOIN company_min m USING (master_id);
