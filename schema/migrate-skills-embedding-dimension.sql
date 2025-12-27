-- ============================================================================
-- Skills System Migration: Fix Embedding Dimension
-- Created: 2025-12-27
-- Issue: skills_triggers.embedding was created as vector(384) but should be
--        vector(1024) for Ollama mxbai-embed-large model
-- ============================================================================

-- This migration fixes installations created before the dimension fix.
-- Safe to run multiple times (idempotent).

-- Check current dimension (for informational purposes)
DO $$
DECLARE
    current_dim INTEGER;
BEGIN
    SELECT atttypmod - 4 INTO current_dim
    FROM pg_attribute
    WHERE attrelid = 'skills_triggers'::regclass
    AND attname = 'embedding';

    RAISE NOTICE 'Current embedding dimension: %', current_dim;

    IF current_dim = 384 THEN
        RAISE NOTICE 'Dimension is 384, needs migration to 1024';
    ELSIF current_dim = 1024 THEN
        RAISE NOTICE 'Dimension is already 1024, no migration needed';
    ELSE
        RAISE NOTICE 'Unexpected dimension: %, manual review needed', current_dim;
    END IF;
END $$;

-- Drop the index first (it depends on the column)
DROP INDEX IF EXISTS idx_skills_triggers_embedding;

-- Alter the column type to 1024 dimensions
-- Any existing embeddings will be dropped (they're wrong dimension anyway)
ALTER TABLE skills_triggers
ALTER COLUMN embedding TYPE vector(1024);

-- Recreate the index for semantic search
CREATE INDEX idx_skills_triggers_embedding
ON skills_triggers
USING hnsw (embedding vector_cosine_ops)
WHERE match_type = 'semantic' AND is_active = TRUE;

-- Verify the change
SELECT
    column_name,
    data_type,
    udt_name,
    CASE
        WHEN udt_name = 'vector' THEN (
            SELECT atttypmod - 4
            FROM pg_attribute
            WHERE attrelid = 'skills_triggers'::regclass
            AND attname = 'embedding'
        )
        ELSE NULL
    END as dimension
FROM information_schema.columns
WHERE table_name = 'skills_triggers'
AND column_name = 'embedding';

-- Note: After running this migration, you should regenerate embeddings:
-- python3 generate-trigger-embeddings.py --backfill
