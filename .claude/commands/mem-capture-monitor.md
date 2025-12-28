---
difficulty: 1
dependencies:
  - docker-compose.yml
  - auto-capture-current-session.py
  - monitor-capture-progress.py
---

# /mem-capture-monitor

Capture current session and monitor progress in one command.

**Command**: `/mem-capture-monitor`

**What this does:**
1. Captures current Claude Code session to database
2. Immediately monitors capture progress with real-time updates
3. Shows when safe to close Claude Code

**Combined workflow:**
- Detects and captures current session (auto-capture-current-session.py)
- Polls database every 5 seconds for completion
- Displays progress stages:
  - 🔄 Processing summary...
  - 🔄 Generating embeddings...
  - ✅ Capture complete!
- Shows final snapshot details and quality score

**Usage:**
Simply run this command - everything is automatic!

Execute:
python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/capture-and-monitor.py

**Example output:**
```
🔍 Claude Memory - Auto-Capture Current Session
============================================================
✅ Found active session: 12cd285c...
✅ Loaded 77 conversation messages
✅ Context capture initiated
⏳ Processing in background...

🔍 Monitoring capture progress...

🔄 Processing summary... (15s elapsed)
   Last check: 2025-12-27 20:15:32
   Snapshot ID: 35

🔄 Generating embeddings... (38s elapsed)
   Last check: 2025-12-27 20:15:55

✅ Capture complete! (67s total)

📋 Snapshot Details:
   ID: 35
   Messages: 77
   Summary: 412 words (2061 chars)
   Tags: 10 extracted
   Files: 17 mentioned
   Quality Score: 8.5/10

✅ Safe to close Claude Code!

To enhance this summary with Claude Sonnet:
   /mem-capture-monitor 35
```

**When to use:**
- End of work session (most common)
- Before manual compact
- After important discussions
- When you want to preserve work AND see completion status

**Alternative commands:**
- `/mem-capture` - Capture only (no monitoring)
- `python3 monitor-capture-progress.py` - Monitor only (after manual capture)

**Timeout:**
- Default: 180 seconds (3 minutes)
- Adjust if needed: Add `--timeout 300` to monitor command

**Background vs Foreground:**
- This command runs monitoring in **foreground** (blocks until complete)
- Use `/mem-capture` if you want to capture and continue working immediately
