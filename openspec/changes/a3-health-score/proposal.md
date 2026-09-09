# Propuesta: health score de A3 con validación medida contra el churn real

## Intención

El caso pide un health score con fórmula, variables y pesos, calculado dos o tres meses antes de la fecha de referencia de cada cuenta, y validado con precisión y recall contra `churn_date`. El ADR-005 ya fijó el modelo completo: cuatro subpuntajes, pesos 0.35 / 0.20 / 0.15 / 0.30, banda "sin historia", umbral por capacidad de los 7 CSM y el error más caro. Falta el código: hoy nadie puede correr ese score ni ver sus métricas junto a la regla que las produjo. El repositorio tiene los tres subpuntajes de uso medidos en el harness, pero no tiene score combinado, ni umbral, ni matriz de confusión, ni recall ponderado por MRR.

Éxito, en una frase: alguien clona el repositorio, corre un comando y obtiene el score de las 650 empresas y su validación, iguales byte a byte en cada corrida, sin haber corrido `build` antes.

## Alcance

### Dentro

- Comando `health`, simétrico a `analyze`: `python -m worky_engine health --data-dir <dir> --out-dir outputs/health`. Abre su propia conexión de DuckDB, resuelve identidad y ensambla el dataset maestro en memoria, y nunca lee `outputs/`.
- Vista nueva de soporte ventanada al mes de corte (`mart_support_asof`), que cierra la fuga de diseño de `mart_support` sin tocarla.
- Los cuatro subpuntajes del ADR-005 en el mes de corte (referencia menos 2 meses para bajas y activas por igual), normalizados a 0 a 100 por rango percentil dentro de la población evaluada, con 100 como lo más sano, y el score como suma ponderada.
- `outputs/health/health_scores.csv`, una fila por empresa: `master_id`, `hubspot_id`, `reference_month`, `asof_month`, `usage_months_asof`, los cuatro subpuntajes, las señales medidas con peso cero (`tickets_window_total`, `tickets_window_urgent`, `csat_window_avg`, `activation_score`), `health_score`, `risk_band` (incluye "sin historia"), `flagged_10` / `flagged_15` / `flagged_20`, `churned`, `mrr_mxn`, `acquisition_channel`, `segment`.
- `outputs/health/validation.md`: AUC por señal, la fórmula y sus pesos, precisión, recall, recall ponderado por MRR y AUC al 10, 15 y 20 % de marcado más un corte fijo de referencia, matriz de confusión al 15 %, cuenta de no detectables, detección temprana en k = 3, sensibilidad a k = 3 y a la lectura literal del caso, capacidad por CSM y la respuesta de A3.4.
- Goldens versionados bajo `outputs/health/`, con las mismas pruebas de idempotencia que ya protegen a `build` y a `analyze`.
- Pruebas por regla sobre fixture mínimo y pruebas marcadas `dataset` que fijan los números reales.

### Fuera

- Modificar `mart_support.sql`, `mart_usage.sql`, `master_dataset.csv` o cualquier golden de A0 y A1.
- Aprender los pesos con regresión logística o reglas por niveles: el ADR-005 las rechazó.
- Meter canal y segmento dentro del score. Se reportan como factores de riesgo aparte.
- Tiempo de resolución como señal, hasta que A6 corrija el signo de los 48 tickets negativos (ADR-004).
- El tablero de A5 y el playbook de la Parte B, que consumen este CSV pero no viven aquí.

## Capacidades

### Nuevas

- `health-score`: el modelo del ADR-005 como requisitos verificables (mes de corte, subpuntajes, normalización, suma ponderada, banda "sin historia", umbrales por capacidad), el comando `health`, sus dos salidas y las métricas de validación, incluidos el recall ponderado por MRR y la detección temprana.

### Modificadas

