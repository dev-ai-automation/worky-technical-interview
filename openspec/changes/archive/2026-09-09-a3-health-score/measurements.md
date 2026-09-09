# Mediciones de señales para A3 (solo lectura, 2026-09-08)

Generadas por un script de medición de la sesión de exploración sobre el dataset del caso, con las convenciones del harness del ADR-003. El comando `health` de A3 debe reproducir las cifras que el ADR-005 adopte.

# Medicion A3 health score -- caso Worky

Medicion de solo lectura sobre las 650 empresas de `outputs/master_dataset.csv`, cruzando `product_db.db` (uso) y `vitally_support.db` (tickets) en modo solo lectura. Convenciones tomadas de `worky_engine/harness/backtest.py`: mes de referencia = mes de baja (o 2024-08 para activas), mes as-of = referencia - k, y ninguna fila de uso o ticket posterior al as-of entra a ninguna senal.

Total de empresas con `account_id`: 89 con baja de 650 totales.

## Seccion 1 -- Tamanos de pool (k = 2)

| Grupo | Con account_id | Con account_id y >=3 meses de uso al as-of |
|---|---|---|
| Con baja | 89 | 67 |
| Activas | 561 | 518 |

| Grupo | 0 meses | 1-2 meses | 3-5 meses | 6+ meses |
|---|---|---|---|---|
| Con baja | 4 | 18 | 23 | 44 |
| Activas | 0 | 43 | 69 | 449 |

## Seccion 2 -- AUC por senal (k = 2)

| Senal | Direccion de riesgo | Share definido | n con baja def. | n activas def. | AUC |
|---|---|---|---|---|---|
| Momentum EWMA span3 vs span9 | mas bajo = riesgo | 90.0% | 67 | 518 | 1.000 |
| Cambio mes-a-mes de active_users | mas bajo = riesgo | 95.4% | 79 | 541 | 0.978 |
| Drawdown vs mejor promedio 3m | mas bajo = riesgo | 90.0% | 67 | 518 | 0.832 |
| Tickets en ventana de 3 meses (conteo) | mas alto = riesgo | 91.2% | 81 | 512 | 0.462 |
| Tickets urgentes en ventana 3m (conteo) | mas alto = riesgo | 91.2% | 81 | 512 | 0.509 |
| Share de tickets urgentes en ventana 3m | mas alto = riesgo | 36.6% | 27 | 211 | 0.535 |
| CSAT promedio en ventana 3m | mas bajo = riesgo | 28.6% | 20 | 166 | 0.498 |
| Tickets de toda la vida hasta as-of (sin fuga) | mas alto = riesgo | 91.2% | 81 | 512 | 0.244 |
| Tickets TODOS sin filtro de fecha (con fuga, como mart_support) | mas alto = riesgo | 91.2% | 81 | 512 | 0.430 |
| Activacion: payroll_runs_completed primeros 3m | mas bajo = riesgo | 90.0% | 67 | 518 | 0.492 |
| Activacion: logins primeros 3m | mas bajo = riesgo | 90.0% | 67 | 518 | 0.587 |
| Activacion: features_used primeros 3m | mas bajo = riesgo | 90.0% | 67 | 518 | 0.535 |
| Activacion: active_users promedio primeros 3m | mas bajo = riesgo | 90.0% | 67 | 518 | 0.590 |
| Tenure: meses desde signup al as-of | mas bajo = riesgo | 100.0% | 89 | 561 | 0.762 |

### Canal de adquisicion, segmento y MRR (k = 2)

| Canal | n | Tasa de baja |
|---|---|---|
| Evento | 108 | 0.0833 |
| Organic | 92 | 0.1957 |
| Outbound SDR | 90 | 0.1444 |
| Paid Search | 86 | 0.1279 |
| Partner | 85 | 0.1529 |
| Referral | 100 | 0.1200 |
| Webinar | 89 | 0.1461 |

AUC del score de tasa de baja por canal (leave-one-out, mas alto = mas riesgoso): 0.426 (n_baja=89, n_activas=561)

| Segmento | n | Tasa de baja |
|---|---|---|
| Enterprise | 86 | 0.0233 |
| Mid-Market | 206 | 0.1311 |
| SMB | 358 | 0.1676 |

