-- Motor: DuckDB 1.5.5. Ventana de soporte de tres meses terminando en
-- `asof_month` (h1), distinta de `mart_support` (que agrega toda la
-- vida de la cuenta): `mart_support.sql` queda intacta, y esta vista
-- vive en `sql/health/` aunque conserva el prefijo `mart_` porque su
-- grano y su forma son las de un mart (decision D10 del diseno).
--
-- Resguardo de fuga (decision D11): `created_date` es una fecha, no un
-- mes, asi que el corte es por dia. El limite inferior es el primer
-- dia de los tres meses que terminan en `asof_month`
-- (`asof_month - 2 meses`), y el limite superior se escribe como
-- "antes del primer dia del mes siguiente al corte" para no depender
-- de cuantos dias tiene cada mes. Solo `priority = 'Urgent'` cuenta
-- como urgente; `csat_window_avg` promedia unicamente los tickets que
-- trajeron puntaje, igual que `mart_support.sql`.
CREATE OR REPLACE VIEW mart_support_asof AS
SELECT
    a.master_id,
    COUNT(t.ticket_id) AS tickets_window_total,
    -- CAST a BIGINT: SUM() de un CASE INTEGER da HUGEINT (mismo resguardo que mart_support.sql).
    CAST(SUM(CASE WHEN t.priority = 'Urgent' THEN 1 ELSE 0 END) AS BIGINT) AS tickets_window_urgent,
    CASE WHEN COUNT(t.csat_score) = 0 THEN NULL
         ELSE printf('%.2f', AVG(t.csat_score)) END AS csat_window_avg
FROM health_company_asof a
LEFT JOIN stg_tickets t
    ON t.vitally_id = a.vitally_id
   AND t.created_date >= CAST(a.asof_month || '-01' AS DATE) - INTERVAL 2 MONTH
   AND t.created_date < CAST(a.asof_month || '-01' AS DATE) + INTERVAL 1 MONTH
GROUP BY a.master_id;
