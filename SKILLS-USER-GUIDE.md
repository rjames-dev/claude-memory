# Skills System - User Guide

**Version:** Phase 1 (Manual Skills)
**Last Updated:** 2025-12-26
**Status:** Production Ready

---

## Table of Contents

1. [Introduction](#introduction)
2. [Core Concepts](#core-concepts)
3. [Getting Started](#getting-started)
4. [Creating Skills](#creating-skills)
5. [Managing Skills](#managing-skills)
6. [Executing Skills](#executing-skills)
7. [Performance Tracking](#performance-tracking)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Reference](#reference)

---

## Introduction

The Skills System allows you to create, manage, and execute reusable automation scripts that integrate with claude-memory. Skills automate repetitive tasks, track performance metrics, and build trust levels over time.

### What is a Skill?

A skill is a named, reusable automation that consists of:
- **Name**: Unique identifier (e.g., `check-db-health`)
- **Triggers**: Phrases that activate the skill
- **Command**: Bash script to execute
- **Metadata**: Category, description, parameters, prerequisites

### Why Use Skills?

- ✅ **Automate Repetitive Tasks** - Create once, reuse forever
- ✅ **Track Performance** - Monitor success rates and time saved
- ✅ **Build Trust** - High-performing skills earn trust levels
- ✅ **Share Knowledge** - Document workflows as executable skills
- ✅ **Save Time** - Reduce manual work through automation

---

## Core Concepts

### Skill Lifecycle

```
Create → List → Inspect → Execute → Track → Improve
   ↓       ↓       ↓         ↓         ↓        ↓
/create  /list   /info   /execute   Metrics  Iterate
```

### Trust Levels

Skills build trust through successful executions:

| Status | Criteria | Behavior |
|--------|----------|----------|
| 🆕 **New** | 0-4 uses | Learning phase |
| 🔄 **Developing** | 5-9 uses, 70%+ success | Building trust |
| ✅ **Stable** | 10+ uses, 90%+ success | High trust (auto-execute in Phase 2) |
| ⚠️ **Needs Improvement** | <70% success | Requires attention |

### Skill Components

**1. Basic Information**
- Name (kebab-case)
- Display name (human-friendly)
- Description
- Category (database, git, maintenance, etc.)

**2. Triggers**
- Phrases that activate the skill
- Exact matching (Phase 1)
- Multiple triggers per skill

**3. Command**
- Bash script stored in database
- Parameters (optional)
- Prerequisites (e.g., docker_running)

**4. Performance Metrics**
- Use count
- Success/failure counts
- Success rate (auto-calculated)
- Time saved
- Execution history

---

## Getting Started

### Prerequisites

1. **PostgreSQL Database** - claude-memory database running
2. **Python 3** - For skill management scripts
3. **Environment Variables** - `CONTEXT_DB_PASSWORD` set

### Quick Start

```bash
# Set database password
export CONTEXT_DB_PASSWORD="your_password_here"

# List existing skills
/mem-skills

# Create your first skill
/mem-skills-create

# View skill details
/mem-skills-info skill-name

# Execute a skill
/mem-skills-execute skill-name
```

### First Skill Example

Let's create a simple "hello world" skill:

```bash
python3 create-skill.py \
  --name "hello-world" \
  --display-name "Hello World" \
  --category "examples" \
  --description "Simple greeting skill" \
  --command-type "bash_script" \
  --script-content 'echo "Hello from Skills System!"' \
  --triggers "hello,greet,say hello"
```

Execute it:
```bash
python3 execute-skill.py hello-world
```

Output:
```
🚀 Executing skill: hello-world
   Type: bash_script
   Confidence: 0.8

Hello from Skills System!

================================================================================
✅ Skill executed successfully
   Execution Time: 0.01 seconds
   Estimated Time Saved: 0.10 seconds
   Performance Log ID: 1
================================================================================
```

---

## Creating Skills

### Skill Creation Workflow

1. **Design** - Plan what the skill will do
2. **Write Script** - Create bash script
3. **Define Metadata** - Name, category, triggers
4. **Create** - Use `/mem-skills-create`
5. **Test** - Execute with `--dry-run`
6. **Verify** - Check with `/mem-skills-info`

### Naming Conventions

**Skill Names:**
- Use kebab-case (lowercase with hyphens)
- 3-50 characters
- Alphanumeric and hyphens only
- Must start with a letter

**Examples:**
```
✅ check-db-health
✅ backup-database
✅ deploy-to-staging
❌ Check DB Health (has spaces)
❌ check_db_health (uses underscores)
❌ 123-check (starts with number)
```

### Categories

Organize skills by category:

- `git` - Git operations (commit, push, status)
- `database` - Database operations (health checks, backups)
- `maintenance` - System maintenance tasks
- `deployment` - Deployment workflows
- `testing` - Test execution
- `scaffolding` - Code generation
- `file-ops` - File operations

### Script Content

Scripts are stored in the database as TEXT:

**Simple Example:**
```bash
#!/bin/bash
echo "Task complete"
```

**With Parameters:**
```bash
#!/bin/bash
BACKUP_DIR="${1:-/tmp/backups}"
mkdir -p "$BACKUP_DIR"
pg_dump -U user -d dbname > "$BACKUP_DIR/backup.sql"
```

**With Error Handling:**
```bash
#!/bin/bash
set -e  # Exit on error

if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found"
    exit 1
fi

docker ps
echo "Docker is running"
```

### Prerequisites

Define prerequisites to validate before execution:

```bash
--prerequisites '{"docker_running": true}'
--prerequisites '{"git_repo": true}'
--prerequisites '{"docker_running": true, "git_repo": true}'
```

**Supported Prerequisites:**
- `docker_running` - Docker must be running
- `git_repo` - Current directory must be a git repository

### Parameters

Define parameters for skill configuration:

```bash
--parameters '{
  "timeout": {"type": "integer", "default": 30},
  "backup_dir": {"type": "string", "default": "/tmp/backups"}
}'
```

---

## Managing Skills

### Listing Skills

**Table Format (Default):**
```bash
/mem-skills
```

Output:
```
ID   Name                      Category        Uses   Success  Status       Triggers
========================================================================================================================
2    check-db-health           database        3      100.0%   new          4
3    backup-claude-memory      maintenance     0      0.0%     new          3
========================================================================================================================
```

**Compact Format:**
```bash
/mem-skills --format compact
```

Output:
```
🆕 check-db-health
   ID: 2 | Category: database | Uses: 3 | Success: 100.0%
   Checks PostgreSQL database health with version, size, and snapshot count
```

**JSON Format:**
```bash
/mem-skills --format json
```

**Filter by Category:**
```bash
/mem-skills --category database
```

**Sort by Success Rate:**
```bash
/mem-skills --sort success_rate
```

**Limit Results:**
```bash
/mem-skills --limit 5
```

### Viewing Skill Details

**Text Format:**
```bash
/mem-skills-info check-db-health
```

**Show Full Script:**
```bash
/mem-skills-info check-db-health --show-script
```

**JSON Format:**
```bash
/mem-skills-info check-db-health --format json
```

**Show More Execution Logs:**
```bash
/mem-skills-info check-db-health --show-logs 10
```

### Finding Skills

**By Category:**
```bash
/mem-skills --category git
```

**By Name Pattern:**
```bash
/mem-skills --format json | grep "backup"
```

**By Success Rate:**
```bash
/mem-skills --sort success_rate | head -5
```

**Most Used:**
```bash
/mem-skills --sort use_count
```

---

## Executing Skills

### Basic Execution

```bash
/mem-skills-execute skill-name
```

### Dry Run (Preview)

Test without executing:
```bash
/mem-skills-execute skill-name --dry-run
```

### With Time Saved Estimate

```bash
/mem-skills-execute backup-database --time-saved 120
```
(120 seconds saved vs manual process)

### With Context

```bash
/mem-skills-execute check-db-health \
  --request "verify database after migration" \
  --session-id "session-123" \
  --time-saved 45
```

### By ID

```bash
/mem-skills-execute --id 2
```

### Execution Output

**Success:**
```
🚀 Executing skill: check-db-health
   Type: bash_script
   Confidence: 0.8

[Skill output appears here]

================================================================================
✅ Skill executed successfully
   Execution Time: 1.25 seconds
   Time Saved: 45 seconds
   Performance Log ID: 2
================================================================================
```

**Failure:**
```
🚀 Executing skill: failing-skill
   Type: bash_script
   Confidence: 0.8

[Error output]

================================================================================
❌ Skill execution failed
   Exit Code: 1
   Execution Time: 0.50 seconds
   Error: Script exited with code 1
   Performance Log ID: 3
================================================================================
```

---

## Performance Tracking

### Metrics Tracked

Every skill execution logs:
- **Outcome** - success, failed, timeout
- **Execution Time** - Milliseconds to complete
- **Time Saved** - Manual time vs automated
- **Error Message** - If failed
- **User Request** - What triggered execution
- **Session ID** - Tracking across session
- **Timestamp** - When executed

### Viewing Performance

```bash
/mem-skills-info skill-name
```

Shows:
```
📊 PERFORMANCE METRICS
   Total Uses: 10
   Successes: 9
   Failures: 1
   Success Rate: 90.0%
   Confidence Score: 0.8
   Avg Time Saved: 45.50 seconds
   Total Time Saved: 7.58 minutes

📜 RECENT EXECUTION HISTORY (Last 5)

   1. ✅ SUCCESS - 2025-12-26 21:41:34
      Execution Time: 1.25 seconds
      Time Saved: 45.00 seconds
      Request: check database health
```

### Success Rate Calculation

```
success_rate = (success_count / use_count) × 100
```

Auto-calculated by database on each execution.

### Time Saved

**Auto-calculated** (if not specified):
```
time_saved = execution_time × 10
```
(Heuristic: manual tasks take 10x longer)

**Manually specified:**
```bash
/mem-skills-execute backup-db --time-saved 300
```
(300 seconds = 5 minutes)

---

## Best Practices

### Skill Design

**1. Single Responsibility**
- One skill = one task
- ✅ `check-db-health` - checks health
- ❌ `check-and-backup-db` - does too much

**2. Descriptive Names**
- Use clear, action-oriented names
- ✅ `deploy-to-staging`
- ❌ `deploy`

**3. Multiple Triggers**
- Add variations users might say
- `"backup database", "backup db", "create backup"`

**4. Error Handling**
- Always use `set -e` in bash scripts
- Provide meaningful error messages
- Return appropriate exit codes

**5. Idempotent**
- Safe to run multiple times
- Check state before changing
- Use `mkdir -p` not `mkdir`

### Script Best Practices

```bash
#!/bin/bash
set -e  # Exit on error
set -u  # Error on undefined variables
set -o pipefail  # Catch errors in pipes

# Validate inputs
if [ -z "${1:-}" ]; then
    echo "Error: Missing required argument"
    exit 1
fi

# Check prerequisites
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not installed"
    exit 1
fi

# Do work
echo "Starting task..."
# ... task logic ...
echo "Task complete"

# Always exit with status
exit 0
```

### Testing Skills

**1. Dry Run First:**
```bash
/mem-skills-execute skill-name --dry-run
```

**2. Test in Safe Environment:**
- Use test databases
- Use staging environments
- Avoid production initially

**3. Monitor First Executions:**
- Watch output carefully
- Verify expected behavior
- Check execution logs

**4. Iterate:**
- Fix issues
- Update script content (Phase 2: edit-skill.py)
- Re-test

### Security

**1. Never Store Secrets in Scripts**
```bash
# ❌ Bad
PASSWORD="hardcoded_secret"

# ✅ Good
PASSWORD="${DB_PASSWORD}"  # From environment
```

**2. Validate Inputs**
```bash
# Validate identifier before using in queries
if [[ ! "$TABLE_NAME" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
    echo "Invalid table name"
    exit 1
fi
```

**3. Use Least Privilege**
- Don't run as root
- Use minimal permissions
- Validate prerequisites

**4. Audit Execution**
- Review execution logs
- Monitor failure patterns
- Track who runs what

---

## Troubleshooting

### Common Issues

**1. Skill Not Found**
```
❌ Skill 'my-skill' not found
```

**Solution:**
```bash
# List all skills
/mem-skills

# Check exact name
/mem-skills --format json | grep "my-skill"
```

**2. Invalid Skill Name**
```
❌ Invalid skill name: Skill name must be kebab-case
```

**Solution:**
- Use lowercase letters, numbers, hyphens only
- Start with a letter
- No spaces or underscores

**3. Duplicate Skill**
```
❌ Skill 'backup-db' already exists (ID: 5)
```

**Solution:**
- Choose a different name
- Or delete existing skill (Phase 2)

**4. Execution Failed**
```
❌ Skill execution failed
   Exit Code: 1
   Error: Script exited with code 1
```

**Solution:**
```bash
# View full script
/mem-skills-info skill-name --show-script

# Check execution logs
/mem-skills-info skill-name --show-logs 5

# Test manually
# Copy script content and run in terminal
```

**5. Prerequisite Failed**
```
❌ Prerequisite check failed: Docker is not running
```

**Solution:**
- Start Docker: `docker ps`
- Or remove prerequisite from skill

**6. Database Connection Failed**
```
❌ Database connection failed
```

**Solution:**
```bash
# Check password is set
echo $CONTEXT_DB_PASSWORD

# Check database is running
docker ps | grep claude-context-db

# Test connection
psql -h localhost -p 5435 -U memory_admin -d claude_memory
```

### Debugging Skills

**1. Use Dry Run:**
```bash
/mem-skills-execute skill-name --dry-run
```

**2. Add Debug Output:**
```bash
#!/bin/bash
set -x  # Enable debug mode
echo "Debug: Starting script"
# ... rest of script ...
```

**3. Check Execution Logs:**
```bash
/mem-skills-info skill-name --show-logs 10
```

**4. Test Script Manually:**
```bash
# Extract script
/mem-skills-info skill-name --show-script > /tmp/test.sh
chmod +x /tmp/test.sh

# Run manually
/tmp/test.sh
```

---

## Reference

### Command Quick Reference

```bash
# Create skill
/mem-skills-create
python3 create-skill.py --name "skill-name" ...

# List skills
/mem-skills
/mem-skills --category database
/mem-skills --sort success_rate
/mem-skills --format json

# View skill details
/mem-skills-info skill-name
/mem-skills-info skill-name --show-script
/mem-skills-info skill-name --format json

# Execute skill
/mem-skills-execute skill-name
/mem-skills-execute skill-name --dry-run
/mem-skills-execute skill-name --time-saved 60
/mem-skills-execute --id 2

# Test integration
python3 test-skills-integration.py
```

### File Locations

```
claude-memory/
├── create-skill.py              # Skill creation tool
├── list-skills.py               # Skill listing tool
├── skill-info.py                # Skill details tool
├── execute-skill.py             # Skill execution engine
├── test-skills-integration.py   # Integration tests
├── schema/
│   └── add-skills-tables.sql    # Database schema
└── .claude/commands/
    ├── mem-skills-create.md     # Create command docs
    ├── mem-skills.md            # List command docs
    ├── mem-skills-info.md       # Info command docs
    └── mem-skills-execute.md    # Execute command docs
```

### Database Tables

- `skills_agents` - Skill metadata and metrics
- `skills_triggers` - Trigger phrases
- `skills_commands` - Command definitions
- `skills_performance_log` - Execution history
- `skills_patterns` - Learned patterns (Phase 2)

### Environment Variables

```bash
# Required
export CONTEXT_DB_PASSWORD="your_password"

# Optional (defaults shown)
export DB_HOST="localhost"
export DB_PORT="5435"
```

### Skill Status Reference

| Icon | Status | Criteria | Description |
|------|--------|----------|-------------|
| 🆕 | new | 0-4 uses | Learning phase |
| 🔄 | developing | 5-9 uses, 70%+ success | Building trust |
| ✅ | stable | 10+ uses, 90%+ success | High trust |
| ⚠️ | needs_improvement | <70% success | Requires attention |

### Exit Codes

- `0` - Success
- `1` - General failure
- `timeout` - Execution exceeded timeout (5 minutes)

---

## Examples

### Example 1: Database Health Check

```bash
python3 create-skill.py \
  --name "check-db-health" \
  --display-name "Database Health Check" \
  --category "database" \
  --description "Checks PostgreSQL database health" \
  --command-type "bash_script" \
  --script-content '#!/bin/bash
echo "=== Database Health Check ==="
psql -U memory_admin -d claude_memory -c "SELECT version();"
psql -U memory_admin -d claude_memory -c "SELECT COUNT(*) FROM context_snapshots;"
echo "=== Health Check Complete ==="' \
  --triggers "check db health,verify database,database status" \
  --prerequisites '{"docker_running": true}'
```

### Example 2: Git Status

```bash
python3 create-skill.py \
  --name "git-status-summary" \
  --display-name "Git Status Summary" \
  --category "git" \
  --description "Shows git status with branch and uncommitted changes" \
  --command-type "bash_script" \
  --script-content '#!/bin/bash
echo "Branch: $(git rev-parse --abbrev-ref HEAD)"
echo "Status:"
git status --short
echo "Recent commits:"
git log --oneline -5' \
  --triggers "git status,show git status,check git" \
  --prerequisites '{"git_repo": true}'
```

### Example 3: Backup with Parameters

```bash
python3 create-skill.py \
  --name "backup-database" \
  --display-name "Backup Database" \
  --category "maintenance" \
  --description "Creates timestamped database backup" \
  --command-type "bash_script" \
  --script-content '#!/bin/bash
BACKUP_DIR="${1:-/tmp/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
docker exec claude-context-db pg_dump -U memory_admin claude_memory | gzip > "$BACKUP_DIR/backup_$TIMESTAMP.sql.gz"
echo "Backup created: $BACKUP_DIR/backup_$TIMESTAMP.sql.gz"
ls -lh "$BACKUP_DIR/backup_$TIMESTAMP.sql.gz"' \
  --triggers "backup database,create backup,db backup" \
  --parameters '{"backup_dir": {"type": "string", "default": "/tmp/backups"}}' \
  --prerequisites '{"docker_running": true}'
```

---

## Getting Help

- **Documentation:** This guide + slash command documentation
- **Integration Tests:** `python3 test-skills-integration.py`
- **Test Results:** `SKILLS-INTEGRATION-TEST-RESULTS.md`
- **Phase 1 Roadmap:** `SKILLS-PHASE1-ROADMAP.md`
- **Database Schema:** `schema/add-skills-tables.sql`

---

**Version:** Phase 1 - Manual Skills
**Status:** Production Ready
**Last Updated:** 2025-12-26
