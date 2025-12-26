# Skills System - Phase 1 Implementation Roadmap

**Phase:** Foundation (Weeks 1-2)
**Goal:** Basic skill storage, manual creation, and simple execution
**Status:** Planning
**Started:** TBD
**Target Completion:** TBD

---

## Phase 1 Overview

### What We're Building

A minimal viable skills system that allows:
1. **Manual skill creation** via `/mem-skills-create` command
2. **Skill storage** in PostgreSQL with metadata
3. **Basic execution** of bash script skills with user approval
4. **Skill listing** and inspection via `/mem-skills` and `/mem-skills-show`
5. **Simple trigger matching** (exact phrase only, no semantic search yet)

### What We're NOT Building Yet

- ❌ Automatic pattern detection (Phase 3)
- ❌ Semantic trigger matching (Phase 2)
- ❌ Tool sequence execution (Phase 2)
- ❌ Agent spawning (Phase 2)
- ❌ Skill suggestions based on patterns (Phase 3)
- ❌ Performance analytics (Phase 2)

---

## Milestones

### Milestone 1: Database Foundation (Days 1-2)

**Goal:** Database schema in place and tested

**Tasks:**
- [ ] Review schema: `schema/add-skills-tables.sql`
- [ ] Run migration on development database
- [ ] Verify all tables created
- [ ] Verify all indexes created
- [ ] Verify all views work
- [ ] Test basic CRUD operations

**Validation:**
```sql
-- Test queries
SELECT * FROM skills_agents LIMIT 1;
SELECT * FROM v_skills_dashboard;
INSERT INTO skills_agents (agent_name, display_name, category)
VALUES ('test-skill', 'Test Skill', 'testing');
```

**Deliverables:**
- ✅ Migration script executed successfully
- ✅ All 5 tables exist
- ✅ All 4 views return data
- ✅ Can insert/query test records

---

### Milestone 2: Skill Creation (Days 3-5)

**Goal:** Users can manually create bash script skills

**Tasks:**
- [ ] Create `create-skill.py` script
- [ ] Implement CLI argument parsing
- [ ] Implement skill validation (check for duplicates)
- [ ] Implement trigger phrase creation
- [ ] Implement bash script storage
- [ ] Create `/mem-skills-create` skill file
- [ ] Write tests for skill creation
- [ ] Document usage in README

**Implementation Details:**

#### create-skill.py

```python
#!/usr/bin/env python3
"""
Create a new skill manually

Usage:
  python3 create-skill.py --name "git-commit-protocol" \
                           --display-name "Git Commit (Our Protocol)" \
                           --category "git" \
                           --script-path "/path/to/script.sh" \
                           --triggers "commit changes,create commit" \
                           --description "Commits using our protocol"
"""

import argparse
import psycopg2
import json
from datetime import datetime

def create_skill(args):
    """Create a new skill in the database"""

    # Connect to database
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="claude_memory",
        user="postgres",
        password=os.environ.get("POSTGRES_PASSWORD")
    )

    cur = conn.cursor()

    try:
        # Check for duplicates
        cur.execute(
            "SELECT id FROM skills_agents WHERE agent_name = %s",
            (args.name,)
        )
        if cur.fetchone():
            raise ValueError(f"Skill '{args.name}' already exists")

        # Insert skill
        cur.execute("""
            INSERT INTO skills_agents
            (agent_name, display_name, description, category, project_path, created_by)
            VALUES (%s, %s, %s, %s, %s, 'user')
            RETURNING id
        """, (
            args.name,
            args.display_name,
            args.description,
            args.category,
            args.project_path
        ))

        skill_id = cur.fetchone()[0]

        # Insert triggers
        triggers = args.triggers.split(',')
        for trigger in triggers:
            cur.execute("""
                INSERT INTO skills_triggers
                (agent_id, trigger_phrase, match_type, confidence_threshold)
                VALUES (%s, %s, 'exact', 1.0)
            """, (skill_id, trigger.strip()))

        # Insert command definition
        cur.execute("""
            INSERT INTO skills_commands
            (agent_id, command_type, script_path, parameters, prerequisites)
            VALUES (%s, 'bash_script', %s, %s, %s)
        """, (
            skill_id,
            args.script_path,
            json.dumps(args.parameters or {}),
            json.dumps(args.prerequisites or {})
        ))

        conn.commit()

        print(f"✅ Skill created: {args.name} (ID: {skill_id})")
        print(f"   Triggers: {len(triggers)}")
        print(f"   Type: bash_script")
        print(f"   Script: {args.script_path}")

        return skill_id

    except Exception as e:
        conn.rollback()
        print(f"❌ Error creating skill: {e}")
        raise
    finally:
        cur.close()
        conn.close()
```

