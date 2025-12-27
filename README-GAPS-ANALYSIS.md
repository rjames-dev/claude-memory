# README.md Git Readiness - Gap Analysis

**Date**: 2025-12-27
**Purpose**: Identify and address gaps for new users cloning claude-memory

---

## User Expectations Checklist

| # | Expectation | Current Status | Priority |
|---|-------------|----------------|----------|
| 1 | Clear overview of capabilities | ✅ GOOD | - |
| 2 | API keys and passwords clarity | ⚠️ PARTIAL | HIGH |
| 3 | Workspace concept | ⚠️ PARTIAL | HIGH |
| 4 | Skills included & initialization | ❌ MISSING | CRITICAL |
| 5 | How to add skills | ⚠️ PARTIAL | HIGH |
| 6 | Enhanced summaries | ✅ GOOD | - |
| 7 | How to bring up claude-memory | ⚠️ PARTIAL | HIGH |
| 8 | WHERE to start claude-memory | ⚠️ PARTIAL | CRITICAL |
| 9 | Workspace limitations | ⚠️ PARTIAL | MEDIUM |
| 10 | Skill marketplaces/limitations | ❌ NOT COVERED | LOW |
| 11 | Skill variables (env, paths) | ❌ MISSING | CRITICAL |

---

## CRITICAL GAPS (Must Fix Before Release)

### Gap 1: Skills Database Initialization

**Problem**: No documentation on how skills get into the database

**Questions users will have:**
- Do skills come pre-installed?
- Is there a seed/import step?
- How do I load the example skills?

**Proposed Solution**: Add "Skills Initialization" section after Quick Start

```markdown
### 9. Initialize Skills System (Required for Skills)

The Skills System requires database tables and initial skills to be loaded.

#### One-Time Setup

```bash
# 1. Ensure containers are running
docker-compose ps

# 2. Skills tables are auto-created on first startup (Phase 1)
# Verify with:
docker exec claude-context-db psql -U memory_admin -d claude_memory \
  -c "\dt skills_*"

# Expected output:
#  skills_agents
#  skills_commands
#  skills_performance_log
#  skills_triggers

# 3. Load example skills (if not already loaded)
# Check if skills exist:
python3 list-skills.py

# If empty, import example skills:
# (Note: Currently skills must be created manually - see "Creating Skills" section)
```

#### Verify Skills Installation

```bash
# List all skills
/mem-skills

# Expected output: 8 example skills
# - check-db-health
# - backup-database
# - show-db-connection
# - find-todos
# - where-am-i
# - system-status
# - restart-services
# - check-volume-safety

# Test semantic search
/mem-skills-search "check database"

# Should return: check-db-health with high similarity
```
```

**Status**: Skills tables are created by schema/init.sql, but:
- ❌ No bulk import script for example skills
- ❌ Skills must be created manually one-by-one
- ❌ No example skills.json to import

**Action Items**:
1. Create `skills/example-skills.json` with all 8 example skills
2. Create `python3 import-skills.py skills/example-skills.json`
3. Add to Quick Start: Step 9

---

### Gap 2: Command Execution Context

**Problem**: Users don't know WHERE to run commands

**Questions users will have:**
- Where do I run `python3 execute-skill.py`?
- Can I run it from any directory?
- What about /mem-skills commands?

**Proposed Solution**: Add clarification section

```markdown
## Command Execution Context

### Where to Run Commands

Claude Memory uses **two types of commands**:

#### 1. Python Scripts (Run from claude-memory directory)

```bash
# These must be run from the claude-memory installation directory
cd /path/to/claude-memory

python3 execute-skill.py check-db-health
python3 generate-trigger-embeddings.py --backfill
python3 skills-stats.py --all
python3 search-skills-semantic.py "query"
```

**Why?** Scripts need access to:
- `.env` file for database password
- Database connection on localhost:5435

#### 2. Slash Commands (Available anywhere in Claude Code)

```bash
# These work from ANY directory under CLAUDE_WORKSPACE_ROOT
cd ~/workspace/any-project

/mem-skills
/mem-skills-search "query"
/mem-skills-stats check-db-health
/mem-enhance-summary 31
```

**How?** Slash commands are installed globally in `~/.claude/commands/`

**Key Points:**
- Claude Memory runs as a **background service** (one instance for all projects)
- Skills work in **any project** under your CLAUDE_WORKSPACE_ROOT
- No per-project setup needed after initial installation
```

