-- Motor: DuckDB 1.5.5. A1.6, tickets con resolution_hours negativo
-- (ADR-004). No se corrige el signo ni se excluyen los tickets:
-- cualquier promedio de tiempo de resolucion en el analisis los trata
-- como nulo, pero se conservan en conteos y CSAT. resolution_hours_abs
-- deja comparar contra el rango de los tickets positivos sin rehacer
-- la cuenta, y status es la evidencia de por que el signo no se voltea
-- sin confirmar (hay tickets abiertos con horas ya registradas).
CREATE OR REPLACE VIEW analysis_a1_06_negative_hours AS
SELECT
    t.ticket_id, t.vitally_id, x.master_id,
    strftime(t.created_date, '%Y-%m-%d')    AS created_date,
    t.priority, t.status, t.category,
    printf('%.2f', t.resolution_hours)      AS resolution_hours,
    printf('%.2f', abs(t.resolution_hours)) AS resolution_hours_abs,
    printf('%.2f', t.csat_score)            AS csat_score
FROM stg_tickets t
LEFT JOIN identity_crosswalk x ON x.vitally_id = t.vitally_id
WHERE t.resolution_hours < 0
ORDER BY t.ticket_id;

-- Vista de excepciones: mismas once columnas de exceptions_log (A0), en
-- el mismo orden, para que A6 pueda fusionar los dos logs cuando
-- corrija el signo en origen. exception_id es
-- sha256(exception_code|source_system|source_id|field_name) truncado a
-- 12 caracteres hex, la misma formula y el mismo orden de campos que
-- mart_mrr.sql. applied_value queda en el literal 'null' porque lo
-- aplicado fue dejar el campo en nulo para promedios, y la columna no
-- puede quedar vacia (regla del contrato de A0).
CREATE OR REPLACE VIEW analysis_exceptions AS
SELECT
    substr(
        sha256('negative_resolution_hours|vitally|' || t.ticket_id || '|resolution_hours'), 1, 12
    )                                                  AS exception_id,
    'negative_resolution_hours'                        AS exception_code,
    'vitally'                                          AS source_system,
    t.ticket_id                                        AS source_id,
    x.master_id                                        AS master_id,
    'resolution_hours'                                  AS field_name,
    printf('%.2f', t.resolution_hours)                  AS original_value,
    'null'                                              AS applied_value,
    t.status                                            AS evidence_ref,
    '1.0.0'                                             AS ruleset_version,
    (SELECT MAX(resolved_at) FROM identity_crosswalk)   AS decided_at
FROM stg_tickets t
LEFT JOIN identity_crosswalk x ON x.vitally_id = t.vitally_id
WHERE t.resolution_hours < 0
ORDER BY exception_code, source_id;
