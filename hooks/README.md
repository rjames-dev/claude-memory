# Claude Memory - Automatic Capture Hooks

## Overview

This directory contains Claude Code hooks that **automatically capture conversations** before they're compacted, providing seamless memory preservation with zero manual effort.

## What This Does

When you work with Claude Code:

1. **You code normally** - No special commands needed
2. **Context fills up** - Claude's context window reaches capacity (~90% full)
3. **Auto-compact triggers** - Claude Code automatically compacts the conversation
4. **Hook captures BEFORE compact** - PreCompact hook runs first
5. **Conversation saved** - Full conversation sent to claude-memory processor
6. **AI summary generated** - llama3.2 creates 200-300 word summary
7. **Embeddings created** - 384-dim vector for semantic search
8. **Snapshot stored** - Permanently saved in PostgreSQL
9. **Compact proceeds** - Claude Code compacts as normal
10. **You continue working** - With full memory preserved!

## Architecture

```
Claude Code Session
         ↓
   Context fills up (~90%)
         ↓
   Auto-compact triggered
         ↓
┌─────────────────────────────────────┐
│  PreCompact Hook (THIS!)            │
│                                      │
│  1. Read transcript file             │
│  2. Parse messages                   │
│  3. POST /capture to processor       │
│  4. Log event                        │
│  5. Return success message           │
└─────────────────────────────────────┘
         ↓
   Compact proceeds
         ↓
   Fresh context window
         ↓
   (Your memory is safe in database!)
```

## Files

| File | Purpose |
|------|---------|
| `auto-capture-precompact.py` | Main hook script (captures conversation) |
| `setup-hooks.sh` | Installation script for Claude Code |
| `settings.json` | Hook configuration template |
| `README.md` | This file (documentation) |

## Prerequisites

The hook script requires Python 3 with the `requests` library:

```bash
# Install from project root
cd /path/to/claude-memory
pip3 install -r requirements.txt

# Or install manually
pip3 install requests
```

## Installation

### Quick Setup (Recommended)

```bash
cd /path/to/claude-memory/hooks
./setup-hooks.sh
```

This script will:
- ✅ Detect your OS and Claude Code config location
- ✅ Check if processor is running
- ✅ Backup existing settings
- ✅ Merge hooks into your Claude Code configuration
- ✅ Provide instructions for manual merge if needed

### Manual Setup

1. **Copy hook script:**
   ```bash
   cp auto-capture-precompact.py ~/.claude/hooks/
   chmod +x ~/.claude/hooks/auto-capture-precompact.py
   ```

2. **Edit Claude Code settings** (`~/.claude/settings.json`):
   ```json
   {
     "hooks": {
       "PreCompact": [
         {
           "matcher": "auto",
           "hooks": [
             {
               "type": "command",
               "command": "/path/to/claude-memory/hooks/auto-capture-precompact.py",
               "timeout": 10
             }
           ]
         }
       ]
     }
   }
   ```

3. **Restart Claude Code**

## How It Works

### PreCompact Hook

**Triggered when:**
- Context reaches ~90% capacity (auto-compact)
- User manually runs `/compact` command

**What it does:**

1. **Receives hook input** via stdin (JSON):
   ```json
   {
     "session_id": "abc123",
     "transcript_path": "/path/to/transcript.jsonl",
     "cwd": "/current/working/directory",
     "hook_event_name": "PreCompact",
     "trigger": "auto"
   }
   ```

2. **Parses transcript** from `.jsonl` file:
   - Reads all messages (user + assistant)
   - Converts to claude-memory format
   - Extracts conversation history

3. **Sends to processor**:
   ```bash
   POST http://localhost:3200/capture
   {
     "project_path": "/current/working/directory",
     "trigger": "auto-compact-2025-12-14-15-30",
     "conversation_data": {
       "messages": [...]
     }
   }
   ```

4. **Logs result** to `~/.claude/memory-captures.jsonl`

5. **Returns to Claude Code**:
   - Success: "✅ Conversation captured to memory (42 messages) before compact."
   - Failure: "⚠️ Failed to capture conversation: [error]"

### Auto vs. Manual Compact

| Trigger | When | Hook Runs? |
|---------|------|------------|
| **Auto** | Context ~90% full | ✅ Yes - Captures automatically |
| **Manual** | User types `/compact` | ✅ Yes - Captures before manual compact |

Both triggers capture the conversation, ensuring nothing is ever lost!

## Testing

### Test Hook Manually

Create a test transcript:
```bash
cat > /tmp/test-transcript.jsonl << EOF
{"type":"user","content":"Hello, how are you?"}
{"type":"assistant","response":{"content":[{"type":"text","text":"I'm doing well, thank you!"}]}}
EOF
```

Run hook:
```bash
echo '{"transcript_path":"/tmp/test-transcript.jsonl","trigger":"manual","cwd":"/test"}' | \
  /path/to/claude-memory/hooks/auto-capture-precompact.py
```

Expected output:
```json
{
  "systemMessage": "✅ Conversation captured to memory (2 messages) before compact.",
  "hookSpecificOutput": {
    "hookEventName": "PreCompact",
    "additionalContext": "Snapshot created. Trigger: manual"
  }
}
```

### View Capture Log

