Execute a skill and log performance metrics.

**Command**: `/mem-skills-execute <skill_name>`

**What this does:**
- Executes a skill's bash script
- Tracks execution time and outcome
- Logs performance to database
- Updates skill counters (uses, successes, failures)
- Calculates and tracks time saved
- Provides detailed execution feedback

**Use cases:**
- **Run automation** - Execute skills to automate repetitive tasks
- **Test skills** - Verify skills work correctly
- **Track performance** - Build execution history for trust levels
- **Save time** - Automate tasks that would be manual
- **Validate changes** - Test skill modifications

**What you get:**
- Real-time execution output (stdout/stderr)
- Execution time measurement
- Time saved calculation
- Success/failure indication
- Performance log ID for tracking
- Updated skill metrics

**Usage:**
```bash
# Execute skill by name
/mem-skills-execute check-db-health

# Execute skill by ID
/mem-skills-execute --id 2

# Dry run (preview without executing)
/mem-skills-execute check-db-health --dry-run

# Specify time saved estimate
/mem-skills-execute backup-claude-memory --time-saved 60

# With user request context
/mem-skills-execute check-db-health --request "check database health"
```

**Example Output (Success):**

```
🚀 Executing skill: check-db-health
   Type: bash_script
   Confidence: 0.8

=== PostgreSQL Database Health Check ===

Version:
 PostgreSQL 15.4

Database Size:
 claude_memory | 11 MB

Table Counts:
 Snapshots  | 33
 Skills     | 3
 Agent Work | 69

=== Health Check Complete ===

================================================================================
✅ Skill executed successfully
   Execution Time: 1.25 seconds
   Time Saved: 45 seconds
   Performance Log ID: 2
================================================================================
```

**Example Output (Failure):**

```
🚀 Executing skill: test-failure
   Type: bash_script
   Confidence: 0.8

This will fail

================================================================================
❌ Skill execution failed
   Exit Code: 1
   Execution Time: 0.00 seconds
   Error: Script exited with code 1
   Performance Log ID: 4
================================================================================
```

**Arguments:**
```
POSITIONAL:
  skill_name              Skill name (e.g., "check-db-health")

OPTIONS:
  --id ID                 Use skill ID instead of name
  --dry-run               Preview without executing
  --time-saved SECONDS    Estimated time saved (default: auto-calculate)
  --request TEXT          User request that triggered this
  --session-id ID         Session ID for tracking
```

**Dry Run Mode:**

Preview what would be executed without actually running the script:

```bash
/mem-skills-execute check-db-health --dry-run
```

Output:
```
🔍 DRY RUN MODE - Would execute:
   Skill: check-db-health (ID: 2)
   Type: bash_script
   Script Length: 716 characters

   Script Content:
   ----------------------------------------------------------------------------
   #!/bin/bash
   echo "=== PostgreSQL Database Health Check ==="
   ...
   ----------------------------------------------------------------------------

✅ Dry run complete (no execution performed)
```

**Time Saved Calculation:**

By default, time saved is estimated as 10x the execution time (heuristic: manual tasks take 10x longer).

```bash
# Auto-calculate (10x execution time)
/mem-skills-execute check-db-health
# If execution takes 2 seconds, time saved = 20 seconds

# Specify exact time saved
/mem-skills-execute backup-claude-memory --time-saved 60
# Time saved = 60 seconds (1 minute)
```

**Execution Flow:**

1. **Lookup**: Find skill by name or ID
2. **Validate**: Check skill is active and has valid command
3. **Prerequisites**: Validate prerequisites (e.g., docker_running)
4. **Extract**: Get bash script from database
5. **Execute**: Write to temp file, make executable, run
6. **Capture**: Collect stdout, stderr, exit code, timing
7. **Log**: Record to skills_performance_log
8. **Update**: Increment counters in skills_agents
9. **Cleanup**: Remove temp file
10. **Report**: Display results to user

**Performance Logging:**

Each execution creates a log entry with:
- **Outcome**: success, failed, timeout, user_rejected, user_corrected
- **Execution Time**: Milliseconds to complete
- **Time Saved**: Estimated or specified time saved
- **Error Message**: Captured if execution failed
- **User Request**: Context about what triggered this
- **Session ID**: Track across session
- **Timestamp**: When execution occurred

**Skill Counter Updates:**

