# Skills Portability Guide - Using Skills Across Projects

**Question**: If I use claude-memory with skills in another project, can volume safety detection work there too?

**Answer**: Yes! There are **two approaches** to make skills portable across projects.

---

## Two Approaches to Skill Portability

### Approach 1: Global Skills with Dynamic Detection (RECOMMENDED)

**How it works:**
- Skill is marked as `scope: global`
- Script detects current project automatically
- Works in ANY docker-compose project
- Exported once, works everywhere

**Example:** `check-any-project-volumes`

**Pros:**
- ✅ Write once, use everywhere
- ✅ Export/import works across projects
- ✅ Automatically adapts to environment
- ✅ Easier to maintain (one version)

**Cons:**
- ⚠️ Must detect project context at runtime
- ⚠️ Slightly more complex scripts

---

### Approach 2: Project-Scoped Skills (SPECIFIC)

**How it works:**
- Skill is marked as `scope: project`
- `project_path` set to specific directory
- Hardcoded paths for that project only
- Each project has its own copy

**Example:** Current `check-volume-safety`

**Pros:**
- ✅ Simple, hardcoded paths
- ✅ No runtime detection needed
- ✅ Project-specific customization
- ✅ Faster execution (no detection overhead)

**Cons:**
- ⚠️ Not portable (must recreate per project)
- ⚠️ Harder to share across projects
- ⚠️ More maintenance (multiple versions)

---

## How Skills Detect Projects Dynamically

### Method 1: Docker Compose Project Name

```bash
# Get project name from docker-compose
PROJECT_NAME=$(docker-compose config 2>/dev/null | grep "name:" | head -1 | awk '{print $2}')

# Fallback to directory name
if [ -z "$PROJECT_NAME" ]; then
    PROJECT_NAME=$(basename "$PWD" | tr '[:upper:]' '[:lower:]')
fi
```

### Method 2: Volume Prefix Matching

```bash
# Find all volumes for current project
PROJECT_VOLUMES=$(docker volume ls --filter "name=$PROJECT_NAME" --format "{{.Name}}")
```

### Method 3: Detect from docker-compose.yml

```bash
# Must be run from project directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Not in a docker-compose project"
    exit 1
fi

# Extract volume names from docker-compose.yml
VOLUMES=$(grep -A 5 "^volumes:" docker-compose.yml | grep -v "^volumes:" | awk '{print $1}' | sed 's/:$//')
```

---

## Making Existing Skills Portable

### Current Hardcoded Skill (Not Portable)

```bash
# check-volume-safety (current)
PROJECT_DIR="/Users/jamesmba/Data/00 GITHUB/Code/claude-memory"
EXPECTED_VOLUMES=(
    "claude-memory-db-data:Database"
    "claude-memory-ollama:Ollama models"
)
```

**Works only in:** `/Users/jamesmba/Data/00 GITHUB/Code/claude-memory`

**Volumes detected:** Only `claude-memory-*`

---

### Portable Version (Works Anywhere)

```bash
# check-any-project-volumes (portable)
PROJECT_DIR="$PWD"
PROJECT_NAME=$(basename "$PWD" | tr '[:upper:]' '[:lower:]')
EXPECTED_VOLUMES=$(docker volume ls --filter "name=$PROJECT_NAME" --format "{{.Name}}")
```

**Works in:** ANY docker-compose project

**Volumes detected:** All volumes matching current project name

---

## Using Skills in Another Project

### Scenario: You have two projects

**Project A**: `/Users/you/claude-memory` (this project)
**Project B**: `/Users/you/another-app` (uses claude-memory + skills)

### Option 1: Export Global Skills, Import to Project B

```bash
# In Project A
cd /Users/you/claude-memory
/mem-skills-export check-any-project-volumes -o portable-volume-check.json

# In Project B
cd /Users/you/another-app
/mem-skills-import portable-volume-check.json

# Generate embeddings
python3 generate-embeddings.py

# Test (now works in Project B!)
/mem-skills-execute check-any-project-volumes
```

**Result**: Skill detects Project B's volumes automatically!

---

### Option 2: Share Global Skills via Database

If both projects use the **same claude-memory database**:

```bash
# Skills are already available in Project B!
cd /Users/you/another-app

# List skills
/mem-skills  # Shows all global skills

# Execute
/mem-skills-execute check-any-project-volumes
```

**Result**: Global skills work immediately in new project.

---

### Option 3: Create Project-Specific Skills

If Project B needs custom behavior:

```bash
cd /Users/you/another-app

# Create project-specific skill
python3 create-skill.py \
  --name "check-project-b-volumes" \
  --project-path "/Users/you/another-app" \
  --script-content "..." \
  ...
```

**Result**: Skill only appears/works in Project B.

---

## Database Schema for Portability

### Skills Table

```sql
CREATE TABLE skills_agents (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(100),
    scope VARCHAR(20) DEFAULT 'global',  -- 'global' or 'project'
    project_path TEXT,                    -- NULL for global
    ...
);
```

### Skill Scoping Rules

**Global Skills** (`scope = 'global'`):
- `project_path` is NULL
- Available in all projects
- Must detect context at runtime
- Example: `check-any-project-volumes`

**Project Skills** (`scope = 'project'`):
- `project_path` is set (e.g., `/Users/you/claude-memory`)
- Only available in that project
- Can use hardcoded paths
- Example: `check-volume-safety` (current)

