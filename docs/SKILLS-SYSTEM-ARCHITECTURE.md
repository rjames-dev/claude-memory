# Skills System Architecture

**Feature:** Self-Learning Skills and Agent Recall System
**Status:** Planning Phase
**Created:** 2025-12-26
**Priority:** HIGH - Transformative addition to claude-memory

---

## Table of Contents

1. [Vision](#vision)
2. [System Overview](#system-overview)
3. [Database Architecture](#database-architecture)
4. [Pattern Detection Engine](#pattern-detection-engine)
5. [Execution Framework](#execution-framework)
6. [User Experience](#user-experience)
7. [Implementation Roadmap](#implementation-roadmap)
8. [Integration Points](#integration-points)

---

## Vision

Transform claude-memory from a **passive archive** into an **active learning system** that:

- **Learns** from repetitive patterns in conversations
- **Suggests** skills when appropriate tasks are detected
- **Executes** proven approaches with user approval
- **Evolves** skills based on user feedback
- **Recalls** the right tool for the right job

### The Hybrid Model

```
┌─────────────────────────────────────────────────────────────┐
│  User Request: "Commit these changes"                       │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │  Skills System Check          │
    │  - Semantic search triggers   │
    │  - Find: git-commit-protocol  │
    │  - Confidence: 95%            │
    └───────────┬───────────────────┘
                │
                ▼
    ┌───────────────────────────────┐
    │  User Approval                │
    │  "Should I use this skill?"   │
    │  [Yes] [No] [Show steps]      │
    └───────────┬───────────────────┘
                │
                ▼ [User: Yes]
    ┌───────────────────────────────┐
    │  Execute Skill                │
    │  - Git status/diff            │
    │  - Draft message              │
    │  - Commit with heredoc        │
    │  - Verify success             │
    └───────────┬───────────────────┘
                │
                ▼
    ┌───────────────────────────────┐
    │  Log Performance              │
    │  - Time saved: 45 seconds     │
    │  - Outcome: success           │
    │  - Update stats               │
    └───────────────────────────────┘
```

**Key Principle:** Speed of automation + Safety of collaboration

---

## System Overview

### Three Core Components

#### 1. **Watcher** (Pattern Detection)
- Runs during snapshot capture
- Detects repetitive tool sequences
- Identifies user corrections
- Finds iteration loops (inefficiency signals)
- Generates skill candidates

#### 2. **Skills Library** (Storage & Retrieval)
- Stores skill definitions (what to do)
- Semantic trigger matching (when to use)
- Performance tracking (how well it works)
- Evolution tracking (version history)

#### 3. **Executor** (Execution Framework)
- Runs skills with user approval
- Logs execution results
- Learns from feedback
- Updates skill definitions

### Data Flow

```
┌──────────────────┐
│  Conversation    │
│  (Live Session)  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐         ┌──────────────────┐
│  Watcher Agent   │────────▶│  Skill           │
│  (Analyze)       │         │  Candidates      │
└────────┬─────────┘         └──────────────────┘
         │                            │
         │ Detect patterns            │ User approves
         │ (tool sequences,           │
         │  corrections,              │
         │  iterations)               ▼
         │                   ┌──────────────────┐
         │                   │  Skills Library  │
         │                   │  (PostgreSQL)    │
         │                   └────────┬─────────┘
         │                            │
         ▼                            │
┌──────────────────┐                 │
│  Snapshot        │                 │
│  Capture         │                 │
│  (claude-memory) │                 │
└──────────────────┘                 │
                                     │
         ┌───────────────────────────┘
         │ Next session
         ▼
┌──────────────────┐
│  User Request    │
│  "commit..."     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐         ┌──────────────────┐
│  Semantic Search │────────▶│  Execute Skill   │
│  (Find skill)    │         │  (With approval) │
└──────────────────┘         └────────┬─────────┘
                                      │
                                      ▼
                             ┌──────────────────┐
                             │  Performance Log │
                             │  (Learn & Adapt) │
                             └──────────────────┘
```

---

## Database Architecture

**Database Location:** Skills system uses the **same PostgreSQL database** as claude-memory. All skills tables coexist with existing context_snapshots, agent_work, and other claude-memory tables.

**Benefits of shared database:**
- Simplified deployment (no second database needed)
- Direct foreign key relationships to context_snapshots
- Single backup/restore process
- Consistent connection pooling
- Easier cross-table analytics

### Tables Overview

#### Core Tables
1. **skills_agents** - Skill definitions and metadata
2. **skills_triggers** - Semantic trigger phrases with embeddings
3. **skills_commands** - Executable definitions (bash, tool sequences, agents)
4. **skills_performance_log** - Execution tracking and learning
5. **skills_patterns** - Detected patterns from snapshots

#### Supporting Tables
6. **skills_categories** - Skill organization
7. **skills_dependencies** - Skill prerequisites and relationships

### Schema Details

#### 1. skills_agents

```sql
CREATE TABLE skills_agents (
    id SERIAL PRIMARY KEY,

    -- Identification
    agent_name VARCHAR(255) UNIQUE NOT NULL,     -- "git-commit-protocol"
    display_name VARCHAR(255),                   -- "Git Commit (Our Protocol)"
    description TEXT,
    category VARCHAR(100),                       -- "git", "database", "scaffolding"

    -- Scope
    project_path TEXT,                           -- NULL = global, path = project-specific
    scope VARCHAR(50) DEFAULT 'global',          -- "global", "project", "user"

    -- Performance tracking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used TIMESTAMP WITH TIME ZONE,
    use_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    success_rate FLOAT GENERATED ALWAYS AS (
        CASE WHEN use_count > 0
        THEN (success_count::FLOAT / use_count::FLOAT) * 100
        ELSE 0
        END
    ) STORED,

    -- Efficiency metrics
    avg_time_saved_ms INTEGER,                   -- vs manual approach
    total_time_saved_ms BIGINT DEFAULT 0,

    -- Learning metadata
    learned_from_snapshot_id INTEGER REFERENCES context_snapshots(id),
    last_improved_snapshot_id INTEGER REFERENCES context_snapshots(id),
    version INTEGER DEFAULT 1,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    confidence_score FLOAT DEFAULT 0.8,          -- How confident we are in this skill

    -- Audit
    created_by VARCHAR(100) DEFAULT 'system',    -- "system", "user", "watcher"
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_skills_agents_category ON skills_agents(category);
CREATE INDEX idx_skills_agents_project ON skills_agents(project_path);
CREATE INDEX idx_skills_agents_active ON skills_agents(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_skills_agents_last_used ON skills_agents(last_used DESC);
CREATE INDEX idx_skills_agents_success_rate ON skills_agents(success_rate DESC);

-- Comments
COMMENT ON TABLE skills_agents IS 'Core skills registry. Each skill is a learned pattern for accomplishing a specific task.';
COMMENT ON COLUMN skills_agents.project_path IS 'NULL = available everywhere, path = only in that project';
COMMENT ON COLUMN skills_agents.confidence_score IS 'System confidence in this skill (0-1). Based on success rate and use count.';
COMMENT ON COLUMN skills_agents.avg_time_saved_ms IS 'Average time saved vs manual approach (estimated from historical data)';
```

#### 2. skills_triggers

```sql
CREATE TABLE skills_triggers (
    id SERIAL PRIMARY KEY,

    -- Linkage
    agent_id INTEGER REFERENCES skills_agents(id) ON DELETE CASCADE,

    -- Trigger definition
    trigger_phrase TEXT NOT NULL,                -- "commit these changes"
    match_type VARCHAR(50) DEFAULT 'semantic',   -- "exact", "semantic", "regex"

    -- Semantic search
    embedding vector(384),                       -- For semantic matching (same as snapshots)
    confidence_threshold FLOAT DEFAULT 0.75,     -- Minimum similarity score to match

    -- Context requirements (optional filters)
    requires_git_repo BOOLEAN DEFAULT FALSE,
    requires_files TEXT[],                       -- Must have these files present
    context_keywords TEXT[],                     -- Boost score if these present

    -- Performance
    match_count INTEGER DEFAULT 0,               -- How often this trigger matched
    false_positive_count INTEGER DEFAULT 0,      -- User said "no" after match

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_skills_triggers_agent ON skills_triggers(agent_id);
CREATE INDEX idx_skills_triggers_embedding ON skills_triggers
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_skills_triggers_match_type ON skills_triggers(match_type);

-- Comments
COMMENT ON TABLE skills_triggers IS 'Trigger phrases that activate skills. Uses embeddings for semantic matching.';
COMMENT ON COLUMN skills_triggers.embedding IS 'Vector embedding of trigger phrase for semantic similarity search';
COMMENT ON COLUMN skills_triggers.confidence_threshold IS 'Minimum cosine similarity (0-1) required to suggest this skill';
```

#### 3. skills_commands

```sql
CREATE TABLE skills_commands (
    id SERIAL PRIMARY KEY,

    -- Linkage
    agent_id INTEGER REFERENCES skills_agents(id) ON DELETE CASCADE,
    version INTEGER DEFAULT 1,

    -- Command type
    command_type VARCHAR(50) NOT NULL,           -- "bash_script", "tool_sequence", "agent_spawn", "skill_file"

    -- Execution definitions (one will be populated based on command_type)
    command_definition JSONB,                    -- For tool sequences
    script_content TEXT,                         -- For bash scripts (stored in database)
    agent_config JSONB,                          -- For spawning agents

    -- Parameters
    parameters JSONB,                            -- Expected parameters with types and defaults

    -- Prerequisites
    prerequisites JSONB,                         -- {"git_repo": true, "has_changes": true}
    validation_rules JSONB,                      -- How to verify prerequisites

    -- Success criteria
    success_indicators TEXT[],                   -- Strings that indicate success
    failure_indicators TEXT[],                   -- Strings that indicate failure

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

-- Comments
COMMENT ON TABLE skills_commands IS 'Executable definitions for skills. Defines HOW to execute the skill.';
COMMENT ON COLUMN skills_commands.command_definition IS 'JSONB containing step-by-step tool sequence for complex skills';
COMMENT ON COLUMN skills_commands.agent_config IS 'JSONB for spawning specialized agents (agent_type, prompt template, etc.)';
COMMENT ON COLUMN skills_commands.prerequisites IS 'JSONB of conditions that must be met before execution';
```

#### 4. skills_performance_log

```sql
CREATE TABLE skills_performance_log (
    id SERIAL PRIMARY KEY,

    -- Linkage
    agent_id INTEGER REFERENCES skills_agents(id),
    snapshot_id INTEGER REFERENCES context_snapshots(id),

    -- Execution context
    user_request TEXT,                           -- Original user request
    matched_trigger_id INTEGER REFERENCES skills_triggers(id),
    similarity_score FLOAT,                      -- Trigger match confidence

    -- Execution details
    outcome VARCHAR(50),                         -- "success", "user_corrected", "failed", "user_rejected"
    execution_time_ms INTEGER,
    error_message TEXT,                          -- If failed

    -- Learning signals
    user_feedback TEXT,                          -- User corrections or comments
    was_suggestion_accepted BOOLEAN,             -- Did user approve using skill?

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

-- Comments
COMMENT ON TABLE skills_performance_log IS 'Execution log for skills. Enables learning and evolution.';
COMMENT ON COLUMN skills_performance_log.outcome IS 'Result of execution. Used to calculate success rate.';
COMMENT ON COLUMN skills_performance_log.user_feedback IS 'User corrections that can improve the skill';
```

#### 5. skills_patterns

```sql
CREATE TABLE skills_patterns (
    id SERIAL PRIMARY KEY,

    -- Pattern identification
    pattern_name VARCHAR(255),                   -- "git-commit-sequence"
    pattern_type VARCHAR(100),                   -- "tool_sequence", "user_correction", "iteration_loop"

    -- Detection criteria
    detection_rules JSONB,                       -- What makes this pattern
    signature_hash VARCHAR(64),                  -- Hash of pattern for deduplication

    -- Occurrence tracking
    occurrences INTEGER DEFAULT 1,
    first_seen_snapshot_id INTEGER REFERENCES context_snapshots(id),
    last_seen_snapshot_id INTEGER REFERENCES context_snapshots(id),
    seen_in_projects TEXT[],                     -- Which projects had this pattern

    -- Skill suggestion
    suggested_agent_id INTEGER REFERENCES skills_agents(id),
    confidence_score FLOAT,                      -- How confident we are this should be a skill
    status VARCHAR(50) DEFAULT 'candidate',      -- "candidate", "approved", "rejected", "created"

    -- User interaction
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_pattern_status CHECK (
        status IN ('candidate', 'approved', 'rejected', 'created')
    )
);

-- Indexes
CREATE INDEX idx_skills_patterns_type ON skills_patterns(pattern_type);
CREATE INDEX idx_skills_patterns_status ON skills_patterns(status);
CREATE INDEX idx_skills_patterns_confidence ON skills_patterns(confidence_score DESC);
CREATE INDEX idx_skills_patterns_occurrences ON skills_patterns(occurrences DESC);

-- Comments
COMMENT ON TABLE skills_patterns IS 'Detected patterns from snapshots. Candidates for new skills.';
COMMENT ON COLUMN skills_patterns.detection_rules IS 'JSONB defining what constitutes this pattern';
COMMENT ON COLUMN skills_patterns.confidence_score IS 'Based on: occurrence count, consistency, user corrections';
```

### Analytical Views

#### v_skills_dashboard

```sql
CREATE VIEW v_skills_dashboard AS
SELECT
    sa.agent_name,
    sa.display_name,
    sa.category,
    sa.scope,
    sa.use_count,
    sa.success_rate,
    sa.avg_time_saved_ms,
    sa.total_time_saved_ms,
    sa.last_used AT TIME ZONE 'America/Los_Angeles' AS last_used_pst,
    sa.version,
    sa.confidence_score,

    -- Trigger count
    COUNT(DISTINCT st.id) AS trigger_count,

    -- Recent performance
    COUNT(spl.id) FILTER (WHERE spl.executed_at > NOW() - INTERVAL '7 days') AS uses_last_7_days,
    COUNT(spl.id) FILTER (WHERE spl.outcome = 'success' AND spl.executed_at > NOW() - INTERVAL '7 days') AS successes_last_7_days,

    -- Trend
    CASE
        WHEN sa.use_count >= 10 AND sa.success_rate >= 90 THEN 'stable'
        WHEN sa.use_count < 5 THEN 'new'
        WHEN sa.success_rate < 70 THEN 'needs_improvement'
        ELSE 'developing'
    END AS status_category

FROM skills_agents sa
LEFT JOIN skills_triggers st ON st.agent_id = sa.id
LEFT JOIN skills_performance_log spl ON spl.agent_id = sa.id
WHERE sa.is_active = TRUE
GROUP BY sa.id
ORDER BY sa.use_count DESC, sa.success_rate DESC;

COMMENT ON VIEW v_skills_dashboard IS 'High-level overview of all active skills with performance metrics';
```

#### v_skill_candidates

```sql
CREATE VIEW v_skill_candidates AS
SELECT
    sp.id,
    sp.pattern_name,
    sp.pattern_type,
    sp.occurrences,
    sp.confidence_score,
    sp.status,
    sp.first_seen_snapshot_id,
    sp.last_seen_snapshot_id,

    -- Time span
    (
        SELECT cs2.timestamp
        FROM context_snapshots cs2
        WHERE cs2.id = sp.last_seen_snapshot_id
    ) - (
        SELECT cs1.timestamp
        FROM context_snapshots cs1
        WHERE cs1.id = sp.first_seen_snapshot_id
    ) AS pattern_timespan,

    -- Projects affected
    array_length(sp.seen_in_projects, 1) AS project_count,
    sp.seen_in_projects,

    -- Sorting priority
    (sp.occurrences * sp.confidence_score * array_length(sp.seen_in_projects, 1)) AS priority_score

FROM skills_patterns sp
WHERE sp.status = 'candidate'
ORDER BY priority_score DESC;

COMMENT ON VIEW v_skill_candidates IS 'Detected patterns ranked by priority for skill creation';
```

#### v_skills_by_category

```sql
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
        WHERE sa2.category = sa.category
        ORDER BY use_count DESC
        LIMIT 1
    ) AS most_used_skill

FROM skills_agents sa
WHERE is_active = TRUE
GROUP BY category
ORDER BY total_uses DESC;

COMMENT ON VIEW v_skills_by_category IS 'Category-level statistics for skill organization';
```

---

## Pattern Detection Engine

### Detection Algorithms

#### 1. Tool Sequence Detection

**What it detects:** Repetitive sequences of tool calls

```python
def detect_tool_sequences(snapshot):
    """
    Analyze message history for repetitive tool call patterns

    Returns patterns like:
    {
        "sequence": ["Bash:git status", "Bash:git diff", "Bash:git log", "Bash:git commit"],
        "occurrences": 3,
        "contexts": [...]
    }
    """
    tool_calls = extract_tool_calls(snapshot['messages'])

    # Find sequences that appear multiple times
    sequences = find_ngrams(tool_calls, min_length=2, max_length=6)

    # Filter for repeated patterns (≥ 2 occurrences)
    repeated = [seq for seq in sequences if seq.count >= 2]

    return repeated
```

**Example pattern:**
```json
{
  "pattern_name": "git-commit-workflow",
  "pattern_type": "tool_sequence",
  "detection_rules": {
    "sequence": [
      {"tool": "Bash", "command_pattern": "git status"},
      {"tool": "Bash", "command_pattern": "git diff"},
      {"tool": "Bash", "command_pattern": "git log"},
      {"tool": "Bash", "command_pattern": "git commit"}
    ],
    "min_occurrences": 2,
    "window": "single_snapshot"
  },
  "occurrences": 3,
  "confidence_score": 0.9
}
```

#### 2. User Correction Detection

**What it detects:** User feedback that clarifies "the right way"

```python
def detect_user_corrections(snapshot):
    """
    Identify user messages that correct Claude's approach

    Signals:
    - "No, use..." / "Actually, ..." / "Instead, ..."
    - User provides alternative command after failed attempt
    - System reminders triggered multiple times
    """
    corrections = []

    for i, msg in enumerate(snapshot['messages']):
        if msg['role'] == 'user':
            # Check for correction language
            if has_correction_language(msg['content']):
                # Get context: what was Claude trying before?
                prev_context = get_previous_assistant_actions(snapshot['messages'][:i])

                corrections.append({
                    "user_correction": msg['content'],
                    "previous_attempt": prev_context,
                    "correction_type": classify_correction(msg)
                })

    return corrections
```

**Example pattern:**
```json
{
  "pattern_name": "heredoc-commit-message",
  "pattern_type": "user_correction",
  "detection_rules": {
    "correction_phrase": "use heredoc format for commit messages",
    "context": "git commit",
    "correction_count": 2
  },
  "confidence_score": 0.95
}
```

#### 3. Iteration Loop Detection

**What it detects:** Claude trying multiple approaches (inefficiency signal)

```python
def detect_iteration_loops(snapshot):
    """
    Find cases where Claude tried multiple approaches for same task

    Signals:
    - Multiple tool calls with similar intent but different parameters
    - Error → retry → error → retry pattern
    - Comments like "Let me try a different approach"
    """
    iterations = []

    # Group tool calls by intent
    tool_groups = group_by_intent(snapshot['messages'])

    for intent, calls in tool_groups.items():
        if len(calls) >= 3:  # 3+ attempts = pattern
            iterations.append({
                "intent": intent,
                "attempts": calls,
                "final_success": calls[-1].get('success', False)
            })

    return iterations
```

**Example pattern:**
```json
{
  "pattern_name": "codebase-search-exploration",
  "pattern_type": "iteration_loop",
  "detection_rules": {
    "task": "search codebase for error handling",
    "attempts": [
      {"tool": "Grep", "failed": true},
      {"tool": "Glob", "partial": true},
      {"tool": "Read", "multiple": true}
    ],
    "should_have_used": "Task with Explore agent"
  },
  "confidence_score": 0.85
}
```

### Pattern Scoring Algorithm

```python
def calculate_confidence_score(pattern):
    """
    Score pattern based on multiple factors

    Factors:
    - Occurrence count (more = better)
    - Consistency (same context each time)
    - User involvement (corrections increase confidence)
    - Cross-project (appears in multiple projects)
    - Success rate (if already executed manually)
    """
    base_score = min(pattern['occurrences'] / 10, 1.0)  # Cap at 10 occurrences

    # Boost for user corrections (strong signal)
    if pattern['type'] == 'user_correction':
        base_score *= 1.5

    # Boost for cross-project patterns
    if len(pattern['seen_in_projects']) > 1:
        base_score *= 1.2

    # Boost for consistency
    consistency = calculate_consistency(pattern)
    base_score *= consistency

    # Cap at 1.0
    return min(base_score, 1.0)
```

---

## Execution Framework

### Skill Execution Types

#### 1. Bash Script

```json
{
  "command_type": "bash_script",
  "script_content": "#!/bin/bash\npsql -d \"$1\" -c 'SELECT version();'",
  "parameters": {
    "database_name": {"type": "string", "required": true}
  },
  "prerequisites": {
    "docker_running": true
  }
}
```

**Note:** Script content is stored directly in the database (not on filesystem) for portability and easier export/import.

**Execution:**
```python
def execute_bash_skill(skill, args):
    # Validate prerequisites
    if not check_prerequisites(skill['prerequisites']):
        return {"error": "Prerequisites not met"}

    # Write script to temp file (for execution only)
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
        f.write(skill['script_content'])
        temp_script_path = f.name

    # Make executable
    os.chmod(temp_script_path, 0o755)

    # Build command with parameters
    cmd = f"{temp_script_path} {args['database_name']}"

    # Execute via Bash tool
    result = bash_tool.execute(cmd)

    # Cleanup temp file
    os.unlink(temp_script_path)

    # Validate success
    if any(indicator in result for indicator in skill['success_indicators']):
        return {"outcome": "success", "result": result}

    return {"outcome": "failed", "result": result}
```

#### 2. Tool Sequence

```json
{
  "command_type": "tool_sequence",
  "command_definition": {
    "steps": [
      {
        "step": 1,
        "tools": [
          {"tool": "Bash", "command": "git status"},
          {"tool": "Bash", "command": "git diff"}
        ],
        "parallel": true
      },
      {
        "step": 2,
        "action": "analyze_and_draft_message"
      },
      {
        "step": 3,
        "tools": [
          {"tool": "Bash", "command": "git commit -m \"$(cat <<'EOF'\\n{message}\\nEOF\\n)\""}
        ]
      }
    ]
  }
}
```

**Execution:**
```python
def execute_tool_sequence(skill, context):
    results = []

    for step in skill['command_definition']['steps']:
        if step.get('parallel'):
            # Execute tools in parallel
            step_results = parallel_execute(step['tools'])
        else:
            # Execute sequentially
            step_results = sequential_execute(step['tools'])

        results.append(step_results)

        # Check if we should continue
        if not validate_step_success(step_results):
            return {"outcome": "failed", "failed_at_step": step['step']}

    return {"outcome": "success", "results": results}
```

#### 3. Agent Spawn

```json
{
  "command_type": "agent_spawn",
  "agent_config": {
    "agent_type": "general-purpose",
    "prompt_template": "Create feature module '{feature_name}' following our established pattern...",
    "parameters": ["feature_name", "route_name"],
    "run_in_background": false
  }
}
```

**Execution:**
```python
def execute_agent_spawn(skill, args):
    # Build prompt from template
    prompt = skill['agent_config']['prompt_template'].format(**args)

    # Spawn agent via Task tool
    result = task_tool.spawn(
        agent_type=skill['agent_config']['agent_type'],
        prompt=prompt,
        run_in_background=skill['agent_config'].get('run_in_background', False)
    )

    return {"outcome": "success", "agent_id": result.agent_id}
```

### User Approval Flow with Trust Levels

**Trust Model:**
- **Low Trust** (new/unproven skills): Always ask user for confirmation
- **High Trust** (proven skills): Auto-execute after meeting criteria

**Trust Progression:**
```
New Skill → Low Trust (0-9 successful uses) → High Trust (10+ successful uses with 90%+ success rate)
```

**Approval Logic:**
```python
def suggest_skill_to_user(user_request, matched_skill):
    """
    Present skill to user for approval, or auto-execute if high trust
    """
    # High trust criteria
    is_high_trust = (
        matched_skill['success_count'] >= 10 and
        matched_skill['success_rate'] >= 90 and
        matched_skill['confidence_score'] >= 0.8
    )

    if is_high_trust:
        # Auto-execute trusted skills (notify user)
        notify_user(f"✓ Using skill: {matched_skill['display_name']}")
        return execute_skill(matched_skill)

    # Low trust - require explicit approval
    message = f"""
    🔍 Found skill: '{matched_skill['display_name']}'
       Used {matched_skill['use_count']} times, {matched_skill['success_rate']:.0f}% success rate
       Trust Level: {'🟢 High' if is_high_trust else '🟡 Low (requires approval)'}

       This skill will:
       {format_skill_steps(matched_skill)}

       Should I use this skill?
       [Yes, use it] [No, manual approach] [Show me the steps first]
    """

    response = ask_user_question(message)

    if response == "Yes, use it":
        return execute_skill(matched_skill)
    elif response == "Show me the steps first":
        show_detailed_steps(matched_skill)
        return suggest_skill_to_user(user_request, matched_skill)  # Ask again
    else:
        # User declined - log for learning
        log_skill_rejection(matched_skill, user_request)
        return None  # Proceed with manual approach
```

**Trust Level Indicators:**
- 🟢 **High Trust**: Auto-execute (10+ successes, 90%+ success rate)
- 🟡 **Low Trust**: Requires approval (new or inconsistent)
- 🔴 **Degraded**: Previously high trust, now failing (drops below 80% success rate)

**User Can Override:**
- Mark skill as "always ask" (disable auto-execute even if high trust)
- Mark skill as "always execute" (enable auto-execute even if low trust)
- Disable skill entirely

---

## User Experience

### CLI Commands

#### /mem-skills

List all available skills

```bash
$ /mem-skills

📚 Skills Library (23 skills)

Git (5 skills)
  git-commit-protocol       ✅ 23 uses, 100% success   [Global]
  git-create-pr            ✅ 8 uses, 100% success    [Global]
  git-branch-cleanup       ✅ 3 uses, 100% success    [Global]

Database (4 skills)
  check-db-health          ✅ 15 uses, 93% success    [Global]
  migrate-database         ✅ 6 uses, 100% success    [Global]

Scaffolding (3 skills)
  scaffold-nlq-feature     ✅ 12 uses, 100% success   [NLQ-Reporting only]
  create-api-endpoint      ✅ 9 uses, 89% success     [NLQ-Reporting only]

# Filter by category
$ /mem-skills git
$ /mem-skills database
```

#### /mem-skills-show

Show detailed skill definition

```bash
$ /mem-skills-show git-commit-protocol

git-commit-protocol
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Display Name: Git Commit (Our Protocol)
Category: git
Scope: Global (available in all projects)

Performance:
  Uses: 23
  Success Rate: 100%
  Avg Time Saved: 45 seconds
  Last Used: 2 hours ago

Triggers (3):
  - "commit these changes"
  - "create a commit"
  - "git commit with message"

Steps:
  1. Check git status and changes (parallel)
     - git status
     - git diff
     - git log -5 --oneline

  2. Analyze changes and draft message
     - Match existing commit style
     - Focus on WHY not WHAT

  3. Add files and commit with co-author footer
     - Uses heredoc format
     - Includes Claude co-author attribution

  4. Verify success
     - git status

Prerequisites:
  ✅ Git repository
  ✅ Has changes to commit

Version: 1
Created: 2025-12-15 (learned from snapshot #31)
Last Updated: 2025-12-20 (added test option)
```

#### /mem-skills-suggest

Review detected patterns and create skills

```bash
$ /mem-skills-suggest

📊 Analyzed last 5 sessions, found 3 skill candidates:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ⭐⭐⭐ database-health-check (High confidence)

   Pattern Type: Tool Sequence
   Seen: 4 times across 2 projects
   Confidence: 0.92

   You ran these commands 4 times:
   - docker-compose ps
   - psql connection test
   - query for table listing

   [Create Skill] [Ignore] [Show Details]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. ⭐⭐ env-validation (Medium confidence)

   Pattern Type: User Correction
   Seen: 2 times in NLQ-Reporting
   Confidence: 0.78

   User said: "Always check .env.example for required vars"

   [Create Skill] [Ignore] [Show Details]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. ⭐ codebase-exploration (Lower confidence)

   Pattern Type: Iteration Loop
   Seen: 3 times
   Confidence: 0.65

   You tried Grep → Glob → Read for exploratory searches.
   Should use: Task tool with Explore agent

   [Create Skill] [Ignore] [Show Details]
```

#### /mem-skills-create

Manually create a skill

```bash
$ /mem-skills-create

Creating new skill...

Skill name: deploy-to-staging
Display name: Deploy to Staging Environment
Category: [git|database|deployment|scaffolding|other]: deployment

Description: Deploy current branch to staging environment with health checks

Command type:
  1. Bash script
  2. Tool sequence
  3. Spawn agent

Choice: 1

Script path: /path/to/deploy-staging.sh

Parameters (JSON):
{
  "branch": {"type": "string", "default": "main"}
}

Prerequisites (JSON):
{
  "git_repo": true,
  "tests_passing": true
}

Triggers (comma-separated): deploy to staging, push to staging, staging deployment

✅ Skill created! Use /mem-skills-show deploy-to-staging to review.
```

#### /mem-skills-stats

View performance statistics

```bash
$ /mem-skills-stats git-commit-protocol

git-commit-protocol - Performance Statistics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Overall:
  Total Uses: 23
  Success: 23 (100%)
  Failed: 0
  Avg Execution Time: 8.2 seconds
  Avg Time Saved: 45 seconds vs manual
  Total Time Saved: 17.25 minutes

Recent Performance (Last 7 days):
  Uses: 8
  Success Rate: 100%
  Trend: ▲ Stable

Usage by Project:
  NLQ-Reporting: 12 uses
  claude-memory: 6 uses
  pgquery-dev: 5 uses

User Acceptance:
  Suggested: 25 times
  Accepted: 23 times (92%)
  Rejected: 2 times

Last 5 Executions:
  2025-12-26 14:23  ✅ Success  7.1s  [NLQ-Reporting]
  2025-12-26 11:45  ✅ Success  8.9s  [claude-memory]
  2025-12-25 16:12  ✅ Success  7.8s  [NLQ-Reporting]
  2025-12-25 10:34  ✅ Success  9.2s  [pgquery-dev]
  2025-12-24 15:56  ✅ Success  7.5s  [NLQ-Reporting]
```

#### /mem-skills-export / import

Share skills across projects

```bash
# Export from current project
$ /mem-skills-export nlq-reporting-skills.json

✅ Exported 12 skills to nlq-reporting-skills.json

Included:
  Global skills: 8 (git, database, file-ops)
  Project-specific: 4 (scaffolding, api-creation)

# Import into new project
$ cd /path/to/new-project
$ /mem-skills-import nlq-reporting-skills.json

Review skills to import:

Global Skills (recommended):
  ✅ git-commit-protocol
  ✅ git-create-pr
  ✅ check-db-health
  ✅ env-validation

Project-Specific Skills:
  ❓ scaffold-nlq-feature (specific to NLQ-Reporting structure)
  ❓ create-api-endpoint (uses NLQ service layer pattern)

Import selected: [Y/n]
```

### Interactive Suggestion Flow

**Example 1: User requests commit**

```
User: commit these changes

Claude: 🔍 Searching skills library...
        ✅ Found: 'git-commit-protocol' (23 uses, 100% success)

        This skill will:
        1. Check git status, diff, and recent commits
        2. Draft message matching your commit style
        3. Commit using heredoc format with co-author footer
        4. Verify success

        Estimated time: 8 seconds (saves ~45 seconds)

        Should I use this skill?

User: yes

Claude: ⚡ Executing git-commit-protocol skill...

        Step 1/4: Checking git status and changes...
        ✅ Found 3 modified files

        Step 2/4: Drafting commit message...
        ✅ "Add skills system architecture documentation"

        Step 3/4: Committing with co-author footer...
        ✅ Committed (hash: a3f2b1c)

        Step 4/4: Verifying success...
        ✅ Working tree clean

        🎉 Complete! (7.8 seconds)
        Saved ~45 seconds vs manual approach
```

**Example 2: End of session learning**

```
Claude: 📊 Session Analysis Complete

        I noticed you corrected my approach 2 times:

        1. You specified: "Always use heredoc for commit messages"
           Context: git commit operations (2 occurrences)

        2. You specified: "Check .env.example for required variables"
           Context: environment validation (2 occurrences)

        Would you like me to create skills for these patterns?

        1. git-commit-protocol (confidence: 0.95) ⭐⭐⭐
           [Create Skill] [Not Yet] [Show Details]

        2. env-validation (confidence: 0.78) ⭐⭐
           [Create Skill] [Not Yet] [Show Details]

User: create both

Claude: ✅ Created skill: git-commit-protocol
        ✅ Created skill: env-validation

        Next session, I'll offer to use these automatically!

        You can review them with:
        /mem-skills-show git-commit-protocol
        /mem-skills-show env-validation
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Goal:** Basic skill storage and manual execution

**Tasks:**
- [ ] Create database schema (5 tables)
- [ ] Create analytical views (3 views)
- [ ] Implement manual skill creation (`/mem-skills-create`)
- [ ] Implement basic execution (bash scripts only)
- [ ] Implement `/mem-skills` list command
- [ ] Implement `/mem-skills-show` detail command
- [ ] Simple trigger matching (exact phrase only)

**Deliverables:**
- Migration: `schema/add-skills-tables.sql`
- Python: `create-skill.py`
- Python: `execute-skill.py`
- Python: `list-skills.py`
- Skill: `/mem-skills-create`
- Skill: `/mem-skills`
- Skill: `/mem-skills-show`

**Validation:**
- User can manually create a bash script skill
- User can execute skill with approval prompt
- User can list and view skills

### Phase 2: Intelligence (Week 3-4)

**Goal:** Semantic matching and performance tracking

**Tasks:**
- [ ] Implement embedding generation for triggers
- [ ] Implement semantic trigger search
- [ ] Implement performance logging
- [ ] Implement `/mem-skills-stats` command
- [ ] Add tool sequence execution support
- [ ] Add export/import functionality

**Deliverables:**
- Python: `generate-trigger-embeddings.py`
- Python: `search-skills.py` (semantic)
- Python: `log-skill-performance.py`
- Python: `export-skills.py`, `import-skills.py`
- Update: `execute-skill.py` (add tool sequences)
- Skill: `/mem-skills-stats`
- Skill: `/mem-skills-export`, `/mem-skills-import`

**Validation:**
- Semantic matching works ("commit changes" matches "create commit")
- Performance is logged after each execution
- Skills can be exported and imported

### Phase 3: Watcher (Week 5-6)

**Goal:** Automatic pattern detection

**Tasks:**
- [ ] Implement tool sequence detection
- [ ] Implement user correction detection
- [ ] Implement iteration loop detection
- [ ] Implement confidence scoring
- [ ] Integrate with snapshot capture
- [ ] Implement `/mem-skills-suggest` command
- [ ] Add end-of-session skill suggestions

**Deliverables:**
- Python: `detect-patterns.py`
- Python: `score-patterns.py`
- Update: `save-snapshot.py` (integrate pattern detection)
- Skill: `/mem-skills-suggest`
- Update: `/mem-save` (show skill suggestions)

**Validation:**
- Repeated tool sequences are detected
- User corrections create pattern candidates
- End of session shows skill suggestions
- User can approve/reject candidates

### Phase 4: Self-Learning (Week 7-8)

**Goal:** Skill evolution and optimization

**Tasks:**
- [ ] Implement skill versioning
- [ ] Implement automatic skill updates from feedback
- [ ] Implement cross-session learning
- [ ] Add A/B testing for skill variants
- [ ] Implement confidence auto-adjustment
- [ ] Add skill recommendation engine

**Deliverables:**
- Python: `evolve-skill.py`
- Python: `recommend-skills.py`
- Update: All execution scripts (add learning feedback)
- Analytics: Skill evolution dashboard

**Validation:**
- Skills improve based on user feedback
- System suggests relevant skills proactively
- Confidence scores adjust based on performance
- Skill variants can be compared

---

## Integration Points

### 1. Integration with Snapshot Capture

**Current flow:**
```python
# processor/src/save-snapshot.py
def save_snapshot(conversation):
    snapshot_id = save_messages(conversation)
    summary = generate_summary(conversation)
    embedding = create_embedding(summary)
    store_snapshot(snapshot_id, summary, embedding)
    return snapshot_id
```

**Enhanced flow:**
```python
# processor/src/save-snapshot.py
def save_snapshot(conversation):
    # Existing flow
    snapshot_id = save_messages(conversation)
    summary = generate_summary(conversation)
    embedding = create_embedding(summary)
    store_snapshot(snapshot_id, summary, embedding)

    # NEW: Skills analysis
    from detect_patterns import analyze_for_skills

    skill_analysis = analyze_for_skills(snapshot_id, conversation)

    # Store detected patterns
    if skill_analysis['patterns']:
        store_skill_patterns(skill_analysis['patterns'], snapshot_id)

    # Update existing skills performance
    if skill_analysis['skills_used']:
        update_skill_metrics(skill_analysis['skills_used'], snapshot_id)

    # Show suggestions if any
    if skill_analysis['new_candidates']:
        print(f"\n📊 Found {len(skill_analysis['new_candidates'])} skill candidates")
        print("Run '/mem-skills-suggest' to review")

    return snapshot_id
```

### 2. Integration with MCP Server

**Add to MCP server endpoints:**

```javascript
// mcp-server/src/server.js

// Search for matching skills
server.tool("search_skills", {
  query: String,
  threshold: { type: Number, optional: true, default: 0.75 }
}, async ({ query, threshold }) => {
  const skills = await searchSkillsSemantic(query, threshold);
  return skills;
});

// Execute skill
server.tool("execute_skill", {
  skill_id: Number,
  parameters: { type: Object, optional: true }
}, async ({ skill_id, parameters }) => {
  const result = await executeSkill(skill_id, parameters);
  return result;
});

// Get skill suggestions
server.tool("suggest_skills", {
  limit: { type: Number, optional: true, default: 5 }
}, async ({ limit }) => {
  const suggestions = await getSkillCandidates(limit);
  return suggestions;
});
```

### 3. Integration with Agent System

**Skills can spawn agents:**

```json
{
  "agent_name": "scaffold-feature-with-tests",
  "command_type": "agent_spawn",
  "agent_config": {
    "agent_type": "general-purpose",
    "prompt": "Create feature module with comprehensive tests...",
    "tools": ["Read", "Write", "Edit", "Bash"]
  }
}
```

**Agents can suggest creating skills:**

When an Explore agent finds a repeated pattern, it can suggest:
```
Agent result: "I found 3 files that handle authentication.
              This pattern appears frequently.
              Suggest creating skill: 'find-auth-files' for faster discovery."
```

### 4. Integration with Project Memory

**Skills are project-aware:**
```sql
-- Global skills (available everywhere)
INSERT INTO skills_agents (agent_name, project_path)
VALUES ('git-commit-protocol', NULL);

-- Project-specific skills
INSERT INTO skills_agents (agent_name, project_path)
VALUES ('scaffold-nlq-feature', '/Users/jamesmba/Data/00 GITHUB/Code/NLQ-Reporting');
```

**Auto-activate project skills when entering directory:**
```python
# When user runs: cd /path/to/NLQ-Reporting
def on_directory_change(new_path):
    project_skills = load_project_skills(new_path)
    if project_skills:
        print(f"📚 Loaded {len(project_skills)} project-specific skills")
        print("Run /mem-skills to see them")
```

---

## Security Considerations

### Skill Execution Safety

1. **Approval Required**
   - NEVER execute skills without user approval
   - Show exactly what will be executed
   - Allow inspection before running

2. **Sandbox Execution**
   - Skills run with same permissions as Claude Code
   - Respect `.claude/settings.json` file restrictions
   - No privileged operations without user consent

3. **Validation**
   - Validate all parameters before execution
   - Check prerequisites before running
   - Timeout protection (max 5 minutes per skill)

4. **Audit Trail**
   - Log all skill executions in `skills_performance_log`
   - Track who created skills (`created_by`)
   - Maintain version history

### Skill Creation Safety

1. **User Review**
   - User must approve before skill is created
   - User can inspect generated skill definition
   - User can edit before saving

2. **Script Validation**
   - Bash scripts are not executed during creation
   - Only stored for later execution
   - User can review script contents

3. **No Automatic Execution**
   - Pattern detection NEVER auto-executes
   - Always requires explicit user approval
   - Skills marked as `status='candidate'` until approved

---

## Success Metrics

### Quantitative Metrics

1. **Usage Adoption**
   - Skills created per week
   - Skills used per session
   - User acceptance rate (% of suggestions accepted)

2. **Efficiency Gains**
   - Total time saved (aggregate across all skills)
   - Average time saved per skill use
   - Reduction in iteration loops

3. **Quality Metrics**
   - Skill success rate (% executions successful)
   - Pattern detection accuracy
   - False positive rate (skills suggested but rejected)

4. **Learning Velocity**
   - Time from pattern detected → skill created
   - Skill evolution rate (improvements per month)
   - Cross-project skill reuse

### Qualitative Metrics

1. **User Satisfaction**
   - Skills feel helpful vs intrusive
   - Suggestions are relevant
   - Execution saves meaningful time

2. **System Intelligence**
   - Learns user preferences
   - Suggests right skill at right time
   - Adapts to corrections

3. **Collaboration Enhancement**
   - Maintains collaborative model
   - Doesn't remove user from decision-making
   - Augments rather than replaces interaction

---

## Future Enhancements

### Phase 5+: Advanced Features

1. **Skill Composition**
   - Chain multiple skills together
   - Conditional execution (if X succeeds, run Y)
   - Parallel skill execution

2. **Context-Aware Suggestions**
   - Suggest skills based on current file
   - Suggest based on git status
   - Suggest based on error messages

3. **Team Collaboration**
   - Share skills across team
   - Skill marketplace
   - Community-contributed skills

4. **Proactive Assistance**
   - "I see you're about to commit, would you like me to use the commit skill?"
   - "This looks like a database query, I have a skill for that"

5. **Multi-Project Intelligence**
   - Learn patterns across all projects
   - Suggest skills from similar projects
   - Cross-pollinate best practices

---

## Appendix

### Example Skill: git-commit-protocol

**Full Definition:**
```json
{
  "agent_name": "git-commit-protocol",
  "display_name": "Git Commit (Our Protocol)",
  "description": "Commits changes following our established protocol: check status, draft message, use heredoc format, verify success",
  "category": "git",
  "project_path": null,
  "scope": "global",
  "confidence_score": 1.0,
  "version": 2,

  "triggers": [
    {
      "trigger_phrase": "commit these changes",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    },
    {
      "trigger_phrase": "create a commit",
      "match_type": "semantic",
      "confidence_threshold": 0.75
    },
    {
      "trigger_phrase": "git commit",
      "match_type": "semantic",
      "confidence_threshold": 0.8
    }
  ],

  "command": {
    "command_type": "tool_sequence",
    "command_definition": {
      "steps": [
        {
          "step": 1,
          "description": "Check git status and changes",
          "tools": [
            {
              "tool": "Bash",
              "command": "git status",
              "description": "Check working tree status"
            },
            {
              "tool": "Bash",
              "command": "git diff",
              "description": "Show unstaged changes"
            },
            {
              "tool": "Bash",
              "command": "git log --oneline -5",
              "description": "Show recent commit style"
            }
          ],
          "parallel": true
        },
        {
          "step": 2,
          "description": "Analyze changes and draft message",
          "action": "analyze_and_draft",
          "rules": [
            "Match existing commit style from git log",
            "Use format: Type: Brief description",
            "Focus on WHY not WHAT",
            "Keep concise (1-2 sentences)"
          ]
        },
        {
          "step": 3,
          "description": "Commit with co-author footer",
          "tools": [
            {
              "tool": "Bash",
              "command": "git add . && git commit -m \"$(cat <<'EOF'\\n{message}\\n\\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\\n\\nCo-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>\\nEOF\\n)\"",
              "description": "Add all files and commit with heredoc"
            }
          ]
        },
        {
          "step": 4,
          "description": "Verify success",
          "tools": [
            {
              "tool": "Bash",
              "command": "git status",
              "description": "Confirm working tree is clean"
            }
          ]
        }
      ]
    },
    "prerequisites": {
      "git_repo": true,
      "has_changes": true
    },
    "success_indicators": [
      "nothing to commit, working tree clean",
      "Your branch is ahead"
    ],
    "failure_indicators": [
      "error:",
      "fatal:",
      "nothing added to commit"
    ]
  },

  "performance": {
    "use_count": 23,
    "success_count": 23,
    "failure_count": 0,
    "success_rate": 100.0,
    "avg_time_saved_ms": 45000,
    "total_time_saved_ms": 1035000
  },

  "metadata": {
    "learned_from_snapshot_id": 31,
    "last_improved_snapshot_id": 42,
    "created_at": "2025-12-15T10:30:00Z",
    "created_by": "watcher",
    "updated_at": "2025-12-20T14:22:00Z"
  }
}
```

---

**Document Version:** 1.0
**Last Updated:** 2025-12-26
**Next Review:** After Phase 1 implementation