After each execution:
- **use_count**: Incremented by 1
- **success_count**: Incremented if successful
- **failure_count**: Incremented if failed
- **success_rate**: Auto-calculated (success_count / use_count × 100)
- **avg_time_saved_ms**: Average across all executions
- **total_time_saved_ms**: Cumulative time saved
- **last_used**: Updated to current timestamp

**Trust Level Progression:**

As skills execute successfully, they build trust:
- **0-4 uses**: 🆕 new (learning phase, always ask approval)
- **5-9 uses, 70%+ success**: 🔄 developing (building trust)
- **10+ uses, 90%+ success**: ✅ stable (high trust, auto-execute)
- **<70% success**: ⚠️ needs_improvement (requires attention)

**Prerequisites Validation:**

Before execution, validates:
- **docker_running**: Docker is running and accessible
- **git_repo**: Current directory is a git repository
- Additional prerequisites as configured

If prerequisites fail, execution is blocked with error message.

**Error Handling:**

**Exit Code != 0:**
```
❌ Skill execution failed
   Exit Code: 1
   Error: Script exited with code 1
```

**Timeout:**
```
❌ Skill execution failed
   Error: Script timed out after 300 seconds
```
(Default timeout: 5 minutes)

**Prerequisite Failure:**
```
❌ Prerequisite check failed: Docker is not running
```

**Skill Not Found:**
```
❌ Skill 'nonexistent-skill' not found
```

**Inactive Skill:**
```
❌ Skill 'old-skill' is inactive
```

**Examples:**

**Execute database health check:**
```bash
/mem-skills-execute check-db-health
```

**Execute backup with time saved:**
```bash
/mem-skills-execute backup-claude-memory --time-saved 60
```

**Test execution (dry run):**
```bash
/mem-skills-execute deploy-to-staging --dry-run
```

**Execute by ID:**
```bash
/mem-skills-execute --id 2
```

**Execute with context:**
```bash
/mem-skills-execute check-db-health \
  --request "user asked to verify database" \
  --session-id "abc-123" \
  --time-saved 45
```

**Verify execution history:**
```bash
/mem-skills-execute check-db-health
# Then check results:
/mem-skills-info check-db-health
```

**Security Considerations:**

- Scripts execute with permissions of current user
- Temp files created in secure temporary directory
- Temp files cleaned up after execution (even on error)
- Script content validated before execution
- Prerequisites checked to prevent unsafe execution
- Execution timeout prevents runaway scripts (5 minutes default)

**Performance Tracking Benefits:**

1. **Build Trust**: Successful executions increase trust level
2. **Identify Issues**: Track failure patterns
3. **Measure Value**: Calculate total time saved
4. **Improve Skills**: See which skills need work
5. **Enable Automation**: High-trust skills can auto-execute (Phase 2)

**Output Streams:**

- **stdout**: Displayed to console (skill output)
- **stderr**: Displayed to console (errors, warnings)
- **exit code**: Used to determine success/failure
- **execution time**: Measured in milliseconds
- **performance log**: Persisted to database

**Notes:**

- Execution creates temp file in system temp directory
- Temp file automatically cleaned up after execution
- Script runs with `/bin/bash` interpreter
- Execution time includes script I/O and subprocess overhead
- Performance log ID can be used to query skills_performance_log
- Counters update in database transaction (atomic)
- Time saved defaults to 10x execution time if not specified

**Supported Command Types:**

Phase 1 (Current):
- ✅ **bash_script**: Execute bash scripts

Phase 2 (Future):
- 🔮 **tool_sequence**: Multi-step tool workflows
- 🔮 **agent_spawn**: Launch Claude Code agents

**Related Commands:**

- `/mem-skills` - List all skills
- `/mem-skills-info <name>` - View skill details and execution history
- `/mem-skills-create` - Create a new skill

**Troubleshooting:**

**Script fails but should succeed:**
1. Use `--dry-run` to preview script
2. Check prerequisites are met
3. Verify script has correct permissions/environment
4. Check execution logs with `/mem-skills-info`

**Time saved seems wrong:**
```bash
# Specify accurate time saved estimate
/mem-skills-execute skill-name --time-saved 120
```

**Need to see full execution details:**
```bash
# Execute skill
/mem-skills-execute skill-name

# View detailed logs
/mem-skills-info skill-name --show-logs 5
```

Execute:
python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/execute-skill.py "$@"
