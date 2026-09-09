-- Motor: DuckDB 1.5.5. A1.4, atribucion por primer y ultimo touch
-- (ADR-004). Grano deal: cada deal se atribuye a dos canales, el
-- primer touch de su empresa (mart_first_touch) y el ultimo touch
-- anterior a su created_date (mart_last_touch, D7). Convierte si
-- stage = closedwon. La tasa por canal es deals ganados entre deals
-- atribuidos, para cada modelo. El empate por touch_id ya lo resuelven
-- mart_first_touch y mart_last_touch, cada una en el extremo que le
-- toca. channel_rank = 1 es el canal ganador de cada modelo; el
-- reporte compara los dos ganadores sin recalcular nada.
CREATE OR REPLACE VIEW analysis_a1_04_attribution AS
WITH attributed AS (
    SELECT d.deal_id, d.stage,
           COALESCE(ft.first_touch_channel, 'unknown')        AS first_touch_channel,
           COALESCE(lt.last_touch_channel, 'no_prior_touch')  AS last_touch_channel
    FROM stg_deals d
    LEFT JOIN mart_first_touch ft ON ft.master_id = d.master_id
    LEFT JOIN mart_last_touch  lt ON lt.deal_id  = d.deal_id
    WHERE d.master_id IS NOT NULL      -- los deals huerfanos son A1.5
),
by_model AS (
    SELECT 'first_touch' AS model, first_touch_channel AS channel, stage FROM attributed
    UNION ALL
    SELECT 'last_touch'  AS model, last_touch_channel  AS channel, stage FROM attributed
),
rates AS (
    SELECT model, channel, COUNT(*) AS deals_attributed,
           CAST(SUM(CASE WHEN stage = 'closedwon' THEN 1 ELSE 0 END) AS BIGINT) AS deals_won
    FROM by_model GROUP BY model, channel
)
SELECT model, channel, deals_attributed, deals_won,
       printf('%.6f', deals_won * 1.0 / deals_attributed) AS conversion_rate,
       ROW_NUMBER() OVER (
           PARTITION BY model
           ORDER BY deals_won * 1.0 / deals_attributed DESC, channel
       ) AS channel_rank
FROM rates
ORDER BY model, channel_rank;
