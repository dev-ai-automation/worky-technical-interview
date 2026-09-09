# Bitacora de limpieza

Corrida sobre `crm_hubspot__companies.csv` y `crm_hubspot__deals.csv`: 678 filas de entrada, 678 filas de salida. De los 997 deals leidos, 962 apuntan a una empresa del dataset.

| Regla | Columnas | Detectado | Corregido | No numerico | Ambiguo | Sin resolver |
|---|---|---|---|---|---|---|
| missing_mrr | mrr | 56 | 28 | 0 | 0 | 0 |
| currency_to_mxn | mrr, currency | 22 | 22 | 0 | 0 | 0 |
| date_format | signup_date, churn_date | 31 | 31 | 0 | 12 | 0 |

Clones excluidos de la imputacion (ADR-001): 28. Deals anualizados (ADR-002, adenda 1): 3. Deals con monto no numerico: 0.

Total de correcciones: 84. Filas en `cleaning_exceptions.csv`: 112.
