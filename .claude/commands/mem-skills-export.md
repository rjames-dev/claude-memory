Export skills to JSON format for backup and sharing.

**Command**: `/mem-skills-export <skill_name> -o output.json`

**What this does:**
- Exports skills to portable JSON format
- Includes triggers, commands, and metadata
- Can export single skill, category, or all skills
- Useful for backup and sharing between systems

**Options:**
- `--id ID` - Export by skill ID instead of name
- `--all` - Export all active skills
- `--category CATEGORY` - Export all skills in category
- `-o FILE, --output FILE` - Output JSON file (default: stdout)
- `--pretty` - Pretty-print JSON output

**Examples:**

```bash
# Export single skill
/mem-skills-export check-db-health -o check-db-health.json

# Export all skills
/mem-skills-export --all -o all-skills.json

# Export by category
/mem-skills-export --category database -o database-skills.json

# Export by ID
/mem-skills-export --id 5 -o skill-5.json

# Export to stdout with pretty formatting
/mem-skills-export check-db-health --pretty

# Export all with pretty formatting
/mem-skills-export --all --pretty -o skills-backup.json
```

**JSON Format:**

```json
{
  "version": "1.0",
  "exported_at": "2025-12-26T10:00:00Z",
  "exported_by": "claude-memory-skills-system",
  "skill_count": 1,
  "skills": [
    {
      "agent_name": "check-db-health",
      "display_name": "Database Health Check",
      "description": "Checks PostgreSQL database health",
      "category": "database",
      "scope": "global",
      "project_path": null,
      "triggers": [
        "check database health",
        "verify database status"
      ],
      "command": {
        "type": "bash_script",
        "content": "#!/bin/bash\n...",
        "prerequisites": {"docker_running": true}
      },
      "metadata": {
        "use_count": 10,
        "success_rate": 95.0,
        "created_at": "2025-12-26T10:00:00Z",
        "updated_at": "2025-12-26T11:00:00Z"
      }
    }
  ]
}
```

**What gets exported:**
- ✅ Skill metadata (name, description, category, scope)
- ✅ All trigger phrases
- ✅ Command type and script content
- ✅ Prerequisites
- ✅ Performance metadata (use count, success rate)
- ❌ Performance logs (not included - too large)
- ❌ Embeddings (regenerated on import)

**Use cases:**
- **Backup** - Regular exports for disaster recovery
- **Sharing** - Share skills between team members
- **Version control** - Track skill changes over time
- **Migration** - Move skills to new system
- **Templates** - Create skill libraries

**Best practices:**
1. **Regular backups** - Export all skills weekly
2. **Category backups** - Export by category for organization
3. **Version control** - Commit exports to git (scripts only, no credentials)
4. **Documentation** - Include export date and purpose

**Related commands:**
- `/mem-skills-import` - Import skills from JSON
- `/mem-skills` - List all skills before exporting

Execute:
python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/export-skill.py "$@"
