Edit existing skills - update metadata, triggers, and script content.

**Command**: `/mem-skills-edit <skill_name> [options]`

**What this does:**
- Modify skill metadata (name, description, category)
- Update script content
- Add or remove trigger phrases
- Preview changes before applying

**Options:**
- `--display-name NAME` - Update display name
- `--description DESC` - Update description
- `--category CATEGORY` - Update category
- `--script-content CONTENT` - Update script content
- `--add-trigger TRIGGER` - Add new trigger phrase
- `--remove-trigger TRIGGER` - Remove trigger phrase
- `--dry-run` - Preview changes without applying
- `--id ID` - Edit by skill ID instead of name

**Examples:**

```bash
# Update description
/mem-skills-edit check-db-health --description "Comprehensive database health monitoring"

# Change category
/mem-skills-edit backup-claude-memory --category backup

# Add trigger phrase
/mem-skills-edit check-db-health --add-trigger "is database ok"

# Remove trigger phrase
/mem-skills-edit check-db-health --remove-trigger "verify database status"

# Multiple changes at once
/mem-skills-edit check-db-health \
  --display-name "DB Health Monitor" \
  --add-trigger "monitor database"

# Preview changes first
/mem-skills-edit check-db-health \
  --description "New description" \
  --dry-run

# Edit by ID
/mem-skills-edit --id 2 --description "Updated description"

# Update script content
/mem-skills-edit check-db-health \
  --script-content "#!/bin/bash
echo 'New script content here'"
```

**Safety features:**
- Confirmation required before applying changes
- `--dry-run` to preview changes
- Cannot remove last trigger (skill must have at least one)
- Displays before/after comparison

**Use cases:**
- **Improve triggers** - Add natural language variations
- **Fix scripts** - Update broken or outdated script content
- **Reorganize** - Change categories as system evolves
- **Enhance descriptions** - Make skills more discoverable

Execute:
python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/edit-skill.py "$@"
