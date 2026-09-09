# Reporte de análisis de A1 sobre la sábana

## Encabezado

| Campo | Valor |
|---|---|
| motor | DuckDB 1.5.5 |
| dataset_asof | 2024-08-31 |
| ruleset_version | 1.0.0 |
| comando | python -m worky_engine analyze --data-dir <ruta> --out-dir outputs/analysis |

| Salida | Filas |
|---|---|
| a1_01_active_mrr | 37 |
| a1_02_usage_drop | 89 |
| a1_03_cohort_retention | 120 |
| a1_04_attribution | 15 |
| a1_05_orphan_deals | 35 |
| a1_06_negative_hours | 48 |
| analysis_exceptions | 48 |

## A1.1. MRR activo por segmento e industria

**Definición (ADR-004):** tabla con una fila por segmento e industria de las empresas activas (`churn_date` nulo), con dos columnas de MRR: la que reporta el CRM y el total con los valores imputados del ADR-002, más una fila de totales. El MRR activo que se reporta es el total con imputados; el del CRM se muestra al lado.

**Motor:** DuckDB 1.5.5

**SQL** (`a1_01_active_mrr.sql`):

```sql
-- Motor: DuckDB 1.5.5. A1.1, MRR activo por segmento e industria (ADR-004).
-- Activa significa churn_date nulo. Dos columnas de MRR: la que reporta
-- el CRM (mrr_source = 'crm') y el total con valores imputados del
-- ADR-002 (mrr_source in 'crm' o 'imputed_from_deal'), mas una fila de
-- totales via GROUPING SETS. row_type ordena la fila de totales al
-- final porque 'segment' es menor que 'total' en orden alfabetico.
CREATE OR REPLACE VIEW analysis_a1_01_active_mrr AS
WITH active AS (
    SELECT segment, industry, mrr_source,
           CAST(NULLIF(mrr_mxn, '') AS DECIMAL(14,2)) AS mrr_mxn
    FROM mart_master_dataset
    WHERE churn_date IS NULL
),
grouped AS (
    SELECT segment, industry,
           GROUPING(segment, industry)                                  AS grouping_id,
           COUNT(*)                                                     AS companies_active,
           CAST(SUM(CASE WHEN mrr_source = 'imputed_from_deal' THEN 1 ELSE 0 END) AS BIGINT) AS companies_imputed,
           CAST(SUM(CASE WHEN mrr_source = 'unresolved' THEN 1 ELSE 0 END) AS BIGINT) AS companies_unresolved,
           SUM(CASE WHEN mrr_source = 'crm' THEN mrr_mxn ELSE 0 END)     AS mrr_crm_mxn,
           SUM(COALESCE(mrr_mxn, 0))                                     AS mrr_total_mxn
    FROM active
    GROUP BY GROUPING SETS ((segment, industry), ())
)
SELECT
    CASE WHEN grouping_id = 3 THEN 'TOTAL' ELSE segment END              AS segment,
    CASE WHEN grouping_id = 3 THEN '' ELSE COALESCE(industry, '') END    AS industry,
    companies_active, companies_imputed, companies_unresolved,
    printf('%.2f', mrr_crm_mxn)                                          AS mrr_crm_mxn,
    printf('%.2f', mrr_total_mxn)                                        AS mrr_total_mxn,
    CASE WHEN grouping_id = 3 THEN 'total' ELSE 'segment' END             AS row_type
FROM grouped
ORDER BY row_type, segment, industry;
```

**Resultado** (`a1_01_active_mrr.csv`):