- Ninguna. El recall ponderado por MRR y la detección temprana viven en `health-score`, no en un delta de `trend-backtest-harness`. Los cuatro requisitos de ese spec describen la comparación de las seis fórmulas de tendencia del ADR-003 y su golden `backtest_report.md` los fija; las métricas de A3 se calculan sobre el score combinado, que no es ninguna de esas seis fórmulas. Cambiar el spec del harness obligaría a regenerar un golden que este cambio no necesita tocar. El código sí reusa el harness (`_auc` y la convención de marcado), y una prueba verifica que `backtest_report.md` no cambia.

## Enfoque

Espejear el patrón `analyze`, que ya resolvió el mismo problema para A1.

| Pieza | Qué hace |
|---|---|
| `worky_engine/sql/marts/mart_support_asof.sql` | Tickets y CSAT en la ventana de 3 meses que termina en el mes de corte, por `master_id`; `mart_support.sql` queda intacta |
| `worky_engine/sql/health/` | Subpuntajes de uso desde `stg_product_usage` con el mismo resguardo de fuga de `mart_usage`, antigüedad desde `signup_date`, y activación de los primeros 3 meses |
| `worky_engine/health/scoring.py` | Rango percentil por subpuntaje dentro de la población evaluada, suma ponderada 0.35 / 0.20 / 0.15 / 0.30, bandas y las tres tasas de marcado |
| `worky_engine/health/metrics.py` | AUC, precisión, recall, recall ponderado por MRR, matriz de confusión, detección temprana y las dos sensibilidades |
| `worky_engine/health/report.py` | Arma `validation.md` desde los DataFrames ya materializados, sin volver a abrir la conexión, igual que `analysis/report.py` |
| `worky_engine/cli.py` | `cmd_health` con importación diferida y el mismo mensaje en español cuando falta una dependencia |

Reglas vinculantes del ADR-005 que el código implementa sin margen: el mismo desplazamiento de 2 meses para bajas y activas; ninguna fila de uso ni ticket posterior al mes de corte entra a ningún subpuntaje; menos de tres meses de uso al corte manda la cuenta a la banda "sin historia", sin subpuntajes de uso y contada en el denominador del recall; soporte, activación, canal y segmento se calculan, se muestran y pesan cero.

Aceptación del harness: si el score con los pesos por juicio da AUC de al menos 0.95 y recall de al menos 0.85 al 20 % de marcado sobre el dataset del caso, los pesos quedan. Si no, se adopta la mezcla ya medida (uso 70, antigüedad 15, activación 15) y se registra una adenda al ADR-005 en el mismo PR que lo detecte.

## Áreas afectadas

| Área | Impacto | Descripción |
|---|---|---|
| `worky_engine/sql/marts/mart_support_asof.sql` | Nueva | Vista de soporte ventanada al mes de corte |
| `worky_engine/sql/health/` | Nueva | SQL de subpuntajes, antigüedad y activación |
| `worky_engine/health/` | Nuevo | Corredor, scoring, métricas y armado de `validation.md` |
| `worky_engine/cli.py` | Modificado | Subcomando `health` y su parser |
| `outputs/health/` | Nueva | `health_scores.csv` y `validation.md` |
| `tests/` | Modificado | Pruebas por regla, pruebas `dataset` e idempotencia |
| `worky_engine/harness/backtest.py` | Sin cambio de comportamiento | Se reusa el cálculo de AUC; su golden se verifica idéntico |
| `outputs/` (goldens de A0 y A1) | Sin cambio | Se verifica que siguen idénticos |

## Plan de PR (presupuesto de 800 líneas de autoría por PR)

Encadenados sobre `main`, cada uno con su verificación y su reversión.

| PR | Contenido | Líneas de autoría estimadas | Qué revisa primero el revisor |
|---|---|---|---|
| 1 | `mart_support_asof.sql`, SQL de subpuntajes, `scoring.py` con normalización percentil, suma ponderada y bandas, y pruebas de regla sobre fixture mínimo | 600 | Que ningún mes de uso ni ticket posterior al corte entre a un subpuntaje, y que una cuenta con menos de tres meses caiga en "sin historia" sin subpuntajes de uso |
| 2 | `metrics.py` (precisión, recall, recall por MRR, AUC, confusión, detección temprana, sensibilidades a k = 3 y a la lectura literal), comando `health`, `health_scores.csv` y pruebas `dataset` | 560 (más ~650 filas de golden, fuera del conteo de autoría) | Que las 10 bajas sin historia estén en el denominador del recall y que `health` corra sin `build` previo |
| 3 | `report.py` y `validation.md`, la respuesta narrativa de A3.4, línea del README y cierre de documentación | 470 | Que cada cifra diga "en este dataset", que el soporte aparezca con su AUC y peso cero, y que ningún golden de A0 ni A1 haya cambiado |

