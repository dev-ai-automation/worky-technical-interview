# Reporte de backtest de tendencia de uso (ADR-003)

Reproduce, con las tres bases de datos reales, la comparacion de las seis formulas de tendencia sobre las empresas con baja que tienen uso y las empresas activas. En k = 0 (el propio mes de baja) el AUC queda cercano a 1.0 para casi todas las formulas: eso es evidencia de fuga de datos, no de una formula buena, tal como advierte el ADR-003.

## k = 0

| Formula | Definida | AUC | Precision | Recall |
|---|---|---|---|---|
| Primeros 3 meses contra ultimos 3 meses | 85% | 1.000 | 0.505 | 0.654 |
| Ultimos 3 meses contra los 3 meses anteriores | 85% | 1.000 | 0.505 | 0.654 |
| Pendiente normalizada a 6 meses | 96% | 1.000 | 0.623 | 0.910 |
| Caida desde el mejor promedio de 3 meses | 100% | 0.930 | 0.597 | 0.910 |
| Momentum, EWMA span 3 contra span 9 (elegida) | 100% | 1.000 | 0.647 | 0.987 |
| Mes contra mes anterior | 98% | 0.578 | 0.128 | 0.192 |

## k = 2

| Formula | Definida | AUC | Precision | Recall |
|---|---|---|---|---|
| Primeros 3 meses contra ultimos 3 meses | 76% | 0.980 | 0.413 | 0.487 |
| Ultimos 3 meses contra los 3 meses anteriores | 76% | 0.962 | 0.407 | 0.474 |
| Pendiente normalizada a 6 meses | 85% | 0.996 | 0.505 | 0.654 |
| Caida desde el mejor promedio de 3 meses | 90% | 0.845 | 0.454 | 0.628 |
| Momentum, EWMA span 3 contra span 9 (elegida) | 90% | 1.000 | 0.556 | 0.769 |
| Mes contra mes anterior | 96% | 0.978 | 0.588 | 0.859 |

## k = 3

| Formula | Definida | AUC | Precision | Recall |
|---|---|---|---|---|
| Primeros 3 meses contra ultimos 3 meses | 73% | 0.814 | 0.195 | 0.218 |
| Ultimos 3 meses contra los 3 meses anteriores | 73% | 0.764 | 0.207 | 0.231 |
| Pendiente normalizada a 6 meses | 80% | 0.829 | 0.281 | 0.346 |
| Caida desde el mejor promedio de 3 meses | 85% | 0.620 | 0.149 | 0.192 |
| Momentum, EWMA span 3 contra span 9 (elegida) | 85% | 0.894 | 0.396 | 0.513 |
| Mes contra mes anterior | 90% | 0.903 | 0.431 | 0.603 |