#### /mem-skills-create Skill File

Location: `.claude/commands/mem-skills-create.md`

```markdown
# /mem-skills-create

Create a new skill manually

## Usage

This command launches an interactive skill creation wizard.

## What it does

1. Prompts for skill details:
   - Skill name (kebab-case)
   - Display name (human-friendly)
   - Category (git, database, scaffolding, etc.)
   - Description
   - Command type (bash_script, tool_sequence, agent_spawn)
   - Trigger phrases

2. Based on command type:
   - **Bash script**: Path to script file
   - **Tool sequence**: Step-by-step tool definitions
   - **Agent spawn**: Agent configuration

3. Saves to database
4. Confirms creation

## Example

```bash
/mem-skills-create
```

Interactive prompts:
```
Skill name: deploy-to-staging
Display name: Deploy to Staging
Category: deployment
Description: Deploy current branch to staging with health checks
Command type: [1] Bash script, [2] Tool sequence, [3] Agent spawn
Choice: 1
Script path: /path/to/deploy.sh
Triggers (comma-separated): deploy to staging, push to staging
```

## Arguments

python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/create-skill.py --interactive

```

**Validation:**
- [ ] Can create skill via command line
- [ ] Can create skill via `/mem-skills-create` skill
- [ ] Duplicate detection works
- [ ] Triggers are saved correctly
- [ ] Can see skill in database

**Deliverables:**
- ✅ `create-skill.py` script working
- ✅ `/mem-skills-create` skill file
- ✅ Documentation updated
- ✅ At least 2 test skills created

---

### Milestone 3: Skill Listing (Days 6-7)

**Goal:** Users can see all available skills

**Tasks:**
- [ ] Create `list-skills.py` script
- [ ] Implement filtering (by category, project, status)
- [ ] Implement formatted output
- [ ] Create `/mem-skills` skill file
- [ ] Write tests
- [ ] Document usage

**Implementation Details:**

#### list-skills.py

```python
#!/usr/bin/env python3
"""
List all skills

Usage:
  python3 list-skills.py [--category git] [--project /path/to/project]
"""

import argparse
import psycopg2
from tabulate import tabulate

def list_skills(category=None, project_path=None):
    """List all active skills with optional filtering"""

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    query = """
        SELECT
            agent_name,
            display_name,
            category,
            use_count,
            success_rate,
            CASE WHEN project_path IS NULL THEN 'Global' ELSE 'Project' END as scope
        FROM v_skills_dashboard
        WHERE 1=1
    """

    params = []

    if category:
        query += " AND category = %s"
        params.append(category)

    if project_path:
        query += " AND (project_path = %s OR project_path IS NULL)"
        params.append(project_path)

    query += " ORDER BY category, use_count DESC"

    cur.execute(query, params)
    skills = cur.fetchall()

    # Group by category
    by_category = {}
    for skill in skills:
        cat = skill[2]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(skill)

    # Print formatted
    print(f"\n📚 Skills Library ({len(skills)} skills)\n")

    for cat, cat_skills in sorted(by_category.items()):
        print(f"{cat.capitalize()} ({len(cat_skills)} skills)")
        for skill in cat_skills:
            name, display, _, uses, success, scope = skill
            status = "✅" if success >= 90 else "⚠️" if success >= 70 else "❌"
            print(f"  {name:30} {status} {uses:3} uses, {success:.0f}% success  [{scope}]")
        print()

    cur.close()
    conn.close()
```

#### /mem-skills Skill File

```markdown
# /mem-skills

List all available skills

## Usage

```bash
# List all skills
/mem-skills

# List skills in specific category
/mem-skills git
/mem-skills database
```

## Output Format

```
📚 Skills Library (12 skills)

Git (4 skills)
  git-commit-protocol       ✅  15 uses, 100% success  [Global]
  git-create-pr            ✅   8 uses, 100% success  [Global]
  git-branch-cleanup       ✅   3 uses, 100% success  [Global]

Database (3 skills)
  check-db-health          ✅  12 uses,  92% success  [Global]
  migrate-database         ✅   6 uses, 100% success  [Global]
