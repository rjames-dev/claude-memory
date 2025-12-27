Delete skills from the Skills System (soft or hard delete).

**Command**: `/mem-skills-delete <skill_name>`

**What this does:**
- Removes unwanted skills from the system
- Soft delete (mark inactive) or hard delete (remove from database)
- Supports batch deletion with pattern matching
- Requires confirmation for safety
- Can list matching skills before deletion

**Use cases:**
- **Clean up test skills** - Remove test/experimental skills
- **Remove obsolete skills** - Delete old/unused automations
- **Batch cleanup** - Remove multiple skills at once
- **Deactivate temporarily** - Soft delete to restore later
- **Permanent removal** - Hard delete to free space

**Deletion Types:**

**Soft Delete (Default):**
- Marks skill as inactive (`is_active = FALSE`)
- Skill hidden from normal listings
- Can be restored later (Phase 2)
- Performance history preserved
- Recommended for most use cases

**Hard Delete:**
- Permanently removes from database
- Deletes skill record, triggers, commands, performance logs
- **Cannot be undone**
- Use for test skills or permanent removal

---

## Usage

### Basic Soft Delete
```bash
/mem-skills-delete skill-name
```

You'll be prompted to confirm:
```
⚠️  WARNING: You are about to soft delete:
   ID: 5
   Name: old-skill
   Uses: 3
   Success Rate: 66.7%

   This will mark the skill as inactive.
   The skill can be restored later.

Type 'yes' to confirm soft delete:
```

### Hard Delete (Permanent)
```bash
/mem-skills-delete skill-name --hard
```

Warning:
```
⚠️  WARNING: You are about to HARD DELETE:
   This will PERMANENTLY remove:
   - Skill record
   - All triggers
   - Command definitions
   - Performance logs

   ⚠️  THIS CANNOT BE UNDONE!

Type 'yes' to confirm HARD DELETE:
```

### Delete by ID
```bash
/mem-skills-delete --id 5
```

### Skip Confirmation
```bash
/mem-skills-delete skill-name --force
```

### Batch Delete by Pattern
```bash
/mem-skills-delete --pattern "test-*"
/mem-skills-delete --pattern "old-*" --hard --force
```

### List Before Deleting
```bash
/mem-skills-delete --pattern "test-*" --list-only
```

Output:
```
Found 5 skill(s) matching pattern 'test-*':
  - test-basic (ID: 10)
  - test-advanced (ID: 11)
  - test-integration (ID: 12)
  - test-performance (ID: 13)
  - test-workflow (ID: 14)

(--list-only mode, no deletion performed)
```

---

## Arguments

```
POSITIONAL:
  skill_name              Skill name (e.g., "old-skill")

OPTIONS:
  --id ID                 Delete by skill ID instead of name
  --pattern PATTERN       Delete multiple skills matching pattern (e.g., "test-*")
  --hard                  Hard delete (permanent removal from database)
  --force                 Skip confirmation prompt
  --list-only             List matching skills without deleting (use with --pattern)
```

---

## Examples

### Example 1: Delete Obsolete Skill

```bash
# Soft delete (can be restored later)
/mem-skills-delete old-backup-script
```

Confirm when prompted, and the skill will be marked inactive.

### Example 2: Permanently Remove Test Skill

```bash
# Hard delete test skill
/mem-skills-delete test-experiment --hard
```

Confirm the permanent deletion warning.

### Example 3: Clean Up All Test Skills

```bash
# First, see what would be deleted
/mem-skills-delete --pattern "test-*" --list-only

# Then delete them all
/mem-skills-delete --pattern "test-integration-*" --hard --force
```

Output:
```
Found 8 skill(s) matching pattern 'test-integration-*':
  - test-integration-basic (ID: 5)
  - test-integration-advanced (ID: 6)
  ...

✅ test-integration-basic hard deleted
✅ test-integration-advanced hard deleted
...

================================================================================
Deletion Summary:
  Deleted: 8
================================================================================
```

### Example 4: Remove Failed Skill

```bash
# Delete skill with poor performance
/mem-skills-delete broken-skill --hard
```

### Example 5: Batch Soft Delete

```bash
# Soft delete all "old-*" skills
/mem-skills-delete --pattern "old-*"
```

---

## Confirmation Prompts

### Soft Delete Prompt

```
⚠️  WARNING: You are about to soft delete:
   ID: 5
   Name: old-skill
   Display: Old Skill Name
   Category: maintenance
   Uses: 10
   Success Rate: 80.0%

   This will mark the skill as inactive.
   The skill can be restored later.

Type 'yes' to confirm soft delete:
```

### Hard Delete Prompt

```
⚠️  WARNING: You are about to HARD DELETE:
   ID: 5
   Name: test-skill
   Display: Test Skill
   Category: testing
   Uses: 3
   Success Rate: 100.0%

   This will PERMANENTLY remove:
   - Skill record
   - All triggers
   - Command definitions
   - Performance logs

   ⚠️  THIS CANNOT BE UNDONE!

Type 'yes' to confirm HARD DELETE:
```