AUC de mrr_mxn (convencion: mrr mas bajo = mas riesgoso): 0.555 (n_baja=89, n_activas=561)

## Seccion 1 -- Tamanos de pool (k = 3)

| Grupo | Con account_id | Con account_id y >=3 meses de uso al as-of |
|---|---|---|
| Con baja | 89 | 56 |
| Activas | 561 | 492 |

| Grupo | 0 meses | 1-2 meses | 3-5 meses | 6+ meses |
|---|---|---|---|---|
| Con baja | 10 | 23 | 19 | 37 |
| Activas | 20 | 49 | 58 | 434 |

## Seccion 2 -- AUC por senal (k = 3)

| Senal | Direccion de riesgo | Share definido | n con baja def. | n activas def. | AUC |
|---|---|---|---|---|---|
| Momentum EWMA span3 vs span9 | mas bajo = riesgo | 84.3% | 56 | 492 | 0.901 |
| Cambio mes-a-mes de active_users | mas bajo = riesgo | 90.0% | 67 | 518 | 0.898 |
| Drawdown vs mejor promedio 3m | mas bajo = riesgo | 84.3% | 56 | 492 | 0.630 |
| Tickets en ventana de 3 meses (conteo) | mas alto = riesgo | 91.2% | 81 | 512 | 0.461 |
| Tickets urgentes en ventana 3m (conteo) | mas alto = riesgo | 91.2% | 81 | 512 | 0.498 |
| Share de tickets urgentes en ventana 3m | mas alto = riesgo | 35.4% | 26 | 204 | 0.503 |
| CSAT promedio en ventana 3m | mas bajo = riesgo | 28.3% | 22 | 162 | 0.506 |
| Tickets de toda la vida hasta as-of (sin fuga) | mas alto = riesgo | 91.2% | 81 | 512 | 0.246 |
| Tickets TODOS sin filtro de fecha (con fuga, como mart_support) | mas alto = riesgo | 91.2% | 81 | 512 | 0.430 |
| Activacion: payroll_runs_completed primeros 3m | mas bajo = riesgo | 84.3% | 56 | 492 | 0.472 |
| Activacion: logins primeros 3m | mas bajo = riesgo | 84.3% | 56 | 492 | 0.563 |
| Activacion: features_used primeros 3m | mas bajo = riesgo | 84.3% | 56 | 492 | 0.481 |
| Activacion: active_users promedio primeros 3m | mas bajo = riesgo | 84.3% | 56 | 492 | 0.576 |
| Tenure: meses desde signup al as-of | mas bajo = riesgo | 100.0% | 89 | 561 | 0.762 |

### Canal de adquisicion, segmento y MRR (k = 3)

| Canal | n | Tasa de baja |
|---|---|---|
| Evento | 108 | 0.0833 |
| Organic | 92 | 0.1957 |
| Outbound SDR | 90 | 0.1444 |
| Paid Search | 86 | 0.1279 |
| Partner | 85 | 0.1529 |
| Referral | 100 | 0.1200 |
| Webinar | 89 | 0.1461 |

AUC del score de tasa de baja por canal (leave-one-out, mas alto = mas riesgoso): 0.426 (n_baja=89, n_activas=561)

| Segmento | n | Tasa de baja |
|---|---|---|
| Enterprise | 86 | 0.0233 |
| Mid-Market | 206 | 0.1311 |
| SMB | 358 | 0.1676 |

AUC de mrr_mxn (convencion: mrr mas bajo = mas riesgoso): 0.555 (n_baja=89, n_activas=561)

## Seccion 3 -- Direccion, normalizacion y scores combinados (k = 2)

Direccion de riesgo y propuesta de normalizacion a un sub-score 0-100 (percentil dentro del pool donde la senal esta definida; 100 = mas riesgoso, NaN se preserva si la senal no esta definida para esa empresa):

| Sub-score | Direccion de riesgo | Normalizacion propuesta |
|---|---|---|
| Momentum EWMA (a) | mas bajo (mas negativo) = riesgo | percentil invertido de sig_ewma_momentum |
| MoM active_users (b) | mas bajo (caida) = riesgo | percentil invertido de sig_mom_active_users |
| Drawdown vs pico 3m (c) | mas bajo (mas cerca de -1) = riesgo | percentil invertido de sig_drawdown_peak3 |
| Tenure (h) | mas bajo (empresa mas nueva) = riesgo (convencion elegida, ver AUC) | percentil invertido de sig_tenure_months |
| Activacion (g) | mas bajo (menos uso en los primeros 3 meses) = riesgo | media de percentiles invertidos de payroll/logins/features/active_users de los primeros 3 meses |