| segment | industry | companies_active | companies_imputed | companies_unresolved | mrr_crm_mxn | mrr_total_mxn | row_type |
|---|---|---|---|---|---|---|---|
| Enterprise | Agroindustria | 4 | 0 | 0 | 201508.00 | 201508.00 | segment |
| Enterprise | Alimentos | 7 | 0 | 0 | 413674.00 | 413674.00 | segment |
| Enterprise | Automotriz | 9 | 0 | 0 | 642591.00 | 642591.00 | segment |
| Enterprise | Construcción | 10 | 1 | 0 | 443163.00 | 522213.00 | segment |
| Enterprise | Educación | 6 | 2 | 0 | 221219.00 | 1211212.00 | segment |
| Enterprise | Hospitalidad | 7 | 0 | 0 | 421224.00 | 421224.00 | segment |
| Enterprise | Logística | 6 | 1 | 0 | 898299.50 | 940691.50 | segment |
| Enterprise | Manufactura | 6 | 2 | 0 | 239486.00 | 714225.00 | segment |
| Enterprise | Retail | 10 | 0 | 0 | 618214.00 | 618214.00 | segment |
| Enterprise | Salud | 5 | 0 | 0 | 1199420.00 | 1199420.00 | segment |
| Enterprise | Servicios Financieros | 9 | 1 | 0 | 467410.00 | 512460.00 | segment |
| Enterprise | Tecnología | 5 | 1 | 0 | 258385.00 | 328929.00 | segment |
| Mid-Market | Agroindustria | 14 | 1 | 0 | 265075.00 | 283742.00 | segment |
| Mid-Market | Alimentos | 21 | 0 | 0 | 609138.00 | 609138.00 | segment |
| Mid-Market | Automotriz | 15 | 0 | 0 | 713664.00 | 713664.00 | segment |
| Mid-Market | Construcción | 13 | 1 | 0 | 384188.00 | 666404.00 | segment |
| Mid-Market | Educación | 16 | 1 | 0 | 749527.00 | 894127.00 | segment |
| Mid-Market | Hospitalidad | 21 | 1 | 0 | 346462.00 | 359598.00 | segment |
| Mid-Market | Logística | 11 | 0 | 0 | 646806.50 | 646806.50 | segment |
| Mid-Market | Manufactura | 18 | 1 | 0 | 752616.00 | 772439.00 | segment |
| Mid-Market | Retail | 12 | 0 | 0 | 233969.00 | 233969.00 | segment |
| Mid-Market | Salud | 10 | 1 | 0 | 154039.00 | 178032.00 | segment |
| Mid-Market | Servicios Financieros | 22 | 2 | 0 | 349097.00 | 402283.00 | segment |
| Mid-Market | Tecnología | 6 | 0 | 0 | 118893.00 | 118893.00 | segment |
| SMB | Agroindustria | 28 | 1 | 0 | 144259.00 | 216283.00 | segment |
| SMB | Alimentos | 17 | 1 | 0 | 245481.00 | 253324.00 | segment |
| SMB | Automotriz | 31 | 0 | 0 | 242446.50 | 242446.50 | segment |
| SMB | Construcción | 30 | 0 | 0 | 158445.00 | 158445.00 | segment |
| SMB | Educación | 32 | 1 | 0 | 268081.50 | 299965.50 | segment |
| SMB | Hospitalidad | 15 | 0 | 0 | 76154.00 | 76154.00 | segment |
| SMB | Logística | 29 | 0 | 0 | 163190.00 | 163190.00 | segment |
| SMB | Manufactura | 17 | 1 | 0 | 231336.00 | 234469.00 | segment |
| SMB | Retail | 29 | 3 | 0 | 154777.00 | 171487.00 | segment |
| SMB | Salud | 21 | 0 | 0 | 162576.50 | 162576.50 | segment |
| SMB | Servicios Financieros | 27 | 1 | 0 | 269827.50 | 276691.50 | segment |
| SMB | Tecnología | 22 | 1 | 0 | 355138.50 | 362736.50 | segment |
| TOTAL |  | 561 | 25 | 0 | 13819780.50 | 16223225.50 | total |

El total con imputados es el MRR activo. 0 fila(s) de segmento quedan 'unresolved' (aportan cero pesos y siguen contando en `companies_active`).

## A1.2. Caída relativa de uso al churn

**Definición (ADR-004):** para cada cuenta con churn y cuenta de producto, el promedio de `active_users` en los tres meses calendario anteriores al mes de baja (ese mes queda fuera) contra el promedio de los primeros tres meses con uso de la cuenta. La caída relativa es (inicial menos final) entre inicial, en orden descendente.

**Motor:** DuckDB 1.5.5

**SQL** (`a1_02_usage_drop.sql`):

```sql
-- Motor: DuckDB 1.5.5. A1.2, caida relativa de uso al churn (ADR-004,
-- formula literal del caso, ADR-003 sobre el resguardo del mes de baja).
-- Promedio de active_users en los tres meses calendario anteriores al
-- mes de baja (ese mes queda fuera) contra el promedio de los primeros
-- tres meses con uso de la cuenta. windows_overlap marca a las cuentas
-- con menos de seis meses de uso, donde las dos ventanas pueden
-- compartir al menos un mes.
CREATE OR REPLACE VIEW analysis_a1_02_usage_drop AS
WITH churned AS (
    SELECT master_id, hubspot_id, company_name, account_id, churn_date,
           substr(churn_date, 1, 7) AS churn_month
    FROM mart_master_dataset
    WHERE churn_status = 'churned' AND account_id IS NOT NULL
),
series AS (
    SELECT c.master_id, u.month, u.active_users,
           ROW_NUMBER() OVER (PARTITION BY c.master_id ORDER BY u.month) AS month_rank
    FROM churned c
    JOIN stg_product_usage u ON u.account_id = c.account_id
),
-- primeros tres meses con uso por orden calendario, no los tres meses
-- siguientes al signup_date: la cuenta de producto puede arrancar despues
first_window AS (
    SELECT master_id, AVG(active_users) AS avg_first
    FROM series WHERE month_rank <= 3 GROUP BY master_id
),
-- los tres meses calendario anteriores al mes de baja; el mes de baja
-- queda fuera (ADR-003, misma razon que el resguardo de trend_usage)
last_window AS (
    SELECT s.master_id, AVG(s.active_users) AS avg_last
    FROM series s
    JOIN churned c ON c.master_id = s.master_id
    WHERE s.month < c.churn_month
      AND s.month >= strftime(CAST(c.churn_month || '-01' AS DATE) - INTERVAL 3 MONTH, '%Y-%m')
    GROUP BY s.master_id
),
totals AS (SELECT master_id, COUNT(*) AS usage_months FROM series GROUP BY master_id)
SELECT
    c.master_id, c.hubspot_id, c.company_name, c.account_id, c.churn_date, c.churn_month,
    COALESCE(t.usage_months, 0)                                   AS usage_months,
    printf('%.2f', f.avg_first)                                   AS avg_users_first_3,
    printf('%.2f', l.avg_last)                                    AS avg_users_last_3_before_churn,
    CASE WHEN t.usage_months IS NULL OR l.avg_last IS NULL OR f.avg_first = 0 THEN NULL
         ELSE printf('%.6f', (f.avg_first - l.avg_last) / f.avg_first) END AS drop_relative,
    CASE WHEN t.usage_months IS NULL THEN 'no_usage'
         WHEN l.avg_last IS NULL     THEN 'final_window_empty'
         WHEN f.avg_first = 0        THEN 'initial_avg_zero'
         ELSE 'computed' END                                       AS drop_status,
    (COALESCE(t.usage_months, 0) < 6)                              AS windows_overlap
FROM churned c
LEFT JOIN totals t       ON t.master_id = c.master_id
LEFT JOIN first_window f ON f.master_id = c.master_id
LEFT JOIN last_window l  ON l.master_id = c.master_id
-- drop_relative es texto con seis decimales para el golden; el orden usa
-- el valor numerico, si no los negativos se ordenan al reves.
ORDER BY CAST(drop_relative AS DOUBLE) DESC NULLS LAST, master_id;
```

