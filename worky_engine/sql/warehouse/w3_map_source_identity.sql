-- map_source_identity (seccion 5 del diseno): identity_crosswalk
-- desdoblado, una fila por sistema vinculado, mas identity_overrides
-- para saber si ese vinculo viene de la cascada o de una decision
-- humana (D16). Cada empresa aporta siempre su fila de crm_hubspot y,
-- cuando el vinculo existe, una de product_db y una de vitally.
CREATE OR REPLACE VIEW map_source_identity AS
WITH unpivoted AS (
    SELECT
        master_id, 'crm_hubspot' AS source_system, hubspot_id AS source_id,
        confidence_tier, 'cascade' AS link_source, resolved_at AS matched_at
    FROM identity_crosswalk

    UNION ALL

    SELECT
        master_id, 'product_db' AS source_system, account_id AS source_id,
        confidence_tier,
        CASE WHEN account_match_tier = 'O' THEN 'override' ELSE 'cascade' END AS link_source,
        resolved_at AS matched_at
    FROM identity_crosswalk
    WHERE account_id IS NOT NULL

    UNION ALL

    SELECT
        master_id, 'vitally' AS source_system, vitally_id AS source_id,
        confidence_tier,
        CASE WHEN vitally_match_tier = 'O' THEN 'override' ELSE 'cascade' END AS link_source,
        resolved_at AS matched_at
    FROM identity_crosswalk
    WHERE vitally_id IS NOT NULL
)
SELECT
    u.source_system,
    u.source_id,
    u.master_id,
    u.confidence_tier,
    u.link_source,
    o.decided_by,
    CASE WHEN u.link_source = 'override' THEN o.decided_at ELSE u.matched_at END AS matched_at
FROM unpivoted u
LEFT JOIN identity_overrides o
    ON o.source_system = u.source_system AND o.source_id = u.source_id
ORDER BY u.source_system, u.source_id;