**Status**: Not documented
**Action Items**: Add "Command Execution Context" section

---

### Gap 3: Skill Variables and Context

**Problem**: No documentation on how to use variables in skills

**Questions users will have:**
- How do I access environment variables in skills?
- How do I get the current project path?
- What variables are available?

**Proposed Solution**: Add "Skill Variables Reference" section

```markdown
### Skill Variables Reference

Skills can access context variables, environment variables, and step outputs.

#### Available Context Variables

**In Bash Script Skills:**
```bash
# Environment variables (from .env)
echo $CONTEXT_DB_PASSWORD     # Database password
echo $CLAUDE_WORKSPACE_ROOT   # Workspace root path

# Skill-specific variables (set by execute-skill.py)
echo $SKILL_PROJECT_PATH      # Current project path (e.g., "Code/my-project")
echo $SKILL_CWD               # Current working directory (full path)
echo $SKILL_NAME              # Skill name being executed
```

**In Tool Sequence Skills:**
```json
{
  "steps": [
    {
      "name": "get_project",
      "tool": "Bash",
      "command": "echo $SKILL_PROJECT_PATH"
    },
    {
      "name": "use_previous",
      "tool": "Bash",
      "command": "echo Previous result: $prev.output"
    },
    {
      "name": "use_specific_step",
      "tool": "Bash",
      "command": "echo First step: $steps.get_project.output"
    }
  ]
}
```

**Variable Types:**

1. **Environment Variables** (`$ENV_VAR`)
   - Loaded from .env file
   - Available in bash scripts
   - Examples: `$CONTEXT_DB_PASSWORD`, `$POSTGRES_HOST_PORT`

2. **Context Variables** (`$SKILL_*`)
   - Set by execute-skill.py at runtime
   - `$SKILL_PROJECT_PATH` - Relative project path
   - `$SKILL_CWD` - Full working directory path
   - `$SKILL_NAME` - Current skill name

3. **Step Variables** (`$steps.name.field`, `$prev.field`)
   - Access previous step outputs
   - `$prev.field` - Previous step's output field
   - `$steps.name.field` - Specific step's output field
   - Supports array indexing: `$steps.find.results[0]`

#### Example: Project-Aware Backup

```json
{
  "skill_name": "backup-current-project",
  "category": "maintenance",
  "command_type": "tool_sequence",
  "steps": [
    {
      "name": "get_project_name",
      "tool": "Bash",
      "command": "basename $SKILL_CWD"
    },
    {
      "name": "create_backup",
      "tool": "Bash",
      "command": "tar -czf /tmp/backup-$prev.output-$(date +%Y%m%d).tar.gz ."
    }
  ]
}
```

#### Example: Database Query with .env Password

```bash
#!/bin/bash
# check-db-health.sh

docker exec claude-context-db \
  psql -U memory_admin \
  -d claude_memory \
  -c "SELECT version();"

# Note: Password comes from .env file via Docker environment
# No need to pass it in the script
```

#### Security Best Practices

✅ **DO:**
- Use environment variables for secrets
- Access via `$ENV_VAR` in bash scripts
- Keep passwords in .env file

❌ **DON'T:**
- Hardcode passwords in skill definitions
- Commit .env file to git
- Store secrets in skill descriptions
```

**Status**: Not documented
**Action Items**: Add comprehensive "Skill Variables Reference"

---

## HIGH PRIORITY CLARIFICATIONS

### Clarification 1: Installation Location

**Add to Quick Start Step 1:**

```markdown
### 1. Clone Repository

**IMPORTANT:** Clone to a permanent location **outside** your workspace.

```bash
# ✅ Good locations:
cd ~/Applications && git clone https://github.com/rjames-dev/claude-memory.git
cd ~/tools && git clone https://github.com/rjames-dev/claude-memory.git

# ❌ Bad locations:
cd ~/workspace && git clone ...  # Don't put it IN your workspace!
```

**Why?**
- Claude Memory is a **system-level tool**, not a per-project dependency
- Runs as a background service for ALL your projects
- Should be separate from your development workspace

**After cloning:**
```bash
cd claude-memory
pwd
# Remember this path - you'll run maintenance commands from here
```
```

### Clarification 2: API Keys - Required vs Optional