**Resultado** (primeras filas, total en `a1_02_usage_drop.csv`):

| master_id | hubspot_id | company_name | account_id | churn_date | churn_month | usage_months | avg_users_first_3 | avg_users_last_3_before_churn | drop_relative | drop_status | windows_overlap |
|---|---|---|---|---|---|---|---|---|---|---|---|
| d3325cc67acf | HS-100156 | Laboratorios Marín, del Río y Garrido | ACC-2155 | 2024-02-18 | 2024-02 | 16 | 4.33 | 1.00 | 0.769231 | computed | False |
| db6aaecba31f | HS-100083 | Ferrer-Bernal e Hijos | ACC-2082 | 2023-12-09 | 2023-12 | 10 | 5.00 | 1.33 | 0.733333 | computed | False |
| dcf4823a4d63 | HS-100614 | Tijerina y Laboy S.C. | ACC-2613 | 2023-07-20 | 2023-07 | 11 | 3.33 | 1.00 | 0.700000 | computed | False |
| 8ab5e8824094 | HS-100453 | Madrid S.A. | ACC-2452 | 2023-08-16 | 2023-08 | 6 | 6.00 | 2.00 | 0.666667 | computed | False |
| acef081a80f0 | HS-100217 | Cornejo-Navarrete S.A. | ACC-2216 | 2024-05-21 | 2024-05 | 9 | 5.00 | 1.67 | 0.666667 | computed | False |
| c14e78b458d1 | HS-100072 | Proyectos Jaramillo, Santillán y Solís | ACC-2071 | 2024-05-01 | 2024-05 | 8 | 11.00 | 3.67 | 0.666667 | computed | False |
| c194e3bdfad5 | HS-100311 | Tovar A.C. | ACC-2310 | 2023-10-29 | 2023-10 | 13 | 9.00 | 3.00 | 0.666667 | computed | False |
| d6eff0593968 | HS-100101 | Grupo Hinojosa y Mojica | ACC-2100 | 2023-06-13 | 2023-06 | 6 | 3.00 | 1.00 | 0.666667 | computed | False |
| eb78824cdc91 | HS-100187 | Marroquín, Leiva y Maya | ACC-2186 | 2024-02-08 | 2024-02 | 12 | 21.67 | 7.67 | 0.646154 | computed | False |
| 6bca486a099d | HS-100336 | Laureano-Ocasio | ACC-2335 | 2024-03-09 | 2024-03 | 15 | 10.33 | 3.67 | 0.645161 | computed | False |
| aa6b09af8aaf | HS-100189 | Industrias Ceballos, Lozada y Nava | ACC-2188 | 2024-05-02 | 2024-05 | 11 | 15.67 | 5.67 | 0.638298 | computed | False |
| 14e457b52fab | HS-100358 | Zapata-Moreno | ACC-2357 | 2023-05-20 | 2023-05 | 9 | 42.00 | 15.33 | 0.634921 | computed | False |
| 868d321ac39e | HS-100225 | de Jesús y Campos y Asociados | ACC-2224 | 2024-06-06 | 2024-06 | 7 | 9.00 | 3.33 | 0.629630 | computed | False |
| 4cfcbde1f51f | HS-100505 | Magaña-Sevilla | ACC-2504 | 2024-04-21 | 2024-04 | 18 | 47.33 | 17.67 | 0.626761 | computed | False |
| 52584d35f5ce | HS-100111 | Industrias Puente y Tello | ACC-2110 | 2024-02-29 | 2024-02 | 11 | 15.00 | 5.67 | 0.622222 | computed | False |

Total: 89 filas. La tabla completa está en `a1_02_usage_drop.csv`.

33 de 89 cuentas traen `windows_overlap` en verdadero: tienen menos de seis meses de uso y sus dos ventanas pueden compartir algun mes.

## A1.3. Retención por cohorte de alta

**Definición (ADR-004):** cohorte por mes de `signup_date` de HubSpot. Una cuenta sigue activa en el mes k si no ha hecho churn k meses despues de su alta, para k en 1, 3, 6 y 12. Las celdas de cohortes que todavía no cumplen k meses al cierre de los datos quedan vacias, sin calcularse con dato parcial.

**Motor:** DuckDB 1.5.5

**SQL** (`a1_03_cohort_retention.sql`):

