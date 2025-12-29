-- Timezone Handling Migration - SKILLS VIEWS
-- Date: 2025-12-28
-- Purpose: Complete timezone migration for skills-related views
--
-- These views were created in schema/add-skills-tables.sql (not init.sql)
-- and were missed in initial discovery due to different column naming.
--
-- This migration completes ALL timezone work with:
-- - v_skills_dashboard (used by skills-stats.py)
-- - v_skill_candidates (not currently used, but fix for completeness)

BEGIN;

-- ============================================================================
-- View 10/11: v_skills_dashboard
-- ============================================================================

ALTER VIEW v_skills_dashboard RENAME TO v_skills_dashboard_backup_20251228;

CREATE VIEW v_skills_dashboard AS
SELECT
    sa.id,
    sa.agent_name,
    sa.display_name,
    sa.description,
    sa.category,
    sa.scope,
    sa.project_path,

    -- Performance metrics
    sa.use_count,
    sa.success_count,
    sa.failure_count,
    sa.success_rate,
    sa.avg_time_saved_ms,
    sa.total_time_saved_ms,
    sa.total_time_saved_ms / 1000 / 60 AS total_time_saved_minutes,

    -- Recency
    sa.last_used AS last_used_pst,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'
    CURRENT_TIMESTAMP - sa.last_used AS time_since_last_use,

    -- Version and confidence
    sa.version,
    sa.confidence_score,

    -- Trigger count
    COUNT(DISTINCT st.id) AS trigger_count,

    -- Recent activity (last 7 days) - DISTINCT prevents cartesian product overcounting
    COUNT(DISTINCT spl.id) FILTER (WHERE spl.executed_at > NOW() - INTERVAL '7 days') AS uses_last_7_days,
    COUNT(DISTINCT spl.id) FILTER (
        WHERE spl.outcome = 'success' AND spl.executed_at > NOW() - INTERVAL '7 days'
    ) AS successes_last_7_days,

    -- Status categorization
    CASE
        WHEN sa.use_count >= 10 AND sa.success_rate >= 90 THEN 'stable'
        WHEN sa.use_count < 5 THEN 'new'
        WHEN sa.success_rate < 70 THEN 'needs_improvement'
        ELSE 'developing'
    END AS status_category

FROM skills_agents sa
LEFT JOIN skills_triggers st ON st.agent_id = sa.id AND st.is_active = TRUE
LEFT JOIN skills_performance_log spl ON spl.agent_id = sa.id
WHERE sa.is_active = TRUE
GROUP BY sa.id
ORDER BY sa.use_count DESC, sa.success_rate DESC;

COMMENT ON VIEW v_skills_dashboard IS 'High-level overview of all active skills with performance and usage metrics. UPDATED: Timezone-aware timestamps.';

-- ============================================================================
-- View 11/11: v_skill_candidates
-- ============================================================================

ALTER VIEW v_skill_candidates RENAME TO v_skill_candidates_backup_20251228;

CREATE VIEW v_skill_candidates AS
SELECT
    sp.id,
    sp.pattern_name,
    sp.pattern_type,
    sp.occurrences,
    sp.confidence_score,
    sp.priority_score,
    sp.status,

    -- Snapshot context
    sp.first_seen_snapshot_id,
    sp.last_seen_snapshot_id,

    -- Time span of pattern
    (
        SELECT cs2.timestamp
        FROM context_snapshots cs2
        WHERE cs2.id = sp.last_seen_snapshot_id
    ) - (
        SELECT cs1.timestamp
        FROM context_snapshots cs1
        WHERE cs1.id = sp.first_seen_snapshot_id
    ) AS pattern_timespan,

    -- Project spread
    array_length(sp.seen_in_projects, 1) AS project_count,
    sp.seen_in_projects,

    -- Timestamps
    sp.created_at AS created_pst,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'
    sp.reviewed_at AS reviewed_pst,  -- CHANGED: was AT TIME ZONE 'America/Los_Angeles'

    -- Confidence level
    CASE
        WHEN sp.confidence_score >= 0.9 THEN 'high'
        WHEN sp.confidence_score >= 0.7 THEN 'medium'
        ELSE 'low'
    END AS confidence_level

FROM skills_patterns sp
ORDER BY sp.priority_score DESC, sp.confidence_score DESC;

COMMENT ON VIEW v_skill_candidates IS 'Detected patterns awaiting review for potential skill creation. UPDATED: Timezone-aware timestamps.';

COMMIT;

-- ============================================================================
-- Verification Summary
-- ============================================================================

-- ALL 11 views now have timezone-aware timestamps:
-- 1. v_snapshot_quality (test phase)
-- 2. v_agent_evolution (full phase)
-- 3. v_agent_work_full (full phase)
-- 4. v_all_decisions (full phase)
-- 5. v_bug_patterns (full phase)
-- 6. v_file_heatmap (full phase)
-- 7. v_messages_flat (full phase)
-- 8. v_project_dashboard (final phase)
-- 9. v_work_timeline (final phase)
-- 10. v_skills_dashboard (skills phase - THIS FILE)
-- 11. v_skill_candidates (skills phase - THIS FILE)

-- Verify both backups exist:
-- SELECT viewname FROM pg_views
-- WHERE viewname IN ('v_skills_dashboard_backup_20251228', 'v_skill_candidates_backup_20251228')
-- ORDER BY viewname;

-- Verify timestamp columns return timestamptz:
-- SELECT
--   c.table_name as view_name,
--   c.column_name,
--   c.data_type
-- FROM information_schema.columns c
-- WHERE c.table_schema = 'public'
--   AND c.table_name IN ('v_skills_dashboard', 'v_skill_candidates')
--   AND c.column_name IN ('last_used_pst', 'created_pst', 'reviewed_pst')
-- ORDER BY c.table_name, c.column_name;
