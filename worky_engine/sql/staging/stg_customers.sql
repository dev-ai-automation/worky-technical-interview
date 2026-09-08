-- Staging de customers (Vitally): recorta espacios, sin ningun join.
CREATE OR REPLACE VIEW stg_customers AS
SELECT
    trim(vitally_id)                                    AS vitally_id,
    trim(domain)                                         AS domain,
    trim(company_name)                                    AS company_name,
    trim(csm_email)                                        AS csm_email
FROM raw_customers;