---

## Current Skill Inventory

| Skill | Scope | Portable? | Notes |
|-------|-------|-----------|-------|
| check-db-health | global | ⚠️ Partial | Hardcoded container name |
| backup-claude-memory | global | ⚠️ Partial | Hardcoded paths |
| show-db-connection | global | ⚠️ Partial | Hardcoded .env path |
| system-status | global | ⚠️ Partial | Hardcoded container filter |
| restart-services | global | ❌ No | Hardcoded PROJECT_DIR |
| check-volume-safety | global | ❌ No | Hardcoded volume names |
| check-any-project-volumes | global | ✅ Yes | Dynamic detection |

---

## Best Practices for Portable Skills

### 1. Detect Project Context

```bash
# Always detect, never hardcode
PROJECT_DIR="$PWD"
PROJECT_NAME=$(basename "$PWD" | tr '[:upper:]' '[:lower:]')
```

### 2. Use Relative Paths

```bash
# Good
ENV_FILE="$PWD/.env"

# Bad
ENV_FILE="/Users/jamesmba/Data/00 GITHUB/Code/claude-memory/.env"
```

### 3. Dynamic Volume Discovery

```bash
# Good - finds all project volumes
VOLUMES=$(docker volume ls --filter "name=$PROJECT_NAME")

# Bad - hardcoded volume names
VOLUMES=("claude-memory-db-data" "claude-memory-ollama")
```

### 4. Container Discovery

```bash
# Good - finds containers by project
CONTAINERS=$(docker ps --filter "name=$PROJECT_NAME")

# Bad - hardcoded container names
CONTAINERS="claude-context-db claude-ollama"
```

### 5. Environment Variables

```bash
# Good - configurable
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}

# Bad - hardcoded
DB_HOST=localhost
DB_PORT=5435
```

---

## Converting Existing Skills to Portable

### Example: Make `show-db-connection` Portable

**Before (Not Portable):**
```bash
ENV_FILE="/Users/jamesmba/Data/00 GITHUB/Code/claude-memory/.env"
```

**After (Portable):**
```bash
# Detect current project directory
ENV_FILE="$PWD/.env"

# Or search for .env in parent directories
find_env_file() {
    dir="$PWD"
    while [ "$dir" != "/" ]; do
        if [ -f "$dir/.env" ]; then
            echo "$dir/.env"
            return 0
        fi
        dir=$(dirname "$dir")
    done
    echo "❌ .env file not found"
    return 1
}

ENV_FILE=$(find_env_file)
```

---

## Testing Portability

### Test Checklist

To verify a skill is truly portable:

1. **Export the skill:**
   ```bash
   /mem-skills-export check-any-project-volumes -o test.json
   ```

2. **Create test project:**
   ```bash
   mkdir /tmp/test-project
   cd /tmp/test-project
   # Create minimal docker-compose.yml
   ```

3. **Import and test:**
   ```bash
   /mem-skills-import test.json
   /mem-skills-execute check-any-project-volumes
   ```

4. **Verify it works:**
   - ✅ Detects test project volumes
   - ✅ No hardcoded paths fail
   - ✅ Adapts to new environment

---

## Recommendation for Your Use Case

**Question**: "If I'm in another project using claude-memory with skills, will volume protection work?"

**Answer**: **Yes, with the new portable skill!**

### Quick Setup in New Project

```bash
# 1. In your new project directory
cd /path/to/your/new/project

# 2. Export portable skills from claude-memory
cd /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory
/mem-skills-export check-any-project-volumes -o /tmp/portable-skills.json

# 3. Import to new project
cd /path/to/your/new/project
/mem-skills-import /tmp/portable-skills.json
python3 generate-embeddings.py

# 4. Test - it works!
/mem-skills-execute check-any-project-volumes
# ✅ Detects YOUR project's volumes
# ✅ Warns about YOUR project's data
# ✅ Protects YOUR project's volumes
```

---

## Future Enhancements

### Smart Project Detection

```bash
# Detect from multiple sources
detect_project() {
    # 1. docker-compose project name
    # 2. git repository name
    # 3. directory name
    # 4. .env file PROJECT_NAME variable
}
```

### Project Configuration File

```yaml
# .claude-skills.yml
project:
  name: my-project
  volumes:
    critical:
      - my-project-db-data
      - my-project-models
    optional:
      - my-project-cache
```

### Automatic Skill Adaptation

```bash
# Skills auto-adapt when imported
if [ -f ".claude-skills.yml" ]; then
    source_project_config
else
    detect_project_dynamically
fi
```

---

## Summary

**Current State:**
- ⚠️ Most skills are hardcoded (not portable)
- ✅ One portable skill created: `check-any-project-volumes`

**To Make Skills Portable:**
1. Use dynamic project detection
2. Avoid hardcoded paths
3. Mark as `scope: global`
4. Test in multiple projects

**For Your Specific Question:**
- ✅ **Yes**, the new `check-any-project-volumes` skill works in ANY project
- ⚠️ **Partial**, existing skills need conversion to be fully portable
- 📋 **Roadmap**: Convert all skills to portable versions in Phase 2

**Next Steps:**
1. Convert existing skills to portable versions
2. Create `.claude-skills.yml` config standard
3. Build skill library of portable utilities
4. Document portable skill patterns

---

**The Skills System CAN protect volumes across projects - we just need to use portable patterns!**