```

## Arguments

python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/list-skills.py "$@"
```

**Validation:**
- [ ] Lists all skills correctly
- [ ] Filtering by category works
- [ ] Output is readable and organized
- [ ] Shows correct usage counts

**Deliverables:**
- ✅ `list-skills.py` script working
- ✅ `/mem-skills` skill file
- ✅ Documentation updated

---

### Milestone 4: Skill Details (Days 8-9)

**Goal:** Users can inspect detailed skill information

**Tasks:**
- [ ] Create `show-skill.py` script
- [ ] Implement formatted detail view
- [ ] Show triggers, commands, performance
- [ ] Create `/mem-skills-show` skill file
- [ ] Write tests
- [ ] Document usage

**Implementation Details:**

#### show-skill.py

```python
#!/usr/bin/env python3
"""
Show detailed information about a skill

Usage:
  python3 show-skill.py git-commit-protocol
"""

import argparse
import psycopg2
import json

def show_skill(skill_name):
    """Display detailed skill information"""

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    # Get skill details
    cur.execute("""
        SELECT
            sa.agent_name,
            sa.display_name,
            sa.description,
            sa.category,
            sa.project_path,
            sa.use_count,
            sa.success_rate,
            sa.avg_time_saved_ms,
            sa.last_used,
            sa.version,
            sa.confidence_score,
            sa.created_at
        FROM skills_agents sa
        WHERE sa.agent_name = %s
    """, (skill_name,))

    skill = cur.fetchone()
    if not skill:
        print(f"❌ Skill not found: {skill_name}")
        return

    # Get triggers
    cur.execute("""
        SELECT trigger_phrase, match_type, confidence_threshold
        FROM skills_triggers
        WHERE agent_id = (SELECT id FROM skills_agents WHERE agent_name = %s)
    """, (skill_name,))
    triggers = cur.fetchall()

    # Get command
    cur.execute("""
        SELECT command_type, script_path, command_definition, parameters, prerequisites
        FROM skills_commands
        WHERE agent_id = (SELECT id FROM skills_agents WHERE agent_name = %s)
        ORDER BY version DESC
        LIMIT 1
    """, (skill_name,))
    command = cur.fetchone()

    # Format output
    print(f"\n{skill[0]}")
    print("━" * 60)
    print(f"\nDisplay Name: {skill[1]}")
    print(f"Category: {skill[3]}")
    print(f"Scope: {'Global' if skill[4] is None else f'Project: {skill[4]}'}")
    print(f"\nDescription:\n  {skill[2] or 'No description'}")

    print(f"\nPerformance:")
    print(f"  Uses: {skill[5]}")
    print(f"  Success Rate: {skill[6]:.0f}%")
    if skill[7]:
        print(f"  Avg Time Saved: {skill[7] / 1000:.1f} seconds")
    if skill[8]:
        print(f"  Last Used: {skill[8]}")

    print(f"\nTriggers ({len(triggers)}):")
    for trigger in triggers:
        print(f"  - \"{trigger[0]}\" ({trigger[1]}, threshold: {trigger[2]})")

    if command:
        cmd_type, script, definition, params, prereqs = command
        print(f"\nCommand Type: {cmd_type}")
        if script:
            print(f"  Script: {script}")
        if definition:
            print(f"  Definition: {json.dumps(definition, indent=2)}")
        if params:
            print(f"  Parameters: {json.dumps(params, indent=2)}")
        if prereqs:
            print(f"  Prerequisites: {json.dumps(prereqs, indent=2)}")

    print(f"\nMetadata:")
    print(f"  Version: {skill[9]}")
    print(f"  Confidence: {skill[10]:.2f}")
    print(f"  Created: {skill[11]}")
    print()

    cur.close()
    conn.close()
```

**Validation:**
- [ ] Shows complete skill information
- [ ] Formatting is clear and readable
- [ ] Handles missing optional fields
- [ ] Works for all skill types

**Deliverables:**
- ✅ `show-skill.py` script working
- ✅ `/mem-skills-show` skill file
- ✅ Documentation updated

---

### Milestone 5: Basic Execution (Days 10-12)

**Goal:** Users can execute bash script skills with approval

