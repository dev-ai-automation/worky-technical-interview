# Delta for identity-resolution

## ADDED Requirements

### Requirement: precedencia de overrides sobre la cascada

Una fila de `identity_overrides` (`source_system`, `source_id`, `master_id`, `decided_by`, `decided_at`, `reason`) aplicada después de la cascada MUST fijar el `master_id` de ese registro de origen, MUST sacarlo de la cola de revisión manual (`needs_review = false`), y MUST dejar evidencia en `match_audit` que nombre el override. Una fila cuyo `master_id` no existe en `identity_crosswalk`, un `source_id` duplicado entre filas de override, o un `source_id` que no existe en su tabla de origen, MUST rechazarse; el comando MUST terminar con un código de salida distinto de cero y un mensaje de error que nombre la fila y el motivo, y MUST NOT escribir ninguna salida parcial. Sin archivo de overrides, `identity_crosswalk`, `match_audit`, `mart_coverage` y todos los goldens de A0 MUST permanecer idénticos byte a byte.

#### Scenario: override fija el master_id y sale de revisión manual

- Dado un registro en revisión manual (nivel M, `needs_review = true`) y una fila de `identity_overrides` que le asigna un `master_id` existente en el crosswalk
- Cuando el sistema aplica los overrides después de la cascada
- Entonces ese registro queda con el `master_id` del override, `needs_review = false`, y `match_audit` registra el override como evidencia de la decisión

#### Scenario: override con master_id inexistente se rechaza

- Dado una fila de `identity_overrides` cuyo `master_id` no existe en `identity_crosswalk`
- Cuando el sistema procesa los overrides
- Entonces el comando se detiene con un código de salida distinto de cero, el mensaje de error nombra la fila y el motivo, y no se escribe ningún archivo de salida

#### Scenario: source_id duplicado entre overrides se rechaza

- Dado dos filas de `identity_overrides` con el mismo `source_id`
- Cuando el sistema procesa los overrides
- Entonces el comando se detiene con un código de salida distinto de cero, el mensaje de error nombra la fila duplicada y el motivo, y no se escribe ningún archivo de salida

#### Scenario: override con source_id desconocido se rechaza

- Dado una fila de `identity_overrides` cuyo `source_id` no existe en la tabla de origen que indica `source_system`
- Cuando el sistema procesa los overrides
- Entonces el comando se detiene con un código de salida distinto de cero, el mensaje de error nombra la fila y el motivo, y no se escribe ningún archivo de salida

#### Scenario: sin archivo de overrides, la salida de A0 no cambia

- Dado una corrida sin ningún archivo de `identity_overrides`
- Cuando el sistema resuelve identidad y ensambla el dataset maestro
- Entonces `identity_crosswalk`, `match_audit`, `mart_coverage` y todos los goldens de A0 quedan idénticos byte a byte a los de antes de este cambio
