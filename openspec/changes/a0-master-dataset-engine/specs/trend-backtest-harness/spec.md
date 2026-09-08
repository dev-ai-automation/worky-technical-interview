# Especificación: harness de backtest de tendencia (`trend-backtest-harness`)

## Propósito

Reproduce, dentro del repositorio, la comparación de fórmulas de tendencia de uso del ADR-003, para que cualquier cambio futuro a una fórmula o a un parámetro se pueda volver a medir contra el mismo backtest.

## ADDED Requirements

### Requirement: reproducción de la comparación de fórmulas

El harness MUST evaluar las seis fórmulas del ADR-003 en k = 0, k = 2 y k = 3 (meses de retroceso desde el mes de referencia), sobre las 78 empresas con baja que tienen uso y las 515 empresas activas.

#### Scenario: corrida completa del backtest

- Dado el conjunto de 78 empresas con baja con uso y 515 empresas activas
- Cuando el harness corre las seis fórmulas en k = 0, 2 y 3
- Entonces el harness produce un resultado para cada combinación de fórmula y k

### Requirement: métricas reportadas por fórmula

El harness MUST reportar, para cada fórmula y cada k, la proporción de empresas para las que la fórmula se puede calcular, el AUC (la probabilidad de que una empresa con baja muestre una tendencia peor que una activa), la precisión y el recall a la tasa de marcado configurable, con 20% como valor por defecto.

#### Scenario: métricas de una fórmula

- Dado el resultado de una fórmula en k = 2
- Cuando el harness reporta sus métricas
- Entonces el reporte incluye la proporción definida, el AUC, la precisión y el recall a la tasa de marcado configurada

### Requirement: regresión del momentum ganador en k = 2

El harness MUST verificar que la fórmula de momentum (EWMA span 3 contra span 9) sigue teniendo el mejor AUC entre las seis fórmulas en k = 2.

#### Scenario: prueba de regresión

- Dado el resultado de las seis fórmulas en k = 2
- Cuando el harness compara sus valores de AUC
- Entonces la fórmula de momentum tiene el AUC más alto

### Requirement: evidencia de fuga de datos en k = 0

El harness MUST reportar el AUC de cada fórmula en k = 0, para dejar visible que evaluar en el propio mes de baja produce una separación casi perfecta y por lo tanto no mide qué tan bien predice la fórmula.

#### Scenario: AUC cercano a 1.0 en k = 0

- Dado el resultado de las seis fórmulas en k = 0
- Cuando el harness reporta sus métricas
- Entonces el AUC reportado en k = 0 queda cercano a 1.0 para la mayoría de las fórmulas
