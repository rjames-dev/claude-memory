-- Timezone Handling Migration - FULL MIGRATION (Remaining 6 Views)
-- Date: 2025-12-28
-- Purpose: Complete timezone migration for all remaining views
--
-- NOTE: v_snapshot_quality already migrated in test phase
-- This script migrates the remaining 6 views

BEGIN;

-- ============================================================================
-- View 2/7: v_agent_evolution
-- ============================================================================

ALTER VIEW v_agent_evolution RENAME TO v_agent_evolution_backup_20251228;

CREATE VIEW v_agent_evolution AS
SELECT
    ad.id,
    ad.agent_type,
    ad.version,
    ad.parent_definition_id,
    ad.configuration_params,
    ad.created_at AS pst_created,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'
    count(aw.id) AS usage_count,
    avg(aw.duration_seconds)::numeric(10,1) AS avg_performance_seconds,
    max(aw.timestamp_end) AS last_used_pst  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'
FROM agent_definitions ad
LEFT JOIN agent_work aw ON aw.agent_definition_id = ad.id
GROUP BY ad.id
ORDER BY ad.agent_type, ad.version, ad.created_at;

COMMENT ON VIEW v_agent_evolution IS 'Agent configuration version history with usage statistics. UPDATED: Timezone-aware timestamps.';

-- ============================================================================
-- View 3/7: v_agent_work_full
-- ============================================================================

ALTER VIEW v_agent_work_full RENAME TO v_agent_work_full_backup_20251228;

CREATE VIEW v_agent_work_full AS
SELECT
    aw.id AS work_id,
    aw.agent_id,
    aw.agent_request,
    aw.duration_seconds,
    aw.timestamp_start AS pst_start,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'
    aw.timestamp_end AS pst_end,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'
    aw.tools_used,
    aw.files_examined,
    aw.urls_fetched,
    ad.agent_type,
    ad.version AS config_version,
    ad.configuration_params,
    ad.model_used,
    ad.tools_available,
    cs.project_path,
    cs.session_id AS parent_session_id,
    cs.timestamp AS parent_pst_time,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'
    cs.tags AS parent_tags,
    left(cs.summary, 200) AS parent_summary_preview
FROM agent_work aw
LEFT JOIN agent_definitions ad ON ad.id = aw.agent_definition_id
LEFT JOIN context_snapshots cs ON cs.id = aw.parent_snapshot_id
ORDER BY aw.timestamp_start DESC;

COMMENT ON VIEW v_agent_work_full IS 'Complete agent work details with parent snapshot context. UPDATED: Timezone-aware timestamps.';

-- ============================================================================
-- View 4/7: v_all_decisions
-- ============================================================================

ALTER VIEW v_all_decisions RENAME TO v_all_decisions_backup_20251228;

CREATE VIEW v_all_decisions AS
SELECT
    cs.id AS snapshot_id,
    cs.project_path,
    cs.session_id,
    cs.timestamp AS pst_time,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'
    cs.trigger_event,
    t.decision_index,
    t.decision_text
FROM context_snapshots cs,
LATERAL unnest(cs.key_decisions) WITH ORDINALITY t(decision_text, decision_index)
WHERE cs.key_decisions IS NOT NULL;

COMMENT ON VIEW v_all_decisions IS 'All architectural decisions with snapshot context. UPDATED: Timezone-aware timestamps.';

-- ============================================================================
-- View 5/7: v_bug_patterns
-- ============================================================================

ALTER VIEW v_bug_patterns RENAME TO v_bug_patterns_backup_20251228;

CREATE VIEW v_bug_patterns AS
SELECT
    cs.id AS snapshot_id,
    cs.project_path,
    cs.session_id,
    cs.timestamp AS pst_time,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'
    cs.trigger_event,
    t.bug_index,
    t.bug_text,
    CASE
        WHEN lower(t.bug_text) LIKE '%sql%' OR lower(t.bug_text) LIKE '%postgres%' THEN 'database'
        WHEN lower(t.bug_text) LIKE '%module%' OR lower(t.bug_text) LIKE '%import%' THEN 'dependency'
        WHEN lower(t.bug_text) LIKE '%exit code%' THEN 'command'
        WHEN lower(t.bug_text) LIKE '%syntax%' OR lower(t.bug_text) LIKE '%parse%' THEN 'syntax'
        WHEN lower(t.bug_text) LIKE '%error:%' THEN 'runtime'
        ELSE 'other'
    END AS bug_category