```sql
-- Motor: DuckDB 1.5.5. A1.3, retencion por cohorte de alta (ADR-004).
-- Cohorte por mes calendario de signup_date. Una cuenta sigue activa en
-- el mes k si no ha hecho churn k meses despues del alta: la empresa
-- que hace churn exactamente en el mes k (months_to_churn = k) ya no
-- cuenta como activa en k, por eso la comparacion es months_to_churn
-- estrictamente mayor a k. Las celdas de cohortes que todavia no
-- cumplen k meses al cierre de los datos quedan censoradas y vacias,
-- nunca calculadas con dato parcial. Formato largo: una fila por
-- cohorte y por k (D8); report.py la pivotea a matriz en el PR 3.
-- Una sola consulta con CTEs, tal como exige el ADR-004.
CREATE OR REPLACE VIEW analysis_a1_03_cohort_retention AS
WITH dataset_end AS (
    -- cierre de los datos derivado de la sabana, nunca escrito como
    -- constante: dataset_asof es la fecha maxima presente en las siete
    -- tablas (D9) y en este dataset da 2024-08-31
    SELECT substr(MAX(dataset_asof), 1, 7) AS end_month FROM mart_master_dataset
),
cohorts AS (
    SELECT substr(signup_date, 1, 7) AS cohort_month,
           CASE WHEN churn_date IS NULL THEN NULL
                ELSE datediff('month', CAST(signup_date AS DATE), CAST(churn_date AS DATE))
           END AS months_to_churn
    FROM mart_master_dataset
),
cohort_size AS (
    SELECT c.cohort_month, COUNT(*) AS cohort_size,
           datediff('month', CAST(c.cohort_month || '-01' AS DATE),
                             CAST(e.end_month || '-01' AS DATE)) AS months_elapsed
    FROM cohorts c CROSS JOIN dataset_end e
    GROUP BY c.cohort_month, months_elapsed
),
horizons AS (SELECT unnest([1, 3, 6, 12]) AS k),
cells AS (
    SELECT s.cohort_month, h.k, s.cohort_size, s.months_elapsed,
           SUM(CASE WHEN c.months_to_churn IS NULL OR c.months_to_churn > h.k
                    THEN 1 ELSE 0 END) AS retained
    FROM cohort_size s
    JOIN cohorts c ON c.cohort_month = s.cohort_month
    CROSS JOIN horizons h
    GROUP BY s.cohort_month, h.k, s.cohort_size, s.months_elapsed
)
SELECT cohort_month, k, cohort_size,
       -- texto para que el golden no muestre 23.0 cuando hay celdas censuradas nulas
       CASE WHEN months_elapsed < k THEN NULL ELSE CAST(retained AS VARCHAR) END AS retained,
       CASE WHEN months_elapsed < k THEN NULL
            ELSE printf('%.2f', 100.0 * retained / cohort_size) END AS retention_pct,
       CASE WHEN months_elapsed < k THEN 'censored' ELSE 'computed' END AS cell_status
FROM cells
ORDER BY cohort_month, k;
```

**Resultado**, pivoteado a una fila por cohorte y una columna por k (`a1_03_cohort_retention.csv` trae el formato largo):

| cohort_month | cohort_size | k=1 | k=3 | k=6 | k=12 |
|---|---|---|---|---|---|
| 2022-01 | 23 | 100.00 | 100.00 | 95.65 | 86.96 |
| 2022-02 | 18 | 100.00 | 94.44 | 94.44 | 94.44 |
| 2022-03 | 20 | 100.00 | 100.00 | 95.00 | 95.00 |
| 2022-04 | 13 | 100.00 | 100.00 | 100.00 | 100.00 |
| 2022-05 | 20 | 100.00 | 100.00 | 100.00 | 95.00 |
| 2022-06 | 22 | 100.00 | 100.00 | 90.91 | 90.91 |
| 2022-07 | 28 | 100.00 | 100.00 | 100.00 | 96.43 |
| 2022-08 | 28 | 100.00 | 100.00 | 96.43 | 89.29 |
| 2022-09 | 23 | 100.00 | 95.65 | 95.65 | 91.30 |
| 2022-10 | 25 | 100.00 | 100.00 | 96.00 | 88.00 |
| 2022-11 | 20 | 100.00 | 100.00 | 95.00 | 95.00 |
| 2022-12 | 21 | 100.00 | 95.24 | 95.24 | 80.95 |
| 2023-01 | 26 | 100.00 | 96.15 | 92.31 | 88.46 |
| 2023-02 | 21 | 100.00 | 100.00 | 90.48 | 80.95 |
| 2023-03 | 24 | 100.00 | 100.00 | 95.83 | 75.00 |
| 2023-04 | 25 | 100.00 | 100.00 | 100.00 | 96.00 |
| 2023-05 | 19 | 100.00 | 94.74 | 89.47 | 78.95 |
| 2023-06 | 15 | 100.00 | 100.00 | 100.00 | 100.00 |
| 2023-07 | 28 | 100.00 | 96.43 | 92.86 | 89.29 |
| 2023-08 | 25 | 100.00 | 96.00 | 92.00 | 92.00 |
| 2023-09 | 14 | 100.00 | 100.00 | 85.71 |  |
| 2023-10 | 15 | 100.00 | 100.00 | 93.33 |  |
| 2023-11 | 14 | 100.00 | 92.86 | 92.86 |  |
| 2023-12 | 25 | 100.00 | 96.00 | 80.00 |  |
| 2024-01 | 18 | 100.00 | 88.89 | 83.33 |  |
| 2024-02 | 26 | 100.00 | 92.31 | 84.62 |  |
| 2024-03 | 25 | 100.00 | 84.00 |  |  |
| 2024-04 | 26 | 100.00 | 100.00 |  |  |
| 2024-05 | 23 | 100.00 | 100.00 |  |  |
| 2024-06 | 20 | 100.00 |  |  |  |

15 de 120 celdas quedan censuradas: la cohorte todavía no cumple ese k al cierre de los datos, y una celda censurada no se calcula con dato parcial.

