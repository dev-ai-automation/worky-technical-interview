-- Motor: DuckDB 1.5.5. mart_last_touch, vista de analisis a grano deal
-- (diseno de sql-analysis, seccion 2.0, decision D7). Simetrica a
-- mart_first_touch: para cada deal, el touch mas reciente de su
-- empresa con touch_date anterior al created_date del deal. El
-- empate se rompe por touch_id, la misma llave que usa el motor, en
-- el extremo opuesto del orden que usa mart_first_touch (esa ordena
-- touch_date, touch_id ascendente y se queda con el menor; esta
-- ordena descendente y se queda con el mayor). Un deal sin ningun
-- touch previo no produce fila aqui; a1_04 lo etiqueta como
-- 'no_prior_touch'. Un deal con created_date nulo tampoco produce
-- fila, porque la comparacion contra un nulo no es verdadera.
CREATE OR REPLACE VIEW mart_last_touch AS
SELECT deal_id, master_id, last_touch_id, last_touch_date, last_touch_channel
FROM (
    SELECT
        d.deal_id,
        d.master_id,
        t.touch_id   AS last_touch_id,
        t.touch_date AS last_touch_date,
        t.channel    AS last_touch_channel,
        ROW_NUMBER() OVER (
            PARTITION BY d.deal_id
            ORDER BY t.touch_date DESC, t.touch_id DESC
        ) AS rn
    FROM stg_deals d
    JOIN stg_marketing_touches t
        ON t.master_id = d.master_id
       AND t.touch_date < d.created_date
    WHERE d.master_id IS NOT NULL
) ranked
WHERE rn = 1;
