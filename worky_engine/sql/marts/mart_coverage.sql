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

-- needs_review, no tier = 'M': hasta antes de la contencion de enlaces
-- duplicados (seccion 3.6 del diseno) ambas condiciones eran equivalentes
-- (M era el unico tier que marcaba needs_review = true), pero un enlace
-- duplicado de product_db o vitally tambien necesita revision manual sin
-- dejar de resolver en T0-T3. Sobre el dataset real (0 duplicados) el
-- conteo no cambia.
CREATE OR REPLACE VIEW mart_coverage_manual_queue AS
SELECT COUNT(*) AS manual_queue_size
FROM match_audit
WHERE needs_review;

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

-- Tendencia de uso (seccion 7 del reporte, ADR-003): distribucion de
-- trend_status y la mediana de trend_usage por churn_status, solo sobre
-- las filas 'computed' (las unicas con valor numerico). Ambas vistas
-- leen mart_master_dataset, ya materializada por este mismo build; el
-- registro con ese mismo nombre en tests/test_coverage_report.py deja
-- entrar el golden commiteado sin correr el resto del pipeline.
--
-- El ORDER BY explicito en las cuatro vistas de esta seccion no es
-- cosmetico: sin el, el orden de un GROUP BY de DuckDB no esta
-- garantizado entre corridas (agregacion hash en paralelo), y
-- test_build_idempotency.py lo detecto como una diferencia real de
-- bytes en coverage_report.md entre dos builds identicos.
CREATE OR REPLACE VIEW mart_coverage_trend AS
SELECT trend_status, COUNT(*) AS row_count
FROM mart_master_dataset
GROUP BY trend_status
ORDER BY trend_status;

CREATE OR REPLACE VIEW mart_coverage_trend_median AS
SELECT churn_status, median(CAST(trend_usage AS DOUBLE)) AS median_trend_usage
FROM mart_master_dataset
WHERE trend_status = 'computed'
GROUP BY churn_status
ORDER BY churn_status;

-- Canal de adquisicion y revenue cerrado (seccion 9 del reporte): la
-- distribucion completa de acquisition_channel ya incluye 'unknown'
-- como un valor mas, asi que su proporcion queda visible sin una
-- columna aparte. closed_revenue_mxn ya viene normalizado a valor
-- mensual en MXN (seccion 4.3 del diseno, regla 12x del ADR-002).
CREATE OR REPLACE VIEW mart_coverage_channel AS
SELECT acquisition_channel, COUNT(*) AS row_count
FROM mart_master_dataset
GROUP BY acquisition_channel
ORDER BY acquisition_channel;

CREATE OR REPLACE VIEW mart_coverage_revenue AS
SELECT SUM(CAST(closed_revenue_mxn AS DOUBLE)) AS closed_revenue_mxn_total
FROM mart_master_dataset;
