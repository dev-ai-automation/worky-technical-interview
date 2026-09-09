-- Los cinco hechos del esquema en estrella (seccion 5 del diseno).
-- Cada uno resuelve su company_sk contra la banda de dim_company
-- vigente en la fecha del propio hecho, nunca contra la fila actual
-- (D13, ADR-003): el intervalo semiabierto de vigencia es
-- effective_from inclusivo, effective_to exclusivo o nulo en la fila
-- vigente (D7). dim_company la puebla el algoritmo de SCD2 del PR3;
-- mientras esa tabla este vacia (como al terminar este PR, en una
-- corrida real), los cinco hechos quedan vacios tambien, porque
-- ninguno tiene con que empresa unirse todavia.
--
-- fact_usage_monthly y fact_revenue_monthly son mensuales y usan el
-- ultimo dia del mes como fecha del hecho (D10); fact_deals,
-- fact_support_tickets y fact_marketing_touches son diarios y usan su
-- propia fecha de evento (close_date/created_date, created_date y
-- touch_date, respectivamente).
--
-- fact_support_tickets resuelve su master_id contra mart_company_core
-- via vitally_id, el mismo join que usa mart_support.sql para el
-- mismo proposito (seccion 4.5 del diseno); un ticket sin vitally_id
-- vinculado a ninguna empresa no aporta fila. fact_marketing_touches
-- ya trae su master_id resuelto en stg_marketing_touches.sql (via
-- identity_crosswalk sobre hubspot_id); un touch sin master_id
-- resuelto tampoco aporta fila, por la misma razon.
--
-- Restaurados por decision del usuario despues del cierre original de
-- este PR: la palanca de reduccion de la seccion 10 del diseno se
-- habia aplicado para caber en el presupuesto de 800 lineas de
-- autoria, dejando estos dos hechos fuera. El usuario acepto
-- size:exception para esta version y pidio revertir la palanca; ver
-- apply-progress.md de este PR para el detalle de la decision.

CREATE OR REPLACE VIEW fact_usage_monthly AS
SELECT
    d.company_sk,
    CAST(strftime(last_day(CAST(u.month || '-01' AS DATE)), '%Y%m%d') AS INTEGER) AS date_key,
    c.master_id,
    u.account_id,
    u.month,
    u.active_users,
    u.logins,
    u.payroll_runs_completed,
    u.features_used,
    u.api_calls
FROM stg_product_usage u
JOIN mart_company_core c ON c.account_id = u.account_id
JOIN dim_company d
    ON d.master_id = c.master_id
   AND last_day(CAST(u.month || '-01' AS DATE)) >= d.effective_from
   AND (d.effective_to IS NULL OR last_day(CAST(u.month || '-01' AS DATE)) < d.effective_to)
ORDER BY c.master_id, u.month;

CREATE OR REPLACE VIEW fact_deals AS
WITH deal_events AS (
    SELECT sd.*, n.normalized_amount, COALESCE(sd.close_date, sd.created_date) AS event_date
    FROM stg_deals sd
    JOIN mart_deal_normalized n ON n.deal_id = sd.deal_id
)
SELECT
    d.company_sk,
    CAST(strftime(e.event_date, '%Y%m%d') AS INTEGER) AS date_key,
    e.master_id,
    e.deal_id,
    e.stage,
    e.normalized_amount AS amount_mxn,
    e.created_date,
    e.close_date,
    e.pipeline,
    e.lead_source
FROM deal_events e
JOIN dim_company d
    ON d.master_id = e.master_id
   AND e.event_date >= d.effective_from
   AND (d.effective_to IS NULL OR e.event_date < d.effective_to)
ORDER BY e.deal_id;

-- fact_revenue_monthly (D11): agrega fact_deals en closedwon por mes
-- de close_date. No es una serie de mrr_mxn: no existe ninguna fuente
-- con MRR fechado (ADR-002), es revenue de deals ya cerrados.
CREATE OR REPLACE VIEW fact_revenue_monthly AS
WITH closed_deals AS (
    SELECT sd.master_id, sd.deal_id, sd.close_date, n.normalized_amount,
           strftime(sd.close_date, '%Y-%m') AS revenue_month
    FROM stg_deals sd
    JOIN mart_deal_normalized n ON n.deal_id = sd.deal_id
    WHERE sd.stage = 'closedwon' AND sd.close_date IS NOT NULL
),
monthly AS (
    SELECT master_id, revenue_month, SUM(normalized_amount) AS revenue_mxn
    FROM closed_deals
    GROUP BY master_id, revenue_month
)
SELECT
    d.company_sk,
    CAST(strftime(last_day(CAST(m.revenue_month || '-01' AS DATE)), '%Y%m%d') AS INTEGER) AS date_key,
    m.master_id,
    m.revenue_month,
    m.revenue_mxn
FROM monthly m
JOIN dim_company d
    ON d.master_id = m.master_id
   AND last_day(CAST(m.revenue_month || '-01' AS DATE)) >= d.effective_from
   AND (d.effective_to IS NULL OR last_day(CAST(m.revenue_month || '-01' AS DATE)) < d.effective_to)
ORDER BY m.master_id, m.revenue_month;

-- fact_support_tickets: grano de un ticket. stg_tickets no trae
-- master_id (Vitally no participa del crosswalk por id propio), asi
-- que se resuelve contra mart_company_core por vitally_id, el mismo
-- join que usa mart_support.sql (seccion 4.5 del diseno). La fecha
-- del hecho es created_date.
CREATE OR REPLACE VIEW fact_support_tickets AS
WITH ticket_company AS (
    SELECT t.*, c.master_id
    FROM stg_tickets t
    JOIN mart_company_core c ON c.vitally_id = t.vitally_id
)
SELECT
    d.company_sk,
    CAST(strftime(e.created_date, '%Y%m%d') AS INTEGER) AS date_key,
    e.master_id,
    e.ticket_id,
    e.priority,
    e.status,
    e.category,
    e.resolution_hours,
    e.csat_score
FROM ticket_company e
JOIN dim_company d
    ON d.master_id = e.master_id
   AND e.created_date >= d.effective_from
   AND (d.effective_to IS NULL OR e.created_date < d.effective_to)
ORDER BY e.ticket_id;

-- fact_marketing_touches: grano de un touch. stg_marketing_touches.sql
-- ya resuelve master_id contra identity_crosswalk por hubspot_id, asi
-- que aqui no se repite ese join. La fecha del hecho es touch_date.
CREATE OR REPLACE VIEW fact_marketing_touches AS
SELECT
    d.company_sk,
    CAST(strftime(t.touch_date, '%Y%m%d') AS INTEGER) AS date_key,
    t.master_id,
    t.touch_id,
    t.hubspot_id,
    t.channel,
    t.campaign
FROM stg_marketing_touches t
JOIN dim_company d
    ON d.master_id = t.master_id
   AND t.touch_date >= d.effective_from
   AND (d.effective_to IS NULL OR t.touch_date < d.effective_to)
ORDER BY t.touch_id;
