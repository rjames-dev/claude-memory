# Volume Safety Guide - Claude Memory System

**Critical**: Volumes contain ALL your data. Losing volumes = permanent data loss.

---

## What's in the Volumes?

### 1. claude-memory-db-data (CRITICAL)
**Size**: ~70MB
**Contains**:
- All conversation snapshots (33+)
- All skills and triggers (6+ skills)
- All agent work history (69+ records)
- Embeddings for semantic search

**Loss Impact**: Complete history wipe, all skills gone, all context lost

---

### 2. claude-memory-ollama (LARGE)
**Size**: ~2.7GB
**Contains**:
- llama3.2 model (2.0 GB)
- mxbai-embed-large model (669 MB)
- Model configurations

**Loss Impact**: Must re-download 2.7GB of models

---

## How to Check Volume Safety

### Quick Check
```bash
/mem-skills-execute check-volume-safety
```

**What it checks**:
- ✅ Both volumes present
- ✅ Database accessible (33 snapshots, 6 skills, 69 agent work)
- ✅ Ollama models installed (2 models)
- ❌ Violations detected (if volumes missing)

### Semantic Search Examples
```bash
# All these work!
/mem-skills-search "did I accidentally delete my data"    # 91.9% match
/mem-skills-search "did I lose data"                       # Exact match
/mem-skills-search "verify data safety"                    # Exact match
/mem-skills-search "check volumes"                         # Exact match
```

---

## How to Safely Restart Services

### Automated Safe Restart
```bash
/mem-skills-execute restart-services
```

**Options presented**:
1. **RECOMMENDED**: Restart containers only (keeps volumes)
2. Stop and start (keeps volumes)
3. Recreate containers only (keeps volumes)
4. Down and up (SAFE - does NOT remove volumes by default)

### Semantic Search Examples
```bash
/mem-skills-search "restart services"                      # Exact match
/mem-skills-search "how do I safely restart"              # 73.7% match
/mem-skills-search "reboot without losing data"           # High match
```

---

## DANGER: Commands That Delete Volumes

### ❌ NEVER RUN THESE

```bash
# DESTROYS ALL DATA
docker-compose down -v

# DESTROYS ALL DATA
docker volume rm claude-memory-db-data
docker volume rm claude-memory-ollama
docker volume rm claude-memory-*

# DESTROYS ALL DATA
docker volume prune (if you select 'y')
```

### What Gets Deleted
- ❌ All 33+ conversation snapshots
- ❌ All 6+ skills we just created
- ❌ All 69+ agent work records
- ❌ All embeddings (1024-dimensional vectors)
- ❌ 2.7GB of Ollama models

---

## Safe Operations

### ✅ ALWAYS SAFE

```bash
# Restart containers (keeps volumes)
docker-compose restart

# Stop and start (keeps volumes)
docker-compose stop
docker-compose up -d

# Recreate containers (keeps volumes)
docker-compose up -d --force-recreate

# Stop containers (keeps volumes)
docker-compose down
docker-compose up -d
```

### Verification After Operations
```bash
# Check volumes still exist
/mem-skills-execute check-volume-safety

# Should show:
# ✅ claude-memory-db-data
# ✅ claude-memory-ollama
# ✅ ALL VOLUMES PRESENT - NO VIOLATIONS DETECTED
```

---

## If Volumes Are Lost

### Violation Detection
When you run `/mem-skills-execute check-volume-safety`, you'll see:

```
╔════════════════════════════════════════════════════════════════╗
║  ⚠️  ⚠️  ⚠️   VOLUME VIOLATION DETECTED   ⚠️  ⚠️  ⚠️           ║
╚════════════════════════════════════════════════════════════════╝

Missing volumes:
  ❌ claude-memory-db-data
  ❌ claude-memory-ollama

CRITICAL: Data loss has occurred!
```

### Recovery Options

**If you have backups:**

