-- ============================================================================
-- Claude Memory - Skills System Migration
-- Adds self-learning skills and agent recall capabilities
-- Created: 2025-12-26
-- Phase: 1 (Foundation)
-- ============================================================================

-- ============================================================================
-- TABLE 1: skills_agents
-- Purpose: Core skills registry - what skills exist and how they perform
-- ============================================================================

CREATE TABLE skills_agents (
    id SERIAL PRIMARY KEY,

    -- Identification
    agent_name VARCHAR(255) UNIQUE NOT NULL,     -- "git-commit-protocol"
    display_name VARCHAR(255),                   -- "Git Commit (Our Protocol)"
    description TEXT,
    category VARCHAR(100),                       -- "git", "database", "scaffolding", "file-ops"

    -- Scope
    project_path TEXT,                           -- NULL = global, path = project-specific
    scope VARCHAR(50) DEFAULT 'global',          -- "global", "project", "user"

    -- Performance tracking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used TIMESTAMP WITH TIME ZONE,
    use_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,

    -- Calculated success rate
    success_rate FLOAT GENERATED ALWAYS AS (
        CASE WHEN use_count > 0
        THEN (success_count::FLOAT / use_count::FLOAT) * 100
        ELSE 0
        END
    ) STORED,

    -- Efficiency metrics
    avg_time_saved_ms INTEGER,                   -- Average time saved vs manual approach
    total_time_saved_ms BIGINT DEFAULT 0,        -- Cumulative time saved

    -- Learning metadata
    learned_from_snapshot_id INTEGER REFERENCES context_snapshots(id),
    last_improved_snapshot_id INTEGER REFERENCES context_snapshots(id),
    version INTEGER DEFAULT 1,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    confidence_score FLOAT DEFAULT 0.8,          -- System confidence (0-1)

    -- Audit
    created_by VARCHAR(100) DEFAULT 'system',    -- "system", "user", "watcher"
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_scope CHECK (scope IN ('global', 'project', 'user')),
    CONSTRAINT valid_confidence CHECK (confidence_score >= 0 AND confidence_score <= 1)
);

