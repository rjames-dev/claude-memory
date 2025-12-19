-- ============================================================================
-- Claude Memory - Agent Capture Migration
-- Adds three-table architecture for complete agent memory
-- Created: 2025-12-18
-- ============================================================================

-- ============================================================================
-- TABLE 1: agent_definitions
-- Purpose: Store agent configurations (the "blueprint")
-- ============================================================================

CREATE TABLE agent_definitions (
    id SERIAL PRIMARY KEY,

    -- Agent identification
    agent_type VARCHAR(255) NOT NULL,              -- "Explore", "Plan", "scrape-web-agent"
    agent_name VARCHAR(255),                       -- User-friendly name (optional)

    -- Agent configuration (THE KEY DATA)
    system_message TEXT,                           -- The prompt/instructions that define the agent
    configuration_params JSONB,                    -- All config: timeout, retries, model, etc.
    tools_available TEXT[],                        -- ["WebFetch", "Read", "Grep", "Write"]
    model_used VARCHAR(100),                       -- "claude-sonnet-4-5", "claude-haiku", etc.

    -- Versioning and evolution
    version INTEGER DEFAULT 1,                     -- For tracking evolution of same agent type
    parent_definition_id INTEGER REFERENCES agent_definitions(id),  -- If forked/modified from another

    -- Metadata
    description TEXT,                              -- What this agent does
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255),                       -- "user" or "system"

    -- Deduplication
    config_hash VARCHAR(64) UNIQUE,                -- SHA256 of (system_message + params + tools + model)

    CONSTRAINT unique_agent_config UNIQUE (agent_type, config_hash)
);

-- Indexes for performance
CREATE INDEX idx_agent_defs_type ON agent_definitions(agent_type);
CREATE INDEX idx_agent_defs_hash ON agent_definitions(config_hash);
CREATE INDEX idx_agent_defs_created ON agent_definitions(created_at);

-- Comments for documentation
COMMENT ON TABLE agent_definitions IS 'Agent configurations (blueprints). Enables tracking agent evolution and performance comparison.';
COMMENT ON COLUMN agent_definitions.system_message IS 'The prompt/instructions that define how the agent behaves';
COMMENT ON COLUMN agent_definitions.configuration_params IS 'JSONB containing all config: timeout, retries, depth, etc.';
COMMENT ON COLUMN agent_definitions.config_hash IS 'SHA256 hash for deduplication - same config = same definition_id';
COMMENT ON COLUMN agent_definitions.version IS 'Incremental version number for tracking evolution of same agent type';


-- ============================================================================
-- TABLE 2: agent_work
-- Purpose: Store individual agent execution instances (linked to definitions)
-- ============================================================================

CREATE TABLE agent_work (
    id SERIAL PRIMARY KEY,

    -- Linkage to parent conversation AND agent definition
    request_id VARCHAR(255) NOT NULL,              -- Ties multiple agents to same request
    parent_snapshot_id INTEGER REFERENCES context_snapshots(id),
    parent_session_id VARCHAR(255) NOT NULL,
    agent_definition_id INTEGER REFERENCES agent_definitions(id),  -- ← Links to config blueprint

    -- Agent identification
    agent_id VARCHAR(255) NOT NULL,                -- From agent-{id}.jsonl filename
    agent_name VARCHAR(255),                       -- If agent has a name (e.g., "Explore", "Plan")
    agent_type VARCHAR(100),                       -- Type of agent (explore, general-purpose, etc.)

    -- Agent task details
    agent_request TEXT NOT NULL,                   -- Original task given to agent
    agent_transcript_path TEXT NOT NULL,           -- Path to agent-*.jsonl file

    -- Work context (messages)
    work_context JSONB NOT NULL,                   -- Agent's conversation messages

    -- Metadata extraction
    tools_used JSONB,                              -- { "Read": 2, "WebFetch": 2, "Grep": 1 }
    files_examined TEXT[],                         -- Array of file paths agent read
    urls_fetched TEXT[],                           -- Array of URLs agent fetched

    -- Results
    result_summary TEXT,                           -- What agent reported back to parent

    -- Timing
    timestamp_start TIMESTAMP WITH TIME ZONE,
    timestamp_end TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (timestamp_end - timestamp_start))::INTEGER
    ) STORED,

    -- Embeddings for semantic search
    embedding vector(384),                         -- Same as parent snapshots (sentence-transformers/all-MiniLM-L6-v2)

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT unique_agent_work UNIQUE (agent_id, parent_session_id)
);

-- Indexes for performance
CREATE INDEX idx_agent_work_parent_snapshot ON agent_work(parent_snapshot_id);
CREATE INDEX idx_agent_work_definition ON agent_work(agent_definition_id);
CREATE INDEX idx_agent_work_request ON agent_work(request_id);
CREATE INDEX idx_agent_work_session ON agent_work(parent_session_id);
CREATE INDEX idx_agent_work_embedding ON agent_work USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_agent_work_tools ON agent_work USING gin (tools_used);
CREATE INDEX idx_agent_work_files ON agent_work USING gin (files_examined);

-- Comments for documentation
COMMENT ON TABLE agent_work IS 'Agent execution instances. Tracks what agents did, linked to both parent snapshot and agent definition.';
COMMENT ON COLUMN agent_work.agent_definition_id IS 'FK to agent_definitions - links execution to configuration blueprint';
COMMENT ON COLUMN agent_work.work_context IS 'JSONB array of agent conversation messages (role/content format)';
COMMENT ON COLUMN agent_work.tools_used IS 'JSONB object counting tool usage, e.g. {"Read": 2, "WebFetch": 1}';
COMMENT ON COLUMN agent_work.embedding IS 'Vector embedding for semantic search of agent work';


