# Skills System - Quick Start Guide

**Get started with Skills in 5 minutes!**

---

## Setup (1 minute)

```bash
# Set database password
export CONTEXT_DB_PASSWORD="your_password_here"

# Verify database is running
docker ps | grep claude-context-db
```

---

## Your First Skill (2 minutes)

### Create a "Hello World" Skill

```bash
python3 create-skill.py \
  --name "hello-world" \
  --display-name "Hello World" \
  --category "examples" \
  --description "Simple greeting skill" \
  --command-type "bash_script" \
  --script-content 'echo "Hello from Skills System!"' \
  --triggers "hello,greet"
```

### Execute It

```bash
python3 execute-skill.py hello-world
```

Output:
```
🚀 Executing skill: hello-world
Hello from Skills System!
✅ Skill executed successfully
```

---

## Essential Commands (2 minutes)

### List All Skills
```bash
/mem-skills
```

### View Skill Details
```bash
/mem-skills-info hello-world
```

### Execute with Dry Run
```bash
/mem-skills-execute hello-world --dry-run
```

---

## Common Skills Examples

### 1. Database Health Check

```bash
python3 create-skill.py \
  --name "check-db" \
  --display-name "DB Health Check" \
  --category "database" \
  --description "Check database health" \
  --command-type "bash_script" \
  --script-content '#!/bin/bash
docker exec claude-context-db psql -U memory_admin -d claude_memory -c "SELECT COUNT(*) FROM context_snapshots;"' \
  --triggers "check database,db health" \
  --prerequisites '{"docker_running": true}'
```

### 2. Git Status

```bash
python3 create-skill.py \
  --name "git-status" \
  --display-name "Git Status" \
  --category "git" \
  --description "Show git status" \
  --command-type "bash_script" \
  --script-content 'git status --short' \
  --triggers "git status,show status" \
  --prerequisites '{"git_repo": true}'
```

### 3. List Docker Containers

```bash
python3 create-skill.py \
  --name "list-containers" \
  --display-name "List Docker Containers" \
  --category "docker" \
  --description "Show running containers" \
  --command-type "bash_script" \
  --script-content 'docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"' \
  --triggers "list containers,show docker,docker ps" \
  --prerequisites '{"docker_running": true}'
```

---

## Command Cheat Sheet

```bash
# CREATE
/mem-skills-create                                    # Interactive creation
python3 create-skill.py --name "..." ...              # Direct creation

# LIST
/mem-skills                                           # All skills (table)
/mem-skills --format compact                          # Compact view
/mem-skills --category database                       # Filter by category
/mem-skills --sort success_rate                       # Sort by success
/mem-skills --format json                             # JSON output

# INFO
/mem-skills-info skill-name                           # Skill details
/mem-skills-info skill-name --show-script             # With full script
/mem-skills-info skill-name --format json             # JSON output
/mem-skills-info skill-name --show-logs 10            # More logs

# EXECUTE
/mem-skills-execute skill-name                        # Execute
/mem-skills-execute skill-name --dry-run              # Preview only
/mem-skills-execute skill-name --time-saved 60        # With time saved
/mem-skills-execute --id 2                            # Execute by ID
```

---

## Skill Naming Rules

✅ **Valid Names:**
- `hello-world`
- `check-db-health`
- `deploy-to-staging`

❌ **Invalid Names:**
- `Hello World` (spaces)
- `check_db` (underscores)
- `123-check` (starts with number)

**Rules:** kebab-case, 3-50 chars, start with letter

---

## Understanding Status

| Icon | Status | Meaning |
|------|--------|---------|
| 🆕 | new | 0-4 uses (learning) |
| 🔄 | developing | 5-9 uses, 70%+ success |
| ✅ | stable | 10+ uses, 90%+ success |
| ⚠️ | needs_improvement | <70% success rate |

---

## Next Steps

1. ✅ Created your first skill
2. ⏭️ Read full docs: `SKILLS-USER-GUIDE.md`
3. ⏭️ Create skills for your workflows
4. ⏭️ Build up execution history
5. ⏭️ Monitor performance metrics

---

## Need Help?

- **Full Guide:** `SKILLS-USER-GUIDE.md`
- **Test Suite:** `python3 test-skills-integration.py`
- **Test Results:** `SKILLS-INTEGRATION-TEST-RESULTS.md`
- **Roadmap:** `SKILLS-PHASE1-ROADMAP.md`

---

**Happy Automating! 🚀**
