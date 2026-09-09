# Especificación: reporte de cobertura (`coverage-report`)

## Propósito

Reporta, a partir de `match_audit`, qué proporción de cada sistema de origen quedó reconciliada, en qué nivel de confianza, y cuántos registros están en revisión manual o en cuarentena. Responde a la pregunta A0.3 del caso.

## ADDED Requirements

### Requirement: cobertura por sistema

El sistema MUST reportar, para HubSpot, Product DB y Vitally, el porcentaje de sus registros que quedaron reconciliados a un `master_id`.

#### Scenario: tres porcentajes por sistema

- Dado `match_audit` con las filas de los tres sistemas
- Cuando el sistema genera el reporte de cobertura
- Entonces el reporte muestra un porcentaje de cobertura separado para HubSpot, Product DB y Vitally

### Requirement: cobertura por nivel de confianza

El sistema MUST reportar el porcentaje de registros en cada nivel de confianza: alta, media y manual.

#### Scenario: desglose por nivel

- Dado `match_audit` con registros en distintos niveles
- Cuando el sistema genera el reporte de cobertura
- Entonces el reporte muestra el porcentaje de registros en confianza alta, media y manual

### Requirement: tamaño de la cola de revisión manual

El sistema MUST reportar el número absoluto de registros marcados para revisión manual.

#### Scenario: conteo de la cola manual

- Dado los registros marcados en el nivel M
- Cuando el sistema genera el reporte de cobertura
- Entonces el reporte muestra cuántos registros están en la cola de revisión manual

### Requirement: conteos de cuarentena

El sistema MUST reportar el número de filas en `quarantine_companies` y en `quarantine_deals`.

#### Scenario: conteos de cuarentena en el reporte

- Dado las 28 filas clon y los 35 deals huérfanos en cuarentena
- Cuando el sistema genera el reporte de cobertura
- Entonces el reporte muestra ambos conteos

### Requirement: recalculo desde match_audit

El sistema MUST calcular todos los porcentajes del reporte a partir de `match_audit`, y MUST NOT escribir ningún porcentaje a mano.

#### Scenario: porcentaje recalculado

- Dado un cambio en el contenido de `match_audit` entre dos corridas
- Cuando el sistema genera el reporte de cobertura en cada corrida
- Entonces los porcentajes reportados cambian de acuerdo con el contenido nuevo de `match_audit`