1. **Restore database from SQL backup:**
   ```bash
   docker cp backup.sql claude-context-db:/tmp/
   docker exec claude-context-db psql -U memory_admin -d claude_memory -f /tmp/backup.sql
   ```

2. **Re-import skills from export:**
   ```bash
   /mem-skills-import skills-backup.json
   python3 generate-embeddings.py  # Regenerate embeddings
   ```

3. **Re-download Ollama models:**
   ```bash
   docker exec claude-ollama ollama pull llama3.2
   docker exec claude-ollama ollama pull mxbai-embed-large
   ```

**If no backups exist:**
- ❌ Data is permanently lost
- Start fresh: `docker-compose up -d`
- Recreate skills manually using documentation

---

## Backup Strategies

### Regular Skill Backups
```bash
# Weekly backup
/mem-skills-export --all -o backups/skills-$(date +%Y-%m-%d).json

# Category backups
/mem-skills-export --category database -o backups/db-skills.json
/mem-skills-export --category monitoring -o backups/monitoring-skills.json
```

### Database Backups
```bash
# Full database dump
docker exec claude-context-db pg_dump -U memory_admin claude_memory > backup-$(date +%Y-%m-%d).sql

# Compressed backup
docker exec claude-context-db pg_dump -U memory_admin claude_memory | gzip > backup-$(date +%Y-%m-%d).sql.gz
```

### Backup Schedule Recommendation
- **Daily**: Skill exports (small, fast)
- **Weekly**: Full database dumps
- **Monthly**: Full system backup (volumes + configs)

---

## Volume Safety Checklist

Before any Docker operation:

- [ ] Check volumes exist: `/mem-skills-execute check-volume-safety`
- [ ] Verify command is safe (no `-v` flag)
- [ ] Have recent backups (skill exports + DB dumps)
- [ ] Know recovery procedure

---

## Monitoring Skills

### 1. check-volume-safety
**When to use**: Before/after any Docker operation
**What it does**:
- Checks both volumes present
- Counts database records
- Verifies Ollama models
- Detects violations and provides recovery steps

**Triggers**:
- "check volumes"
- "verify data safety"
- "did I lose data"
- "check volume violations"
- "volume safety check"

### 2. restart-services
**When to use**: Need to restart services
**What it does**:
- Shows current volumes
- Warns about dangerous commands
- Presents 4 safe restart options
- Requires confirmation for each

**Triggers**:
- "restart services"
- "restart claude memory"
- "reboot services"
- "restart containers"
- "service restart"

### 3. system-status
**When to use**: Check overall system health
**What it does**:
- Docker container status
- Service health (DB, Processor, Ollama)
- Database statistics
- Disk usage
- Model list

**Triggers**:
- "system status"
- "check services"
- "are services running"
- "show system health"
- "claude memory status"

---

## Current System State

**As of**: 2025-12-26

**Volumes**:
- ✅ claude-memory-db-data: 69MB (33 snapshots, 6 skills, 69 agent work)
- ✅ claude-memory-ollama: 2.7GB (llama3.2, mxbai-embed-large)

**Skills**:
- 6 active skills
- 27 total triggers (all embedded)
- 100% volume safety coverage

**Backups**:
- Skill exports available via `/mem-skills-export`
- Database dumps via `pg_dump`
- All tools documented and tested

---

## Emergency Contacts

**If volumes are lost and you need help:**

1. Check this guide's recovery section
2. Run `/mem-skills-execute check-volume-safety` for specific guidance
3. Review skill export files in `backups/` directory
4. Check database dump files: `backup-*.sql`

**Prevention is better than recovery!**
- ✅ Use `/mem-skills-execute restart-services` for safe restarts
- ✅ Run `/mem-skills-execute check-volume-safety` regularly
- ✅ Export skills weekly: `/mem-skills-export --all`
- ✅ Never use `docker-compose down -v`

---

**Your data is precious. Protect your volumes!** 🛡️
