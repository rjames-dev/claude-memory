Search for skills using natural language semantic matching.

**Command**: `/mem-skills-search <query>`

**What this does:**
- Finds relevant skills using semantic similarity (AI embeddings)
- Matches natural language queries to trigger phrases
- No need for exact keyword matches
- Returns skills ranked by relevance

**Examples:**

```bash
# Find database connection help
/mem-skills-search "I need the database password"
# Result: show-db-connection (86% match)

# Find health check tools
/mem-skills-search "is the database healthy"
# Result: check-db-health (84% match)

# Find backup tools
/mem-skills-search "make a backup of the data"
# Result: backup-claude-memory (83% match)

# Broader search
/mem-skills-search "database" --threshold 0.6
# Results: All database-related skills
```

**Options:**
- `--threshold FLOAT` - Minimum similarity score (0.0-1.0, default: 0.7)
- `--limit N` - Maximum results (default: 5)
- `--show-scores` - Display similarity percentages

**Similarity Levels:**
- 90-100%: 🎯 Excellent match (nearly identical)
- 80-90%:  ✅ Very good match (very similar)
- 70-80%:  👍 Good match (similar)
- 60-70%:  👌 Acceptable match (somewhat similar)

**Use cases:**
- **Forgot exact command** - "how do I check database health?"
- **Discover skills** - "what backup tools are available?"
- **Natural language** - "I need database credentials"
- **Fuzzy matching** - "db password" matches "show database connection"

Execute:
python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/search-skills-semantic.py "$@"
