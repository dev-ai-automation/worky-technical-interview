-- Staging de tickets (Vitally): tipa fecha, horas de resolucion y csat.
-- mart_support la consume en el PR 4; aqui solo tipa y recorta.
CREATE OR REPLACE VIEW stg_tickets AS
SELECT
    trim(ticket_id)                                     AS ticket_id,
    trim(vitally_id)                                     AS vitally_id,
    CAST(created_date AS DATE)                            AS created_date,
    trim(priority)                                         AS priority,
    trim(status)                                            AS status,
    trim(category)                                           AS category,
    CAST(resolution_hours AS DECIMAL(10,2))                  AS resolution_hours,
    CAST(csat_score AS DECIMAL(3,2))                           AS csat_score
FROM raw_tickets;
