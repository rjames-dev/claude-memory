-- Migration: Delta capture tracking
-- Enables per-compaction-event summaries instead of re-summarizing the full session.
--
-- message_start_index: index into the transcript where this snapshot's delta begins
--   compaction 1: 0           (covers messages 0..N)
--   compaction 2: N+1         (covers messages N+1..M — only new work)
--
-- compaction_index: Nth compaction within this session (1-based)
--   Used to order compactions within a session and prevent upsert collisions.

ALTER TABLE context_snapshots
  ADD COLUMN IF NOT EXISTS message_start_index INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS compaction_index    INTEGER NOT NULL DEFAULT 1;

-- Back-fill the single existing row (first and only compaction of its session)
UPDATE context_snapshots SET message_start_index = 0, compaction_index = 1;

-- Index for efficient per-session lookups (used by hook before each capture)
CREATE INDEX IF NOT EXISTS idx_session_compaction
  ON context_snapshots(session_id, compaction_index);
