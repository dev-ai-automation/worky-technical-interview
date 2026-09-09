-- Motor: DuckDB 1.5.5. Une h1 a h5 en una sola fila por empresa
-- (decision D9 del diseno): la entrada que consume `scoring.py` para
-- calcular percentiles, bandas, marcas y la suma ponderada. Cada join
-- es por `master_id`, y las cinco vistas ya traen exactamente una fila
-- por empresa porque cada una parte de `health_company_asof`.
CREATE OR REPLACE VIEW health_asof_inputs AS
SELECT
    a.master_id, a.hubspot_id, a.account_id, a.vitally_id,
    a.segment, a.acquisition_channel, a.mrr_mxn, a.churned,
    a.signup_date, a.reference_month, a.asof_month,
    u.usage_months_asof, u.sig_momentum, u.sig_mom, u.sig_drawdown,
    t.sig_tenure,
    s.tickets_window_total, s.tickets_window_urgent, s.csat_window_avg,
    v.activation_raw
FROM health_company_asof a
JOIN health_usage_signals u ON u.master_id = a.master_id
JOIN health_tenure t ON t.master_id = a.master_id
JOIN mart_support_asof s ON s.master_id = a.master_id
JOIN health_activation v ON v.master_id = a.master_id
ORDER BY a.master_id;
