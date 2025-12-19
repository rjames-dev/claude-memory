-- Claude Memory - Project Path Migration Stored Procedure
-- Migrates all stored file paths when project location changes
--
-- Created: 2025-12-18
-- Status: DESIGN PROPOSAL - Not yet applied to production
--
-- Usage:
--   -- Preview changes (safe, default)
--   SELECT * FROM migrate_project_paths(
--       '/Users/jamesmba/Data/00 GITHUB',
--       '/Users/jamesmba/Projects',
--       dry_run := true
--   );
--
--   -- Apply changes (requires explicit dry_run := false)
--   SELECT * FROM migrate_project_paths(
--       '/Users/jamesmba/Data/00 GITHUB',
--       '/Users/jamesmba/Projects',
--       dry_run := false
--   );
--
-- IMPORTANT: Always run with dry_run := true first to preview changes!

CREATE OR REPLACE FUNCTION migrate_project_paths(
    old_path TEXT,
    new_path TEXT,
    dry_run BOOLEAN DEFAULT TRUE
) RETURNS TABLE (
    table_name TEXT,
    column_name TEXT,
    rows_affected BIGINT,
    sample_old_value TEXT,
    sample_new_value TEXT
) AS $$
DECLARE
    affected_rows BIGINT;
    sample_old TEXT;
    sample_new TEXT;
BEGIN
    -- =====================================================
    -- Input Validation
    -- =====================================================

    IF old_path IS NULL OR new_path IS NULL THEN
        RAISE EXCEPTION 'old_path and new_path cannot be NULL';
    END IF;

    IF old_path = new_path THEN
        RAISE EXCEPTION 'old_path and new_path are identical - no migration needed';
    END IF;

    IF LENGTH(old_path) < 5 THEN
        RAISE EXCEPTION 'old_path seems too short (< 5 chars) - safety check';
    END IF;

    IF LENGTH(new_path) < 5 THEN
        RAISE EXCEPTION 'new_path seems too short (< 5 chars) - safety check';
    END IF;

    -- =====================================================
    -- Output Mode Banner
    -- =====================================================

    IF dry_run THEN
        RAISE NOTICE '╔════════════════════════════════════════════════════════════╗';
        RAISE NOTICE '║            DRY RUN MODE - No changes will be made         ║';
        RAISE NOTICE '╚════════════════════════════════════════════════════════════╝';
    ELSE
        RAISE NOTICE '╔════════════════════════════════════════════════════════════╗';
        RAISE NOTICE '║          LIVE MODE - Database will be modified!           ║';
        RAISE NOTICE '╚════════════════════════════════════════════════════════════╝';
    END IF;

    RAISE NOTICE '';
    RAISE NOTICE 'Old path: %', old_path;
    RAISE NOTICE 'New path: %', new_path;
    RAISE NOTICE '';

    -- =====================================================
    -- 1. Update context_snapshots.project_path
    -- =====================================================

    SELECT COUNT(*),
           MIN(project_path),
           MIN(REPLACE(project_path, old_path, new_path))
    INTO affected_rows, sample_old, sample_new
    FROM context_snapshots
    WHERE project_path LIKE old_path || '%';

    IF NOT dry_run AND affected_rows > 0 THEN
        UPDATE context_snapshots
        SET project_path = REPLACE(project_path, old_path, new_path)
        WHERE project_path LIKE old_path || '%';
    END IF;

    RETURN QUERY SELECT
        'context_snapshots'::TEXT,
        'project_path'::TEXT,
        affected_rows,
        sample_old,
        sample_new;

    -- =====================================================
    -- 2. Update context_snapshots.transcript_path
    -- =====================================================

    SELECT COUNT(*),
           MIN(transcript_path),
           MIN(REPLACE(transcript_path, old_path, new_path))
    INTO affected_rows, sample_old, sample_new
    FROM context_snapshots
    WHERE transcript_path LIKE old_path || '%';

    IF NOT dry_run AND affected_rows > 0 THEN
        UPDATE context_snapshots
        SET transcript_path = REPLACE(transcript_path, old_path, new_path)
        WHERE transcript_path LIKE old_path || '%';
    END IF;

    RETURN QUERY SELECT
        'context_snapshots'::TEXT,
        'transcript_path'::TEXT,
        affected_rows,
        sample_old,
        sample_new;

    -- =====================================================
    -- 3. Update context_snapshots.mentioned_files (TEXT[] array)
    -- =====================================================

    SELECT COUNT(*),
           (SELECT mentioned_files[1]
            FROM context_snapshots
            WHERE mentioned_files::text LIKE '%' || old_path || '%'
            LIMIT 1),
           (SELECT REPLACE(mentioned_files[1], old_path, new_path)
            FROM context_snapshots
            WHERE mentioned_files::text LIKE '%' || old_path || '%'
            LIMIT 1)
    INTO affected_rows, sample_old, sample_new
    FROM context_snapshots
    WHERE mentioned_files::text LIKE '%' || old_path || '%';

    IF NOT dry_run AND affected_rows > 0 THEN
        UPDATE context_snapshots
        SET mentioned_files = (
            SELECT ARRAY_AGG(REPLACE(f, old_path, new_path))
            FROM UNNEST(mentioned_files) AS f
        )
        WHERE mentioned_files::text LIKE '%' || old_path || '%';
    END IF;

    RETURN QUERY SELECT
        'context_snapshots'::TEXT,
        'mentioned_files'::TEXT,
        affected_rows,
        sample_old,
        sample_new;

    -- =====================================================
    -- 4. Update agent_work.files_examined (JSONB array)
    -- =====================================================

    SELECT COUNT(*),
           MIN(files_examined::text),
           MIN(REPLACE(files_examined::text, old_path, new_path))
    INTO affected_rows, sample_old, sample_new
    FROM agent_work
    WHERE files_examined IS NOT NULL
      AND files_examined::text LIKE '%' || old_path || '%';

    IF NOT dry_run AND affected_rows > 0 THEN
        UPDATE agent_work
        SET files_examined = (
            SELECT jsonb_agg(
                REPLACE(value::text, old_path, new_path)::jsonb
            )
            FROM jsonb_array_elements(files_examined)
        )
        WHERE files_examined IS NOT NULL
          AND files_examined::text LIKE '%' || old_path || '%';
    END IF;

    RETURN QUERY SELECT
        'agent_work'::TEXT,
        'files_examined'::TEXT,
        affected_rows,
        sample_old,
        sample_new;

    -- =====================================================
    -- Summary Banner
    -- =====================================================

    RAISE NOTICE '';
    IF dry_run THEN
        RAISE NOTICE '╔════════════════════════════════════════════════════════════╗';
        RAISE NOTICE '║               DRY RUN COMPLETE - No changes made          ║';
        RAISE NOTICE '╠════════════════════════════════════════════════════════════╣';
        RAISE NOTICE '║  Run with dry_run := false to apply these changes         ║';
        RAISE NOTICE '╚════════════════════════════════════════════════════════════╝';
    ELSE
        RAISE NOTICE '╔════════════════════════════════════════════════════════════╗';
        RAISE NOTICE '║            MIGRATION COMPLETE - Changes applied!          ║';
        RAISE NOTICE '╠════════════════════════════════════════════════════════════╣';
        RAISE NOTICE '║  Update .env file and restart containers with new paths   ║';
        RAISE NOTICE '╚════════════════════════════════════════════════════════════╝';
    END IF;
    RAISE NOTICE '';