## A1.4. Atribución por primer y último touch

**Definición (ADR-004):** grano deal. Cada deal se atribuye a dos canales: el primer touch de su empresa y el último touch anterior a su fecha de creacion, con empate por `touch_id` igual que el motor. Convierte si su etapa es `closedwon`. La tasa por canal es deals ganados entre deals atribuidos, y se reportan ambos modelos lado a lado.

**Motor:** DuckDB 1.5.5

**SQL** (`a1_04_attribution.sql`):

```sql
-- Motor: DuckDB 1.5.5. A1.4, atribucion por primer y ultimo touch
-- (ADR-004). Grano deal: cada deal se atribuye a dos canales, el
-- primer touch de su empresa (mart_first_touch) y el ultimo touch
-- anterior a su created_date (mart_last_touch, D7). Convierte si
-- stage = closedwon. La tasa por canal es deals ganados entre deals
-- atribuidos, para cada modelo. El empate por touch_id ya lo resuelven
-- mart_first_touch y mart_last_touch, cada una en el extremo que le
-- toca. channel_rank = 1 es el canal ganador de cada modelo; el
-- reporte compara los dos ganadores sin recalcular nada.
CREATE OR REPLACE VIEW analysis_a1_04_attribution AS
WITH attributed AS (
    SELECT d.deal_id, d.stage,
           COALESCE(ft.first_touch_channel, 'unknown')        AS first_touch_channel,
           COALESCE(lt.last_touch_channel, 'no_prior_touch')  AS last_touch_channel
    FROM stg_deals d
    LEFT JOIN mart_first_touch ft ON ft.master_id = d.master_id
    LEFT JOIN mart_last_touch  lt ON lt.deal_id  = d.deal_id
    WHERE d.master_id IS NOT NULL      -- los deals huerfanos son A1.5
),
by_model AS (
    SELECT 'first_touch' AS model, first_touch_channel AS channel, stage FROM attributed
    UNION ALL
    SELECT 'last_touch'  AS model, last_touch_channel  AS channel, stage FROM attributed
),
rates AS (
    SELECT model, channel, COUNT(*) AS deals_attributed,
           CAST(SUM(CASE WHEN stage = 'closedwon' THEN 1 ELSE 0 END) AS BIGINT) AS deals_won
    FROM by_model GROUP BY model, channel
)
SELECT model, channel, deals_attributed, deals_won,
       printf('%.6f', deals_won * 1.0 / deals_attributed) AS conversion_rate,
       ROW_NUMBER() OVER (
           PARTITION BY model
           ORDER BY deals_won * 1.0 / deals_attributed DESC, channel
       ) AS channel_rank
FROM rates
ORDER BY model, channel_rank;
```

**Resultado** (`a1_04_attribution.csv`):

| model | channel | deals_attributed | deals_won | conversion_rate | channel_rank |
|---|---|---|---|---|---|
| first_touch | Paid Search | 120 | 27 | 0.225000 | 1 |
| first_touch | Organic | 129 | 19 | 0.147287 | 2 |
| first_touch | Webinar | 128 | 16 | 0.125000 | 3 |
| first_touch | Outbound SDR | 153 | 19 | 0.124183 | 4 |
| first_touch | Partner | 130 | 16 | 0.123077 | 5 |
| first_touch | Evento | 147 | 14 | 0.095238 | 6 |
| first_touch | Referral | 155 | 14 | 0.090323 | 7 |
| last_touch | Paid Search | 87 | 20 | 0.229885 | 1 |
| last_touch | Partner | 93 | 13 | 0.139785 | 2 |
| last_touch | no_prior_touch | 326 | 42 | 0.128834 | 3 |
| last_touch | Organic | 87 | 11 | 0.126437 | 4 |
| last_touch | Evento | 103 | 12 | 0.116505 | 5 |
| last_touch | Outbound SDR | 95 | 11 | 0.115789 | 6 |
| last_touch | Webinar | 85 | 8 | 0.094118 | 7 |
| last_touch | Referral | 86 | 8 | 0.093023 | 8 |

El canal ganador (`channel_rank = 1`) es 'Paid Search' en el modelo de primer touch y 'Paid Search' en el de último touch; el ganador no cambia entre modelos. En el modelo de último touch, 326 deals caen en 'no_prior_touch': se crearon antes del primer touch registrado de su empresa, así que no tienen un último touch anterior que atribuirles.

## A1.5. Deals sin empresa real

**Definición (ADR-004):** consulta SQL equivalente a la cuarentena del motor: deals de `crm_hubspot.deals` cuyo `hubspot_id` no existe en ninguna empresa real.

**Motor:** DuckDB 1.5.5

**SQL** (`a1_05_orphan_deals.sql`):

