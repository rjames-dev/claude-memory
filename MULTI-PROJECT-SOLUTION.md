# Multi-Project Solution - Skills Across Projects

**Problem**: How does Claude orient itself when waking up in different projects?

**Solution**: "Where Am I?" skill + portable skills + .claude/CLAUDE.md pattern

---

## The Complete Multi-Project System

### Component 1: "Where Am I?" Skill (NEW ⭐)

**Purpose**: Orient Claude to any project automatically

**What it does**:
1. **Looks for .claude/CLAUDE.md** (source of truth)
   - If found: Displays complete project context
   - If missing: Discovers assets and offers to create it

2. **Discovers Project Assets**:
   - Git repository info
   - Docker compose services
   - Running containers
   - Docker volumes (with criticality detection)
   - Environment variables
   - Claude Code configuration

3. **Validates Documentation**:
   - Compares discovered assets to documented assets
   - Warns if docs are outdated
   - Offers to update

4. **Creates Documentation** (if missing):
   - Interactive: offers to create .claude/CLAUDE.md or CLAUDE.md
   - Auto-populates with discovered information
   - Includes critical volume warnings

**Triggers** (5):
- "where am i"
- "what project is this"
- "orient me"
- "what am I working with"
- "project context"

---

### Component 2: Portable Skills

**Volume Safety Skills**:
- `check-any-project-volumes` - Works in ANY docker-compose project
- `check-volume-safety` - Claude-memory specific (can be made portable)

**Maintenance Skills**:
- `restart-services` - Can be made portable
- `show-db-connection` - Can be made portable

**Monitoring Skills**:
- `system-status` - Can be made portable
- `check-db-health` - Can be made portable

---

## How It Works: Multi-Project Workflow

### Scenario: Claude Wakes Up in New Project

```bash
# Claude is in /Users/you/another-project
# Claude doesn't know what project this is

# User (or Claude) runs:
/mem-skills-execute where-am-i
```

**What Happens**:

```
╔══════════════════════════════════════════════════════════════════╗
║           PROJECT ORIENTATION - Where Am I?                      ║
╚══════════════════════════════════════════════════════════════════╝

=== Looking for Claude Project Documentation ===

✅ Found Claude documentation: .claude/CLAUDE.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📖 PROJECT CONTEXT (from .claude/CLAUDE.md)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# My Awesome Project

**Project Root:** `/Users/you/another-project`
**Auto-Loaded:** This file is automatically read by Claude Code

## Quick Context

This is a web application with:
- PostgreSQL database (port 5432)
- Redis cache (port 6379)
- Node.js API (port 3000)

### Critical Volumes
- `awesome-project-db-data` - PostgreSQL database (⚠️  CRITICAL)
- `awesome-project-redis` - Redis cache

### Important Paths
- `src/` - Application source code
- `docker/` - Docker configuration
- `.env` - Environment variables (DO NOT COMMIT)

---

(rest of CLAUDE.md content...)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

=== Discovering Project Assets ===

📁 Current Directory: /Users/you/another-project
📦 Project Name: another-project

🐳 Docker Compose: docker-compose.yml
   Project: another-project
   Services (3):
     - postgres
     - redis
     - api

💾 Volumes:
   - awesome-project-db-data (⚠️  CRITICAL - database)
   - awesome-project-redis (📦 cache)

✅ ALL DOCUMENTED ASSETS FOUND

╔══════════════════════════════════════════════════════════════════╗
║                   ORIENTATION COMPLETE                           ║
╚══════════════════════════════════════════════════════════════════╝
```

**Now Claude knows:**
- ✅ What project it's in
- ✅ What services are running
- ✅ Which volumes are critical
- ✅ Project-specific conventions
- ✅ Where to find important files

---

### Scenario: Claude in Project Without CLAUDE.md

```bash
# Claude is in /Users/you/legacy-project
# No .claude/CLAUDE.md exists

/mem-skills-execute where-am-i
```

**What Happens**:

