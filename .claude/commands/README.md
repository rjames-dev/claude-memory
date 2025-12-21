# Claude Code Slash Commands

This directory contains custom slash commands for the claude-memory system.

## Installation

Copy these command files to your user's Claude Code commands directory:

```bash
# Copy all commands
cp .claude/commands/*.md ~/.claude/commands/

# Or copy individual commands
cp .claude/commands/mem-enhance-summary.md ~/.claude/commands/
```

## Available Commands

### `/mem-enhance-summary`

Generate comprehensive 1500-3000 word summaries for critical sessions using Claude Sonnet 4.5.

**Usage:**
```
/mem-enhance-summary <snapshot_id>
```

**Prerequisites:**
- Python dependencies: `pip install -r requirements-enhance.txt`
- API key configured in `.env`: `ANTHROPIC_API_KEY='sk-ant-...'`

**Example:**
```
/mem-enhance-summary 21
```

**See:** `mem-enhance-summary.md` for full documentation
