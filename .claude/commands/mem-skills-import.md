Import skills from JSON export files.

**Command**: `/mem-skills-import <json_file>`

**What this does:**
- Imports skills from JSON export files
- Creates new skills from exported data
- Handles conflicts with existing skills
- Regenerates embeddings on import

**Options:**
- `--skip-existing` - Skip skills that already exist (don't fail)
- `--overwrite` - Overwrite existing skills with imported versions
- `--dry-run` - Preview import without making changes

**Examples:**

```bash
# Import skills from file
/mem-skills-import backup.json

# Skip skills that already exist
/mem-skills-import all-skills.json --skip-existing

# Overwrite existing skills
/mem-skills-import database-skills.json --overwrite

# Preview import without making changes
/mem-skills-import skills.json --dry-run
```

**Conflict Resolution:**

**Default behavior (fail on conflict):**
```bash
/mem-skills-import backup.json
# ❌ Skill exists (use --skip-existing or --overwrite): check-db-health
```

**Skip existing:**
```bash
/mem-skills-import backup.json --skip-existing
# ⏭️  Skipped (already exists): check-db-health
# ✅ Imported: new-skill (ID: 15)
```

**Overwrite existing:**
```bash
/mem-skills-import backup.json --overwrite
# ✅ Imported: check-db-health (ID: 14) [overwrote existing]
```

**Import Summary:**

```
Found 5 skill(s) in import file
Export version: 1.0
Exported at: 2025-12-26T10:00:00Z

================================================================================
Importing Skills...
================================================================================

[1/5] ✅ Imported: check-db-health (ID: 14)
[2/5] ⏭️  Skipped (already exists): backup-claude-memory
[3/5] ✅ Imported: new-skill (ID: 15)
[4/5] ✅ Imported: another-skill (ID: 16)
[5/5] ❌ Failed to import broken-skill: Invalid JSON in prerequisites

================================================================================
Import Summary:
  Imported: 3
  Skipped: 1
  Failed: 1
================================================================================
```

**What gets imported:**
- ✅ Skill metadata (name, description, category, scope)
- ✅ All trigger phrases
- ✅ Command type and script content
- ✅ Prerequisites
- ❌ Performance history (starts fresh with 0 uses)
- ❌ Embeddings (regenerated automatically via generate-embeddings.py)

**Important notes:**
1. **New IDs** - Imported skills get new database IDs
2. **Fresh start** - Performance history starts at 0 uses
3. **Regenerate embeddings** - Run `/mem-skills-embeddings` after import
4. **Validate first** - Use `--dry-run` to preview before importing

**Post-import steps:**

```bash
# 1. Import skills
/mem-skills-import backup.json --skip-existing

# 2. Generate embeddings for new triggers
python3 generate-embeddings.py

# 3. Verify imported skills
/mem-skills --format compact

# 4. Test a skill
/mem-skills-execute new-skill --dry-run
```

**Use cases:**
- **Disaster recovery** - Restore from backup after data loss
- **Team sharing** - Import skills created by teammates
- **System migration** - Move skills to new environment
- **Skill libraries** - Import curated skill collections
- **Testing** - Import test skills in sandbox environment

**Safety features:**
- Preview with `--dry-run`
- Confirmation for conflicts (unless --skip-existing or --overwrite)
- Validates JSON format before importing
- Transaction safety (all or nothing per skill)

**Related commands:**
- `/mem-skills-export` - Export skills to JSON
- `python3 generate-embeddings.py` - Generate embeddings after import
- `/mem-skills` - List imported skills

Execute:
python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/import-skill.py "$@"
