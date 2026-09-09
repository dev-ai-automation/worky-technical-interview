-- Motor: DuckDB 1.5.5. Antiguedad en meses desde `signup_date` hasta
-- `asof_month` (h1): la unica de las cuatro senales con cobertura
-- total (requirement "los cuatro subpuntajes normalizados por
-- percentil", escenario "antiguedad con cobertura total"), incluidas
-- las empresas que caen en la banda "sin historia" por falta de uso.
--
-- `GREATEST(..., 0)` recorta a cero una empresa dada de alta despues
-- de su propio mes de corte: sin este recorte, una alta muy reciente
-- entregaria un `datediff` negativo, que ninguna otra senal del score
-- puede producir.
CREATE OR REPLACE VIEW health_tenure AS
SELECT
    master_id,
    GREATEST(datediff('month', CAST(signup_date AS DATE), CAST(asof_month || '-01' AS DATE)), 0) AS sig_tenure
FROM health_company_asof;
