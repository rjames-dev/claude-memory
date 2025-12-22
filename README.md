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
✅ **Two-Tier AI Summaries** - Free Ollama summaries + Premium Claude enhancements
✅ **Vector Embeddings** - sentence-transformers generates 384-dim embeddings
✅ **Project Timeline** - Chronological view of all work sessions
✅ **Portable Configuration** - Environment-based setup, works on any system

---

## Prerequisites

### Required

- **Docker Desktop** (v4.0+)
  - Download: https://www.docker.com/products/docker-desktop
  - Includes Docker Compose v2
  - **For Apple Silicon (M1/M2/M3/M4):** See configuration notes below
- **Node.js v18+** (for MCP tools only)
  - Download: https://nodejs.org/
  - Check version: `node --version`
  - **Not required** for basic capture/hooks - only needed if you want MCP search tools
- **Claude Code CLI** (recommended)
  - Installation: https://claude.ai/download
  - Required for: MCP tools, auto-capture hooks
  - Not required for: Manual API-based capture

### System Requirements

- **macOS, Linux, or WSL2** (Windows via WSL)
- **8GB RAM minimum** (16GB+ recommended)
- **5GB disk space** (for Docker images and database)

### Apple Silicon (M1/M2/M3/M4) Configuration

**Important:** Docker Desktop on Apple Silicon needs more memory for Ollama.

1. **Open Docker Desktop** → Settings → Resources
2. **Increase Memory:**
   - **Minimum:** 6GB (basic functionality)
   - **Recommended:** 8GB (smooth Ollama performance)
   - **Optimal:** 12GB (multiple models, no slowdowns)
3. **CPU:** 4 cores recommended
4. **Click "Apply & Restart"**

**Why?** Ollama (llama3.2:latest) needs ~4GB for model + inference. With default 2GB Docker allocation, captures will be very slow or fail.

**Alternative:** If you don't need AI summaries, set `USE_AI_SUMMARIES=false` in `.env` to skip Ollama entirely

---

## Quick Start

**Installation Checklist:**
```markdown
□ Prerequisites verified (Docker, Node.js if using MCP)
□ Cloned repository to permanent location
□ Configured .env (CLAUDE_WORKSPACE_ROOT + password)
□ Started Docker containers
□ Verified installation (API responds)
□ Configure auto-capture hooks (REQUIRED for automatic capture feature)
□ (Optional) Set up MCP search tools
```

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
# This is the parent directory of your projects
CLAUDE_WORKSPACE_ROOT=/Users/yourname/workspace

# Set a secure database password
CONTEXT_DB_PASSWORD=$(openssl rand -base64 32)
```

**Workspace Path Examples:**

| Your Setup | CLAUDE_WORKSPACE_ROOT Example |
|------------|-------------------------------|
| Projects in `~/Code/` | `/Users/yourname/Code` |
| Projects in `~/workspace/` | `/Users/yourname/workspace` |
| Projects in `~/Documents/Projects/` | `/Users/yourname/Documents/Projects` |
| Multiple roots? | Use the common parent (e.g., `/Users/yourname`) |

**How to find your workspace root:**
```bash
# Navigate to where you run Claude Code
cd ~/Code/my-project  # or wherever you work

# Print parent directory
pwd | sed 's|/[^/]*$||'
# Example output: /Users/yourname/Code
# Use this as CLAUDE_WORKSPACE_ROOT
```

Or use the setup helper (auto-detects):
```bash
./scripts/setup-env.sh
```

### 3. Start Services

```bash
docker-compose up -d
```

**First-time setup:** Docker will:
- Pull PostgreSQL + pgvector image (~300MB)
- Pull Ollama image (~1GB)
- Build processor service image (~2GB with dependencies)
- Initialize database schema
- Download Ollama model (llama3.2:latest, ~2GB)

**Total download:** ~5GB | **Time:** 5-15 minutes (varies by connection speed)

**Apple Silicon users:** First-time Ollama model download can take 10-20 minutes. Be patient!

**Watch progress:**
```bash
# Monitor Ollama downloading the model
docker logs -f claude-ollama
# Press Ctrl+C to stop viewing logs (containers keep running)
```

**Expected output during first-time setup:**
```
Pulling ollama (ollama/ollama:latest)...
latest: Pulling from ollama/ollama
[====>                                              ]  234.5MB/1.2GB

