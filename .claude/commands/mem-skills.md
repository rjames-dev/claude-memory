List all skills in the Skills System with filtering, sorting, and multiple output formats.

**Command**: `/mem-skills`

**What this does:**
- Lists all active skills with performance metrics
- Filters by category, scope, or project path
- Sorts by name, success rate, use count, or last used
- Outputs in multiple formats (table, JSON, compact, detailed)
- Shows performance metrics and status categorization

**Use cases:**
- **View all skills** - See what automation is available
- **Find specific skills** - Filter by category or project
- **Identify top performers** - Sort by success rate or usage
- **Export skill data** - Output as JSON for processing
- **Quick overview** - Use compact format for summaries

**What you get:**
- Skill ID, name, and display name
- Category and scope (global or project)
- Performance metrics (uses, success rate, time saved)
- Status category (stable, new, developing, needs_improvement)
- Trigger count
- Last used and created timestamps

**Usage:**
```bash
# List all active skills (default table format)
/mem-skills

# Filter by category
/mem-skills --category database

# Filter by scope
/mem-skills --scope global

# Sort by success rate (highest first)
/mem-skills --sort success_rate

# Show top 5 most used skills
/mem-skills --sort use_count --limit 5

# Output as JSON
/mem-skills --format json

# Compact view for quick overview
/mem-skills --format compact

# Detailed view of specific category
/mem-skills --category database --format detailed

# Show all skills including inactive
/mem-skills --show-inactive
```

**Output Formats:**

**Table (default):**
```
ID   Name                      Category        Uses   Success  Status       Triggers
========================================================================================================================
2    check-db-health           database        1      100.0%   new          4
3    backup-claude-memory      maintenance     0      0.0%     new          3
========================================================================================================================
Total: 2 skill(s)
```

**Compact:**
```
🆕 check-db-health
   ID: 2 | Category: database | Uses: 1 | Success: 100.0%
   Checks PostgreSQL database health with version, size, and snapshot count

🆕 backup-claude-memory
   ID: 3 | Category: maintenance | Uses: 0 | Success: 0.0%
   Creates a backup of claude-memory database with timestamp
```

**JSON:**
```json
[
  {
    "id": 2,
    "agent_name": "check-db-health",
    "display_name": "Database Health Check",
    "category": "database",
    "use_count": 1,
    "success_rate": 100.0,
    "status_category": "new",
    "trigger_count": 4
    ...
  }
]
```

**Detailed:**
```
ID: 2
Name: check-db-health
Display Name: Database Health Check
Description: Checks PostgreSQL database health with version, size, and snapshot count
Category: database
Scope: global

Performance:
  Uses: 1
  Successes: 1
  Failures: 0
  Success Rate: 100.0%
  Status: new

Metadata:
  Version: 1
  Confidence: 0.8
  Active: Yes
  Created By: manual
  Created: 2025-12-26 20:34:47.735837+00:00
  Last Used: 2025-12-26 20:37:43.127592+00:00
  Triggers: 4
```

**Status Categories:**
- 🆕 **new**: Less than 5 uses (learning phase)
- ✅ **stable**: 10+ uses, 90%+ success rate (high trust)
- 🔄 **developing**: 5-9 uses, 70%+ success rate (building trust)
- ⚠️ **needs_improvement**: Less than 70% success rate (requires attention)

**Filter Options:**
```bash
--category CATEGORY     Filter by category (git, database, scaffolding, maintenance, etc.)
--scope SCOPE           Filter by scope (global or project)
--project-path PATH     Filter by specific project path
--show-inactive         Include inactive skills (default: active only)
```

**Sort Options:**
```bash
--sort name             Sort alphabetically by name (default)
--sort success_rate     Sort by success rate (highest first)
--sort use_count        Sort by number of uses (most used first)
--sort last_used        Sort by most recently used
--sort created          Sort by creation date (newest first)
```

**Output Options:**
```bash
--format table          Table format (default)
--format compact        Compact view with icons
--format json           JSON format for scripting
--format detailed       Full details for each skill
--limit N               Limit results to N skills
```

**Examples:**

**Find database skills sorted by usage:**
```bash
/mem-skills --category database --sort use_count
```

**Top 3 most successful skills:**
```bash
/mem-skills --sort success_rate --limit 3
```

**Export all skills as JSON:**
```bash
/mem-skills --format json > skills.json
```

**Quick overview of all skills:**
```bash
/mem-skills --format compact
```

**View project-specific skills:**
```bash
/mem-skills --scope project --project-path "/path/to/project"
```

**See skills that need attention:**
```bash
/mem-skills --sort success_rate | grep "needs_improvement"
```

**Arguments:**
```
FILTER OPTIONS:
  --category CATEGORY     Filter by category
  --scope SCOPE           Filter by scope (global or project)
  --project-path PATH     Filter by specific project path
  --show-inactive         Include inactive skills

SORT OPTIONS:
  --sort FIELD            Sort field (name, success_rate, use_count, last_used, created)

OUTPUT OPTIONS:
  --format FORMAT         Output format (table, json, compact, detailed)
  --limit N               Limit results to N skills
```

**Notes:**
- Skills with 0 uses show "new" status
- Success rate calculated as (success_count / use_count) * 100
- Time saved metrics only shown when applicable
- Inactive skills hidden by default (use --show-inactive to include)
- JSON format converts timestamps to ISO 8601 format

**Related Commands:**
- `/mem-skills-create` - Create a new skill
- `/mem-skills-info <name>` - View detailed skill information (Coming soon)
- `/mem-skills-execute <name>` - Execute a skill (Coming soon)

Execute:
python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/list-skills.py "$@"
