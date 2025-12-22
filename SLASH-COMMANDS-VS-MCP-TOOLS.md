# Slash Commands vs MCP Tools - Understanding the Difference

**Last Updated:** 2025-12-22

---

## The Confusion

Many users expect `/mem-capture`, `/mem-save`, and `/mem-search` to be slash commands you type directly in Claude Code. **These DO NOT exist as slash commands.**

This guide explains what actually exists and how to use each integration method.

---

## What Actually Exists

### 1. **Slash Commands** (Manual, You Type Them)

**Location:** `~/.claude/commands/*.md`

**How They Work:**
- You explicitly type the command in Claude Code
- Example: `/mem-enhance-summary 31`
- Claude executes the script defined in the command file

**Available Commands:**
| Command | Purpose | Usage |
|---------|---------|-------|
| `/mem-enhance-summary <id>` | Generate detailed 1500-3000 word summary using Claude Sonnet 4.5 | `/mem-enhance-summary 21` |

**Installation:**
```bash
mkdir -p ~/.claude/commands
cp .claude/commands/mem-enhance-summary.md ~/.claude/commands/
# Restart Claude Code
```

**After restart:**
- Type `/mem` and press Tab to see available commands
- `/mem-enhance-summary` should appear in autocomplete

---

### 2. **MCP Tools** (Automatic, Claude Uses Them)

**Location:** MCP server process (invoked by Claude Code)

**How They Work:**
- Claude automatically invokes these when relevant to your question
- You DON'T type commands - you just ask Claude naturally
- Example: Ask "What were we working on last week?" → Claude uses `search_memory` tool

**Available MCP Tools:**
| Tool | What Claude Does With It | Example Question |
|------|-------------------------|------------------|
| `search_memory` | Searches past conversations by meaning | "Find that bug fix we did for authentication" |
| `get_timeline` | Shows chronological project history | "Show me the timeline for this project" |
| `get_snapshot` | Retrieves specific snapshot details | "What happened in snapshot 21?" |

**Installation:**
See [MCP-SETUP.md](./MCP-SETUP.md) for full setup.

**How to use:**
- Just ask Claude questions naturally
- Claude decides when to use these tools
- You never type `/mem-search` or similar

---

## The Source of Confusion

### Outdated Documentation (Fixed)

Earlier versions of the README incorrectly suggested these were slash commands:
```
❌ WRONG (outdated docs):
/mem-capture  # Doesn't exist
/mem-save     # Doesn't exist
/mem-search   # Doesn't exist
```

**What Actually Happens:**

**For Search:**
- ❌ You DON'T type: `/mem-search "authentication bug"`
- ✅ You DO ask: "Find that authentication bug we fixed"
- Claude automatically uses the `search_memory` MCP tool

**For Capture:**
- ❌ You DON'T type: `/mem-capture`
- ✅ Auto-capture hooks do this automatically when context fills up
- Or call API directly: `curl -X POST http://localhost:3200/api/capture ...`

---

## Complete Command Reference

### Slash Commands (You Type These)

```bash
# Enhanced summary generation
/mem-enhance-summary 31
```

That's it! Only ONE slash command exists currently.

---

### MCP Tools (Claude Uses These Automatically)

**You ask questions like:**
```
"What were we working on in the authentication module?"
"Show me the timeline for this project"
"Find discussions about performance optimization"
"What happened in snapshot 21?"
```

**Claude automatically uses:**
- `search_memory` for semantic search
- `get_timeline` for project history
- `get_snapshot` for specific snapshot details

**You NEVER type:**
- `/mem-search` ❌
- `/mem-timeline` ❌
- `/mem-snapshot` ❌

---

## How to Tell Which is Which

### Slash Commands
- **You type them explicitly**: `/command-name args`
- **Defined in**: `~/.claude/commands/*.md`
- **Execute scripts**: Python, bash, etc.
- **Example**: `/mem-enhance-summary 31`

### MCP Tools
- **Claude uses them automatically**: You just ask questions
- **Defined in**: MCP server (`mcp-server/src/server.js`)
- **Return data**: JSON responses to Claude
- **Example**: "Find that bug fix" (Claude uses `search_memory` internally)

---

## Installation Quick Reference

### For Slash Commands:
```bash
# One-time setup
mkdir -p ~/.claude/commands
cp .claude/commands/mem-enhance-summary.md ~/.claude/commands/

# Restart Claude Code
# Then use: /mem-enhance-summary <id>
```

### For MCP Tools:
```bash
# See MCP-SETUP.md for full guide
cd mcp-server
npm install
# Configure in Claude Code settings
# Then just ask Claude questions naturally
```

---

## FAQs

### Q: Why don't `/mem-capture` and `/mem-save` commands exist?

**A:** Because capture happens automatically via hooks!

**The workflow:**
1. You work normally in Claude Code
2. Context fills up (~90%)
3. Auto-capture hook triggers
4. Conversation saved to database automatically
5. No command needed!

**If you need manual capture:**
- Use the API directly (see "Manual Capture" in README.md)
- Or create your own slash command if you want

---

### Q: Can I create my own slash commands for capture?

**A:** Yes! Create `~/.claude/commands/mem-capture.md`:

```markdown
Capture current Claude Code session to claude-memory database.

Execute:
curl -X POST http://localhost:3200/api/capture \
  -H "Content-Type: application/json" \
  -d '{"session_id":"$CLAUDE_SESSION_ID","cwd":"$PWD"}'
```

**Note:** You'd need to handle session ID and transcript path properly. The hooks already do this correctly, so it's easier to rely on auto-capture.

---

### Q: Why is `/mem-search` not a slash command?

**A:** Because Claude's MCP integration is better!

**With slash command:**
```
You: /mem-search "authentication bug"
Claude: Here are the results... [shows JSON]
You: Now tell me about result #3
Claude: [needs another /mem-search]
```

**With MCP tools:**
```
You: Find that authentication bug we fixed
Claude: [automatically uses search_memory]
      I found it in snapshot 21. It was a SQL injection fix...
      [can reference the data in natural conversation]
```

MCP tools allow Claude to seamlessly integrate search into the conversation flow.

---

### Q: How do I know if MCP tools are working?

**Method 1: Ask Claude**
```
You: Search my memory for "authentication"
Claude: [If MCP configured] Let me search for that...
        [If MCP NOT configured] I don't have access to search tools
```

**Method 2: Check settings**
```bash
cat ~/.claude/settings.json | grep claude-memory
# Should show MCP server configuration
```

---

### Q: What commands will I actually use day-to-day?

**Most Common:**
- Just ask Claude questions → MCP tools work automatically
- Auto-capture hooks → No commands needed

**Occasionally:**
- `/mem-enhance-summary <id>` → For critical sessions needing detailed summaries

**Rarely:**
- Direct API calls → For custom integrations or debugging

---

## Summary

✅ **What Exists:**
- **1 slash command**: `/mem-enhance-summary <id>`
- **3 MCP tools**: `search_memory`, `get_timeline`, `get_snapshot`
- **Auto-capture**: Hooks capture automatically (no commands)

❌ **What Doesn't Exist:**
- `/mem-capture` - Use auto-capture hooks instead
- `/mem-save` - Use auto-capture hooks instead
- `/mem-search` - Ask Claude questions, MCP tools handle it

✅ **What You Should Do:**
1. Install hooks for auto-capture (Step 6 in README)
2. Install slash commands (Step 7 in README)
3. Optionally set up MCP tools (Step 8 in README)
4. Just use Claude normally - tools work seamlessly!

---

**The key insight:** Most features work automatically or via natural conversation. You rarely need to type explicit commands!
