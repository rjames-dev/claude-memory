# Skills System - Phase 2 Planning

**Status:** Planning
**Timeline:** Weeks 3-4 (14 days)
**Prerequisites:** Phase 1 Complete ✅

---

## Table of Contents

1. [Overview](#overview)
2. [Phase 2 Objectives](#phase-2-objectives)
3. [Milestone 3: Semantic Matching](#milestone-3-semantic-matching)
4. [Milestone 4: Tool Sequences & Agents](#milestone-4-tool-sequences--agents)
5. [Milestone 5: Analytics & Intelligence](#milestone-5-analytics--intelligence)
6. [Additional Features](#additional-features)
7. [Implementation Timeline](#implementation-timeline)
8. [Technical Architecture](#technical-architecture)
9. [Success Criteria](#success-criteria)

---

## Overview

Phase 2 builds on Phase 1's foundation to add:
- **Semantic trigger matching** using embeddings
- **Tool sequence execution** for multi-step workflows
- **Agent spawning** to launch Claude Code agents
- **Analytics dashboard** for insights
- **Auto-execution** based on trust levels
- **Skill management** (edit, delete, export/import)

### Phase 1 Recap (Completed)

✅ Database foundation (5 tables, 31+ indexes, 4 views)
✅ Manual skill creation (create-skill.py)
✅ Skill listing & filtering (list-skills.py)
✅ Skill details & inspection (skill-info.py)
✅ Basic execution & tracking (execute-skill.py)
✅ Integration testing (21/21 tests passing)

### Phase 2 Goals

🎯 **Enable intelligent automation**
🎯 **Support complex workflows**
🎯 **Build trust-based auto-execution**
🎯 **Provide actionable analytics**
🎯 **Streamline skill management**

---

## Phase 2 Objectives

### Primary Objectives

1. **Semantic Matching** - Match triggers using embeddings instead of exact strings
2. **Tool Sequences** - Execute multi-step workflows combining multiple tools
3. **Agent Spawning** - Launch Claude Code agents (Explore, Plan) from skills
4. **Analytics** - Visualize skill performance and patterns
5. **Auto-Execution** - High-trust skills execute automatically

### Secondary Objectives

6. **Skill Editing** - Modify existing skills
7. **Skill Deletion** - Remove unwanted skills
8. **Export/Import** - Backup and share skills
9. **Pattern Learning** - Learn from repeated user actions
10. **Advanced Prerequisites** - More validation options

---

## Milestone 3: Semantic Matching

**Duration:** Days 1-5
**Goal:** Replace exact trigger matching with embedding-based semantic search

### Features

**1. Embedding Generation (Days 1-2)**
- Generate embeddings for trigger phrases using Ollama
- Store embeddings in `skills_triggers.embedding_vector` (already in schema)
- Create HNSW index for fast similarity search
- Batch process existing triggers

**2. Semantic Search (Days 2-3)**
- Match user requests to triggers using cosine similarity
- Configurable similarity threshold (e.g., 0.7)
- Return top N matches ranked by similarity
- Fall back to exact matching if no semantic match

**3. Trigger Management (Days 4-5)**
- Auto-generate embeddings on trigger creation
- Re-index when triggers updated
- Support multiple match types:
  - `exact` - Exact string match
  - `semantic` - Embedding similarity
  - `regex` - Pattern matching (future)

### Implementation

```python
# Example: generate_trigger_embedding.py
import ollama

def generate_embedding(text):
    """Generate embedding using Ollama."""
    response = ollama.embeddings(
        model='mxbai-embed-large',
        prompt=text
    )
    return response['embedding']

def store_embedding(trigger_id, embedding):
    """Store embedding in database."""
    cur.execute("""
        UPDATE skills_triggers
        SET embedding_vector = %s::vector
        WHERE id = %s
    """, (embedding, trigger_id))
```

**Database Query:**
```sql
-- Find triggers similar to user request
SELECT
    st.id,
    st.trigger_phrase,
    st.agent_id,
    1 - (st.embedding_vector <=> %s::vector) AS similarity
FROM skills_triggers st
WHERE st.is_active = TRUE
  AND 1 - (st.embedding_vector <=> %s::vector) > 0.7
ORDER BY similarity DESC
LIMIT 5;
```

### Success Criteria

- [  ] Embeddings generated for all triggers
- [  ] HNSW index performing <100ms searches
- [  ] Semantic matching finds relevant skills
- [  ] Similarity threshold configurable
- [  ] Backward compatible with exact matching

---

## Milestone 4: Tool Sequences & Agents

**Duration:** Days 6-10
**Goal:** Support multi-step workflows and agent spawning

### Features

**1. Tool Sequences (Days 6-8)**

Multi-step workflows combining Claude Code tools:

```json
{
  "command_type": "tool_sequence",
  "command_definition": {
    "steps": [
      {
        "tool": "Grep",
        "params": {"pattern": "TODO", "output_mode": "files_with_matches"}
      },
      {
        "tool": "Read",
        "params": {"file_path": "$prev.files[0]"}
      },
      {
        "tool": "Edit",
        "params": {"file_path": "$prev.file_path", "old_string": "TODO", "new_string": "DONE"}
      }
    ]
  }
}
```

**Features:**
- Sequential execution
- Variable substitution between steps (`$prev.field`)
- Error handling and rollback
- Step-by-step logging
- Conditional steps (if/else)

**2. Agent Spawning (Days 8-10)**

Launch Claude Code agents from skills:

```json
{
  "command_type": "agent_spawn",
  "agent_config": {
    "agent_type": "Explore",
    "prompt": "Find all API endpoints in the codebase",
    "model": "haiku",
    "timeout": 300
  }
}
```

**Supported Agents:**
- `Explore` - Codebase exploration
- `Plan` - Implementation planning
- `general-purpose` - Complex tasks

**Features:**
- Async agent execution
- Result capture
- Timeout handling
- Agent output parsing

### Implementation

**Tool Sequence Executor:**
```python
def execute_tool_sequence(sequence_def, context):
    """Execute a sequence of tools."""
    results = []

    for step in sequence_def['steps']:
        tool = step['tool']
        params = substitute_variables(step['params'], results)

        result = execute_tool(tool, params)

        if not result['success']:
            if step.get('required', True):
                rollback_sequence(results)
                return {'success': False, 'error': result['error']}

        results.append(result)

    return {'success': True, 'results': results}
```

### Success Criteria

- [  ] Tool sequences execute sequentially
- [  ] Variable substitution working
- [  ] Error handling and rollback functional
- [  ] Agent spawning launches agents correctly
- [  ] Agent results captured and returned
- [  ] Timeout handling prevents hangs

---

## Milestone 5: Analytics & Intelligence

**Duration:** Days 11-14
**Goal:** Provide insights and enable auto-execution

### Features

**1. Analytics Dashboard (Days 11-12)**

View for skill performance insights:

```sql
CREATE VIEW v_skills_analytics AS
SELECT
    sa.id,
    sa.agent_name,
    sa.category,

    -- Usage patterns
    sa.use_count,
    sa.success_rate,
    sa.total_time_saved_ms / 1000 / 60 AS total_minutes_saved,

    -- Trend analysis
    COUNT(DISTINCT spl.id) FILTER (
        WHERE spl.executed_at > NOW() - INTERVAL '7 days'
    ) AS uses_last_week,
    COUNT(DISTINCT spl.id) FILTER (
        WHERE spl.executed_at > NOW() - INTERVAL '30 days'
    ) AS uses_last_month,

    -- Trust level
    CASE
        WHEN sa.use_count >= 10 AND sa.success_rate >= 90 THEN 'high_trust'
        WHEN sa.use_count >= 5 AND sa.success_rate >= 70 THEN 'medium_trust'
        ELSE 'low_trust'
    END AS trust_level,

    -- Peak usage time
    MODE() WITHIN GROUP (ORDER BY EXTRACT(HOUR FROM spl.executed_at)) AS peak_hour

FROM skills_agents sa
LEFT JOIN skills_performance_log spl ON spl.agent_id = sa.id
GROUP BY sa.id;
```

**Queries:**
- Top time savers
- Most used skills
- Skills needing improvement
- Usage patterns by time/day
- Category performance

**2. Auto-Execution (Days 13-14)**

High-trust skills execute automatically:

```python
def should_auto_execute(skill):
    """Determine if skill should auto-execute."""
    # Trust level calculation
    if skill['use_count'] < 10:
        return False  # Not enough history

    if skill['success_rate'] < 90:
        return False  # Not reliable enough

    # Check recent performance
    recent_failures = count_recent_failures(skill['id'], days=7)
    if recent_failures > 0:
        return False  # Recent failures

    return True  # High trust - auto-execute
```

**Features:**
- Configurable trust thresholds
- User confirmation for first auto-execution
- Safety checks (no auto-exec for destructive ops)
- Audit trail for all auto-executions

**3. Pattern Learning (Bonus)**

Learn from repeated user actions:

```python
def detect_pattern(user_actions):
    """Detect repeated action patterns."""
    # Look for sequences of 3+ actions repeated 3+ times
    patterns = find_repeated_sequences(user_actions, min_length=3, min_occurrences=3)

    for pattern in patterns:
        suggest_skill_from_pattern(pattern)
```

**Suggest creating skills from detected patterns.**

### Success Criteria

- [  ] Analytics view provides useful insights
- [  ] Trust level calculation working
- [  ] Auto-execution respects trust levels
- [  ] User can disable auto-execution
- [  ] Audit trail for all auto-executions
- [  ] Pattern detection identifies repeated actions

---

## Additional Features

### Skill Management

**1. Edit Skills (edit-skill.py)**

```bash
python3 edit-skill.py skill-name \
  --description "New description" \
  --add-trigger "new trigger phrase" \
  --remove-trigger "old trigger" \
  --script-content "new script"
```

**Features:**
- Update any field
- Add/remove triggers
- Modify script content
- Version tracking (increment version number)
- Before/after snapshots in `skills_performance_log`

**2. Delete Skills (delete-skill.py)**

```bash
python3 delete-skill.py skill-name
python3 delete-skill.py --id 5
python3 delete-skill.py skill-name --force  # Skip confirmation
```

**Features:**
- Soft delete (mark `is_active = FALSE`)
- Hard delete (remove from database)
- Cascade delete (triggers, commands, logs)
- Confirmation prompt
- Undo capability (restore soft-deleted)

**3. Export/Import Skills**

**Export:**
```bash
python3 export-skill.py skill-name -o skill-backup.json
python3 export-skill.py --category database -o db-skills.json
python3 export-skill.py --all -o all-skills.json
```

**Import:**
```bash
python3 import-skill.py skill-backup.json
python3 import-skill.py all-skills.json --skip-existing
```

**JSON Format:**
```json
{
  "version": "1.0",
  "exported_at": "2025-12-26T10:00:00Z",
  "skills": [
    {
      "agent_name": "check-db-health",
      "display_name": "Database Health Check",
      "description": "...",
      "category": "database",
      "triggers": ["check db", "verify database"],
      "command": {
        "type": "bash_script",
        "content": "#!/bin/bash\n...",
        "prerequisites": {"docker_running": true}
      }
    }
  ]
}
```

---

## Implementation Timeline

### Week 3: Semantic Matching & Tool Sequences

**Days 1-2: Embeddings**
- Implement embedding generation
- Batch process existing triggers
- Test HNSW index performance

**Days 3-5: Semantic Search**
- Implement similarity search
- Add to execute-skill.py
- Test with various queries

**Days 6-8: Tool Sequences**
- Implement sequence executor
- Add variable substitution
- Test error handling

**Days 9-10: Agent Spawning**
- Implement agent launcher
- Test with Explore/Plan agents
- Add result capture

### Week 4: Analytics & Management

**Days 11-12: Analytics**
- Create analytics views
- Implement trust level calculation
- Test queries

**Days 13-14: Auto-Execution**
- Implement auto-exec logic
- Add safety checks
- Test trust levels

**Bonus: Skill Management**
- Edit skill (1-2 days)
- Delete skill (1 day)
- Export/import (1-2 days)

---

## Technical Architecture

### Embedding Pipeline

```
User Request
    ↓
Generate Embedding (Ollama)
    ↓
Similarity Search (pgvector)
    ↓
Rank by Similarity
    ↓
Return Top Matches
```

### Tool Sequence Execution

```
Parse Sequence Definition
    ↓
For Each Step:
    ↓
  Substitute Variables
    ↓
  Execute Tool
    ↓
  Check Success
    ↓
  Store Result
    ↓
Return Combined Results
```

### Agent Spawning

```
Parse Agent Config
    ↓
Launch Agent (Task tool)
    ↓
Monitor Execution
    ↓
Capture Output
    ↓
Return Results
```

### Auto-Execution Flow

```
User Request
    ↓
Match to Skill (Semantic)
    ↓
Calculate Trust Level
    ↓
If High Trust → Auto-Execute
    ↓
If Low Trust → Ask Confirmation
    ↓
Execute & Log
```

---

## Success Criteria

### Milestone 3: Semantic Matching
- [  ] 90%+ of user requests match relevant skills
- [  ] <100ms embedding search time
- [  ] Backward compatible with exact matching
- [  ] No false positives on unrelated queries

### Milestone 4: Tool Sequences & Agents
- [  ] Tool sequences execute without errors
- [  ] Variable substitution works correctly
- [  ] Agents launch and return results
- [  ] Timeout handling prevents hangs
- [  ] Error recovery functional

### Milestone 5: Analytics & Auto-Execution
- [  ] Analytics provide actionable insights
- [  ] Trust levels calculated correctly
- [  ] Auto-execution only for high-trust skills
- [  ] User can control auto-execution
- [  ] All auto-execs audited

### Overall Phase 2
- [  ] All Phase 1 tests still passing
- [  ] New integration tests for Phase 2 features
- [  ] Documentation updated
- [  ] User guide includes Phase 2 features
- [  ] Performance maintained or improved

---

## Dependencies

### External Services
- **Ollama** - Embedding generation (mxbai-embed-large model)
- **pgvector** - Vector similarity search (already installed)
- **Claude Code** - Agent spawning via Task tool

### Database Extensions
- [x] pgvector - Already enabled
- [  ] pg_cron - For scheduled skill execution (optional)

### Python Packages
- [x] psycopg2 - PostgreSQL adapter
- [  ] ollama - Ollama Python client
- [x] json - JSON parsing
- [x] subprocess - Command execution

---

## Risks & Mitigation

### Risk 1: Embedding Performance
**Risk:** Embedding generation too slow
**Mitigation:**
- Batch process triggers
- Cache embeddings
- Use faster embedding model if needed

### Risk 2: False Positive Matches
**Risk:** Semantic search matches unrelated skills
**Mitigation:**
- Tune similarity threshold
- Allow user to confirm matches
- Fall back to exact matching

### Risk 3: Tool Sequence Complexity
**Risk:** Complex sequences hard to debug
**Mitigation:**
- Step-by-step logging
- Dry run mode for sequences
- Clear error messages

### Risk 4: Auto-Execution Safety
**Risk:** Auto-executing wrong skill
**Mitigation:**
- High trust threshold (90%+ success)
- User confirmation first time
- Blacklist destructive operations
- Audit all auto-executions

---

## Next Steps

1. **Review Phase 2 Plan** - Get feedback on scope and priorities
2. **Set Up Ollama** - Install and test embedding model
3. **Prototype Semantic Matching** - Build POC for trigger matching
4. **Design Tool Sequence Schema** - Define JSON structure
5. **Begin Milestone 3** - Start with embedding generation

---

**Phase 2 Status:** Planning
**Ready to Begin:** Upon approval
**Estimated Completion:** 14 days from start
