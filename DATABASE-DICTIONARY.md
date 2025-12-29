# Claude Memory - Database Data Dictionary

**Generated:** 2025-12-28
**Database:** claude_memory
**PostgreSQL Version:** 16 with pgvector extension

---

## Tables (8)

### 1. context_snapshots
**Primary table storing conversation snapshots**

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| id | integer | NO | nextval() | Primary key |
| project_path | text | NO | - | Project path (e.g., "Code/claude-memory") |
| session_id | text | YES | - | Claude Code session UUID |
| **timestamp** | **timestamptz** | **YES** | **now()** | **Capture time in UTC** |
| context_window_size | integer | YES | - | Number of messages |
| trigger_event | text | YES | - | What triggered capture |
| raw_context | jsonb | NO | - | Full conversation JSON |
| summary | text | YES | - | AI-generated summary |
| embedding | vector(384) | YES | - | Semantic embedding |
| tags | text[] | YES | - | Extracted tags |
| mentioned_files | text[] | YES | - | Files mentioned in conversation |
| key_decisions | text[] | YES | - | Architectural decisions |
| bugs_fixed | text[] | YES | - | Bug fixes documented |
| git_commit_hash | text | YES | - | Associated git commit |
| git_branch | text | YES | - | Associated git branch |
| created_by | text | YES | 'claude-code' | Source of capture |
| storage_size_bytes | integer | YES | - | Size of raw_context |
| transcript_path | text | YES | - | Path to transcript file |

**Indexes:**
- Primary key: `id`
- HNSW index on `embedding` (vector search)
- GIN indexes on `mentioned_files`, `tags`
- B-tree indexes on `project_path`, `session_id`, `timestamp DESC`, `transcript_path`, `trigger_event`

**Dependencies:**
- Referenced by `agent_work.parent_snapshot_id`

---

### 2. agent_work
**Tracks agent/subprocess execution**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| agent_id | text | YES | Agent identifier |
| request_id | text | YES | Request UUID |
| agent_definition_id | integer | YES | FK to agent_definitions |
| parent_session_id | text | YES | Parent Claude session |
| parent_snapshot_id | integer | YES | FK to context_snapshots |
| agent_request | text | YES | Agent task description |
| timestamp_start | timestamptz | YES | Agent start time (UTC) |
| timestamp_end | timestamptz | YES | Agent end time (UTC) |
| duration_seconds | numeric | YES | Execution duration |
| tools_used | text[] | YES | Tools invoked by agent |
| files_examined | text[] | YES | Files read by agent |
| urls_fetched | text[] | YES | URLs fetched by agent |
| final_output | text | YES | Agent output |
| embedding | vector(384) | YES | Semantic embedding |

**Indexes:**
- Primary key: `id`
- HNSW index on `embedding`
- GIN indexes on `tools_used`, `files_examined`
- B-tree indexes on `agent_definition_id`, `parent_snapshot_id`, `parent_session_id`, `request_id`
- Unique constraint: `(agent_id, parent_session_id)`

---

### 3. agent_definitions
**Agent configuration versions**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| agent_type | text | NO | Agent type (e.g., "Explore", "Plan") |
| version | integer | NO | Configuration version |
| parent_definition_id | integer | YES | Previous version FK |
| configuration_params | jsonb | YES | Agent configuration |
| model_used | text | YES | LLM model |
| tools_available | text[] | YES | Available tools |
| config_hash | text | NO | Configuration hash |
| created_at | timestamptz | NO | Creation time (UTC) |

**Indexes:**
- Primary key: `id`
- Unique: `config_hash`, `(agent_type, config_hash)`
- B-tree: `agent_type`, `config_hash`, `created_at`

---

### 4. skills_agents
**Skills system agent definitions**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| agent_name | text | NO | Unique skill name |
| display_name | text | YES | Human-readable name |
| description | text | YES | Skill description |
| category | text | YES | Skill category |
| scope | text | YES | 'global' or 'project' |
| project_path | text | YES | Project path if scoped |
| created_at | timestamptz | NO | Creation time (UTC) |
| modified_at | timestamptz | NO | Last modified (UTC) |
| is_active | boolean | NO | Active status |
| use_count | integer | NO | Times executed |
| success_rate | numeric | YES | Success percentage |
| avg_execution_time | numeric | YES | Average duration |
| last_used | timestamptz | YES | Last execution time (UTC) |

**Indexes:**
- Primary key: `id`
- Unique: `agent_name`
- B-tree: `category`, `project_path`, `use_count DESC`, `success_rate DESC`, `last_used DESC`
- Partial index on `is_active WHERE is_active = true`

**Triggers:**
- `update_skills_agents_modtime` - Updates `modified_at` on UPDATE

---

### 5. skills_commands
**Skill command definitions**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| agent_id | integer | NO | FK to skills_agents |
| version | integer | NO | Command version |
| command_type | text | NO | 'bash_script', 'tool_sequence', 'agent_spawn' |
| content | jsonb | NO | Command definition |
| prerequisites | jsonb | YES | Prerequisites |
| created_at | timestamptz | NO | Creation time (UTC) |
| is_active | boolean | NO | Active status |

**Indexes:**
- Primary key: `id`
- B-tree: `agent_id`, `command_type`, `(agent_id, version DESC)`
- Partial index on `is_active WHERE is_active = true`

---

### 6. skills_triggers
**Skill trigger phrases with embeddings**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| agent_id | integer | NO | FK to skills_agents |
| trigger_phrase | text | NO | Natural language trigger |
| match_type | text | NO | 'semantic' or 'exact' |
| embedding | vector(1024) | YES | Semantic embedding (Ollama) |
| created_at | timestamptz | NO | Creation time (UTC) |
| is_active | boolean | NO | Active status |

