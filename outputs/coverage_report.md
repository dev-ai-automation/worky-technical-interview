# Reporte de cobertura del dataset maestro

## 1. Encabezado

| Campo | Valor |
|---|---|
| dataset_asof | 2024-08-31 |
| ruleset_version | 1.0.0 |
| identity_crosswalk | 650 |
| match_audit | 1978 |
| quarantine_companies | 28 |
| quarantine_deals | 35 |
| exceptions_log | 28 |
| master_dataset | 650 |

## 2. Cobertura por sistema

| Sistema | Filas totales | Filas resueltas | Cobertura |
|---|---|---|---|
| crm_hubspot | 678 | 650 | 95.87% |
| product_db | 650 | 650 | 100.00% |
| vitally | 650 | 650 | 100.00% |

## 3. Cobertura por nivel de confianza

| Nivel | Filas | Porcentaje |
|---|---|---|
| M | 0 | 0.00% |
| T0 | 596 | 45.85% |
| T1 | 650 | 50.00% |
| T2 | 54 | 4.15% |
| T3 | 0 | 0.00% |

## 4. Cola de revision manual

0 registros en el nivel M, la respuesta directa a A0.3.

## 5. MRR

| Metrica | Valor |
|---|---|
| MRR reportado del CRM (mensual, MXN) | 15448762.50 |
| MRR total incluyendo imputados (mensual, MXN) | 17899442.50 |
| Proporcion imputada | 13.69% |

| mrr_confidence (filas imputadas) | Filas |
|---|---|
| high | 4 |
| medium | 24 |

## 6. Cuarentena

| Concepto | Valor |
|---|---|
| Empresas clon (quarantine_companies) | 28 |
| Deals huerfanos (quarantine_deals) | 35 |
| Monto excluido, unidades mezcladas (MXN/USD, mensual/anual) | 667251.00 |
| Monto excluido, normalizado a mensual con la regla 12x | 667251.00 |

## 7. Tendencia de uso

| trend_status | Filas |
|---|---|
| computed | 585 |
| insufficient_history | 61 |
| no_usage | 4 |

Mediana de trend_usage por churn_status, solo filas 'computed':

| churn_status | Mediana trend_usage |
|---|---|
| active | 0.000433 |
| churned | -0.192664 |

## 8. Excepciones

| exception_code | Filas |
|---|---|
| mrr_imputed_from_deal | 28 |

## 9. Canal de adquisicion

| acquisition_channel | Filas | Porcentaje |
|---|---|---|
| Evento | 108 | 16.62% |
| Organic | 92 | 14.15% |
| Outbound SDR | 90 | 13.85% |
| Paid Search | 86 | 13.23% |
| Partner | 85 | 13.08% |
| Referral | 100 | 15.38% |
| Webinar | 89 | 13.69% |

Revenue cerrado total, mensual normalizado y en MXN (closed_revenue_mxn): 11046172.00
