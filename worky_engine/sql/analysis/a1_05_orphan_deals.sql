-- Motor: DuckDB 1.5.5. A1.5, deals sin empresa real (ADR-004). Consulta
-- SQL equivalente a la cuarentena del motor: deals cuyo hubspot_id no
-- existe en ninguna empresa real. El segundo LEFT JOIN, contra
-- quarantine_companies, evita el falso positivo de un deal que apunta a
-- un clon remapeado a su sobreviviente (stg_deals.master_id ya lo
-- resuelve): ese deal si tiene empresa real y no debe salir como
-- huerfano. amount se reporta crudo (no amount_mxn) porque estos deals
-- no tienen empresa de la que heredar la moneda, en unidades mezcladas
-- segun la adenda 1 del ADR-002.
CREATE OR REPLACE VIEW analysis_a1_05_orphan_deals AS
SELECT
    d.deal_id, d.hubspot_id, d.stage,
    printf('%.2f', d.amount)             AS amount,
    strftime(d.created_date, '%Y-%m-%d') AS created_date,
    strftime(d.close_date, '%Y-%m-%d')   AS close_date,
    d.pipeline, d.lead_source
FROM stg_deals d
LEFT JOIN mart_master_dataset m  ON m.hubspot_id = d.hubspot_id
LEFT JOIN quarantine_companies q ON q.hubspot_id = d.hubspot_id
WHERE m.hubspot_id IS NULL   -- ninguna empresa real de la sabana tiene ese hubspot_id
  AND q.hubspot_id IS NULL   -- y tampoco es un clon remapeado a su sobreviviente
ORDER BY d.deal_id;