**Update Prerequisites section:**

```markdown
## Prerequisites

### Required

- **Docker Desktop** (v4.0+) - ✅ REQUIRED
- **Python 3** - ✅ REQUIRED (for hooks)
- **Database Password** - ✅ REQUIRED (auto-generate in .env)

### Optional (Enhanced Features)

- **Node.js v18+** - ⚠️ OPTIONAL (only for MCP search tools)
- **Anthropic API Key** - ⚠️ OPTIONAL (only for enhanced summaries)
  - Cost: ~$0.15-0.25 per enhanced summary
  - Not needed for basic functionality

### Can I use claude-memory without Node.js or API keys?

**YES!** The core features work without either:
- ✅ Auto-capture (Python hooks only)
- ✅ Database storage
- ✅ AI summaries (free Ollama)
- ✅ Embeddings
- ✅ Skills System
- ❌ MCP search tools (requires Node.js)
- ❌ Enhanced summaries (requires API key)
```

### Clarification 3: Workspace Scope

**Add warning box after CLAUDE_WORKSPACE_ROOT configuration:**

```markdown
> ⚠️ **IMPORTANT: Workspace Scope**
>
> Claude Memory and Skills **only work for projects under CLAUDE_WORKSPACE_ROOT**.
>
> **Example:**
> - `CLAUDE_WORKSPACE_ROOT=/Users/alice/workspace`
> - ✅ Works: `/Users/alice/workspace/project1`
> - ✅ Works: `/Users/alice/workspace/subdir/project2`
> - ❌ Doesn't work: `/Users/alice/Documents/other-project`
>
> **Why?**
> - Session capture requires transcript paths to be under workspace root
> - Skills execution checks project paths against workspace
> - Security: Prevents accidental capture of non-development sessions
>
> **Solution if you have multiple workspace roots:**
> - Set `CLAUDE_WORKSPACE_ROOT` to the common parent
> - Example: `/Users/alice` covers both `~/workspace` and `~/Documents/Projects`
```

---

## MEDIUM PRIORITY ADDITIONS

### Addition 1: Creating Your First Skill Tutorial

**Add after "Create Custom Skills" section:**

```markdown
### Creating Your First Skill - Step by Step

Let's create a simple skill that checks Docker container status.

#### Step 1: Plan Your Skill

```
Name: docker-status
Category: monitoring
Type: bash_script
Purpose: Show running Docker containers for claude-memory
```

#### Step 2: Create the Skill

```bash
# Use the mem-skills-create command (if available)
# Or manually via database insert

# For now, create using Python:
python3 -c "
import psycopg2
import os

# Get password from .env
password = os.popen('grep CONTEXT_DB_PASSWORD .env | cut -d= -f2').read().strip()

conn = psycopg2.connect(
    host='localhost',
    port=5435,
    database='claude_memory',
    user='memory_admin',
    password=password
)
cur = conn.cursor()

# Create skill
cur.execute('''
    INSERT INTO skills_agents (agent_name, display_name, description, category, confidence_threshold)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id
''', ('docker-status', 'Docker Status', 'Show running claude-memory containers', 'monitoring', 0.8))

skill_id = cur.fetchone()[0]

# Add trigger
cur.execute('''
    INSERT INTO skills_triggers (agent_id, trigger_phrase, match_type, confidence_threshold)
    VALUES (%s, %s, %s, %s)
''', (skill_id, 'show docker status', 'semantic', 0.75))

# Add command
script = '''#!/bin/bash
docker-compose ps
'''

cur.execute('''
    INSERT INTO skills_commands (agent_id, command_type, script_content)
    VALUES (%s, %s, %s)
''', (skill_id, 'bash_script', script))

conn.commit()
print(f'✅ Skill created with ID: {skill_id}')
"
```

#### Step 3: Generate Embedding

```bash
# Generate embedding for semantic search
python3 generate-trigger-embeddings.py --backfill
```

#### Step 4: Test Your Skill

```bash
# Search for it
/mem-skills-search "docker status"
# Should return: docker-status with high similarity

# Execute it
python3 execute-skill.py docker-status

# Check stats
/mem-skills-stats docker-status
```

#### Step 5: Iterate and Improve

- Add more trigger phrases for better matching
- Track success rate via `/mem-skills-stats`
- Adjust confidence threshold based on usage
```