FROM context_snapshots cs,
LATERAL unnest(cs.bugs_fixed) WITH ORDINALITY t(bug_text, bug_index)
WHERE cs.bugs_fixed IS NOT NULL;

COMMENT ON VIEW v_bug_patterns IS 'Bug patterns with automatic categorization. UPDATED: Timezone-aware timestamps.';

-- ============================================================================
-- View 6/7: v_file_heatmap
-- ============================================================================

ALTER VIEW v_file_heatmap RENAME TO v_file_heatmap_backup_20251228;

CREATE VIEW v_file_heatmap AS
SELECT
    file_path.file_path,
    count(*) AS mention_count,
    count(DISTINCT cs.project_path) AS project_count,
    min(cs.timestamp) AS first_mentioned,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'
    max(cs.timestamp) AS last_mentioned,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'
    array_agg(DISTINCT cs.project_path) AS mentioned_in_projects,
    CASE
        WHEN file_path.file_path LIKE '%.md' THEN 'documentation'
        WHEN file_path.file_path LIKE '%.js' OR file_path.file_path LIKE '%.ts' THEN 'javascript'
        WHEN file_path.file_path LIKE '%.py' THEN 'python'
        WHEN file_path.file_path LIKE '%.sql' THEN 'sql'
        WHEN file_path.file_path LIKE 'docker%' OR file_path.file_path LIKE '%.yml' OR file_path.file_path LIKE '%.yaml' THEN 'config'
        WHEN file_path.file_path LIKE '%.json' THEN 'json'
        ELSE 'other'
    END AS file_type
FROM context_snapshots cs,
LATERAL unnest(cs.mentioned_files) file_path(file_path)
WHERE cs.mentioned_files IS NOT NULL
GROUP BY file_path.file_path
ORDER BY count(*) DESC;

COMMENT ON VIEW v_file_heatmap IS 'File activity heatmap showing frequency and recency. UPDATED: Timezone-aware timestamps.';

-- ============================================================================
-- View 7/7: v_messages_flat
-- ============================================================================

ALTER VIEW v_messages_flat RENAME TO v_messages_flat_backup_20251228;

CREATE VIEW v_messages_flat AS
SELECT
    cs.id AS snapshot_id,
    cs.project_path,
    cs.session_id,
    cs.timestamp,
    cs.timestamp AS pst_time,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'
    t.msg_index - 1 AS message_index,
    t.msg ->> 'role' AS role,
    t.msg ->> 'content' AS content,
    length(t.msg ->> 'content') AS content_length
FROM context_snapshots cs,
LATERAL jsonb_array_elements(cs.raw_context -> 'messages') WITH ORDINALITY t(msg, msg_index);

COMMENT ON VIEW v_messages_flat IS 'Flattened message view for content search. UPDATED: Timezone-aware timestamps.';

COMMIT;

-- ============================================================================
-- Verification Summary
-- ============================================================================

-- All 7 views should now have timezone-aware timestamps:
-- 1. v_snapshot_quality (migrated in test phase)
-- 2. v_agent_evolution
-- 3. v_agent_work_full
-- 4. v_all_decisions
-- 5. v_bug_patterns
-- 6. v_file_heatmap
-- 7. v_messages_flat

-- Verify all backups exist:
-- SELECT viewname FROM pg_views
-- WHERE viewname LIKE '%_backup_20251228'
-- ORDER BY viewname;

-- Verify all views return timestamptz:
-- SELECT
--   c.table_name as view_name,
--   c.column_name,
--   c.data_type
-- FROM information_schema.columns c
-- WHERE c.table_schema = 'public'
--   AND c.table_name IN ('v_snapshot_quality', 'v_agent_evolution', 'v_agent_work_full',
--                        'v_all_decisions', 'v_bug_patterns', 'v_file_heatmap', 'v_messages_flat')
--   AND c.column_name IN ('pst_time', 'pst_created', 'pst_start', 'pst_end',
--                         'last_used_pst', 'parent_pst_time', 'first_mentioned', 'last_mentioned')
-- ORDER BY c.table_name, c.column_name;
