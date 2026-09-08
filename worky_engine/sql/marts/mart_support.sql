-- Agregados de soporte por empresa, via el vitally_id del crosswalk
-- (seccion 4.5 del diseno). Solo `priority = 'Urgent'` cuenta como
-- urgente; `csat_avg` promedia unicamente los tickets que trajeron
-- puntaje. El LEFT JOIN nunca descarta una fila de mart_company_core:
-- una empresa sin vitally_id, o con vitally_id pero sin tickets, queda
-- en tickets_total = 0, tickets_urgent = 0 y csat_avg vacio.
CREATE OR REPLACE VIEW mart_support AS
SELECT
    c.master_id,
    COUNT(t.ticket_id)                                             AS tickets_total,
    -- SUM() de un CASE INTEGER da HUGEINT en DuckDB, que .df() convierte
    -- a float64 (no hay tipo entero de 128 bits en pandas) y el CSV
    -- terminaria con "1.0" en vez de "1"; CAST a BIGINT lo evita.
    CAST(SUM(CASE WHEN t.priority = 'Urgent' THEN 1 ELSE 0 END) AS BIGINT) AS tickets_urgent,
    CASE WHEN COUNT(t.csat_score) = 0 THEN NULL
         ELSE printf('%.2f', AVG(t.csat_score)) END                 AS csat_avg
FROM mart_company_core c
LEFT JOIN stg_tickets t ON t.vitally_id = c.vitally_id
GROUP BY c.master_id;