# After containers start, Ollama downloads model:
pulling manifest
pulling 8eeb52dfb3bb... 100% ▕████████████████▏ 1.3 GB
pulling 73b313b5552d... 100% ▕████████████████▏  11 KB
pulling 0ba8f0e314b4... 100% ▕████████████████▏  12 KB
pulling 56bb8bd477a5... 100% ▕████████████████▏  96 B
pulling 1a4c3c319823... 100% ▕████████████████▏ 485 B
verifying sha256 digest
writing manifest
success  # ← Model ready!
```

**This is normal!** Don't interrupt. Wait for "success" message.

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

### 5. Set Up Automatic Capture (Required for Key Feature)

**⚠️ IMPORTANT:** The "Automatic Capture" feature (highlighted in the features list above) requires configuring hooks. Without this step, captures will only work via manual API calls.

#### Quick Hook Setup (2 minutes)

```bash
cd hooks
./setup-hooks.sh
```

This script will:
- ✅ Detect your OS and Claude Code config location
- ✅ Check if processor is running
- ✅ Backup existing settings
- ✅ Configure PreCompact hook in `~/.claude/settings.json`

**After setup:**
- Work normally in Claude Code
- When context fills up (~90%), conversations automatically save to memory
- Zero manual effort required!

**Detailed instructions:** See [hooks/README.md](./hooks/README.md)

---

### 6. Optional Integrations

You can enhance claude-memory with these additional integrations:

| Integration | What It Does | Setup Required | Best For |
|-------------|--------------|----------------|----------|
| **MCP Search Tools** | Let Claude search your memory from within conversations | Install MCP server + configure | Interactive memory queries |
| **Manual API Calls** | Call capture API directly | None (just Docker running) | Custom integrations, scripts |

**Setup guides:**
- **MCP Tools:** See [MCP-SETUP.md](./MCP-SETUP.md)
- **API:** See "API Reference" section below

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

### Automatic Capture (Default Workflow)

If you completed Step 5 (hook setup), automatic capture is already working!

**How it works:**
1. Work normally in Claude Code (no special commands needed)
2. When context fills up (~90%), PreCompact hook automatically triggers
3. Conversation is captured, summarized, and stored in the database
4. Continue working with full memory preserved

**Verify it's working:**
```bash
# Check recent captures
curl http://localhost:3200/api/stats

# View capture log
tail -5 ~/.claude/memory-captures.jsonl | jq .
```

**If hooks aren't set up yet:** See Step 5 in the Quick Start section above, or [hooks/README.md](./hooks/README.md) for detailed instructions.

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

### Enhanced Summaries (Premium Feature)

Generate comprehensive 1500-3000 word summaries for critical sessions using Claude Sonnet 4.5:

#### Setup

1. Install Python dependencies:
```bash
pip install -r requirements-enhance.txt
```

2. Configure API key in `.env`:
```bash
echo "ANTHROPIC_API_KEY='sk-ant-...'" >> .env
```

#### Usage

```bash
# Via slash command (recommended)
/mem-enhance-summary <snapshot_id>

# Or direct script
python3 enhance-summary.py <snapshot_id>
```

**Example:**
```bash
# Enhance snapshot #21
/mem-enhance-summary 21

# Output:
# ✅ Enhanced summary generated (14,992 chars)
# ✅ Embedding regenerated (384 dimensions)
# ✅ Database updated
#
# Before: 329 chars
# After:  14,992 chars
# Improvement: +14,663 chars
```

#### When to Use

- **Fix poor-quality summaries** from before Phase 6C improvements
- **Critical work sessions** requiring detailed archival records
- **Complex features** needing comprehensive documentation
- **Production incidents** requiring compliance/audit trails
- **Knowledge transfer** for team onboarding
- **Search not finding details** - enhance summary to improve searchability

#### Cost & Performance

- **Cost:** ~$0.12-0.25 per enhanced summary (uses Claude Sonnet 4.5 API)
- **Time:** 10-20 seconds per summary
- **Quality:** 10-45x more detailed than standard Ollama summaries
- **On-demand:** Only enhance snapshots you choose

#### Two-Tier Summary Architecture

| Feature | Standard (Ollama) | Enhanced (Claude) |
|---------|------------------|-------------------|
| **Cost** | Free | ~$0.12-0.25 each |
| **Trigger** | Automatic | On-demand |
| **Length** | 400 words | 1500-3000 words |
| **Model** | llama3.2 | claude-sonnet-4-5 |
| **Use Case** | All captures | Critical sessions |
| **Context** | 4k tokens | 200k tokens |

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

### Apple Silicon (M1/M2/M3/M4) Specific Issues

#### Capture Takes Forever / Timeouts

**Symptom:** Captures take 5+ minutes or timeout entirely

**Cause:** Docker Desktop has insufficient memory for Ollama

**Solution:**
```bash
# 1. Stop containers
docker-compose down

# 2. Increase Docker memory allocation:
#    Docker Desktop → Settings → Resources → Memory
#    Set to 8GB minimum (12GB recommended)

# 3. Apply & Restart Docker Desktop

# 4. Start containers
docker-compose up -d

# 5. Wait for Ollama to fully start (can take 2-3 minutes)
docker logs -f claude-ollama
# Look for: "llama server listening"
```

#### Ollama Crashes or Fails to Start

**Symptom:** `docker logs claude-ollama` shows crashes or out of memory errors

**Quick Fix - Disable AI Summaries:**
```bash
# Edit .env
nano .env

# Add or change this line:
USE_AI_SUMMARIES=false

# Restart
docker-compose restart
```

**This disables Ollama** but capture still works (without AI summaries). Metadata extraction, embeddings, and search all continue working normally.

#### Node.js Not Required for Basic Use

**Note:** You don't need Node.js installed on your host machine. The processor service runs entirely in Docker. Node.js is only needed if you want to:
- Run migration scripts locally (can also use bash versions)
- Develop/modify the processor service
- Run local tests

For normal use, Docker is all you need!

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