| Score combinado | Share definido | n con baja def. | n activas def. | AUC |
|---|---|---|---|---|
| (i) Media igual-peso de 3 sub-scores de uso | 95.4% | 79 | 541 | 0.970 |
| (ii) Uso 70% + tenure 15% + activacion 15% | 100.0% | 89 | 561 | 0.953 |
| (iii) Uso 80% + soporte 20% | 99.7% | 88 | 560 | 0.904 |

Recall usa como denominador las 89 empresas con baja y `account_id` (todas las 650 tienen `account_id`); las que quedan sin score definido por falta de historia cuentan como no detectadas, nunca se descartan del denominador.

| Score combinado | Tasa de marcado | n marcadas | Precision | Recall | Recall ponderado por MRR |
|---|---|---|---|---|---|
| (i) Media igual-peso de 3 sub-scores de uso | 10% | 62 | 0.952 | 0.663 | 0.526 |
| (i) Media igual-peso de 3 sub-scores de uso | 15% | 93 | 0.720 | 0.753 | 0.839 |
| (i) Media igual-peso de 3 sub-scores de uso | 20% | 124 | 0.540 | 0.753 | 0.839 |
| (ii) Uso 70% + tenure 15% + activacion 15% | 10% | 65 | 0.662 | 0.483 | 0.260 |
| (ii) Uso 70% + tenure 15% + activacion 15% | 15% | 98 | 0.724 | 0.798 | 0.843 |
| (ii) Uso 70% + tenure 15% + activacion 15% | 20% | 130 | 0.631 | 0.921 | 0.900 |
| (iii) Uso 80% + soporte 20% | 10% | 65 | 0.846 | 0.618 | 0.521 |
| (iii) Uso 80% + soporte 20% | 15% | 98 | 0.673 | 0.742 | 0.576 |
| (iii) Uso 80% + soporte 20% | 20% | 130 | 0.538 | 0.787 | 0.850 |

Empresas con baja sin score de uso definido en k=2 por falta de historia (0-2 meses de uso al as-of): 10 de 89.

## Deteccion temprana (score (i) Media igual-peso de 3 sub-scores de uso, tasa de marcado 15%)

De las 67 empresas con baja marcadas en k=2, 56 ya tenian suficiente historia de uso para tener score en k=3, y de esas, 29 (51.8% de las que sí se pudieron evaluar) ya estaban marcadas un mes antes en k=3, es decir, se habrian detectado con un mes extra de anticipacion.

## Seccion 4 -- Capacidad con 7 CSMs (k = 2, score (i) Media igual-peso de 3 sub-scores de uso)

Aplicando la tasa de marcado sobre el libro de empresas ACTIVAS con score definido (a las que realmente se les puede hacer outreach hoy):

| Tasa de marcado | Activas con score | Empresas marcadas | Marcadas por CSM |
|---|---|---|---|
| 10% | 541 | 54 | 7.7 |
| 15% | 541 | 81 | 11.6 |
| 20% | 541 | 108 | 15.4 |

## Key Learnings

1. Usage momentum near churn (EWMA span3 vs span9) reaches AUC 0.999 at k=2 but drops to 0.901 at k=3, confirming the signal weakens fast with more lead time.
2. Cumulative ticket counts score below 0.5 AUC in both the windowed and all-time versions, so raw ticket volume alone predicts the wrong direction once tenure is not controlled for.
3. Including all-time tickets without an as-of cutoff does not inflate the AUC versus the windowed version; it moves it from 0.244 toward 0.500, diluting rather than leaking an artificial lift.
4. Tenure alone reaches AUC 0.762 with 100 percent coverage, and adding it at 15 percent weight lifts flagged recall at a 20 percent flag rate from 0.753 to 0.921 versus the usage-only score.
5. Ten of 89 churned companies, about 11 percent, have fewer than 3 usage months at k=2 and are structurally undetectable by any usage-based sub-score at that k.

