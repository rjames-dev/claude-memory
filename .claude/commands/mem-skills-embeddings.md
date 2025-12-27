Generate embeddings for skill trigger phrases using Ollama.

**Command**: `/mem-skills-embeddings`

**What this does:**
- Generates 1024-dimensional embeddings for trigger phrases
- Uses Ollama's mxbai-embed-large model
- Stores embeddings in PostgreSQL with pgvector
- Enables semantic search for natural language queries
- Creates HNSW index for fast similarity search

**Options:**
- `--all` - Regenerate all embeddings (overwrite existing)
- `--skill-id ID` - Generate for specific skill only
- `--dry-run` - Preview what would be done

**Examples:**

```bash
# Generate embeddings for triggers that don't have them
/mem-skills-embeddings

# Regenerate all embeddings (overwrite existing)
/mem-skills-embeddings --all

# Generate for specific skill only
/mem-skills-embeddings --skill-id 5

# Preview what would be done
/mem-skills-embeddings --dry-run

# Regenerate all with preview first
/mem-skills-embeddings --all --dry-run
```

**Output example:**

```
Testing Ollama connection...
✅ Connected to Ollama at http://localhost:11434
✅ mxbai-embed-large model available

Fetching triggers...
Found 7 trigger(s) to process:
  - [backup-claude-memory] 'backup database' (no embedding)
  - [check-db-health] 'check database health' (no embedding)
  ...

================================================================================
Generating embeddings...
================================================================================

[1/7] Processing: 'backup database'
   ✅ Generated 1024-dimensional vector
   ✅ Stored in database

[2/7] Processing: 'check database health'
   ✅ Generated 1024-dimensional vector
   ✅ Stored in database

...

================================================================================
Embedding Generation Summary:
  Total triggers: 7
  Success: 7
================================================================================
```

**When to use:**
- **After creating new skills** - Generate embeddings for new triggers
- **After import** - Embeddings are not imported, must regenerate
- **Model upgrade** - When switching to better embedding model
- **Corruption recovery** - If embeddings become corrupted

**Technical details:**
- **Model**: mxbai-embed-large (Ollama)
- **Dimensions**: 1024 (high precision)
- **Storage**: PostgreSQL vector column
- **Index**: HNSW for O(log n) similarity search
- **Search**: Cosine similarity (1 - distance)

**Performance:**
- ~1-2 seconds per trigger phrase
- Batch processing with progress display
- HNSW index automatically updated
- Search queries <100ms after indexing

**Requirements:**
- Ollama running (claude-ollama container)
- mxbai-embed-large model installed
- PostgreSQL with pgvector extension

**Troubleshooting:**

```bash
# Check Ollama status
docker ps | grep ollama

# Check if model is installed
docker exec claude-ollama ollama list | grep mxbai

# Install model if missing
docker exec claude-ollama ollama pull mxbai-embed-large

# Test connection
curl http://localhost:11434/api/tags
```

**Related commands:**
- `/mem-skills-create` - Create new skills (then run this)
- `/mem-skills-import` - Import skills (then run this)
- `/mem-skills-search` - Search using semantic matching

Execute:
python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/generate-embeddings.py "$@"
