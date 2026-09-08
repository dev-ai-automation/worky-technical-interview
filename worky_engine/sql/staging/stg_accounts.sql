-- Staging de accounts (product_db): tipa la fecha de alta y recorta
-- espacios. mart_usage la consume en el PR 4.
CREATE OR REPLACE VIEW stg_accounts AS
SELECT
    trim(account_id)                                    AS account_id,
    trim(hubspot_id)                                     AS hubspot_id,
    trim(account_name)                                    AS account_name,
    CAST(created_at AS DATE)                              AS created_at
FROM raw_accounts;