```sql
-- Motor: DuckDB 1.5.5. A1.5, deals sin empresa real (ADR-004). Consulta
-- SQL equivalente a la cuarentena del motor: deals cuyo hubspot_id no
-- existe en ninguna empresa real. El segundo LEFT JOIN, contra
-- quarantine_companies, evita el falso positivo de un deal que apunta a
-- un clon remapeado a su sobreviviente (stg_deals.master_id ya lo
-- resuelve): ese deal si tiene empresa real y no debe salir como
-- huerfano. amount se reporta crudo (no amount_mxn) porque estos deals
-- no tienen empresa de la que heredar la moneda, en unidades mezcladas
-- segun la adenda 1 del ADR-002.
CREATE OR REPLACE VIEW analysis_a1_05_orphan_deals AS
SELECT
    d.deal_id, d.hubspot_id, d.stage,
    printf('%.2f', d.amount)             AS amount,
    strftime(d.created_date, '%Y-%m-%d') AS created_date,
    strftime(d.close_date, '%Y-%m-%d')   AS close_date,
    d.pipeline, d.lead_source
FROM stg_deals d
LEFT JOIN mart_master_dataset m  ON m.hubspot_id = d.hubspot_id
LEFT JOIN quarantine_companies q ON q.hubspot_id = d.hubspot_id
WHERE m.hubspot_id IS NULL   -- ninguna empresa real de la sabana tiene ese hubspot_id
  AND q.hubspot_id IS NULL   -- y tampoco es un clon remapeado a su sobreviviente
ORDER BY d.deal_id;
```

**Resultado** (`a1_05_orphan_deals.csv`):

| deal_id | hubspot_id | stage | amount | created_date | close_date | pipeline | lead_source |
|---|---|---|---|---|---|---|---|
| D00963 | HS-990000 | closedwon | 11096.00 | 2024-02-15 | 2024-03-20 | New Business | Webinar |
| D00964 | HS-990001 | closedwon | 18094.00 | 2024-02-15 | 2024-03-20 | New Business | Outbound SDR |
| D00965 | HS-990002 | closedwon | 29470.00 | 2024-02-15 | 2024-03-20 | New Business | Partner |
| D00966 | HS-990003 | closedwon | 16926.00 | 2024-02-15 | 2024-03-20 | New Business | Outbound SDR |
| D00967 | HS-990004 | closedwon | 17131.00 | 2024-02-15 | 2024-03-20 | New Business | Organic |
| D00968 | HS-990005 | closedwon | 15490.00 | 2024-02-15 | 2024-03-20 | New Business | Referral |
| D00969 | HS-990006 | closedwon | 7524.00 | 2024-02-15 | 2024-03-20 | New Business | Referral |
| D00970 | HS-990007 | closedwon | 28017.00 | 2024-02-15 | 2024-03-20 | New Business | Evento |
| D00971 | HS-990008 | closedwon | 22638.00 | 2024-02-15 | 2024-03-20 | New Business | Organic |
| D00972 | HS-990009 | closedwon | 8166.00 | 2024-02-15 | 2024-03-20 | New Business | Partner |
| D00973 | HS-990010 | closedwon | 20588.00 | 2024-02-15 | 2024-03-20 | New Business | Referral |
| D00974 | HS-990011 | closedwon | 8434.00 | 2024-02-15 | 2024-03-20 | New Business | Organic |
| D00975 | HS-990012 | closedwon | 28596.00 | 2024-02-15 | 2024-03-20 | New Business | Partner |
| D00976 | HS-990013 | closedwon | 28007.00 | 2024-02-15 | 2024-03-20 | New Business | Evento |
| D00977 | HS-990014 | closedwon | 12338.00 | 2024-02-15 | 2024-03-20 | New Business | Referral |
| D00978 | HS-990015 | closedwon | 23817.00 | 2024-02-15 | 2024-03-20 | New Business | Outbound SDR |
| D00979 | HS-990016 | closedwon | 25277.00 | 2024-02-15 | 2024-03-20 | New Business | Outbound SDR |
| D00980 | HS-990017 | closedwon | 24367.00 | 2024-02-15 | 2024-03-20 | New Business | Paid Search |
| D00981 | HS-990018 | closedwon | 10614.00 | 2024-02-15 | 2024-03-20 | New Business | Webinar |
| D00982 | HS-990019 | closedwon | 19695.00 | 2024-02-15 | 2024-03-20 | New Business | Partner |
| D00983 | HS-990020 | closedwon | 6885.00 | 2024-02-15 | 2024-03-20 | New Business | Outbound SDR |
| D00984 | HS-990021 | closedwon | 28144.00 | 2024-02-15 | 2024-03-20 | New Business | Paid Search |
| D00985 | HS-990022 | closedwon | 27348.00 | 2024-02-15 | 2024-03-20 | New Business | Paid Search |
| D00986 | HS-990023 | closedwon | 28555.00 | 2024-02-15 | 2024-03-20 | New Business | Webinar |
| D00987 | HS-990024 | closedwon | 13257.00 | 2024-02-15 | 2024-03-20 | New Business | Partner |
| D00988 | HS-990025 | closedwon | 24586.00 | 2024-02-15 | 2024-03-20 | New Business | Outbound SDR |
| D00989 | HS-990026 | closedwon | 28075.00 | 2024-02-15 | 2024-03-20 | New Business | Outbound SDR |
| D00990 | HS-990027 | closedwon | 12051.00 | 2024-02-15 | 2024-03-20 | New Business | Referral |
| D00991 | HS-990028 | closedwon | 22642.00 | 2024-02-15 | 2024-03-20 | New Business | Referral |
| D00992 | HS-990029 | closedwon | 12620.00 | 2024-02-15 | 2024-03-20 | New Business | Evento |
| D00993 | HS-990030 | closedwon | 21644.00 | 2024-02-15 | 2024-03-20 | New Business | Organic |
| D00994 | HS-990031 | closedwon | 22682.00 | 2024-02-15 | 2024-03-20 | New Business | Referral |
| D00995 | HS-990032 | closedwon | 5222.00 | 2024-02-15 | 2024-03-20 | New Business | Paid Search |
| D00996 | HS-990033 | closedwon | 28334.00 | 2024-02-15 | 2024-03-20 | New Business | Webinar |
| D00997 | HS-990034 | closedwon | 8921.00 | 2024-02-15 | 2024-03-20 | New Business | Webinar |

