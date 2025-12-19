# Claude Memory System

**Persistent context memory for Claude Code with semantic search, embeddings, and auto-capture**

[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-%23316192.svg?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Node.js](https://img.shields.io/badge/node.js-6DA55F?style=flat&logo=node.js&logoColor=white)](https://nodejs.org/)

---

## Overview

Claude Memory System solves the **context loss problem** in Claude Code by automatically capturing, storing, and making searchable all your development conversations. Think of it as a "shared brain" for your projects that never forgets.

### Key Features

✅ **Zero Context Overhead** - Capture runs out-of-band, uses 0% of your Claude Code window
✅ **Semantic Search** - Find past solutions by meaning using pgvector cosine similarity
✅ **Automatic Capture** - PreCompact and PostCompact hooks trigger auto-saves
✅ **Agent Work Tracking** - Captures agent/subprocess tasks and links to parent sessions
✅ **MCP Tools Integration** - Claude can search your history automatically
✅ **Rich Metadata Extraction** - Tags, files, decisions, bugs, Git state
✅ **AI Summaries** - Ollama generates meaningful summaries of each session
✅ **Vector Embeddings** - sentence-transformers generates 384-dim embeddings
✅ **Project Timeline** - Chronological view of all work sessions
✅ **Portable Configuration** - Environment-based setup, works on any system

---

## Prerequisites

- **Docker & Docker Compose** (v2.0+)
- **Claude Code CLI** (for MCP integration)
- **macOS, Linux, or WSL2** (Windows via WSL)
- **8GB RAM minimum** (16GB recommended for Ollama)
- **5GB disk space** (for Docker images and database)

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/rjames-dev/claude-memory.git
cd claude-memory
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and configure:
nano .env
```

**Required configuration:**
```bash
# Set your workspace root (where Claude Code runs)
CLAUDE_WORKSPACE_ROOT=/Users/yourname/workspace

# Set a secure database password
CONTEXT_DB_PASSWORD=$(openssl rand -base64 32)
```

Or use the setup helper:
```bash
./scripts/setup-env.sh
```

### 3. Start Services

```bash
docker-compose up -d
```

**First-time setup:** Docker will:
- Pull PostgreSQL + pgvector image
- Pull Ollama image
- Build processor service image
- Initialize database schema
- Download Ollama model (llama3.2:latest, ~2GB)

This takes 5-10 minutes depending on your internet connection.

### 4. Verify Installation

```bash
# Check containers are running
docker-compose ps

# Test processor API
curl http://localhost:3200/api/stats

# Expected output:
# {
#   "database": {"status": "connected", "snapshots": 0},
#   "ollama": {"status": "running"},
#   "processor": {"status": "healthy"}
# }
```

### 5. Set Up MCP Tools (Optional)

See [MCP-SETUP.md](./MCP-SETUP.md) for Claude Code integration.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Claude Code Session (Host)                                 │
│  - Runs on your machine                                     │
│  - Transcript files: ~/.claude/projects/.../*.jsonl         │
│  - Hooks: hooks/*.py (trigger on PreCompact/PostCompact)    │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP POST (capture request)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Docker Containers                                          │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Context Processor (Node.js)       Port: 3200      │    │
│  │ - Receives capture requests                       │    │
│  │ - Parses transcript files                         │    │
│  │ - Extracts metadata (tags, files, decisions)      │    │
│  │ - Generates embeddings via sentence-transformers  │    │
│  │ - Stores in PostgreSQL                            │    │
│  └────────────────┬──────────────┬────────────────────┘    │
│                   │              │                          │
│                   │              │                          │
│  ┌────────────────▼──────────┐  │  ┌──────────────────┐   │
│  │ Ollama (AI)   Port: 11434 │  │  │ PostgreSQL       │   │
│  │ - Generates summaries     │  │  │ + pgvector       │   │
│  │ - Model: llama3.2:latest  │  │  │ Port: 5435       │   │
│  └───────────────────────────┘  │  │ - 31 snapshots   │   │
│                                  │  │ - Vector search  │   │
│                                  └─▶│ - HNSW indexing  │   │
│                                     └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                       ▲
                       │ MCP Tools (optional)
┌──────────────────────┴──────────────────────────────────────┐
│  Claude Code MCP Server (Host)                Port: 9001    │
│  - search_memory: Semantic search across conversations      │
│  - get_timeline: Chronological project history              │
│  - get_snapshot: Retrieve specific snapshot details         │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Environment Variables (.env)

All configuration is managed via the `.env` file. See [.env.example](./.env.example) for full documentation.

#### Essential Variables

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `CLAUDE_WORKSPACE_ROOT` | Root directory for Claude Code workspace | `/Users/alice/workspace` | Yes |
| `CONTEXT_DB_PASSWORD` | PostgreSQL database password | `$(openssl rand -base64 32)` | Yes |
| `POSTGRES_HOST_PORT` | Host port for database | `5435` | No (default: 5435) |
| `PROCESSOR_HOST_PORT` | Host port for processor API | `3200` | No (default: 3200) |

#### Optional Customization

| Variable | Description | Default |
|----------|-------------|---------|
| `EMBEDDING_MODEL` | sentence-transformers model | `all-MiniLM-L6-v2` |
| `SUMMARY_MODEL` | Ollama model for summaries | `llama3.2:latest` |
| `LOG_LEVEL` | Logging verbosity | `info` |
| `POSTGRES_SHARED_BUFFERS` | PostgreSQL memory | `256MB` |

### Port Conflicts

If default ports are in use, customize in `.env`:
```bash
POSTGRES_HOST_PORT=5436  # Instead of 5435
PROCESSOR_HOST_PORT=3201 # Instead of 3200
OLLAMA_HOST_PORT=11435   # Instead of 11434
```

---

## Usage

### Automatic Capture (Recommended)

Set up Claude Code hooks to automatically capture sessions:

1. Configure hooks in `~/.claude/settings.json`:
```json
{
  "hooks": {
    "PreCompact": "/path/to/claude-memory/hooks/auto-capture-precompact.py",
    "PostCompact": "/path/to/claude-memory/hooks/post-compact-capture.py"
  }
}
```

2. Work normally in Claude Code
3. When auto-compact triggers, session is automatically saved
4. View captures: `curl http://localhost:3200/api/stats`

See [Phase 6A troubleshooting](./dev-docs/testing/TROUBLESHOOTING-MEM-CAPTURE.md) for common issues.

### Manual Capture

Use MCP tools (if configured):
```
/mem-capture  # Capture current session
/mem-save     # Save and compact current session
```

Or call API directly:
```bash
curl -X POST http://localhost:3200/api/capture \\
  -H "Content-Type: application/json" \\
  -d '{
    "transcript_path": "/Users/alice/.claude/projects/.../{session-uuid}.jsonl",
    "session_id": "{session-uuid}",
    "project_path": "Code/my-project",
    "cwd": "/Users/alice/workspace/Code/my-project"
  }'
```

### Searching Memory

#### Via MCP Tools (In Claude Code)

Ask Claude:
```
"What were we working on last week in the auth system?"
"Find that bug fix we did for SQL injection"
"Show me the timeline for this project"
```

#### Via API

```bash
# Semantic search
curl -X POST http://localhost:3200/api/search \\
  -H "Content-Type: application/json" \\
  -d '{
    "query": "authentication bug fix",
    "limit": 5
  }'

# Get timeline
curl http://localhost:3200/api/timeline?project_path=Code/my-project

# Get snapshot
curl http://localhost:3200/api/snapshot/31
```

#### Via Database (Advanced)

```bash
# Connect to database
docker exec -it claude-context-db psql -U memory_admin -d claude_memory

# Search snapshots
SELECT id, project_path, timestamp, LEFT(summary, 100)
FROM context_snapshots
WHERE project_path LIKE '%my-project%'
ORDER BY timestamp DESC
LIMIT 10;

# Semantic search
SELECT id, summary, 1 - (embedding <=> '[0.1, 0.2, ...]') AS similarity
FROM context_snapshots
WHERE embedding <=> '[0.1, 0.2, ...]' < 0.5
ORDER BY similarity DESC
LIMIT 5;
```

---

## Maintenance

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker logs -f claude-context-processor
docker logs -f claude-context-db
docker logs -f claude-ollama

# Last 100 lines
docker-compose logs --tail=100
```

### Restarting Services

```bash
# Restart all (preserves data)
docker-compose restart

# Restart specific service
docker-compose restart context-processor
```

### Updating Code

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

**Note:** `docker-compose down` (without `-v`) preserves your database data.

### Database Backup

```bash
# Backup database
docker exec claude-context-db pg_dump \\
  -U memory_admin \\
  -d claude_memory \\
  -F c \\
  -f /tmp/backup.dump

docker cp claude-context-db:/tmp/backup.dump ./backups/$(date +%Y%m%d)-backup.dump

# Restore database
docker cp ./backups/20251219-backup.dump claude-context-db:/tmp/restore.dump
docker exec claude-context-db pg_restore \\
  -U memory_admin \\
  -d claude_memory \\
  -c \\
  /tmp/restore.dump
```

### Path Migration

If you move your workspace to a new location:

```bash
# Preview changes (dry run)
./scripts/migrate-paths.sh preview "/old/path" "/new/path"

# Apply migration
./scripts/migrate-paths.sh apply "/old/path" "/new/path"

# Update .env
nano .env  # Update CLAUDE_WORKSPACE_ROOT

# Restart containers
docker-compose restart
```

---

## Troubleshooting

### Containers Won't Start

```bash
# Check logs
docker-compose logs

# Common issues:
# 1. Port conflicts
docker-compose ps  # Check which ports are in use
# Solution: Change ports in .env

# 2. Missing CLAUDE_WORKSPACE_ROOT
grep CLAUDE_WORKSPACE_ROOT .env
# Solution: Add to .env

# 3. Database authentication failed
# Solution: Use original password or remove volume
```

### Capture Fails / Timeouts

See [TROUBLESHOOTING-MEM-CAPTURE.md](./dev-docs/testing/TROUBLESHOOTING-MEM-CAPTURE.md) for detailed troubleshooting.

**Quick fixes:**
- Wait 2-3 minutes for large sessions (don't exit!)
- Check processor logs: `docker logs -f claude-context-processor`
- Verify database: `curl http://localhost:3200/api/stats`

### Empty Summaries / No Metadata

Likely caused by transcript parser bug (fixed in Phase 6A).

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Rebuild containers with fixes
docker-compose down
docker-compose up -d --build
```

### Database Connection Errors

```bash
# Check database is healthy
docker-compose ps

# Test connection
docker exec claude-context-db psql -U memory_admin -d claude_memory -c "SELECT COUNT(*) FROM context_snapshots;"

# Check password matches
grep CONTEXT_DB_PASSWORD .env
# Must match the password used when database was first initialized
```

---

## API Reference

### GET /api/stats

Get system statistics.

**Response:**
```json
{
  "database": {"status": "connected", "snapshots": 31},
  "ollama": {"status": "running", "model": "llama3.2:latest"},
  "processor": {"status": "healthy", "uptime": 1234.5},
  "captures": {"total": 31, "today": 2, "week": 31}
}
```

### POST /api/capture

Capture a conversation snapshot.

**Request:**
```json
{
  "transcript_path": "/path/to/transcript.jsonl",
  "session_id": "uuid",
  "project_path": "Code/project",
  "cwd": "/full/path/to/project"
}
```

**Response:**
```json
{
  "success": true,
  "snapshot_id": 32,
  "messages": 357,
  "tags": ["bug-fix", "security"],
  "files": ["src/auth.js", "test/auth.test.js"]
}
```

### POST /api/search

Semantic search across snapshots.

**Request:**
```json
{
  "query": "authentication bug fix",
  "limit": 5,
  "project_path": "Code/my-project"  // optional
}
```

**Response:**
```json
{
  "results": [
    {
      "id": 28,
      "similarity": 0.87,
      "summary": "Fixed SQL injection vulnerability...",
      "timestamp": "2025-12-18T10:30:00Z",
      "tags": ["security", "bug-fix"]
    }
  ]
}
```

Full API documentation: [dev-docs/architecture/API-REFERENCE.md](./dev-docs/architecture/) (coming soon)

---

## Development

### Project Structure

```
claude-memory/
├── .env                          # Environment configuration (gitignored)
├── .env.example                  # Environment template
├── docker-compose.yml            # Multi-container orchestration
├── README.md                     # This file
├── MCP-SETUP.md                  # MCP tools setup guide
├── processor/                    # Context processing service
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   │   ├── server.js            # Express API server
│   │   ├── capture.js           # Capture logic + progress indicators
│   │   ├── metadata.js          # Metadata extraction
│   │   ├── summarize.js         # Ollama integration
│   │   ├── embed.js             # Embedding generation
│   │   └── storage.js           # PostgreSQL storage + verification
│   └── scripts/
│       └── generate_embedding.py # Python embedding script
├── mcp-server/                   # MCP tools server
│   ├── Dockerfile
│   ├── package.json
│   └── src/server.js
├── schema/                       # Database schema
│   ├── init.sql                 # Base schema + views
│   ├── add-agent-tables.sql     # Agent work tracking
│   ├── add-transcript-path-column.sql
│   └── migrate_project_paths.sql # Path migration function
├── hooks/                        # Claude Code hooks
│   ├── auto-capture-precompact.py  # PreCompact hook (Phase 6A fixed)
│   ├── post-compact-capture.py     # PostCompact hook
│   └── agent_capture.py            # Agent work capture
├── scripts/                      # Utility scripts
│   ├── setup-env.sh             # Environment setup helper
│   ├── init-schema.sh           # Schema initialization
│   ├── migrate-paths.sh         # Path migration (bash)
│   └── migrate-paths.js         # Path migration (node)
└── dev-docs/                     # Internal documentation (gitignored)
    ├── DEV-DOCS-INDEX.md        # Documentation index
    ├── planning/                # Planning documents
    ├── architecture/            # Architecture docs
    ├── implementation/          # Implementation notes
    └── testing/                 # Test results
```

### Running Tests

```bash
# Test capture
node test/capture-request.js

# Test transcript parsing
node test/parse-transcript.js

# Integration test
./scripts/test-full-capture.sh
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and test thoroughly
4. Commit with descriptive messages (see git.md in .claude/rules/)
5. Push to your fork: `git push origin feature/amazing-feature`
6. Open a Pull Request

**Code style:**
- Follow existing patterns in each file
- Add comments for non-obvious logic
- Update documentation for user-facing changes
- Run tests before committing

---

## Data Safety

Your conversation snapshots are precious! The system stores data in Docker named volumes:

**Safe Commands (preserve data):**
```bash
docker-compose restart      # Restart containers, keep data
docker-compose stop         # Stop containers, keep data
docker-compose down         # Remove containers, keep volumes
docker-compose up -d        # Start with existing data
```

**Dangerous Command (deletes ALL snapshots):**
```bash
docker-compose down -v      # ⚠️  DELETES VOLUMES AND ALL DATA!
```

**Best Practices:**
1. Backup database regularly (see Maintenance section)
2. Don't change `CONTEXT_DB_PASSWORD` after initial setup
3. Use `docker-compose down` (not `down -v`) when updating code
4. Test migrations with `dry_run := true` first

---

## License

MIT License - See [LICENSE](./LICENSE) for details

---

## Support

- **Issues:** [GitHub Issues](https://github.com/rjames-dev/claude-memory/issues)
- **Discussions:** [GitHub Discussions](https://github.com/rjames-dev/claude-memory/discussions)
- **Documentation:** [dev-docs/DEV-DOCS-INDEX.md](./dev-docs/DEV-DOCS-INDEX.md)

---

## Acknowledgments

- **pgvector** - Vector similarity search for PostgreSQL
- **sentence-transformers** - Embedding generation
- **Ollama** - Local LLM for summaries
- **Claude Code** - Development environment and hooks system

---

**Last Updated:** 2025-12-19
**Version:** Phase 6B (Portability & Deployment Ready)
**Status:** Production Ready ✅
