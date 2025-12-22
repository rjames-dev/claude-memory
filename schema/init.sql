-- Claude Memory System - Database Schema
-- PostgreSQL + pgvector for semantic context search
-- Created: 2025-12-13

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Main context snapshots table
CREATE TABLE context_snapshots (
    id SERIAL PRIMARY KEY,

    -- Project identification
    project_path TEXT NOT NULL,              -- e.g., "Code/pgquery-dev/nlq-data-bridge"
    session_id TEXT,                         -- Claude session identifier

    -- Temporal data
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Context metadata
    context_window_size INTEGER,             -- Number of messages in snapshot
    trigger_event TEXT,                      -- 'auto_compact', 'manual_save', 'session_end'

    -- Content
    raw_context JSONB NOT NULL,              -- Full conversation messages array
    summary TEXT,                            -- AI-generated summary (200-300 words)

    -- Vector embeddings for semantic search
    embedding vector(384),                   -- sentence-transformers/all-MiniLM-L6-v2 dimensions

    -- Indexing and metadata
    tags TEXT[],                             -- ['security', 'sql-injection', 'performance']
    mentioned_files TEXT[],                  -- Files discussed in this context
    key_decisions TEXT[],                    -- Extracted architectural decisions
    bugs_fixed TEXT[],                       -- Bug descriptions from this session

    -- Git state at capture time
    git_commit_hash TEXT,
    git_branch TEXT,

    -- Source file tracking
    transcript_path TEXT,                    -- Path to Claude Code transcript (.jsonl)

    -- Metadata
    created_by TEXT DEFAULT 'claude-code',
    storage_size_bytes INTEGER              -- Size of raw_context for monitoring
);

-- Indexes for fast retrieval
CREATE INDEX idx_project_path ON context_snapshots(project_path);
CREATE INDEX idx_session_id ON context_snapshots(session_id);
CREATE INDEX idx_timestamp_desc ON context_snapshots(timestamp DESC);
CREATE INDEX idx_trigger_event ON context_snapshots(trigger_event);
CREATE INDEX idx_transcript_path ON context_snapshots(transcript_path);
CREATE INDEX idx_tags ON context_snapshots USING GIN(tags);
CREATE INDEX idx_files ON context_snapshots USING GIN(mentioned_files);

-- Vector similarity search index (HNSW for fast approximate search)
CREATE INDEX idx_embedding ON context_snapshots
USING hnsw (embedding vector_cosine_ops);

-- Statistics view for monitoring
CREATE VIEW context_stats AS
SELECT
    project_path,
    COUNT(*) as snapshot_count,
    MIN(timestamp) as first_snapshot,
    MAX(timestamp) as last_snapshot,
    SUM(storage_size_bytes) / 1024 / 1024 as total_mb,
    AVG(context_window_size) as avg_messages
FROM context_snapshots
GROUP BY project_path;

-- ============================================================================
-- ANALYTICAL VIEWS - Phase 1
-- These views work with current schema and are forward-compatible with JSONB migration
-- Phase 2 views (using summary_v2 JSONB) will be added after architecture improvements
-- ============================================================================

-- View 1: Flatten JSONB messages for easy querying
-- Purpose: Convert nested raw_context->messages array into flat rows
-- Use case: Search exact phrases, reconstruct conversations, message-level analysis
CREATE VIEW v_messages_flat AS
SELECT
    cs.id AS snapshot_id,
    cs.project_path,
    cs.session_id,
    cs.timestamp,
    cs.timestamp AT TIME ZONE 'America/Los_Angeles' AS pst_time,
    (msg_index - 1) AS message_index,  -- 0-indexed for consistency
    msg->>'role' AS role,
    msg->>'content' AS content,
    length(msg->>'content') AS content_length
FROM context_snapshots cs,
     jsonb_array_elements(cs.raw_context->'messages') WITH ORDINALITY AS t(msg, msg_index);

COMMENT ON VIEW v_messages_flat IS 'Flattened view of all messages from raw_context JSONB. Each row is one message.';

-- View 2: Assistant messages only (for analyzing AI responses)
-- Purpose: Filter v_messages_flat to only assistant messages
-- Use case: Search what Claude said, analyze response patterns, find specific answers
CREATE VIEW v_assistant_messages AS
SELECT
    snapshot_id,
    project_path,
    session_id,
    timestamp,
    pst_time,
    message_index,
    content,
    content_length
