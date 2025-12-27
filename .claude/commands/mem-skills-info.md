Display comprehensive information about a specific skill.

**Command**: `/mem-skills-info <skill_name>`

**What this does:**
- Shows complete details about a specific skill
- Displays all triggers and command configuration
- Shows performance metrics and execution history
- Reveals script content and prerequisites
- Provides execution logs with context

**Use cases:**
- **Debug skills** - See full configuration and execution history
- **Review performance** - Check success rate and time saved
- **Audit changes** - View version and update history
- **Understand triggers** - See all trigger phrases and match types
- **Inspect scripts** - View bash script content before execution

**What you get:**
- Basic info (ID, name, description, category, scope)
- Status category and trust level indicator
- Complete performance metrics
- All triggers with confidence thresholds
- Command definition (script content, parameters, prerequisites)
- Recent execution history with detailed logs
- Timestamps (created, updated, last used)

**Usage:**
```bash
# Show skill by name
/mem-skills-info check-db-health

# Show skill by ID
/mem-skills-info --id 2

# Show full script content
/mem-skills-info check-db-health --show-script

# Show last 10 execution logs
/mem-skills-info check-db-health --show-logs 10

# Output as JSON
/mem-skills-info check-db-health --format json
```

**Example Output (Text Format):**

```
================================================================================
SKILL INFORMATION: check-db-health
================================================================================

📋 BASIC INFORMATION
   ID: 2
   Name: check-db-health
   Display Name: Database Health Check
   Description: Checks PostgreSQL database health with version, size, and snapshot count
   Category: database
   Scope: global
   Status: 🆕 new
   Active: Yes
   Created By: manual
   Version: 1

📊 PERFORMANCE METRICS
   Total Uses: 1
   Successes: 1
   Failures: 0
   Success Rate: 100.0%
   Confidence Score: 0.8
   Total Time Saved: 0.75 minutes

🕐 TIMESTAMPS
   Created: 2025-12-26 20:34:47.735837+00:00
   Updated: 2025-12-26 20:37:43.127592+00:00
   Last Used: 2025-12-26 20:37:43.127592+00:00

🎯 TRIGGERS (4)
   1. [✓] "check database health"
      Type: exact | Confidence: 1.0
   2. [✓] "check db health"
      Type: exact | Confidence: 1.0
   3. [✓] "verify database status"
      Type: exact | Confidence: 1.0
   4. [✓] "database health check"
      Type: exact | Confidence: 1.0

⚙️  COMMAND DEFINITION
   Type: bash_script
   Command ID: 2
   Script Length: 716 characters

   Script Preview:
   ----------------------------------------------------------------------------
   #!/bin/bash
   echo "=== PostgreSQL Database Health Check ==="
   ...
   (truncated, use --show-script for full content)
   ----------------------------------------------------------------------------

   Prerequisites:
      docker_running: True

   Created: 2025-12-26 20:36:41.276115+00:00

📜 RECENT EXECUTION HISTORY (Last 1)

   1. ✅ SUCCESS - 2025-12-26 20:37:43.127592+00:00
      Execution Time: 1.25 seconds
      Time Saved: 45.00 seconds
      Request: check database health
      Match Score: 1.00

================================================================================
```

**Status Icons:**
- 🆕 **new**: Less than 5 uses (learning phase)
- ✅ **stable**: 10+ uses, 90%+ success rate (high trust)
- 🔄 **developing**: 5-9 uses, 70%+ success rate (building trust)
- ⚠️ **needs_improvement**: Less than 70% success rate (requires attention)

**Trigger Indicators:**
- [✓] Active trigger
- [✗] Inactive trigger

**Execution Outcome Icons:**
- ✅ Success
- ❌ Failed, user_rejected, timeout, user_corrected

**Arguments:**
```
POSITIONAL:
  skill_name              Skill name (e.g., "check-db-health")

OPTIONS:
  --id ID                 Use skill ID instead of name
  --format FORMAT         Output format: text (default) or json
  --show-script           Show full script content (default: preview only)
  --show-logs N           Number of execution logs to show (default: 5)
```