### Batch Deletion Prompt

```
⚠️  WARNING: You are about to delete 8 skills
Type 'yes' to confirm HARD DELETE of all skills:
```

---

## What Gets Deleted

### Soft Delete:
- Sets `skills_agents.is_active = FALSE`
- Sets `skills_triggers.is_active = FALSE`
- Sets `skills_commands.is_active = FALSE`
- **Preserves:** All data (can be restored)
- **Effect:** Skill hidden from normal listings

### Hard Delete (Permanent):
Deletes in this order:
1. `skills_performance_log` entries (all execution history)
2. `skills_triggers` records (all trigger phrases)
3. `skills_commands` records (command definitions)
4. `skills_agents` record (skill metadata)

**⚠️ Warning:** Hard delete is permanent and cannot be undone!

---

## Safety Features

1. **Confirmation Required** - Must type "yes" to proceed
2. **--force Override** - Skip confirmation with explicit flag
3. **--list-only** - Preview without deleting
4. **Clear Warnings** - Different warnings for soft vs hard delete
5. **Transaction Safety** - All deletes in single transaction (rollback on error)
6. **Batch Summary** - Shows deletion results

---

## Pattern Matching

Use wildcards to match multiple skills:

**Examples:**
```bash
# All skills starting with "test"
--pattern "test-*"

# All skills ending with "old"
--pattern "*-old"

# All skills containing "backup"
--pattern "*backup*"

# Exact match (same as skill_name)
--pattern "exact-name"
```

**Pattern Syntax:**
- `*` - Matches any number of characters
- `?` - Matches single character
- `[abc]` - Matches any character in brackets
- `[!abc]` - Matches any character not in brackets

---

## Common Use Cases

### Clean Up After Testing

```bash
# List test skills
/mem-skills-delete --pattern "test-*" --list-only

# Delete them permanently
/mem-skills-delete --pattern "test-*" --hard --force
```

### Remove Duplicate Skills

```bash
# Delete old version
/mem-skills-delete old-db-backup --hard

# Keep new version
# (new-db-backup remains)
```

### Deactivate Temporarily

```bash
# Soft delete (can restore later)
/mem-skills-delete seasonal-task
```

### Bulk Cleanup

```bash
# Remove all "experimental" skills
/mem-skills-delete --pattern "experimental-*" --hard
```

---

## Error Handling

**Skill Not Found:**
```
❌ Skill 'nonexistent-skill' not found
```

**No Pattern Matches:**
```
❌ No skills match pattern 'xyz-*'
```

**Database Error:**
```
❌ Database error: [error details]
```

**Deletion Failed:**
```
❌ Failed to delete skill-name
```

**Some Deletions Failed:**
```
================================================================================
Deletion Summary:
  Deleted: 5
  Failed: 2
================================================================================
```

---

## Restoration (Phase 2)

Soft-deleted skills can be restored in Phase 2:

```bash
# (Future feature)
/mem-skills-restore skill-name
```

Hard-deleted skills **cannot** be restored.

---

## Best Practices

1. **Use Soft Delete First** - Try soft delete before hard delete
2. **List Before Deleting** - Use `--list-only` with patterns
3. **Backup Important Skills** - Export skills before hard delete (Phase 2)
4. **Double-Check Patterns** - Verify pattern matches correct skills
5. **Review Performance** - Check if skill is still useful before deleting
6. **Archive Over Delete** - Consider soft delete for historical skills

---

## Alternatives to Deletion

Instead of deleting, consider:

1. **Soft Delete** - Deactivate instead of hard delete
2. **Export** - Backup skill before deleting (Phase 2)
3. **Update** - Modify skill instead of deleting (Phase 2)
4. **Document** - Add note about why skill is obsolete

---

## Security Considerations

- Deletion requires confirmation (unless `--force`)
- Hard delete is permanent - no recovery
- Performance history lost with hard delete
- Soft delete preserves audit trail

---

## Notes

- **Default:** Soft delete (safe, reversible)
- **Hard delete:** Permanent, irreversible
- **Transaction safety:** All deletes in single transaction
- **Pattern matching:** Uses fnmatch (shell-style wildcards)
- **Batch deletion:** Processes multiple skills sequentially
- **Performance logs:** Deleted with hard delete only

---

## Related Commands

- `/mem-skills` - List all skills
- `/mem-skills-info <name>` - View skill details before deleting
- `/mem-skills-create` - Create new skills
- `/mem-skills-restore <name>` - Restore soft-deleted skills (Phase 2)

---

**Example Workflow:**

```bash
# 1. Find obsolete skills
/mem-skills --sort use_count

# 2. View details
/mem-skills-info old-skill

# 3. List similar skills
/mem-skills-delete --pattern "old-*" --list-only

# 4. Soft delete for review
/mem-skills-delete old-skill

# 5. If confirmed obsolete, hard delete
/mem-skills-delete old-skill --hard
```

Execute:
python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/delete-skill.py "$@"