Las pruebas se reparten con su PR: reglas mínimas en el 1 (exclusión por mes de corte, normalización percentil, banda sin historia, suma ponderada, tasas de marcado y cuentas por CSM, recall ponderado por MRR), números reales en el 2 (89 bajas con 10 no detectables, umbrales de AUC y recall, 81 marcadas al 15 %), idempotencia de dos corridas y goldens de A0 y A1 sin cambio en los dos.

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Los pesos por juicio no alcanzan AUC 0.95 y recall 0.85 al 20 % | Media | El PR 2 corre la verificación; si falla, se adopta la mezcla medida y se escribe la adenda al ADR-005 antes de cerrar el PR |
| Reusar código del harness cambia `backtest_report.md` | Baja | Solo se importa el cálculo de AUC, y una prueba compara el golden antes y después |
| El AUC cercano a 1 se lee como calidad del modelo | Media | `validation.md` marca cada cifra como "en este dataset" y publica la sensibilidad en k = 3, donde las señales se debilitan |
| El 11 % de bajas sin historia se lee como falla del score | Media | Se reportan en su propia banda, contadas aparte del conteo de falsos negativos |
| La normalización percentil cambia el score de todos cuando entra una cuenta nueva | Media | La población evaluada y su tamaño quedan escritos en `validation.md`; A5 consume el CSV de una corrida, no compara corridas distintas |
| El PR 2 se acerca al presupuesto por el golden de 650 filas | Media | El golden es generado y queda fuera del conteo de autoría; si las métricas crecen, las sensibilidades se mueven al PR 3 |

## Plan de reversión

Cada PR se revierte solo con `git revert` de su merge. El cambio agrega archivos nuevos y una rama del parser de argumentos, así que revertir los tres deja los goldens de A0 y A1 intactos y `pytest -m dataset` en verde sin ningún paso manual. `outputs/health/` se borra completo con la reversión.

## Dependencias

- DuckDB 1.5.5, pandas y numpy, ya fijados en `pyproject.toml`. No se agrega ninguna dependencia.
- Las tres bases SQLite del caso, leídas con `load_raw_tables` en modo solo lectura.
- ADR-003 (mes de corte y subpuntajes de uso), ADR-004 (señales de soporte por conteos y CSAT) y ADR-005 (modelo completo).

## Criterios de éxito

- [ ] `python -m worky_engine health --data-dir ... --out-dir outputs/health` corre sin `build` previo y termina en 0.
- [ ] Dos corridas seguidas producen archivos idénticos byte a byte bajo `outputs/health/`.
- [ ] Los goldens de A0 y A1, incluido `backtest_report.md`, quedan sin cambio, verificado por prueba.
- [ ] `health_scores.csv` trae una fila por empresa con los cuatro subpuntajes, las señales de peso cero, el score, la banda y las tres marcas.
- [ ] `validation.md` reporta precisión, recall, recall ponderado por MRR y AUC al 10, 15 y 20 %, la matriz de confusión al 15 %, la detección temprana en k = 3 y las dos sensibilidades.
- [ ] Los números del ADR-005 quedan fijados por pruebas `dataset`: 89 bajas, 10 no detectables en k = 2, 81 marcadas al 15 % y unas 12 por CSM.
- [ ] El score con los pesos del ADR-005 alcanza AUC de al menos 0.95 y recall de al menos 0.85 al 20 %, o queda la adenda con la mezcla medida.
- [ ] La lista de verificación del ADR-005 pasa completa.
- [ ] Ningún PR de la cadena supera 800 líneas de autoría.