35 deals por 667251.00 en unidades mezcladas (mensual y anual sin distincion, adenda 1 del ADR-002): cada deal es el único de su id, así que no hay forma rigurosa de saber en que unidad viene su monto.

## A1.6. Tickets con horas de resolución negativas

**Definición (ADR-004):** los tickets con `resolution_hours` negativo se dejan en nulo para cualquier promedio de tiempo de resolución, se conservan en conteos y CSAT, y se registran en `analysis_exceptions.csv` con las mismas columnas de `exceptions_log.csv`, sin tocar ninguna salida existente de A0.

**Motor:** DuckDB 1.5.5

**SQL** (`a1_06_negative_hours.sql`, incluye la vista de detalle y `analysis_exceptions`):

```sql
-- Motor: DuckDB 1.5.5. A1.6, tickets con resolution_hours negativo
-- (ADR-004). No se corrige el signo ni se excluyen los tickets:
-- cualquier promedio de tiempo de resolucion en el analisis los trata
-- como nulo, pero se conservan en conteos y CSAT. resolution_hours_abs
-- deja comparar contra el rango de los tickets positivos sin rehacer
-- la cuenta, y status es la evidencia de por que el signo no se voltea
-- sin confirmar (hay tickets abiertos con horas ya registradas).
CREATE OR REPLACE VIEW analysis_a1_06_negative_hours AS
SELECT
    t.ticket_id, t.vitally_id, x.master_id,
    strftime(t.created_date, '%Y-%m-%d')    AS created_date,
    t.priority, t.status, t.category,
    printf('%.2f', t.resolution_hours)      AS resolution_hours,
    printf('%.2f', abs(t.resolution_hours)) AS resolution_hours_abs,
    printf('%.2f', t.csat_score)            AS csat_score
FROM stg_tickets t
LEFT JOIN identity_crosswalk x ON x.vitally_id = t.vitally_id
WHERE t.resolution_hours < 0
ORDER BY t.ticket_id;

-- Vista de excepciones: mismas once columnas de exceptions_log (A0), en
-- el mismo orden, para que A6 pueda fusionar los dos logs cuando
-- corrija el signo en origen. exception_id es
-- sha256(exception_code|source_system|source_id|field_name) truncado a
-- 12 caracteres hex, la misma formula y el mismo orden de campos que
-- mart_mrr.sql. applied_value queda en el literal 'null' porque lo
-- aplicado fue dejar el campo en nulo para promedios, y la columna no
-- puede quedar vacia (regla del contrato de A0).
CREATE OR REPLACE VIEW analysis_exceptions AS
SELECT
    substr(
        sha256('negative_resolution_hours|vitally|' || t.ticket_id || '|resolution_hours'), 1, 12
    )                                                  AS exception_id,
    'negative_resolution_hours'                        AS exception_code,
    'vitally'                                          AS source_system,
    t.ticket_id                                        AS source_id,
    x.master_id                                        AS master_id,
    'resolution_hours'                                  AS field_name,
    printf('%.2f', t.resolution_hours)                  AS original_value,
    'null'                                              AS applied_value,
    t.status                                            AS evidence_ref,
    '1.0.0'                                             AS ruleset_version,
    (SELECT MAX(resolved_at) FROM identity_crosswalk)   AS decided_at
FROM stg_tickets t
LEFT JOIN identity_crosswalk x ON x.vitally_id = t.vitally_id
WHERE t.resolution_hours < 0
ORDER BY exception_code, source_id;
```

**Resultado** (primeras filas, total en `a1_06_negative_hours.csv`):

| ticket_id | vitally_id | master_id | created_date | priority | status | category | resolution_hours | resolution_hours_abs | csat_score |
|---|---|---|---|---|---|---|---|---|---|
| TK000013 | cus_100003 | 6d621ac6bce1 | 2023-08-31 | Medium | Closed | Duda funcional | -18.50 | 18.50 |  |
| TK000017 | cus_100005 | 5df58f1cd011 | 2024-04-11 | Medium | Closed | Onboarding | -56.90 | 56.90 |  |
| TK000025 | cus_100007 | bfcc93c1234c | 2023-07-23 | Low | Open | Duda funcional | -16.20 | 16.20 | 3.00 |
| TK000062 | cus_100020 | 7c49bd17517b | 2024-03-31 | Medium | Open | Bug plataforma | -8.00 | 8.00 | 2.00 |
| TK000081 | cus_100028 | 8dc56996e31a | 2024-03-08 | Medium | Closed | Bug plataforma | -2.40 | 2.40 | 3.00 |
| TK000099 | cus_100033 | c0d5050c1786 | 2023-01-31 | Medium | Closed | Duda funcional | -8.50 | 8.50 | 5.00 |
| TK000123 | cus_100043 | f750af5db82c | 2023-10-18 | Urgent | Open | Onboarding | -3.50 | 3.50 | 1.00 |
| TK000131 | cus_100048 | e5bcc1fbee61 | 2023-05-06 | High | Closed | Nómina errónea | -15.90 | 15.90 | 1.00 |
| TK000249 | cus_100084 | a323d4abf458 | 2023-03-15 | Low | Open | Nómina errónea | -9.40 | 9.40 |  |
| TK000262 | cus_100089 | 32abb429e0d8 | 2023-02-02 | Urgent | Closed | Bug plataforma | -58.20 | 58.20 |  |
| TK000282 | cus_100095 | 4b4752da4a83 | 2023-05-04 | Low | Closed | Bug plataforma | -9.30 | 9.30 | 2.00 |
| TK000345 | cus_100120 | 76352359fd43 | 2023-12-20 | Medium | Closed | Billing | -6.50 | 6.50 | 1.00 |
| TK000347 | cus_100120 | 76352359fd43 | 2023-12-30 | High | Open | Bug plataforma | -1.40 | 1.40 | 5.00 |
| TK000365 | cus_100126 | 1197d211e7e1 | 2023-08-29 | High | Closed | Bug plataforma | -10.40 | 10.40 | 2.00 |
| TK000442 | cus_100156 | f618418fca35 | 2023-11-29 | Medium | Open | Duda funcional | -4.00 | 4.00 |  |