**Indexes:**
- Primary key: `id`
- B-tree: `agent_id`, `match_type`
- HNSW index on `embedding WHERE match_type = 'semantic' AND is_active = true`
- Partial index on `is_active WHERE is_active = true`

---

### 7. skills_performance_log
**Skill execution history**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| agent_id | integer | NO | FK to skills_agents |
| executed_at | timestamptz | NO | Execution time (UTC) |
| duration_seconds | numeric | YES | Execution duration |
| outcome | text | NO | 'success', 'failure', 'timeout' |
| error_message | text | YES | Error details if failed |
| session_id | text | YES | Claude session UUID |
| snapshot_id | integer | YES | Associated snapshot |

**Indexes:**
- Primary key: `id`
- B-tree: `agent_id`, `executed_at DESC`, `outcome`, `session_id`, `snapshot_id`
- Partial index on `outcome WHERE outcome = 'success'`

---

### 8. skills_patterns
**Detected skill patterns**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| pattern_type | text | NO | Pattern category |
| signature_hash | text | NO | Pattern signature |
| occurrences | integer | NO | Times seen |
| confidence_score | numeric | NO | Confidence level |
| priority_score | numeric | YES | Priority ranking |
| status | text | NO | 'detected', 'reviewed', 'implemented' |
| detected_at | timestamptz | NO | First detection (UTC) |
| last_seen | timestamptz | YES | Last occurrence (UTC) |

**Indexes:**
- Primary key: `id`
- B-tree: `pattern_type`, `signature_hash`, `status`, `occurrences DESC`, `confidence_score DESC`, `priority_score DESC`

---

## Views (17)

### Views with PST Timezone Conversion (⚠️ CRITICAL)

The following views hardcode PST timezone conversion using `AT TIME ZONE 'America/Los_Angeles'`:

1. **v_snapshot_quality** - Uses `pst_time` column
2. **v_agent_evolution** - Uses `pst_created`, `last_used_pst`
3. **v_agent_work_full** - Uses `pst_start`, `pst_end`, `parent_pst_time`
4. **v_all_decisions** - Uses `pst_time`
5. **v_bug_patterns** - Uses `pst_time`
6. **v_file_heatmap** - Uses `first_mentioned`, `last_mentioned` (PST)
7. **v_messages_flat** - Uses `pst_time` (assumed, referenced by v_assistant_messages)

### Views Using Raw UTC Timestamp

8. **context_stats** - Uses `timestamp` directly (UTC)

### Views Without Timestamp Fields

9. **v_agent_config_performance**
10. **v_agent_tool_usage**
11. **v_assistant_messages** - References v_messages_flat
12. **v_project_dashboard**
13. **v_skill_candidates**
14. **v_skill_performance_trends**
15. **v_skills_by_category**
16. **v_skills_dashboard**
17. **v_work_timeline**

---

## Triggers (1)

### update_skills_agents_modtime
- **Table:** skills_agents
- **Timing:** BEFORE UPDATE
- **Function:** `update_modified_column()`
- **Purpose:** Automatically updates `modified_at` column

**Function Definition:**
```sql
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';
```

**Impact on Timezone Migration:** ✅ None - Function uses `now()` which returns UTC

---

## Functions/Stored Procedures

### pgvector Extension Functions (37)
All related to vector operations (distance, similarity, etc.)

### Custom Functions (1)
- `update_modified_column()` - Trigger function for timestamp updates

---

## Timezone Handling Issues

### Current State

**Base Table (✅ Correct):**
- `context_snapshots.timestamp` is `TIMESTAMPTZ` (stores UTC)
- Agent tables use `TIMESTAMPTZ` (stores UTC)
- Skills tables use `TIMESTAMPTZ` (stores UTC)

**Views (❌ Problem):**
- 7 views hardcode PST conversion via `AT TIME ZONE 'America/Los_Angeles'`
- Views return `timestamp without time zone` for PST fields
- Breaks for non-PST users

### Affected Views and Fields

| View | PST Fields | Impact |
|------|-----------|--------|
| v_snapshot_quality | pst_time | HIGH - Used by new skills |
| v_agent_evolution | pst_created, last_used_pst | MEDIUM - Agent analytics |
| v_agent_work_full | pst_start, pst_end, parent_pst_time | MEDIUM - Agent work tracking |
| v_all_decisions | pst_time | MEDIUM - Decision timeline |
| v_bug_patterns | pst_time | MEDIUM - Bug analysis |
| v_file_heatmap | first_mentioned, last_mentioned | MEDIUM - File activity |
| v_messages_flat | pst_time | MEDIUM - Message search |

### Migration Scope

**If fixing ALL views (comprehensive approach):**
- 7 views need updating
- Each view needs BOTH `timestamp` (UTC) and legacy PST field
- More testing required
- Larger scope but complete fix

**If fixing ONLY v_snapshot_quality (minimal approach):**
- 1 view updated
- Other 6 views still show PST times
- Inconsistent user experience
- Partial fix

---

## Dependencies Summary

**No triggers on timestamp columns** ✅
**No functions that would break** ✅
**Multiple views reference timestamps** ⚠️ Need coordination

---

## Recommendations

1. **Comprehensive Fix:** Update all 7 views to include UTC timestamps
2. **Phased Approach:** Start with v_snapshot_quality (highest priority)
3. **Testing:** Focus on views not just tables
4. **Future:** Consider removing PST fields after 6+ months

---

**Last Updated:** 2025-12-28
**Maintained By:** Claude Memory Team