-- Indexes for performance
CREATE INDEX idx_skills_agents_category ON skills_agents(category);
CREATE INDEX idx_skills_agents_project ON skills_agents(project_path);
CREATE INDEX idx_skills_agents_active ON skills_agents(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_skills_agents_last_used ON skills_agents(last_used DESC NULLS LAST);
CREATE INDEX idx_skills_agents_success_rate ON skills_agents(success_rate DESC);
CREATE INDEX idx_skills_agents_use_count ON skills_agents(use_count DESC);

-- Comments
COMMENT ON TABLE skills_agents IS 'Core skills registry. Each skill is a learned pattern for accomplishing specific tasks.';
COMMENT ON COLUMN skills_agents.agent_name IS 'Unique identifier for the skill (kebab-case, e.g., git-commit-protocol)';
COMMENT ON COLUMN skills_agents.project_path IS 'NULL = available everywhere, path = only available in that project';
COMMENT ON COLUMN skills_agents.success_rate IS 'Calculated field: (success_count / use_count) * 100';
COMMENT ON COLUMN skills_agents.confidence_score IS 'System confidence in this skill (0-1). Based on success rate and usage.';
COMMENT ON COLUMN skills_agents.avg_time_saved_ms IS 'Average time saved vs manual approach (estimated from performance log)';


-- ============================================================================
-- TABLE 2: skills_triggers
-- Purpose: Semantic trigger matching - when to suggest a skill
-- ============================================================================

CREATE TABLE skills_triggers (
    id SERIAL PRIMARY KEY,

    -- Linkage
    agent_id INTEGER REFERENCES skills_agents(id) ON DELETE CASCADE,

    -- Trigger definition
    trigger_phrase TEXT NOT NULL,                -- "commit these changes"
    match_type VARCHAR(50) DEFAULT 'semantic',   -- "exact", "semantic", "regex"

    -- Semantic search (for match_type='semantic')
    embedding vector(1024),                      -- Ollama mxbai-embed-large (1024 dims)
    confidence_threshold FLOAT DEFAULT 0.75,     -- Minimum similarity to match (0-1)

    -- Context requirements (optional filters)
    requires_git_repo BOOLEAN DEFAULT FALSE,
    requires_files TEXT[],                       -- Must have these files present
    context_keywords TEXT[],                     -- Boost score if these keywords present

    -- Performance tracking
    match_count INTEGER DEFAULT 0,               -- How often this trigger matched
    false_positive_count INTEGER DEFAULT 0,      -- User said "no" after match
    acceptance_rate FLOAT GENERATED ALWAYS AS (
        CASE WHEN match_count > 0
        THEN ((match_count - false_positive_count)::FLOAT / match_count::FLOAT) * 100
        ELSE 0
        END
    ) STORED,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,

    CONSTRAINT valid_match_type CHECK (match_type IN ('exact', 'semantic', 'regex')),
    CONSTRAINT valid_confidence_threshold CHECK (confidence_threshold >= 0 AND confidence_threshold <= 1)
);

-- Indexes
CREATE INDEX idx_skills_triggers_agent ON skills_triggers(agent_id);
CREATE INDEX idx_skills_triggers_match_type ON skills_triggers(match_type);
CREATE INDEX idx_skills_triggers_active ON skills_triggers(is_active) WHERE is_active = TRUE;

-- Vector similarity index (for semantic matching)
CREATE INDEX idx_skills_triggers_embedding ON skills_triggers
USING hnsw (embedding vector_cosine_ops)
WHERE match_type = 'semantic' AND is_active = TRUE;

-- Comments
COMMENT ON TABLE skills_triggers IS 'Trigger phrases that activate skills. Uses vector embeddings for semantic matching.';
COMMENT ON COLUMN skills_triggers.embedding IS 'Vector embedding (384-dim) for semantic similarity search';
COMMENT ON COLUMN skills_triggers.confidence_threshold IS 'Minimum cosine similarity (0-1) required to suggest skill';
COMMENT ON COLUMN skills_triggers.match_type IS 'How to match: exact (string match), semantic (embedding similarity), regex (pattern)';
COMMENT ON COLUMN skills_triggers.acceptance_rate IS 'Calculated: percentage of times user accepted suggestion after match';


-- ============================================================================
-- TABLE 3: skills_commands
-- Purpose: Executable definitions - HOW to execute a skill
-- ============================================================================

CREATE TABLE skills_commands (
    id SERIAL PRIMARY KEY,

    -- Linkage
    agent_id INTEGER REFERENCES skills_agents(id) ON DELETE CASCADE,
    version INTEGER DEFAULT 1,

    -- Command type
    command_type VARCHAR(50) NOT NULL,           -- "bash_script", "tool_sequence", "agent_spawn", "skill_file"

    -- Execution definitions (one populated based on command_type)
    command_definition JSONB,                    -- For tool_sequence: step-by-step instructions
    script_content TEXT,                         -- For bash_script: script stored in database
    agent_config JSONB,                          -- For agent_spawn: agent configuration

    -- Parameters (what inputs does this skill need?)
    parameters JSONB,                            -- {"database_name": {"type": "string", "required": true}}

    -- Prerequisites (what must be true before execution?)
    prerequisites JSONB,                         -- {"git_repo": true, "has_changes": true}
    validation_rules JSONB,                      -- How to check prerequisites

    -- Success/Failure detection
    success_indicators TEXT[],                   -- Strings indicating success
    failure_indicators TEXT[],                   -- Strings indicating failure

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,

    CONSTRAINT valid_command_type CHECK (
        command_type IN ('bash_script', 'tool_sequence', 'agent_spawn', 'skill_file')
    )
);

-- Indexes
CREATE INDEX idx_skills_commands_agent ON skills_commands(agent_id);
CREATE INDEX idx_skills_commands_type ON skills_commands(command_type);
CREATE INDEX idx_skills_commands_active ON skills_commands(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_skills_commands_version ON skills_commands(agent_id, version DESC);

-- Comments
COMMENT ON TABLE skills_commands IS 'Executable definitions for skills. Defines HOW to run the skill.';
COMMENT ON COLUMN skills_commands.command_definition IS 'JSONB: For tool_sequence, contains step-by-step tool calls';
COMMENT ON COLUMN skills_commands.script_content IS 'For bash_script: script content stored in database (not filesystem)';
COMMENT ON COLUMN skills_commands.agent_config IS 'For agent_spawn: {agent_type, prompt_template, parameters}';
COMMENT ON COLUMN skills_commands.parameters IS 'JSONB: Expected parameters with types, defaults, validation';
COMMENT ON COLUMN skills_commands.prerequisites IS 'JSONB: Conditions that must be met before execution';


-- ============================================================================
-- TABLE 4: skills_performance_log
-- Purpose: Execution tracking and learning from outcomes
-- ============================================================================

CREATE TABLE skills_performance_log (
    id SERIAL PRIMARY KEY,

    -- Linkage
    agent_id INTEGER REFERENCES skills_agents(id),
    snapshot_id INTEGER REFERENCES context_snapshots(id),

    -- Execution context
    user_request TEXT,                           -- Original user request
    matched_trigger_id INTEGER REFERENCES skills_triggers(id),
    similarity_score FLOAT,                      -- Trigger match confidence (0-1)

    -- Execution details
    outcome VARCHAR(50),                         -- "success", "user_corrected", "failed", "user_rejected", "timeout"
    execution_time_ms INTEGER,
    time_saved_ms INTEGER,                       -- Estimated time saved vs manual
    error_message TEXT,                          -- If failed

    -- Learning signals
    user_feedback TEXT,                          -- User corrections or comments
    was_suggestion_accepted BOOLEAN,             -- Did user approve the suggestion?

    -- Evolution tracking
    before_definition JSONB,                     -- Skill definition before execution
    after_definition JSONB,                      -- If skill was updated based on feedback

    -- Metadata
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_id VARCHAR(255),
    project_path TEXT,

    CONSTRAINT valid_outcome CHECK (
        outcome IN ('success', 'user_corrected', 'failed', 'user_rejected', 'timeout')
    )
);

-- Indexes
CREATE INDEX idx_skills_perf_agent ON skills_performance_log(agent_id);
CREATE INDEX idx_skills_perf_outcome ON skills_performance_log(outcome);
CREATE INDEX idx_skills_perf_executed ON skills_performance_log(executed_at DESC);
CREATE INDEX idx_skills_perf_snapshot ON skills_performance_log(snapshot_id);
CREATE INDEX idx_skills_perf_session ON skills_performance_log(session_id);
CREATE INDEX idx_skills_perf_success ON skills_performance_log(outcome)
    WHERE outcome = 'success';

-- Comments
COMMENT ON TABLE skills_performance_log IS 'Execution log for skills. Enables learning, evolution, and performance tracking.';
COMMENT ON COLUMN skills_performance_log.outcome IS 'Result of execution: success, user_corrected, failed, user_rejected, timeout';
COMMENT ON COLUMN skills_performance_log.user_feedback IS 'User corrections or comments that can improve the skill';
COMMENT ON COLUMN skills_performance_log.was_suggestion_accepted IS 'TRUE if user approved using skill, FALSE if rejected';
COMMENT ON COLUMN skills_performance_log.time_saved_ms IS 'Estimated time saved vs manual approach';


-- ============================================================================
-- TABLE 5: skills_patterns
-- Purpose: Detected patterns from conversations - candidates for new skills
-- ============================================================================

CREATE TABLE skills_patterns (
    id SERIAL PRIMARY KEY,

    -- Pattern identification
    pattern_name VARCHAR(255),                   -- "git-commit-sequence"
    pattern_type VARCHAR(100),                   -- "tool_sequence", "user_correction", "iteration_loop"

    -- Detection criteria
    detection_rules JSONB,                       -- What makes this pattern (rules for detection)
    signature_hash VARCHAR(64),                  -- Hash for deduplication

    -- Occurrence tracking
    occurrences INTEGER DEFAULT 1,
    first_seen_snapshot_id INTEGER REFERENCES context_snapshots(id),
    last_seen_snapshot_id INTEGER REFERENCES context_snapshots(id),
    seen_in_projects TEXT[],                     -- Which projects had this pattern

    -- Skill suggestion
    suggested_agent_id INTEGER REFERENCES skills_agents(id),  -- If skill was created
    confidence_score FLOAT,                      -- How confident this should be a skill (0-1)
    status VARCHAR(50) DEFAULT 'candidate',      -- "candidate", "approved", "rejected", "created"

    -- Priority (for sorting candidates)
    priority_score FLOAT GENERATED ALWAYS AS (
        occurrences::FLOAT * confidence_score * COALESCE(array_length(seen_in_projects, 1), 1)::FLOAT
    ) STORED,

    -- User interaction
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_pattern_type CHECK (
        pattern_type IN ('tool_sequence', 'user_correction', 'iteration_loop', 'system_reminder', 'other')
    ),
    CONSTRAINT valid_pattern_status CHECK (
        status IN ('candidate', 'approved', 'rejected', 'created')
    ),
    CONSTRAINT valid_confidence CHECK (confidence_score >= 0 AND confidence_score <= 1)
);

-- Indexes
CREATE INDEX idx_skills_patterns_type ON skills_patterns(pattern_type);
CREATE INDEX idx_skills_patterns_status ON skills_patterns(status);
CREATE INDEX idx_skills_patterns_confidence ON skills_patterns(confidence_score DESC);
CREATE INDEX idx_skills_patterns_occurrences ON skills_patterns(occurrences DESC);
CREATE INDEX idx_skills_patterns_priority ON skills_patterns(priority_score DESC);
CREATE INDEX idx_skills_patterns_hash ON skills_patterns(signature_hash);

-- Comments
COMMENT ON TABLE skills_patterns IS 'Detected patterns from snapshots. Candidates for creating new skills.';
COMMENT ON COLUMN skills_patterns.detection_rules IS 'JSONB: Rules that define what constitutes this pattern';
COMMENT ON COLUMN skills_patterns.confidence_score IS 'Based on: occurrence count, consistency, user corrections (0-1)';
COMMENT ON COLUMN skills_patterns.priority_score IS 'Calculated: occurrences × confidence × project_count. Used for ranking.';
COMMENT ON COLUMN skills_patterns.signature_hash IS 'SHA256 hash for deduplication of similar patterns';


-- ============================================================================
-- ANALYTICAL VIEWS
-- ============================================================================

-- View 1: Skills Dashboard (high-level overview)
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
    sa.last_used AS last_used_pst,
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

COMMENT ON VIEW v_skills_dashboard IS 'High-level overview of all active skills with performance and usage metrics';


-- View 2: Skill Candidates (detected patterns awaiting review)
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
    sp.created_at AS created_pst,
    sp.reviewed_at AS reviewed_pst,

    -- Confidence level
    CASE
        WHEN sp.confidence_score >= 0.9 THEN 'high'
        WHEN sp.confidence_score >= 0.7 THEN 'medium'
        ELSE 'low'
    END AS confidence_level

FROM skills_patterns sp
WHERE sp.status = 'candidate'
ORDER BY sp.priority_score DESC, sp.created_at DESC;

COMMENT ON VIEW v_skill_candidates IS 'Detected patterns ranked by priority, awaiting user review for skill creation';


-- View 3: Skills by Category (organizational view)
CREATE VIEW v_skills_by_category AS
SELECT
    category,
    COUNT(*) AS skill_count,
    AVG(success_rate)::NUMERIC(5,2) AS avg_success_rate,
    SUM(use_count) AS total_uses,
    SUM(total_time_saved_ms) / 1000 / 60 AS total_time_saved_minutes,

    -- Top skill in category
    (
        SELECT agent_name
        FROM skills_agents sa2
        WHERE sa2.category = sa.category AND sa2.is_active = TRUE
        ORDER BY use_count DESC, success_rate DESC
        LIMIT 1
    ) AS most_used_skill,

    -- Best performing skill
    (
        SELECT agent_name
        FROM skills_agents sa3
        WHERE sa3.category = sa.category
          AND sa3.is_active = TRUE
          AND sa3.use_count >= 5  -- Minimum usage for reliability
        ORDER BY success_rate DESC, use_count DESC
        LIMIT 1
    ) AS best_performing_skill

FROM skills_agents sa
WHERE is_active = TRUE
GROUP BY category
ORDER BY total_uses DESC, avg_success_rate DESC;

COMMENT ON VIEW v_skills_by_category IS 'Category-level statistics showing skill distribution and performance';


-- View 4: Skill Performance Trends (recent activity)
CREATE VIEW v_skill_performance_trends AS
SELECT
    sa.agent_name,
    sa.display_name,
    sa.category,

    -- Overall stats
    sa.use_count AS total_uses,
    sa.success_rate AS overall_success_rate,

    -- Last 7 days
    COUNT(spl.id) FILTER (WHERE spl.executed_at > NOW() - INTERVAL '7 days') AS uses_last_7d,
    COUNT(spl.id) FILTER (
        WHERE spl.outcome = 'success' AND spl.executed_at > NOW() - INTERVAL '7 days'
    ) AS successes_last_7d,
    ROUND(
        CASE WHEN COUNT(spl.id) FILTER (WHERE spl.executed_at > NOW() - INTERVAL '7 days') > 0
        THEN (
            COUNT(spl.id) FILTER (WHERE spl.outcome = 'success' AND spl.executed_at > NOW() - INTERVAL '7 days')::NUMERIC /
            COUNT(spl.id) FILTER (WHERE spl.executed_at > NOW() - INTERVAL '7 days')::NUMERIC * 100
        )
        ELSE 0
        END, 2
    ) AS success_rate_last_7d,

    -- Last 30 days
    COUNT(spl.id) FILTER (WHERE spl.executed_at > NOW() - INTERVAL '30 days') AS uses_last_30d,

    -- Trend indicator
    CASE
        WHEN COUNT(spl.id) FILTER (WHERE spl.executed_at > NOW() - INTERVAL '7 days') >
             COUNT(spl.id) FILTER (WHERE spl.executed_at > NOW() - INTERVAL '14 days' AND spl.executed_at <= NOW() - INTERVAL '7 days')
        THEN 'increasing'
        WHEN COUNT(spl.id) FILTER (WHERE spl.executed_at > NOW() - INTERVAL '7 days') <
             COUNT(spl.id) FILTER (WHERE spl.executed_at > NOW() - INTERVAL '14 days' AND spl.executed_at <= NOW() - INTERVAL '7 days')
        THEN 'decreasing'
        ELSE 'stable'
    END AS usage_trend

FROM skills_agents sa
LEFT JOIN skills_performance_log spl ON spl.agent_id = sa.id
WHERE sa.is_active = TRUE
GROUP BY sa.id
HAVING COUNT(spl.id) > 0  -- Only show skills that have been used
ORDER BY uses_last_7d DESC;

COMMENT ON VIEW v_skill_performance_trends IS 'Recent performance trends showing skill usage patterns over time';


-- ============================================================================
-- TRIGGERS - Auto-update timestamps
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for skills_agents
CREATE TRIGGER update_skills_agents_modtime
BEFORE UPDATE ON skills_agents
FOR EACH ROW
EXECUTE FUNCTION update_modified_column();


-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Skills System Migration Complete';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Tables Created: 5';
    RAISE NOTICE '  - skills_agents (core registry)';
    RAISE NOTICE '  - skills_triggers (semantic matching)';
    RAISE NOTICE '  - skills_commands (execution definitions)';
    RAISE NOTICE '  - skills_performance_log (learning)';
    RAISE NOTICE '  - skills_patterns (pattern detection)';
    RAISE NOTICE '';
    RAISE NOTICE 'Views Created: 4';
    RAISE NOTICE '  - v_skills_dashboard';
    RAISE NOTICE '  - v_skill_candidates';
    RAISE NOTICE '  - v_skills_by_category';
    RAISE NOTICE '  - v_skill_performance_trends';
    RAISE NOTICE '';
    RAISE NOTICE 'Indexes: 31 created';
    RAISE NOTICE 'Triggers: 1 created (auto-update timestamps)';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Phase 1: Foundation - READY';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Next Steps:';
    RAISE NOTICE '  1. Run migration: psql -f add-skills-tables.sql';
    RAISE NOTICE '  2. Implement /mem-skills-create command';
    RAISE NOTICE '  3. Implement /mem-skills list command';
    RAISE NOTICE '  4. See docs/SKILLS-SYSTEM-ARCHITECTURE.md';
    RAISE NOTICE '========================================';
END $$;
