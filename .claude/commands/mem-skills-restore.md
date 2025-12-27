Restore soft-deleted skills (skills marked as inactive).

**Command**: `/mem-skills-restore <skill_name>`

**What this does:**
- Restores skills that were soft-deleted (not hard-deleted)
- Reactivates skill and all its triggers/commands
- Does not restore hard-deleted skills (permanently removed)

**Options:**
- `--id ID` - Restore by skill ID instead of name
- `--list` - List all soft-deleted skills
- `--all` - Restore all soft-deleted skills
- `--force` - Skip confirmation prompt

**Examples:**

```bash
# List all soft-deleted skills
/mem-skills-restore --list

# Restore by name
/mem-skills-restore old-skill

# Restore by ID
/mem-skills-restore --id 5

# Restore without confirmation
/mem-skills-restore old-skill --force

# Restore all soft-deleted skills
/mem-skills-restore --all
```

**Output example:**

```
⚠️  You are about to restore:
   ID: 5
   Name: old-skill
   Display: Old Skill Name
   Category: maintenance
   Uses: 10
   Success Rate: 80.0%

   This will mark the skill as active.

Type 'yes' to confirm restore:
```

**What gets restored:**
- Skill record (is_active = TRUE)
- All trigger phrases
- Command definition
- Performance history (preserved from before deletion)

**Limitations:**
- Only works for soft-deleted skills
- Hard-deleted skills cannot be restored
- Use `--list` to see what's available for restoration

**Use cases:**
- **Accidentally deleted** - Restore skills deleted by mistake
- **Seasonal skills** - Reactivate skills needed periodically
- **Testing** - Deactivate during testing, restore after
- **Cleanup mistakes** - Undo overzealous cleanup

**Related commands:**
- `/mem-skills-delete` - Soft delete (mark inactive)
- `/mem-skills-delete --hard` - Hard delete (permanent)
- `/mem-skills` - List active skills

Execute:
python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/restore-skill.py "$@"