-- ============================================================================
-- ANALYTICAL VIEWS - Agent Performance & Evolution
-- ============================================================================

-- View 1: Agent configuration performance comparison
CREATE VIEW v_agent_config_performance AS
SELECT
    ad.id as definition_id,
    ad.agent_type,
    ad.version,
    ad.configuration_params,
    ad.model_used,
    ad.tools_available,
    COUNT(aw.id) as times_used,
    AVG(aw.duration_seconds)::numeric(10,1) as avg_duration_seconds,
    MIN(aw.duration_seconds) as min_duration,
    MAX(aw.duration_seconds) as max_duration,
    AVG(jsonb_array_length(aw.work_context))::numeric(10,1) as avg_messages,
    COUNT(CASE WHEN aw.result_summary IS NOT NULL THEN 1 END) as successful_runs,
    ROUND(
        COUNT(CASE WHEN aw.result_summary IS NOT NULL THEN 1 END)::NUMERIC / NULLIF(COUNT(aw.id), 0) * 100,
        2
    ) as success_rate_pct
FROM agent_definitions ad
LEFT JOIN agent_work aw ON aw.agent_definition_id = ad.id
GROUP BY ad.id
ORDER BY ad.agent_type, ad.version;

COMMENT ON VIEW v_agent_config_performance IS 'Performance comparison across agent configurations. Shows which configs are fastest and most successful.';


-- View 2: Agent evolution timeline
CREATE VIEW v_agent_evolution AS
SELECT
    ad.id,
    ad.agent_type,
    ad.version,
    ad.parent_definition_id,
    ad.configuration_params,
    ad.created_at AT TIME ZONE 'America/Los_Angeles' AS pst_created,
    COUNT(aw.id) as usage_count,
    AVG(aw.duration_seconds)::numeric(10,1) as avg_performance_seconds,
    MAX(aw.timestamp_end) AT TIME ZONE 'America/Los_Angeles' AS last_used_pst
FROM agent_definitions ad
LEFT JOIN agent_work aw ON aw.agent_definition_id = ad.id
GROUP BY ad.id
ORDER BY ad.agent_type, ad.version, ad.created_at;

COMMENT ON VIEW v_agent_evolution IS 'Track how agent types evolved over time. Shows version progression and usage patterns.';


-- View 3: Agent work with full context (joins all three tables)
CREATE VIEW v_agent_work_full AS
SELECT
    aw.id as work_id,
    aw.agent_id,
    aw.agent_request,
    aw.duration_seconds,
    aw.timestamp_start AT TIME ZONE 'America/Los_Angeles' AS pst_start,
    aw.timestamp_end AT TIME ZONE 'America/Los_Angeles' AS pst_end,
    aw.tools_used,
    aw.files_examined,
    aw.urls_fetched,

    -- Agent definition details
    ad.agent_type,
    ad.version as config_version,
    ad.configuration_params,
    ad.model_used,
    ad.tools_available,

    -- Parent snapshot details
    cs.project_path,
    cs.session_id as parent_session_id,
    cs.timestamp AT TIME ZONE 'America/Los_Angeles' AS parent_pst_time,
    cs.tags as parent_tags,
    LEFT(cs.summary, 200) as parent_summary_preview

FROM agent_work aw
LEFT JOIN agent_definitions ad ON ad.id = aw.agent_definition_id
LEFT JOIN context_snapshots cs ON cs.id = aw.parent_snapshot_id
ORDER BY aw.timestamp_start DESC;

COMMENT ON VIEW v_agent_work_full IS 'Complete agent work view with definition and parent snapshot context. Use for comprehensive agent analysis.';


-- View 4: Tool usage heatmap (which tools are used most by agents)
CREATE VIEW v_agent_tool_usage AS
SELECT
    ad.agent_type,
    ad.model_used,
    jsonb_object_keys(aw.tools_used) as tool_name,
    SUM((aw.tools_used->>jsonb_object_keys(aw.tools_used))::int) as total_uses,
    COUNT(DISTINCT aw.id) as sessions_used_in,
    AVG(aw.duration_seconds)::numeric(10,1) as avg_duration_when_used
FROM agent_work aw
JOIN agent_definitions ad ON ad.id = aw.agent_definition_id
WHERE aw.tools_used IS NOT NULL
GROUP BY ad.agent_type, ad.model_used, tool_name
ORDER BY total_uses DESC;

COMMENT ON VIEW v_agent_tool_usage IS 'Tool usage statistics. Shows which tools are most popular and their impact on duration.';


-- Success message
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Agent Tables Migration Complete';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'agent_definitions table: CREATED';
    RAISE NOTICE 'agent_work table: CREATED';
    RAISE NOTICE 'Indexes: 10 created';
    RAISE NOTICE 'Views: 4 analytical views created';
    RAISE NOTICE '  - v_agent_config_performance';
    RAISE NOTICE '  - v_agent_evolution';
    RAISE NOTICE '  - v_agent_work_full';
    RAISE NOTICE '  - v_agent_tool_usage';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Three-table architecture ready!';
    RAISE NOTICE 'Complete end-to-end agent memory enabled.';
    RAISE NOTICE '========================================';
END $$;