Total: 48 filas. La tabla completa está en `a1_06_negative_hours.csv`.

**Justificación:**

> Los 48 tickets con `resolution_hours` negativo se dejan en nulo para cualquier promedio de tiempo de resolución, se conservan para conteos y CSAT, y quedan registrados en `analysis_exceptions.csv`. Sin el signo, la mayoría caen en el rango normal de los tickets positivos, lo que apunta a un error de captura con las fechas invertidas, pero 10 de los 48 siguen abiertos con horas ya registradas, así que voltear el signo sería asumir algo que el dato no confirma. Nulo con rastro es la única opción que no inventa datos, y la corrección en origen queda para A6.

## A1.7. Respuesta de diseño para escalar

A1.7 pregunta que cambia en el modelo y en el pipeline si la tabla de uso mensual crece a cientos de millones de filas por dia, en vez de las pocas miles de este caso. No es una consulta contra el dataset: es una decision de arquitectura, con este DDL como ilustracion, no ejecutable en este repositorio.

| Cambio | Que resuelve |
|---|---|
| Particionar el uso por mes y agrupar fisicamente por cuenta | Una consulta de un rango de meses lee solo esas particiones |
| Agregado mensual precalculado con la llave (account_id, month) | La sábana consume el agregado y no el detalle diario |
| Tabla de marca de agua por partición | Permite refrescar solo las particiones cuyos datos cambiaron |
| Ventana de reproceso acotada para datos que llegan tarde | Un registro con fecha de hace dos meses vuelve a agregar solo esa partición |

```sql
-- DDL ilustrativo, no se ejecuta en este repositorio.

-- 1. Detalle diario particionado por mes y ordenado por cuenta.
CREATE TABLE usage_daily (
    account_id   VARCHAR NOT NULL,
    usage_date   DATE    NOT NULL,
    month        VARCHAR(7) NOT NULL,   -- llave de particion
    active_users INTEGER NOT NULL,
    logins       INTEGER NOT NULL,
    ingested_at  TIMESTAMP NOT NULL
) PARTITIONED BY (month);

-- 2. Agregado mensual, que es lo que consume la sabana.
CREATE TABLE usage_monthly_rollup (
    account_id        VARCHAR    NOT NULL,
    month             VARCHAR(7) NOT NULL,
    active_users      INTEGER    NOT NULL,
    logins            INTEGER    NOT NULL,
    source_max_ingest TIMESTAMP  NOT NULL,
    PRIMARY KEY (account_id, month)
);

-- 3. Marca de agua por particion: que se cargo y hasta cuando.
CREATE TABLE refresh_state (
    table_name     VARCHAR    NOT NULL,
    month          VARCHAR(7) NOT NULL,
    last_ingest_at TIMESTAMP  NOT NULL,
    PRIMARY KEY (table_name, month)
);

-- 4. Refresco incremental: solo los meses con datos nuevos o corregidos.
MERGE INTO usage_monthly_rollup AS target
USING (
    SELECT account_id, month, SUM(active_users) AS active_users, SUM(logins) AS logins,
           MAX(ingested_at) AS source_max_ingest
    FROM usage_daily
    WHERE month IN (
        SELECT d.month
        FROM usage_daily d
        LEFT JOIN refresh_state r
            ON r.table_name = 'usage_monthly_rollup' AND r.month = d.month
        GROUP BY d.month, r.last_ingest_at
        HAVING r.last_ingest_at IS NULL OR MAX(d.ingested_at) > r.last_ingest_at
    )
    GROUP BY account_id, month
) AS source
ON target.account_id = source.account_id AND target.month = source.month
WHEN MATCHED THEN UPDATE SET
    active_users = source.active_users, logins = source.logins, source_max_ingest = source.source_max_ingest
WHEN NOT MATCHED THEN INSERT (account_id, month, active_users, logins, source_max_ingest)
    VALUES (source.account_id, source.month, source.active_users, source.logins, source.source_max_ingest);
```

El crosswalk de identidad (`identity_crosswalk`) y los marts siguen calculandose por encima del agregado mensual, no del detalle diario: cada refresco solo recalcula las cuentas cuyo mes cambio, y `dataset_asof` derivado de los datos, que este cambio ya usa, sigue siendo lo que audita hasta donde llego cada refresco.

## Referencias

- ADR-002: imputación y normalización de MRR (`docs/decisions/ADR-002-mrr-imputation-and-normalization.md`).
- ADR-003: ventana de tendencia de uso y resguardo de fuga (`docs/decisions/ADR-003-usage-trend-and-leakage-guard.md`).
- ADR-004: definiciones de las consultas de A1 (`docs/decisions/ADR-004-sql-analysis-definitions.md`).
