-- Claude Memory - Add transcript_path Column
-- Fixes schema inconsistency: Index exists but column was never added
-- Created: 2025-12-19 (Phase 6B)
--
-- Background:
-- - init.sql line 50 creates index on transcript_path
-- - But column was never added to table definition
-- - This migration adds it retroactively

-- Add transcript_path column if it doesn't exist
DO $$
BEGIN
    -- Check if column exists
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'context_snapshots'
          AND column_name = 'transcript_path'
    ) THEN
        -- Add the missing column
        ALTER TABLE context_snapshots
        ADD COLUMN transcript_path TEXT;

        RAISE NOTICE '✅ Added transcript_path column to context_snapshots';
    ELSE
        RAISE NOTICE 'ℹ️  transcript_path column already exists - no changes needed';
    END IF;

    -- Ensure index exists (it should from init.sql, but verify)
    IF NOT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE tablename = 'context_snapshots'
          AND indexname = 'idx_transcript_path'
    ) THEN
        CREATE INDEX idx_transcript_path ON context_snapshots(transcript_path);
        RAISE NOTICE '✅ Created idx_transcript_path index';
    ELSE
        RAISE NOTICE 'ℹ️  idx_transcript_path index already exists';
    END IF;

END $$;

-- Add helpful comment
COMMENT ON COLUMN context_snapshots.transcript_path IS
'Path to the Claude Code transcript file (.jsonl) for this snapshot.
Example: /Users/username/.claude/projects/-Users-username-Code-project/session-uuid.jsonl';

-- Success message
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'transcript_path Column Migration Complete';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Schema inconsistency resolved';
    RAISE NOTICE 'Ready for path migration utility';
END $$;
