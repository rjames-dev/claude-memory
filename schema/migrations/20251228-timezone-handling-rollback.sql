-- Timezone Handling Migration - ROLLBACK SCRIPT
-- Date: 2025-12-28
-- Purpose: Rollback timezone migration to original state
--
-- Use this if issues are discovered during testing

BEGIN;

-- ============================================================================
-- ROLLBACK: v_snapshot_quality
-- ============================================================================

-- Drop the new view
DROP VIEW IF EXISTS v_snapshot_quality;

-- Restore the backup by renaming it back
ALTER VIEW v_snapshot_quality_backup_20251228
RENAME TO v_snapshot_quality;

COMMIT;

-- ============================================================================
-- Verification after rollback
-- ============================================================================

-- Verify old view is restored
-- Expected: pst_time | timestamp without time zone
-- \d+ v_snapshot_quality

-- Verify backup no longer exists
-- Expected: 0 rows
-- SELECT COUNT(*) FROM pg_views WHERE viewname = 'v_snapshot_quality_backup_20251228';
