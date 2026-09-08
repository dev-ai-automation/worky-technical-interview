# Especificación: CLI de construcción (`build-cli`)

## Propósito

Ofrece un único comando reproducible que genera todas las salidas de `outputs/` a partir de las tres bases SQLite de origen, para que cualquier persona pueda regenerar el dataset maestro sin conocer los módulos internos del motor.

## ADDED Requirements

### Requirement: comando único de construcción

El comando `python -m worky_engine build` MUST leer las tres bases SQLite de origen en modo solo lectura y MUST generar todas las salidas esperadas en `outputs/`.

#### Scenario: corrida completa

- Dado las tres bases SQLite de origen disponibles
- Cuando alguien corre `python -m worky_engine build`
- Entonces `outputs/` contiene `master_dataset.csv`, `match_audit.csv`, `identity_crosswalk.csv`, los CSV de cuarentena, `exceptions_log.csv` y `coverage_report.md`

### Requirement: idempotencia byte a byte

Dos corridas consecutivas de `python -m worky_engine build` sobre la misma entrada MUST producir salidas idénticas byte por byte.

#### Scenario: dos corridas seguidas

- Dado la misma entrada sin cambios
- Cuando alguien corre el comando dos veces seguidas
- Entonces los archivos de la segunda corrida son idénticos byte por byte a los de la primera

### Requirement: mensajes de error claros

Cuando falta una de las tres bases SQLite o una dependencia requerida, el comando MUST detenerse con un mensaje de error en español que nombre qué falta.

#### Scenario: falta una base de datos

- Dado que una de las tres bases SQLite no está presente en la carpeta de datos
- Cuando alguien corre el comando
- Entonces el comando termina con un mensaje en español que nombra la base faltante, sin generar salidas parciales

#### Scenario: falta una dependencia

- Dado que una dependencia requerida (por ejemplo rapidfuzz o duckdb) no está instalada
- Cuando alguien corre el comando
- Entonces el comando termina con un mensaje en español que nombra la dependencia faltante

### Requirement: carpeta de datos configurable

El comando MAY recibir una opción para indicar la carpeta donde están las tres bases SQLite, distinta de la ubicación por defecto.

#### Scenario: carpeta de datos indicada

- Dado una carpeta de datos distinta de la ubicación por defecto
- Cuando alguien corre el comando con la opción de carpeta de datos
- Entonces el comando lee las tres bases desde esa carpeta
