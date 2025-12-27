-- Migration: Update embedding column dimensions for mxbai-embed-large model
-- Changes: 384 → 1024 dimensions
-- Model: mxbai-embed-large (Ollama)
-- Date: 2025-12-26

BEGIN;

-- Drop the existing HNSW index (references vector(384))
DROP INDEX IF EXISTS idx_skills_triggers_embedding;

-- Alter the column type from vector(384) to vector(1024)
ALTER TABLE skills_triggers
  ALTER COLUMN embedding TYPE vector(1024);

-- Recreate the HNSW index for fast similarity search
CREATE INDEX idx_skills_triggers_embedding
  ON skills_triggers
  USING hnsw (embedding vector_cosine_ops)
  WHERE match_type = 'semantic' AND is_active = TRUE;

-- Verify the change
SELECT
  column_name,
  data_type,
  udt_name
FROM information_schema.columns
WHERE table_name = 'skills_triggers'
  AND column_name = 'embedding';

COMMIT;

-- Expected output:
--  column_name | data_type | udt_name
-- -------------+-----------+-----------
--  embedding   | USER-DEFINED | vector
--
-- The actual dimensions (1024) are stored in pg_type but not shown in information_schema