```
⚠️  No Claude documentation found (.claude/CLAUDE.md)

I'll discover project details and offer to create one...

=== Discovering Project Assets ===

📁 Current Directory: /Users/you/legacy-project
📦 Project Name: legacy-project

🐳 Docker Compose: docker-compose.yml
   Project: legacy
   Services (2):
     - mysql
     - nginx

💾 Volumes:
   - legacy-mysql-data (⚠️  CRITICAL - database)

╔══════════════════════════════════════════════════════════════════╗
║                 CREATE CLAUDE.MD DOCUMENTATION?                  ║
╚══════════════════════════════════════════════════════════════════╝

I discovered project assets but no CLAUDE.md exists.
This file helps Claude understand the project quickly.

Would you like me to:
  1. Create .claude/CLAUDE.md with discovered info
  2. Create CLAUDE.md at project root
  3. Skip (just show current state)

Select option (1-3): 1

Creating .claude/CLAUDE.md...
✅ Created .claude/CLAUDE.md

You can edit it to add:
  - Project description
  - Setup instructions
  - Important paths
  - Custom workflows
```

**Created File** (`.claude/CLAUDE.md`):
```markdown
# Legacy Project - Project Context

**Project Root:** `/Users/you/legacy-project`
**Auto-discovered:** 2025-12-26

---

## Quick Context

### Docker Infrastructure
- **Compose File:** docker-compose.yml
- **Project Name:** legacy
- **Services:** 2

**Service List:**
- mysql
- nginx

### Critical Volumes (⚠️  DO NOT DELETE)

- `legacy-mysql-data` - Contains persistent data

---

## Important Notes

<!-- Add project-specific notes here -->

---

**Last Updated:** 2025-12-26
**Next Review:** Update when significant changes occur
```

**Now:**
- ✅ Project is documented for future sessions
- ✅ Claude can read this next time
- ✅ Team members can edit and improve it
- ✅ Critical volumes are documented

---

## The .claude/CLAUDE.md Pattern

### What Goes in CLAUDE.md?

**Essential Information**:
```markdown
# Project Name

**Project Root:** `/absolute/path`
**Auto-Loaded:** Yes (Claude Code reads this automatically)

## Quick Context

Brief description of what this project does.

### Docker Infrastructure
- Service names and ports
- Critical volumes (with warnings!)
- Network configuration

### Critical Volumes (⚠️  DO NOT DELETE)
- `project-db-data` - Database (contains all application data)
- `project-models` - AI models (2GB+ downloads)

### Important Paths
- `src/` - Source code
- `docs/` - Documentation
- `.env` - Secrets (DO NOT COMMIT)

### Key Commands
- Start: `docker-compose up -d`
- Logs: `docker-compose logs -f`
- Stop: `docker-compose stop`

### Development Workflow
1. Step-by-step setup
2. Common tasks
3. Troubleshooting tips

---

**Last Updated:** YYYY-MM-DD
```

**Benefits**:
- ✅ Claude reads this automatically on session start
- ✅ Team members have single source of truth
- ✅ Onboarding is faster
- ✅ Prevents volume deletion mistakes
- ✅ Documents critical infrastructure

---

## Portable Skills + CLAUDE.md = Complete Solution

### How They Work Together

**1. Claude Wakes Up**:
```bash
# Automatic or manual
/mem-skills-execute where-am-i
```

**2. Reads CLAUDE.md**:
- Gets project context
- Understands critical volumes
- Knows key commands

**3. Validates Against Reality**:
- Checks if documented services are running
- Verifies volumes exist
- Warns if docs are outdated

**4. Uses Portable Skills**:
```bash
# These adapt to current project automatically
/mem-skills-execute check-any-project-volumes
/mem-skills-execute restart-services (if made portable)
/mem-skills-execute show-db-connection (if made portable)
```

---

## Setting Up Multi-Project Support

### Step 1: Create CLAUDE.md in Each Project

**Option A: Automatic** (using where-am-i skill):
```bash
cd /path/to/your/project
/mem-skills-execute where-am-i
# Select option 1 to create .claude/CLAUDE.md
```

**Option B: Manual**:
```bash
cd /path/to/your/project
mkdir -p .claude
nano .claude/CLAUDE.md
# Copy template and fill in details
```

---

### Step 2: Export Portable Skills

**From claude-memory project**:
```bash
cd /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory

# Export portable skills
/mem-skills-export where-am-i -o where-am-i.json
/mem-skills-export check-any-project-volumes -o check-volumes.json

# Or export all portable skills at once
/mem-skills-export --category project-management -o project-mgmt-skills.json
/mem-skills-export --category monitoring -o monitoring-skills.json
```

---

### Step 3: Import into Other Projects

**In each project that uses claude-memory**:
```bash
cd /path/to/your/other/project

# Import skills
/mem-skills-import where-am-i.json
/mem-skills-import check-volumes.json

# Generate embeddings
python3 generate-embeddings.py

# Test
/mem-skills-execute where-am-i
# ✅ Automatically adapts to current project!
```

