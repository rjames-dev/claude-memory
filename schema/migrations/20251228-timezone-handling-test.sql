-- Timezone Handling Migration - TEST PHASE
-- Date: 2025-12-28
-- Purpose: Test migration with v_snapshot_quality only
--
-- CRITICAL: This is a TEST migration for v_snapshot_quality ONLY
-- If successful, we'll create the full migration for all 7 views

BEGIN;

-- ============================================================================
-- TEST: Migrate v_snapshot_quality ONLY
-- ============================================================================

-- Step 1: Backup existing view (rename, don't drop)
ALTER VIEW v_snapshot_quality
RENAME TO v_snapshot_quality_backup_20251228;

-- Step 2: Create new version with timezone-aware timestamps
CREATE VIEW v_snapshot_quality AS
SELECT
    id,
    project_path,
    timestamp AS pst_time,  -- CHANGED: was "timestamp AT TIME ZONE 'America/Los_Angeles'"
    session_id,
    trigger_event,

    -- Message metrics
    jsonb_array_length(raw_context->'messages') AS message_count,

    -- Metadata completeness scores (0 or 1 for each field)
    CASE WHEN summary IS NOT NULL AND length(summary) > 50 THEN 1 ELSE 0 END AS has_summary,
    CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END AS has_embedding,
    CASE WHEN tags IS NOT NULL AND array_length(tags, 1) > 0 THEN 1 ELSE 0 END AS has_tags,
    CASE WHEN mentioned_files IS NOT NULL AND array_length(mentioned_files, 1) > 0 THEN 1 ELSE 0 END AS has_files,
    CASE WHEN key_decisions IS NOT NULL AND array_length(key_decisions, 1) > 0 THEN 1 ELSE 0 END AS has_decisions,
    CASE WHEN bugs_fixed IS NOT NULL AND array_length(bugs_fixed, 1) > 0 THEN 1 ELSE 0 END AS has_bugs,
    CASE WHEN git_commit_hash IS NOT NULL THEN 1 ELSE 0 END AS has_git_hash,
    CASE WHEN session_id IS NOT NULL THEN 1 ELSE 0 END AS has_session_id,

    -- Array sizes
    COALESCE(array_length(tags, 1), 0) AS tag_count,
    COALESCE(array_length(mentioned_files, 1), 0) AS file_count,
    COALESCE(array_length(key_decisions, 1), 0) AS decision_count,
    COALESCE(array_length(bugs_fixed, 1), 0) AS bug_count,

    -- Overall quality score (0-10)
    (
        CASE WHEN summary IS NOT NULL AND length(summary) > 50 THEN 1 ELSE 0 END +
        CASE WHEN embedding IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN tags IS NOT NULL AND array_length(tags, 1) > 0 THEN 1 ELSE 0 END +
        CASE WHEN mentioned_files IS NOT NULL AND array_length(mentioned_files, 1) > 0 THEN 1 ELSE 0 END +
        CASE WHEN key_decisions IS NOT NULL AND array_length(key_decisions, 1) > 0 THEN 1 ELSE 0 END +
        CASE WHEN bugs_fixed IS NOT NULL AND array_length(bugs_fixed, 1) > 0 THEN 1 ELSE 0 END +
        CASE WHEN git_commit_hash IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN session_id IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN jsonb_array_length(raw_context->'messages') >= 5 THEN 1 ELSE 0 END +
        CASE WHEN length(summary) > 200 THEN 1 ELSE 0 END
    ) AS quality_score,

    -- Summary length
    length(summary) AS summary_length

FROM context_snapshots;

COMMENT ON VIEW v_snapshot_quality IS 'Quality metrics for each snapshot. Quality score 0-10 based on metadata completeness. UPDATED: Timezone-aware timestamps.';

COMMIT;

-- ============================================================================
-- Verification Queries (run these after migration)
-- ============================================================================

-- 1. Verify new view returns timestamptz (not naive timestamp)
-- Expected: pst_time | timestamp with time zone
-- \d+ v_snapshot_quality

-- 2. Verify backup view still exists
-- Expected: 1 row
-- SELECT COUNT(*) FROM pg_views WHERE viewname = 'v_snapshot_quality_backup_20251228';

-- 3. Compare a sample timestamp in both views
-- Expected: Same UTC moment, different representations
-- SELECT
--   id,
--   (SELECT pst_time FROM v_snapshot_quality_backup_20251228 WHERE id = v.id) as old_pst,
--   v.pst_time as new_timestamptz
-- FROM v_snapshot_quality v
-- LIMIT 1;

-- 4. Test timezone conversion works
-- Expected: Different display times for different timezones
-- SELECT
--   pst_time,
--   pst_time AT TIME ZONE 'America/Los_Angeles' as pst_display,
--   pst_time AT TIME ZONE 'America/New_York' as est_display,
--   pst_time AT TIME ZONE 'UTC' as utc_display
-- FROM v_snapshot_quality
-- LIMIT 1;
