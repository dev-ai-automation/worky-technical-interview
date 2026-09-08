# Perfil del esquema tal cual: dataset_caso_v3 (3 sistemas sin sincronizar)

Este archivo es una fotografía de los tres sistemas origen exactamente como existen hoy, antes de cualquier limpieza o cruce. Sirve para ver qué datos hay disponibles en cada sistema, cómo está estructurada cada tabla, y dónde están los problemas de calidad de datos ya conocidos, antes de leer la decisión de resolución de identidad en el [ADR-001](../decisions/ADR-001-identity-resolution-scorecard.md).

Origen: `fundation-docs/dataset_caso_v3.zip` (SQLite + gemelos en CSV). Perfilado el 2026-09-07 con Python/pandas.
Ninguna tabla declara una PRIMARY KEY ni una FOREIGN KEY. Todas las llaves de abajo son *implícitas* y deben aplicarse desde el warehouse.

## Sistema 1: CRM de HubSpot (`crm_hubspot.db`), llave nativa `hubspot_id` (HS-######)

| Tabla | Filas | PK implícita | Columnas relevantes | Hallazgos de calidad de datos |
|---|---|---|---|---|
| companies | 678 | hubspot_id (única) | name, domain, segment, industry, mrr, currency, signup_date, csm_owner, plan, state, churn_date | mrr NULL = 56; currency USD = 22; signup_date con formatos mixtos (647 ISO, 31 DD/MM/YYYY); churn_date con valor = 95 (14%); 33 dominios duplicados (las filas HS-9000xx son clones en MAYÚSCULAS o con "SA DE CV" de filas HS-1000xx; unas cuantas colisiones reales como club290.com.mx); segment↔plan es una relación 1:1 estricta (SMB=Basico, Mid-Market=Pro, Enterprise=Premium) |
| deals | 997 | deal_id (única) | hubspot_id (FK→companies), stage, amount, created_date, close_date, owner, pipeline, lead_source | 35 deals huérfanos (hubspot_id ausente en companies), todos en `closedwon`, amount = 667,251; close_date NULL = 768 |
| marketing_touches | 1,635 | touch_id (única) | hubspot_id (FK→companies), channel, touch_date, campaign | 0 huérfanos; 650 empresas distintas con al menos un touch |

## Sistema 2: Product DB (`product_db.db`), llave nativa `account_id` (ACC-####)

| Tabla | Filas | PK implícita | Columnas relevantes | Hallazgos de calidad de datos |
|---|---|---|---|---|
| accounts | 650 | account_id (única) | hubspot_id (FK→companies, admite nulos), account_name, created_at | hubspot_id con valor en 596/650 (91.7%); las 596 resuelven a una empresa; 0 duplicados. De las 54 sin valor, 44 resuelven por nombre exacto normalizado; 10 tienen nombres truncados (por ejemplo "Sanches y Asocia", "Rosas-Var") |
| product_usage | 9,793 | compuesta (account_id, month) | active_users, logins, payroll_runs_completed, features_used, api_calls | 24 meses, de 2022-09 a 2024-08; 0 duplicados en (account, month); 3 cuentas sin uso; de 2 a 24 meses por cuenta |

## Sistema 3: Vitally CS/Soporte (`vitally_support.db`), llave nativa `vitally_id` (cus_######)

| Tabla | Filas | PK implícita | Columnas relevantes | Hallazgos de calidad de datos |
|---|---|---|---|---|
| customers | 650 | vitally_id (única) | domain, company_name, csm_email | SIN id compartido con HubSpot. Cruce exacto de dominio contra companies = 573/650; 77 sin cruce, de las cuales 75 cruzan por nombre normalizado. Patrones de dominio sin cruce: subdominio `app.`, `.mx` contra `.com.mx`, caracteres acentuados |
| tickets | 1,888 | ticket_id (única) | vitally_id (FK→customers), created_date, priority, status, category, resolution_hours, csat_score | resolution_hours negativo = 48, NULL = 206 (143 en Closed / 63 en Open); csat en NULL ≈ 28% sin importar el estado; 593/650 clientes tienen tickets |

## Uniones entre sistemas (como existen hoy)

| Relación | Mecanismo | Fuerza | Cobertura medida |
|---|---|---|---|
| companies → deals / marketing_touches | hubspot_id | determinista, FK no declarada | deals 96.5% (35 huérfanos), touches 100% |
| companies ⇢ accounts | accounts.hubspot_id (admite nulos) | determinista cuando tiene valor | 596/650 cuentas; 82 empresas no tienen cuenta |
| companies ⇢ customers | solo domain y/o company_name | difusa (fuzzy) | domain exacto 573/650; name exacto 636/650; ambos 561/650 |
| accounts → product_usage | account_id | determinista, FK no declarada | 100% |
| customers → tickets | vitally_id | determinista, FK no declarada | 100% |

Atributos secundarios compartidos que sirven como evidencia: CSM (companies.csm_owner ↔ customers.csm_email, las mismas 7 personas), signup_date ↔ accounts.created_at, y el nombre en los tres sistemas.