END;
$$ LANGUAGE plpgsql;

-- Grant execute permission to memory admin user
GRANT EXECUTE ON FUNCTION migrate_project_paths TO memory_admin;

-- Add helpful comment
COMMENT ON FUNCTION migrate_project_paths IS
'Migrate all stored file paths when project location changes.

This function updates:
- context_snapshots.project_path (TEXT)
- context_snapshots.transcript_path (TEXT)
- context_snapshots.mentioned_files (TEXT[])
- agent_work.files_examined (JSONB)

SAFETY FEATURES:
- dry_run mode is DEFAULT (true) - must explicitly set false to apply
- Input validation prevents accidental data corruption
- Returns detailed preview of all changes before applying
- Can be wrapped in transaction and rolled back if needed

USAGE EXAMPLES:

-- 1. Preview changes (safe - default)
SELECT * FROM migrate_project_paths(
    ''/Users/jamesmba/Data/00 GITHUB'',
    ''/Users/jamesmba/Projects''
);

-- 2. Preview changes (explicit dry_run)
SELECT * FROM migrate_project_paths(
    ''/Users/jamesmba/Data/00 GITHUB'',
    ''/Users/jamesmba/Projects'',
    dry_run := true
);

-- 3. Apply changes (requires explicit false)
SELECT * FROM migrate_project_paths(
    ''/Users/jamesmba/Data/00 GITHUB'',
    ''/Users/jamesmba/Projects'',
    dry_run := false
);

-- 4. Wrapped in transaction (safest for production)
BEGIN;
SELECT * FROM migrate_project_paths(
    ''/Users/jamesmba/Data/00 GITHUB'',
    ''/Users/jamesmba/Projects'',
    dry_run := false
);
-- Review results, then either:
COMMIT;   -- Keep changes
-- or
ROLLBACK; -- Undo changes

WORKFLOW:
1. Run with dry_run := true to preview
2. Review output carefully
3. Run with dry_run := false to apply
4. Update .env file with new path
5. Restart docker containers
6. Verify system is working

Created: 2025-12-18
Status: Design proposal for Phase 6
';