**Tasks:**
- [ ] Create `execute-skill.py` script
- [ ] Implement prerequisite checking
- [ ] Implement user approval prompt
- [ ] Implement bash script execution
- [ ] Implement success/failure detection
- [ ] Implement performance logging
- [ ] Write tests for execution
- [ ] Document execution flow

**Implementation Details:**

#### execute-skill.py

```python
#!/usr/bin/env python3
"""
Execute a skill

Usage:
  python3 execute-skill.py git-commit-protocol --approve --param branch=main
"""

import argparse
import psycopg2
import subprocess
import json
import time
from datetime import datetime

def check_prerequisites(prereqs):
    """Check if prerequisites are met"""
    if not prereqs:
        return True, None

    # Check git_repo
    if prereqs.get('git_repo'):
        result = subprocess.run(['git', 'rev-parse', '--git-dir'],
                              capture_output=True, text=True)
        if result.returncode != 0:
            return False, "Not in a git repository"

    # Check has_changes
    if prereqs.get('has_changes'):
        result = subprocess.run(['git', 'status', '--porcelain'],
                              capture_output=True, text=True)
        if not result.stdout.strip():
            return False, "No changes to commit"

    return True, None

def execute_bash_skill(skill_id, skill_name, script_path, params, prereqs, user_request):
    """Execute a bash script skill"""

    print(f"\n⚡ Executing skill: {skill_name}")

    # Check prerequisites
    prereqs_met, error = check_prerequisites(prereqs)
    if not prereqs_met:
        print(f"❌ Prerequisites not met: {error}")
        return {
            'outcome': 'failed',
            'error': error
        }

    # Execute script
    start_time = time.time()

    try:
        result = subprocess.run(
            [script_path] + [str(v) for v in params.values()],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        execution_time_ms = int((time.time() - start_time) * 1000)

        if result.returncode == 0:
            print(f"✅ Success! ({execution_time_ms / 1000:.1f}s)")
            print(result.stdout)

            outcome = 'success'
            error = None
        else:
            print(f"❌ Failed! ({execution_time_ms / 1000:.1f}s)")
            print(result.stderr)

            outcome = 'failed'
            error = result.stderr

        # Log performance
        log_performance(skill_id, outcome, execution_time_ms, error, user_request)

        return {
            'outcome': outcome,
            'execution_time_ms': execution_time_ms,
            'stdout': result.stdout,
            'stderr': result.stderr
        }

    except subprocess.TimeoutExpired:
        print(f"❌ Timeout after 5 minutes")
        log_performance(skill_id, 'timeout', 300000, 'Execution timeout', user_request)
        return {
            'outcome': 'timeout',
            'error': 'Execution timeout'
        }

def log_performance(skill_id, outcome, execution_time_ms, error, user_request):
    """Log execution to performance log"""

    conn = psycopg2.connect(...)
    cur = conn.cursor()

    try:
        # Insert performance log
        cur.execute("""
            INSERT INTO skills_performance_log
            (agent_id, outcome, execution_time_ms, error_message, user_request, executed_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (skill_id, outcome, execution_time_ms, error, user_request))

        # Update skill counters
        if outcome == 'success':
            cur.execute("""
                UPDATE skills_agents
                SET use_count = use_count + 1,
                    success_count = success_count + 1,
                    last_used = NOW()
                WHERE id = %s
            """, (skill_id,))
        else:
            cur.execute("""
                UPDATE skills_agents
                SET use_count = use_count + 1,
                    failure_count = failure_count + 1,
                    last_used = NOW()
                WHERE id = %s
            """, (skill_id,))

        conn.commit()

    finally:
        cur.close()
        conn.close()
```

**Validation:**
- [ ] Prerequisites checking works
- [ ] User approval prompt appears
- [ ] Bash scripts execute correctly
- [ ] Performance is logged
- [ ] Counters update correctly
- [ ] Timeouts work

**Deliverables:**
- ✅ `execute-skill.py` script working
- ✅ Performance logging functional
- ✅ Tests passing
- ✅ Documentation updated

---

### Milestone 6: Integration Testing (Days 13-14)

**Goal:** End-to-end workflow tested and documented

**Tasks:**
- [ ] Create example skill (test-simple-echo.sh)
- [ ] Test full workflow: create → list → show → execute
- [ ] Test error handling
- [ ] Test prerequisite checking
- [ ] Document example workflows
- [ ] Update main README
- [ ] Create quick-start guide

**Test Scenarios:**

#### Scenario 1: Create and Execute Simple Skill