FROM v_messages_flat
WHERE role = 'assistant';

COMMENT ON VIEW v_assistant_messages IS 'All assistant (AI) messages. Useful for searching Claude responses.';

-- View 3: Snapshot quality metrics
-- Purpose: Score each snapshot based on metadata completeness
-- Use case: Identify sparse snapshots, monitor capture quality, data health dashboard
CREATE VIEW v_snapshot_quality AS
SELECT
    id,
    project_path,
    timestamp AT TIME ZONE 'America/Los_Angeles' AS pst_time,
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

COMMENT ON VIEW v_snapshot_quality IS 'Quality metrics for each snapshot. Quality score 0-10 based on metadata completeness.';

-- View 4: Project dashboard
-- Purpose: High-level statistics per project
-- Use case: Project health monitoring, activity tracking, session analysis
CREATE VIEW v_project_dashboard AS
SELECT
    project_path,
    COUNT(*) AS total_snapshots,
    COUNT(DISTINCT session_id) FILTER (WHERE session_id IS NOT NULL) AS tracked_sessions,
    MIN(timestamp AT TIME ZONE 'America/Los_Angeles') AS first_activity,
    MAX(timestamp AT TIME ZONE 'America/Los_Angeles') AS last_activity,
    CURRENT_TIMESTAMP AT TIME ZONE 'America/Los_Angeles' - MAX(timestamp AT TIME ZONE 'America/Los_Angeles') AS time_since_last_activity,

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
GROUP BY project_path
ORDER BY last_activity DESC;

COMMENT ON VIEW v_project_dashboard IS 'Per-project statistics and health metrics. Shows activity, message counts, and metadata richness.';

-- View 5: All decisions extracted
-- Purpose: Flatten key_decisions array across all snapshots
-- Use case: Search for specific decisions, track decision evolution, decision analytics
CREATE VIEW v_all_decisions AS
SELECT
    cs.id AS snapshot_id,
    cs.project_path,
    cs.session_id,
    cs.timestamp AT TIME ZONE 'America/Los_Angeles' AS pst_time,
    cs.trigger_event,
    decision_index,
    decision_text
FROM context_snapshots cs,
     unnest(cs.key_decisions) WITH ORDINALITY AS t(decision_text, decision_index)
WHERE cs.key_decisions IS NOT NULL;

COMMENT ON VIEW v_all_decisions IS 'All key decisions flattened. Each row is one decision with context.';

-- View 6: All bugs fixed extracted
-- Purpose: Flatten bugs_fixed array across all snapshots
-- Use case: Bug pattern analysis, recurrence detection, bug category classification
CREATE VIEW v_bug_patterns AS
SELECT
    cs.id AS snapshot_id,
    cs.project_path,
    cs.session_id,
    cs.timestamp AT TIME ZONE 'America/Los_Angeles' AS pst_time,
    cs.trigger_event,
    bug_index,
    bug_text,

    -- Bug classification heuristics
    CASE
        WHEN LOWER(bug_text) LIKE '%sql%' OR LOWER(bug_text) LIKE '%postgres%' THEN 'database'
        WHEN LOWER(bug_text) LIKE '%module%' OR LOWER(bug_text) LIKE '%import%' THEN 'dependency'
        WHEN LOWER(bug_text) LIKE '%exit code%' THEN 'command'
        WHEN LOWER(bug_text) LIKE '%syntax%' OR LOWER(bug_text) LIKE '%parse%' THEN 'syntax'
        WHEN LOWER(bug_text) LIKE '%error:%' THEN 'runtime'
        ELSE 'other'
    END AS bug_category

FROM context_snapshots cs,
     unnest(cs.bugs_fixed) WITH ORDINALITY AS t(bug_text, bug_index)
WHERE cs.bugs_fixed IS NOT NULL;

COMMENT ON VIEW v_bug_patterns IS 'All bugs fixed flattened with automatic categorization.';

