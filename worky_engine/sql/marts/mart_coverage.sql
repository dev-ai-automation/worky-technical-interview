-- Conteos de cobertura recalculados desde match_audit y las dos
-- cuarentenas en cada build (seccion 2 del diseno, contrato de
-- coverage_report.md). Ningun porcentaje se escribe a mano: todos salen
-- de COUNT/SUM sobre las filas que ya produjo la resolucion de identidad.
CREATE OR REPLACE VIEW mart_coverage_by_system AS
SELECT
    source_system,
    COUNT(*)                                                          AS total_rows,
    SUM(CASE WHEN master_id IS NOT NULL THEN 1 ELSE 0 END)            AS resolved_rows,
    ROUND(100.0 * SUM(CASE WHEN master_id IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS coverage_pct
FROM match_audit
GROUP BY source_system
ORDER BY source_system;

-- T0 a T3 y M son los niveles con los que product_db y vitally se
-- vinculan contra el registro dorado de HubSpot (crm_hubspot solo aporta
-- S y Q, ya resumidos arriba); el porcentaje de cada nivel se calcula
-- sobre ese mismo universo (650 + 650 = 1300 filas en el dataset real).
-- La lista fija de niveles evita que un nivel en cero (T3 y M en este
-- dataset) desaparezca del reporte por un simple GROUP BY.
CREATE OR REPLACE VIEW mart_coverage_by_tier AS
WITH known_tiers(tier) AS (VALUES ('T0'), ('T1'), ('T2'), ('T3'), ('M')),
counted AS (
    SELECT tier, COUNT(*) AS row_count
    FROM match_audit
    WHERE tier IN ('T0', 'T1', 'T2', 'T3', 'M')
    GROUP BY tier
),
total AS (SELECT SUM(row_count) AS total_rows FROM counted)
SELECT
    k.tier,
    COALESCE(c.row_count, 0)                                             AS row_count,
    ROUND(100.0 * COALESCE(c.row_count, 0) / t.total_rows, 2)            AS coverage_pct
FROM known_tiers k
LEFT JOIN counted c USING (tier)
CROSS JOIN total t
ORDER BY k.tier;

CREATE OR REPLACE VIEW mart_coverage_manual_queue AS
SELECT COUNT(*) AS manual_queue_size
FROM match_audit
WHERE tier = 'M';

-- Cuarentena: 28 empresas clon y 35 deals huerfanos. El monto de los
-- deals huerfanos se conserva en unidades mezcladas porque no tienen
-- empresa de la que heredar moneda (seccion 4.5 del diseno). La version
-- "normalizada" aplica la misma regla de 12x que mart_mrr por
-- consistencia; como cada hubspot_id huerfano trae un unico deal, no hay
-- un segundo monto de la misma empresa contra el cual detectar el
-- multiplo, asi que el total normalizado coincide con el crudo en este
-- dataset y el reporte lo explica en vez de fingir una conversion real.
CREATE OR REPLACE VIEW mart_coverage_quarantine AS
WITH quarantine_deals_typed AS (
    -- quarantine_deals.amount llega como VARCHAR: format_money ya lo
    -- escribio con dos decimales al armar la salida (identity_resolution).
    SELECT hubspot_id, CAST(amount AS DECIMAL(14,2)) AS amount
    FROM quarantine_deals
),
deal_min AS (
    SELECT hubspot_id, MIN(amount) AS min_amount
    FROM quarantine_deals_typed
    GROUP BY hubspot_id
),
normalized AS (
    SELECT q.hubspot_id,
           CASE WHEN q.amount = m.min_amount * 12 THEN m.min_amount ELSE q.amount END AS normalized_amount
    FROM quarantine_deals_typed q
    JOIN deal_min m USING (hubspot_id)
)
SELECT
    (SELECT COUNT(*) FROM quarantine_companies)                     AS quarantine_companies_count,
    (SELECT COUNT(*) FROM quarantine_deals)                         AS quarantine_deals_count,
    (SELECT COALESCE(SUM(amount), 0) FROM quarantine_deals_typed)   AS quarantine_deals_amount_raw,
    (SELECT COALESCE(SUM(normalized_amount), 0) FROM normalized)    AS quarantine_deals_amount_normalized;