```bash
# 1. Create simple test script
cat > /tmp/test-echo.sh <<'EOF'
#!/bin/bash
echo "Hello from skill: $1"
exit 0
EOF
chmod +x /tmp/test-echo.sh

# 2. Create skill
/mem-skills-create
# Name: test-echo
# Display: Test Echo
# Category: testing
# Type: bash_script
# Script: /tmp/test-echo.sh
# Triggers: test echo

# 3. List skills
/mem-skills testing
# Should show: test-echo

# 4. Show details
/mem-skills-show test-echo
# Should show complete definition

# 5. Execute (would need manual approval in real flow)
python3 execute-skill.py test-echo --approve --param message="test"
# Should output: "Hello from skill: test"

# 6. Verify performance logged
psql -c "SELECT * FROM skills_performance_log WHERE agent_id = (SELECT id FROM skills_agents WHERE agent_name = 'test-echo')"
```

#### Scenario 2: Prerequisites Blocking

```bash
# Create skill requiring git repo
/mem-skills-create
# Name: test-prereq
# Prerequisites: {"git_repo": true}

# Try to execute outside git repo
cd /tmp
python3 execute-skill.py test-prereq
# Should fail: "Prerequisites not met: Not in a git repository"
```

**Deliverables:**
- ✅ All test scenarios pass
- ✅ Example skills documented
- ✅ Quick-start guide created
- ✅ Main README updated

---

## Success Criteria

Phase 1 is complete when:

- [  ] All 6 milestones delivered
- [ ] Database schema in production
- [ ] Can create skills manually
- [ ] Can list and inspect skills
- [ ] Can execute bash script skills
- [ ] Performance is logged
- [ ] Documentation is complete
- [ ] At least 3 real skills created and tested

---

## File Structure

After Phase 1, the structure should be:

```
claude-memory/
├── schema/
│   ├── init.sql (existing)
│   ├── add-agent-tables.sql (existing)
│   └── add-skills-tables.sql (NEW)
├── docs/
│   ├── SKILLS-SYSTEM-ARCHITECTURE.md (NEW)
│   ├── SKILLS-PHASE1-ROADMAP.md (NEW - this file)
│   └── SKILLS-QUICK-START.md (NEW)
├── create-skill.py (NEW)
├── list-skills.py (NEW)
├── show-skill.py (NEW)
├── execute-skill.py (NEW)
├── .claude/
│   └── commands/
│       ├── mem-skills-create.md (NEW)
│       ├── mem-skills.md (NEW)
│       └── mem-skills-show.md (NEW)
├── scripts/
│   └── examples/
│       ├── test-echo.sh (NEW - example skill)
│       └── check-git-status.sh (NEW - example skill)
└── README.md (UPDATED)
```

---

## Next Steps (Phase 2)

After Phase 1 is complete, Phase 2 will add:

1. **Semantic trigger matching** (embedding-based)
2. **Tool sequence execution**
3. **Agent spawning**
4. **Performance analytics** (/mem-skills-stats)
5. **Export/import** functionality

See `SKILLS-PHASE2-ROADMAP.md` (to be created)

---

## Questions & Decisions

### Open Questions

1. **Database connection configuration**
   - Where should connection params be stored?
   - Use existing claude-memory database or separate?
   - **Decision:** Use existing claude_memory database

2. **Skill script storage**
   - Store scripts in database or filesystem?
   - **Decision:** Filesystem (store path in DB, scripts in `~/.claude-memory/skills/scripts/`)

3. **User approval UI**
   - How to prompt for approval in CLI?
   - **Decision:** Use Python `input()` for now, enhance in Phase 2

### Decisions Made

- ✅ Use PostgreSQL (existing claude_memory database)
- ✅ Phase 1 focuses on bash scripts only
- ✅ Exact phrase matching only (no embeddings in Phase 1)
- ✅ Manual creation only (no pattern detection yet)
- ✅ User approval required for all executions

---

## Resources

- **Architecture:** `docs/SKILLS-SYSTEM-ARCHITECTURE.md`
- **Database Schema:** `schema/add-skills-tables.sql`
- **Existing Agent System:** `schema/add-agent-tables.sql` (reference)
- **Main claude-memory:** `schema/init.sql` (reference)

---

**Document Version:** 1.0
**Last Updated:** 2025-12-26
**Status:** Planning - Ready to Start Phase 1