-- View 7: File activity heatmap
-- Purpose: Track which files are most frequently mentioned/modified
-- Use case: Find hotspots, identify active components, detect abandoned files
CREATE VIEW v_file_heatmap AS
SELECT
    file_path,
    COUNT(*) AS mention_count,
    COUNT(DISTINCT cs.project_path) AS project_count,
    MIN(cs.timestamp AT TIME ZONE 'America/Los_Angeles') AS first_mentioned,
    MAX(cs.timestamp AT TIME ZONE 'America/Los_Angeles') AS last_mentioned,
    array_agg(DISTINCT cs.project_path) AS mentioned_in_projects,

    -- File categorization
    CASE
        WHEN file_path LIKE '%.md' THEN 'documentation'
        WHEN file_path LIKE '%.js' OR file_path LIKE '%.ts' THEN 'javascript'
        WHEN file_path LIKE '%.py' THEN 'python'
        WHEN file_path LIKE '%.sql' THEN 'sql'
        WHEN file_path LIKE 'docker%' OR file_path LIKE '%.yml' OR file_path LIKE '%.yaml' THEN 'config'
        WHEN file_path LIKE '%.json' THEN 'json'
        ELSE 'other'
    END AS file_type

FROM context_snapshots cs,
     unnest(cs.mentioned_files) AS file_path
WHERE cs.mentioned_files IS NOT NULL
GROUP BY file_path
ORDER BY mention_count DESC;

COMMENT ON VIEW v_file_heatmap IS 'File activity tracking. Shows which files are most frequently worked on.';

-- View 8: Work timeline
-- Purpose: Chronological view of all snapshots with key metadata
-- Use case: Timeline visualization, activity tracking, session flow
CREATE VIEW v_work_timeline AS
SELECT
    id,
    timestamp AT TIME ZONE 'America/Los_Angeles' AS pst_time,
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

    -- Legacy flag
    CASE
        WHEN trigger_event LIKE '%-LEGACY%' THEN true
        ELSE false
    END AS is_legacy,

    -- Message and metadata counts
    jsonb_array_length(raw_context->'messages') AS message_count,
    COALESCE(array_length(tags, 1), 0) AS tag_count,
    COALESCE(array_length(mentioned_files, 1), 0) AS file_count,
    COALESCE(array_length(key_decisions, 1), 0) AS decision_count,
    COALESCE(array_length(bugs_fixed, 1), 0) AS bug_count,

    -- Summary preview (first 100 chars)
    LEFT(summary, 100) AS summary_preview,

    -- Quality indicator
    CASE
        WHEN summary IS NOT NULL AND array_length(tags, 1) > 0
             AND array_length(mentioned_files, 1) > 0 THEN 'rich'
        WHEN summary IS NOT NULL THEN 'basic'
        ELSE 'sparse'
    END AS metadata_richness

FROM context_snapshots
ORDER BY timestamp DESC;

COMMENT ON VIEW v_work_timeline IS 'Chronological timeline of all work sessions with metadata richness indicators.';

-- Comments for documentation
COMMENT ON TABLE context_snapshots IS 'Stores Claude Code conversation snapshots with vector embeddings for semantic search';
COMMENT ON COLUMN context_snapshots.embedding IS 'Vector embedding (384 dimensions) from sentence-transformers/all-MiniLM-L6-v2 model';
COMMENT ON COLUMN context_snapshots.raw_context IS 'Full conversation in JSONB format (array of message objects)';
COMMENT ON COLUMN context_snapshots.summary IS 'Condensed summary generated via OpenWebUI';
COMMENT ON INDEX idx_embedding IS 'HNSW index for fast cosine similarity search on embeddings';

-- Success message
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Claude Memory Database Initialized';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'pgvector extension: INSTALLED';
    RAISE NOTICE 'context_snapshots table: CREATED';
    RAISE NOTICE 'Indexes: 9 created (including HNSW vector search)';
    RAISE NOTICE 'Views: 9 analytical views created';
    RAISE NOTICE '  - context_stats (legacy)';
    RAISE NOTICE '  - v_messages_flat';
    RAISE NOTICE '  - v_assistant_messages';
    RAISE NOTICE '  - v_snapshot_quality';
    RAISE NOTICE '  - v_project_dashboard';
    RAISE NOTICE '  - v_all_decisions';
    RAISE NOTICE '  - v_bug_patterns';
    RAISE NOTICE '  - v_file_heatmap';
    RAISE NOTICE '  - v_work_timeline';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Ready for context capture!';
END $$;
