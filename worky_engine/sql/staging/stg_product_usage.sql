-- Staging de product_usage: tipa los conteos mensuales. `month` se deja
-- como texto `YYYY-MM`, que es como llega el dato, porque no describe un
-- dia y una comparacion lexicografica basta para ordenarlo y para MAX().
CREATE OR REPLACE VIEW stg_product_usage AS
SELECT
    trim(account_id)                                    AS account_id,
    trim(month)                                          AS month,
    CAST(active_users AS INTEGER)                        AS active_users,
    CAST(logins AS INTEGER)                               AS logins,
    CAST(payroll_runs_completed AS INTEGER)                AS payroll_runs_completed,
    CAST(features_used AS INTEGER)                          AS features_used,
    CAST(api_calls AS INTEGER)                                AS api_calls
FROM raw_product_usage;
