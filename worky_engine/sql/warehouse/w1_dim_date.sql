-- dim_date (D10): un dia de calendario por fila, de MIN(signup_date)
-- a dataset_asof, generado con generate_series para que el rango se
-- mueva con los datos y no con un valor fijo a mano. date_key es un
-- entero YYYYMMDD, la llave que usan los hechos de w5.
CREATE OR REPLACE VIEW dim_date AS
SELECT
    CAST(strftime(gs.day, '%Y%m%d') AS INTEGER) AS date_key,
    CAST(gs.day AS DATE)                        AS calendar_date,
    CAST(strftime(gs.day, '%Y') AS INTEGER)     AS year_number,
    CAST(strftime(gs.day, '%m') AS INTEGER)     AS month_number,
    strftime(gs.day, '%Y-%m')                    AS year_month
FROM generate_series(
    (SELECT MIN(signup_date) FROM mart_company_core),
    (SELECT CAST(dataset_asof AS DATE) FROM mart_master_dataset LIMIT 1),
    INTERVAL 1 DAY
) AS gs(day);