---

### Step 4: Maintain CLAUDE.md

**Keep it updated**:
```bash
# After adding new services
/mem-skills-execute where-am-i  # Shows new assets

# Manually update CLAUDE.md
nano .claude/CLAUDE.md

# Or re-run to regenerate
/mem-skills-execute where-am-i
# Select option 1 to recreate (backs up old one)
```

---

## Real-World Example: Three Projects

### Project A: claude-memory (Current)

**Location**: `/Users/jamesmba/Data/00 GITHUB/Code/claude-memory`

**CLAUDE.md Status**: ❌ None (project-level), ✅ Yes (parent-level)

**Volumes**:
- `claude-memory-db-data` (69MB - CRITICAL)
- `claude-memory-ollama` (2.7GB - models)

**Skills**: All 8 production skills available

---

### Project B: another-app

**Location**: `/Users/you/another-app`

**CLAUDE.md**: ✅ Created via where-am-i skill

**Volumes**:
- `another-app-db` (150MB - CRITICAL)
- `another-app-cache` (50MB - cache)

**Skills**: Imported portable skills:
- `where-am-i`
- `check-any-project-volumes`
- `check-db-health` (portable version)

**Works!**:
```bash
cd /Users/you/another-app
/mem-skills-execute where-am-i
# ✅ Shows another-app context

/mem-skills-execute check-any-project-volumes
# ✅ Detects another-app volumes, warns about deletion
```

---

### Project C: legacy-system

**Location**: `/Users/you/legacy-system`

**CLAUDE.md**: ❌ None yet

**Process**:
```bash
cd /Users/you/legacy-system

# First time
/mem-skills-execute where-am-i
# Discovers assets, creates CLAUDE.md

# Second time
/mem-skills-execute where-am-i
# ✅ Reads existing CLAUDE.md, validates assets
```

---

## Benefits of This System

### For Claude

✅ **Instant Orientation**:
- No more "where am I?" confusion
- Immediate access to project context
- Knows what services/volumes are critical

✅ **Consistent Workflows**:
- Same skills work across projects
- Portable patterns
- Reduced errors

✅ **Safety**:
- Volume protection in any project
- Documented critical assets
- Warnings before dangerous operations

---

### For Users

✅ **Documentation**:
- Single source of truth (.claude/CLAUDE.md)
- Auto-generated from discoveries
- Team can collaborate on it

✅ **Onboarding**:
- New team members read CLAUDE.md
- Claude reads same document
- Everyone aligned

✅ **Consistency**:
- Same skills work everywhere
- Export once, import anywhere
- No project-specific learning curve

---

## Current Skill Inventory

**Portable (✅ Work in any project)**:
- `where-am-i` ⭐ - Project orientation
- `check-any-project-volumes` ⭐ - Volume safety

**Needs Portability Conversion**:
- `restart-services` - Safe restart with volume checks
- `show-db-connection` - Database credentials
- `system-status` - System health dashboard
- `check-db-health` - Database health check
- `check-volume-safety` - Volume violations (specific)
- `backup-claude-memory` - Database backup

---

## Next Steps

### Phase 1: Document Current Projects

```bash
# For each project
cd /path/to/project
/mem-skills-execute where-am-i
# Create .claude/CLAUDE.md
```

### Phase 2: Convert Skills to Portable

- Update restart-services (remove hardcoded paths)
- Update show-db-connection (detect .env dynamically)
- Update system-status (detect containers dynamically)
- Export portable versions

### Phase 3: Build Skill Library

Create portable skill collections:
- `project-management-skills.json` (where-am-i, etc.)
- `volume-safety-skills.json` (all volume protection)
- `monitoring-skills.json` (health checks, status)
- `maintenance-skills.json` (restart, backup)

### Phase 4: Automate

- Auto-run where-am-i on cd into new directory
- Auto-validate CLAUDE.md on changes
- Auto-export skills on updates

---

## Summary

**Question**: "Where am I? What am I working with?"

**Answer**:

1. **Run**: `/mem-skills-execute where-am-i`

2. **Get**:
   - Project name and location
   - Git repository info
   - Docker services and volumes
   - Critical volume warnings
   - Documented project context from CLAUDE.md

3. **Create**: .claude/CLAUDE.md if missing

4. **Use**: Portable skills that adapt to current project

**Result**: Claude is oriented, volumes are protected, team is documented!

---

**The complete multi-project solution is ready to deploy!** 🚀
