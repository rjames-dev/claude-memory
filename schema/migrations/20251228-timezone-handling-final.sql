-- Timezone Handling Migration - FINAL 2 VIEWS
-- Date: 2025-12-28
-- Purpose: Complete timezone migration for remaining 2 views
--
-- Views migrated in previous phases:
-- - v_snapshot_quality (test phase)
-- - v_agent_evolution, v_agent_work_full, v_all_decisions,
--   v_bug_patterns, v_file_heatmap, v_messages_flat (full phase)
--
-- This migration completes the work with:
-- - v_project_dashboard (actively used by /api/projects)
-- - v_work_timeline (not currently used, but fix for completeness)

BEGIN;

-- ============================================================================
-- View 8/9: v_project_dashboard
-- ============================================================================

ALTER VIEW v_project_dashboard RENAME TO v_project_dashboard_backup_20251228;

CREATE VIEW v_project_dashboard AS
SELECT
    project_path,
    COUNT(*) AS total_snapshots,
    COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL) AS tracked_sessions,
    MIN(timestamp) AS first_activity,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'
    MAX(timestamp) AS last_activity,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'
    CURRENT_TIMESTAMP - MAX(timestamp) AS time_since_last_activity,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'

    -- Message statistics
    SUM(jsonb_array_length(raw_context->'messages')) AS total_messages,
    AVG(jsonb_array_length(raw_context->'messages'))::numeric(10,1) AS avg_messages_per_snapshot,
    MAX(jsonb_array_length(raw_context->'messages')) AS max_messages,

    -- Metadata statistics
    AVG(COALESCE(array_length(tags, 1), 0))::numeric(10,1) AS avg_tags,
    AVG(COALESCE(array_length(mentioned_files, 1), 0))::numeric(10,1) AS avg_files,
    AVG(COALESCE(array_length(key_decisions, 1), 0))::numeric(10,1) AS avg_decisions,
    AVG(COALESCE(array_length(bugs_fixed, 1), 0))::numeric(10,1) AS avg_bugs,

    -- Quality metrics
    COUNT(*) FILTER (WHERE summary IS NOT NULL) AS snapshots_with_summary,
    COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS snapshots_with_embedding,
    COUNT(*) FILTER (WHERE session_id IS NOT NULL) AS snapshots_with_session_id,

    -- Dominant tags (most common tag)
    (
        SELECT unnest(tags) AS tag
        FROM context_snapshots cs2
        WHERE cs2.project_path = cs.project_path
        AND tags IS NOT NULL
        GROUP BY tag
        ORDER BY COUNT(*) DESC
        LIMIT 1
    ) AS most_common_tag

FROM context_snapshots cs
WHERE project_path IS NOT NULL
GROUP BY project_path
ORDER BY last_activity DESC;

COMMENT ON VIEW v_project_dashboard IS 'Per-project statistics and health metrics. Shows activity, message counts, and metadata richness. UPDATED: Timezone-aware timestamps.';

-- ============================================================================
-- View 9/9: v_work_timeline
-- ============================================================================

ALTER VIEW v_work_timeline RENAME TO v_work_timeline_backup_20251228;

CREATE VIEW v_work_timeline AS
SELECT
    id,
    timestamp AS pst_time,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'
    project_path,
    session_id,
    trigger_event,

    -- Extract trigger type (auto-capture, manual, test, etc.)
    CASE
        WHEN trigger_event LIKE 'auto-capture%' THEN 'auto-capture'
        WHEN trigger_event LIKE 'manual%' THEN 'manual'
        WHEN trigger_event LIKE 'test%' THEN 'test'
        WHEN trigger_event LIKE '%compact%' THEN 'compact'
        ELSE 'other'
    END AS trigger_type,

    -- Message count
    jsonb_array_length(raw_context->'messages') AS message_count,

    -- Metadata counts
    COALESCE(array_length(tags, 1), 0) AS tag_count,
    COALESCE(array_length(mentioned_files, 1), 0) AS file_count,
    COALESCE(array_length(key_decisions, 1), 0) AS decision_count,
    COALESCE(array_length(bugs_fixed, 1), 0) AS bug_count,

    -- Summary preview
    LEFT(summary, 100) AS summary_preview

FROM context_snapshots
ORDER BY timestamp DESC;

COMMENT ON VIEW v_work_timeline IS 'Chronological timeline of all snapshots. UPDATED: Timezone-aware timestamps.';

COMMIT;

-- ============================================================================
-- Verification Summary
-- ============================================================================

-- All 9 views now have timezone-aware timestamps:
-- 1. v_snapshot_quality (test phase)
-- 2. v_agent_evolution (full phase)
-- 3. v_agent_work_full (full phase)
-- 4. v_all_decisions (full phase)
-- 5. v_bug_patterns (full phase)
-- 6. v_file_heatmap (full phase)
-- 7. v_messages_flat (full phase)
-- 8. v_project_dashboard (final phase - THIS FILE)
-- 9. v_work_timeline (final phase - THIS FILE)

-- Verify both backups exist:
-- SELECT viewname FROM pg_views
-- WHERE viewname IN ('v_project_dashboard_backup_20251228', 'v_work_timeline_backup_20251228')
-- ORDER BY viewname;

-- Verify timestamp columns return timestamptz:
-- SELECT
--   c.table_name as view_name,
--   c.column_name,
--   c.data_type
-- FROM information_schema.columns c
-- WHERE c.table_schema = 'public'
--   AND c.table_name IN ('v_project_dashboard', 'v_work_timeline')
--   AND c.column_name IN ('first_activity', 'last_activity', 'pst_time')
-- ORDER BY c.table_name, c.column_name;