---

## PROPOSED README STRUCTURE

```
# Claude Memory System

## Overview
[Existing - Good]

## 🎯 Skills System - Intelligent Automation
[Existing - Good]
  - What Are Skills?
  - Key Features
  - Quick Start
  - Example Skills
  - Semantic Search Examples
  - Create Custom Skills
  + [NEW] Skill Variables Reference ⭐ CRITICAL
  + [NEW] Creating Your First Skill - Step by Step
  - Installation Requirements
  - Performance
  - Use Cases

## Prerequisites
+ [CLARIFY] Required vs Optional ⭐ HIGH
[Existing sections...]

## Quick Start
+ [ADD] Step 0: Installation Location ⭐ HIGH
[Existing Steps 1-7...]
+ [ADD] Step 9: Initialize Skills System ⭐ CRITICAL
+ [ADD] Step 10: Verify Installation ⭐ MEDIUM

+ [NEW SECTION] Command Execution Context ⭐ CRITICAL
  - Where to Run Commands
  - Python Scripts vs Slash Commands
  - Background Service Concept

## Architecture
[Existing - Good]

## Configuration
+ [ADD] Workspace Scope Warning Box ⭐ HIGH
[Existing sections...]

## Usage
[Existing - Good]

## Maintenance
[Existing - Good]

## Troubleshooting
+ [ADD] Skills Not Found
+ [ADD] Command Execution Errors
[Existing sections...]

## API Reference
[Existing - Good]

## Development
[Existing - Good]

## Data Safety
[Existing - Good]
```

---

## ACTION ITEMS SUMMARY

### Critical (Must Do Before Release)

1. ✅ **Create skills/example-skills.json**
   - All 8 example skills in importable format
   - Complete with triggers, commands, metadata

2. ✅ **Create import-skills.py script**
   - Bulk import from JSON
   - Generate embeddings automatically
   - Validate before import

3. ✅ **Add "Skill Variables Reference" section**
   - Environment variables
   - Context variables
   - Step variables with examples

4. ✅ **Add "Command Execution Context" section**
   - WHERE to run each type of command
   - Background service explanation

5. ✅ **Add "Skills Initialization" to Quick Start**
   - Step 9: Initialize Skills System
   - Verify installation

### High Priority

6. ✅ **Clarify installation location**
   - Step 0: Where to clone repo

7. ✅ **Clarify required vs optional**
   - Prerequisites section update

8. ✅ **Add workspace scope warning**
   - Projects must be under CLAUDE_WORKSPACE_ROOT

9. ✅ **Add "Creating Your First Skill" tutorial**
   - Step-by-step walkthrough

### Medium Priority

10. ⏸️ **Add Troubleshooting entries**
    - Skills not found
    - Command execution errors

11. ⏸️ **Add verification step**
    - Quick Start Step 10: Verify Everything Works

### Low Priority (Future)

12. ⏸️ **Skill export/import documentation**
13. ⏸️ **Skill marketplace concept**
14. ⏸️ **Advanced variables guide**

---

## ESTIMATED TIME

- Critical items (1-5): **4-6 hours**
  - Create example-skills.json: 1 hour
  - Create import-skills.py: 1-2 hours
  - Write documentation sections: 2-3 hours

- High priority items (6-9): **2-3 hours**
  - Update existing sections: 1-2 hours
  - Write tutorial: 1 hour

- Medium priority items (10-11): **1 hour**

**Total**: 7-10 hours of work

---

## RECOMMENDATION

**Phase 1 (Today if possible):**
- Items 3, 4, 5 (documentation only - no code)
- Items 6, 7, 8 (quick clarifications)
- Estimated: 2-3 hours

**Phase 2 (Next session):**
- Items 1, 2 (create import system)
- Item 9 (tutorial)
- Estimated: 4-5 hours

**Phase 3 (Future):**
- Items 10-14 as needed

---

## QUESTIONS FOR USER

1. **Skills Import**: Do you have example skills already created in the database, or do we need to create the import system?

2. **Priority**: Which gaps are most critical for YOUR use case?

3. **Timing**: Should we tackle documentation-only updates now (Phase 1), or include the import system (Phase 2)?

4. **Scope**: Are there other user expectations we haven't covered?

---

**Document Created**: 2025-12-27
**Status**: Proposal - Awaiting User Feedback
