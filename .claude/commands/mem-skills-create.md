Create a new skill in the Skills System for reusable workflows and automation.

**Command**: `/mem-skills-create`

**What this does:**
- Creates a new skill with triggers and execution definition
- Stores bash script content directly in database (not filesystem)
- Adds semantic triggers for skill activation
- Tracks performance and success rate over time
- Makes reusable automation available across sessions

**Use cases:**
- **Repetitive workflows** - Git commit protocols, deployment procedures
- **Database operations** - Health checks, backups, migrations
- **File operations** - Scaffolding, cleanup, organization
- **Testing workflows** - Run tests, check coverage, lint code
- **Project-specific tasks** - Build, deploy, configure

**What you provide:**
- Skill name (kebab-case, e.g., "check-db-health")
- Display name (human-friendly, e.g., "Database Health Check")
- Category (git, database, scaffolding, file-ops, maintenance, etc.)
- Description (what the skill does)
- Trigger phrases (comma-separated)
- Bash script content (stored in database)

**Usage:**
```bash
/mem-skills-create
```

Then I'll help you create the skill interactively, or you can use the CLI directly:

```bash
python3 create-skill.py \
  --name "check-db-health" \
  --display-name "Database Health Check" \
  --category "database" \
  --description "Checks PostgreSQL database health with version, size, and table counts" \
  --command-type "bash_script" \
  --script-content "#!/bin/bash
echo 'Database Health Check'
psql -U memory_admin -d claude_memory -c 'SELECT version();'" \
  --triggers "check db health,verify database,database health check"
```

**Example Skills:**

**1. Git Commit Protocol:**
```bash
/mem-skills-create
Name: git-commit-protocol
Display: Git Commit (Our Protocol)
Category: git
Description: Creates git commit following team protocol with heredoc format
Triggers: commit changes, create commit, git commit
```

**2. Database Backup:**
```bash
/mem-skills-create
Name: backup-claude-memory
Display: Backup Claude Memory
Category: maintenance
Description: Creates timestamped backup of claude-memory database
Triggers: backup database, create db backup
```

**3. Deploy to Staging:**
```bash
/mem-skills-create
Name: deploy-staging
Display: Deploy to Staging
Category: deployment
Description: Deploys application to staging environment
Triggers: deploy to staging, staging deployment
```

**Advanced Options:**
- `--project-path` - Make skill project-specific instead of global
- `--confidence` - Set confidence score 0-1 (default: 0.8)
- `--parameters` - Define required/optional parameters as JSON
- `--prerequisites` - Define prerequisites (git_repo, docker_running, etc.)

**After Creation:**
- Skill appears in `/mem-skills` list
- Can be executed with triggers or `/mem-skills-execute <name>`
- Performance tracked automatically (success rate, time saved)
- Trust level increases with successful uses (low → high trust)

**Trust Levels:**
- **Low trust** (0-9 uses): Always asks for approval
- **High trust** (10+ uses, 90%+ success): Auto-executes

**Phase 1 Features:**
- ✅ Bash script skills
- ✅ Exact trigger matching
- ✅ Manual skill creation
- ✅ Performance tracking

**Phase 2 Features (Coming Soon):**
- 🔮 Semantic trigger matching (embedding-based)
- 🔮 Tool sequence execution (multi-step workflows)
- 🔮 Agent spawning (launch Explore, Plan agents)
- 🔮 Natural language skill creation

**Arguments:**
```
REQUIRED:
  --name              Skill name (kebab-case)
  --display-name      Human-friendly name
  --category          Category identifier
  --description       What this skill does
  --command-type      bash_script (tool_sequence, agent_spawn in Phase 2)
  --triggers          Comma-separated trigger phrases

OPTIONAL:
  --script-content    Bash script (required for bash_script type)
  --project-path      Project path for scoping (default: global)
  --confidence        Confidence score 0-1 (default: 0.8)
  --parameters        JSON parameters definition
  --prerequisites     JSON prerequisites definition
```

**Notes:**
- Script content stored in database (not filesystem) for portability
- Skills are backed up with database backups
- Can be exported/imported (Phase 2)
- Duplicate names are rejected
- Skill names must be kebab-case (lowercase, hyphens only)

Execute:
python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/create-skill.py "$@"