```bash
# View all captures
cat ~/.claude/memory-captures.jsonl | jq .

# View recent captures
tail -5 ~/.claude/memory-captures.jsonl | jq .

# Count total captures
wc -l ~/.claude/memory-captures.jsonl
```

Example log entry:
```json
{
  "timestamp": "2025-12-14T15:30:45.123456",
  "event": "AUTO_CAPTURE",
  "trigger": "auto",
  "session_id": "abc123",
  "project_path": "/Users/john/projects/my-app",
  "message_count": 42,
  "capture_result": {
    "status": "success",
    "data": {
      "status": "accepted",
      "message": "Context capture initiated"
    }
  }
}
```

### Test End-to-End

1. **Start Claude Code** in any project:
   ```bash
   claude
   ```

2. **Work normally** - Have a conversation

3. **Manually trigger compact** to test:
   ```
   /compact
   ```

4. **Check capture log**:
   ```bash
   tail -1 ~/.claude/memory-captures.jsonl | jq .
   ```

5. **Verify snapshot in database**:
   ```bash
   docker exec claude-context-db psql -U memory_admin -d claude_memory \
     -c "SELECT id, trigger_event, length(summary) FROM context_snapshots ORDER BY id DESC LIMIT 1;"
   ```

## Troubleshooting

### Hook Not Running

**Symptom:** No captures in log after compact

**Solutions:**
1. Check hook is registered:
   ```bash
   cat ~/.claude/settings.json | jq '.hooks.PreCompact'
   ```

2. Verify script is executable:
   ```bash
   ls -l /path/to/auto-capture-precompact.py
   ```

3. Test hook manually (see Testing section)

### Processor Connection Error

**Symptom:** Log shows "Cannot connect to processor"

**Solutions:**
1. Check processor is running:
   ```bash
   curl http://localhost:3200/health
   ```

2. Start docker services:
   ```bash
   cd /path/to/claude-memory
   docker compose up -d
   ```

3. Check logs:
   ```bash
   docker logs claude-context-processor
   ```

### Hook Timeout

**Symptom:** Hook times out after 10 seconds

**Solutions:**
1. Increase timeout in settings.json:
   ```json
   {
     "timeout": 30
   }
   ```

2. Check processor performance:
   ```bash
   docker logs claude-context-processor --tail 50
   ```

### Permission Errors

**Symptom:** "Permission denied" when running hook

**Solutions:**
1. Make script executable:
   ```bash
   chmod +x /path/to/auto-capture-precompact.py
   ```

2. Check Python is available:
   ```bash
   which python3
   ```

## Advanced Configuration

### Custom Processor URL

Set environment variable:
```bash
export CLAUDE_MEMORY_PROCESSOR_URL="http://custom-host:3200"
```

Or modify script directly (line 18):
```python
PROCESSOR_URL = "http://custom-host:3200"
```

### Disable Auto-Capture

Remove PreCompact hooks from `~/.claude/settings.json`:
```json
{
  "hooks": {}
}
```

### Capture Only Auto-Compacts

Change matcher to only "auto":
```json
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "auto",
        "hooks": [...]
      }
    ]
  }
}
```

### Add Additional Processing

Modify `auto-capture-precompact.py` to:
- Send notifications
- Backup transcripts to external storage
- Trigger additional workflows
- Custom logging

## How This Relates to Context Monitoring

### What We Discussed vs. What's Possible

**Original Vision:**
- Monitor context at 10% remaining
- Trigger capture proactively

**Claude Code Reality:**
- Hooks can't access context percentage directly
- PreCompact triggers at ~90% (close enough!)
- This is actually **better** - no manual threshold checking needed

**Why PreCompact Works:**
- Claude Code knows when to compact
- Hook runs BEFORE compact (preserves full context)
- Automatic, zero configuration
- Works for both auto and manual compacts

### Effective Threshold

```
Context Usage:  [████████████████░░] 90%
                                   ↑
                         PreCompact triggers here
```

This is effectively a **10% remaining** threshold, which matches our original design goal!

## Performance

### Hook Execution Time

- Parse transcript: <100ms
- Send to processor: <200ms
- Total: **<300ms overhead**

The compact waits for the hook, but 300ms is imperceptible to users.

### Storage

Capture logs: ~500 bytes per entry
- 1,000 captures = 500 KB
- 10,000 captures = 5 MB

Minimal overhead!

## Security

### What Data is Sent

- ✅ Conversation messages
- ✅ Project path (current directory)
- ✅ Timestamp and trigger type
- ❌ No API keys or credentials
- ❌ No file contents (unless in conversation)

### Network Communication

- Local only (localhost:3200)
- No external connections
- All data stays on your machine

## Next Steps

1. **Install hooks**: Run `./setup-hooks.sh`
2. **Start working**: Use Claude Code normally
3. **Let it auto-capture**: Hooks work invisibly
4. **Search your memory**: Use MCP tools to find past work

---

## Summary

**What you get:**
- 🤖 **Automatic** conversation capture (no commands needed)
- 📊 **AI summaries** of every session (llama3.2)
- 🔍 **Semantic search** through all past work
- 💾 **Zero context cost** (full memory preserved)
- ⚡ **Fast** (<300ms overhead per capture)

**How it works:**
- PreCompact hook triggers when context fills up
- Conversation captured to database automatically
- AI summary and embeddings generated
- Searchable via MCP tools
- Completely transparent to you!

---

*Last updated: 2025-12-14*