**Examples:**

**View skill by name:**
```bash
/mem-skills-info check-db-health
```

**View skill by ID:**
```bash
/mem-skills-info --id 2
```

**Show full bash script:**
```bash
/mem-skills-info check-db-health --show-script
```

**Show last 10 executions:**
```bash
/mem-skills-info backup-claude-memory --show-logs 10
```

**Export as JSON for processing:**
```bash
/mem-skills-info check-db-health --format json > skill-config.json
```

**Performance Metrics Explained:**
- **Total Uses**: Number of times skill has been executed
- **Successes**: Executions that completed successfully
- **Failures**: Executions that failed or were rejected
- **Success Rate**: (successes / total uses) × 100
- **Confidence Score**: Base confidence level (0-1)
- **Avg Time Saved**: Average time saved per execution
- **Total Time Saved**: Cumulative time saved across all executions

**Execution History Fields:**
- **Outcome**: success, failed, user_rejected, user_corrected, timeout
- **Execution Time**: How long the command took to run
- **Time Saved**: Estimated time saved by automation
- **Request**: User request that triggered the skill
- **Match Score**: Similarity score (0-1) for trigger matching
- **Error**: Error message if execution failed
- **Feedback**: User feedback on execution
- **Session**: Session ID where skill was executed

**Script Preview vs Full Content:**

By default, script content is truncated to 500 characters. Use `--show-script` to see the complete script:

```bash
# Preview (default)
/mem-skills-info backup-claude-memory
# Shows: First 500 chars + "... (truncated, use --show-script for full content)"

# Full script
/mem-skills-info backup-claude-memory --show-script
# Shows: Complete bash script
```

**JSON Output Structure:**
```json
{
  "skill": {
    "id": 2,
    "agent_name": "check-db-health",
    "display_name": "Database Health Check",
    "description": "...",
    "category": "database",
    "scope": "global",
    "use_count": 1,
    "success_rate": 100.0,
    ...
  },
  "triggers": [
    {
      "id": 1,
      "trigger_phrase": "check database health",
      "match_type": "exact",
      "confidence_threshold": 1.0,
      "is_active": true
    }
  ],
  "command": {
    "id": 2,
    "command_type": "bash_script",
    "script_content": "#!/bin/bash\n...",
    "parameters": {...},
    "prerequisites": {...}
  },
  "performance_logs": [
    {
      "id": 1,
      "outcome": "success",
      "time_saved_ms": 45000,
      "executed_at": "2025-12-26T20:37:43.127592+00:00",
      ...
    }
  ]
}
```

**Use Cases:**

**1. Debug Failed Skill:**
```bash
/mem-skills-info problematic-skill --show-logs 10
# Review last 10 executions to find patterns
```

**2. Verify Skill Configuration:**
```bash
/mem-skills-info deploy-to-staging --show-script
# Review script before promoting to production
```

**3. Audit Skill Performance:**
```bash
/mem-skills-info backup-database
# Check success rate and total time saved
```

**4. Export Skill Definition:**
```bash
/mem-skills-info git-commit-protocol --format json > skill-backup.json
# Backup skill configuration
```

**5. Check Trigger Phrases:**
```bash
/mem-skills-info check-db-health
# Review all trigger phrases to add more variations
```

**Notes:**
- Script content stored in database (portable across environments)
- Execution logs limited to specified number (default: 5)
- JSON format includes all fields (no truncation)
- Timestamps shown in ISO 8601 format for JSON
- Prerequisites shown if configured (e.g., docker_running, git_repo)
- Parameters shown if configured (e.g., backup_dir, timeout)

**Related Commands:**
- `/mem-skills` - List all skills
- `/mem-skills-create` - Create a new skill
- `/mem-skills-execute <name>` - Execute a skill (Coming soon)

Execute:
python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/skill-info.py "$@"
