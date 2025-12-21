# Pre-Commit QC Checklist - Phase 6C + Enhancement Feature

## ✅ Files Ready to Commit

### New Files (need `git add`)
- [ ] `enhance-summary.py` - Enhancement script
- [ ] `requirements-enhance.txt` - Python dependencies
- [ ] `README.md` - Updated with enhancement docs

### Modified Files (Phase 6C)
- [ ] `processor/src/summarize.js` - Session-aware summarization
- [ ] `processor/src/storage.js` - getLastSnapshotForProject()
- [ ] `processor/src/capture.js` - Pass metadata to summarizer
- [ ] `auto-capture-current-session.py` - Removed 100-message limit

## ⚠️ Files to EXCLUDE from Commit

### Protected Files (contains secrets or local config)
- [x] `.env` - Contains ANTHROPIC_API_KEY (in .gitignore ✅)
- [ ] `.claude/settings.local.json` - LOCAL MCP configuration

### Files NOT in Repo (user-space)
- [ ] `~/.claude/commands/mem-enhance-summary.md` - Slash command (document installation instead)

## 🔧 Docker Image Status

- [x] Processor code modified: Dec 20 09:40-09:58
- [x] Docker container rebuilt: Dec 20 17:59 (AFTER code changes ✅)
- [x] Running latest code: YES

## 📋 Installation Requirements for Enhancement Feature

Users will need to:
1. Pull repo
2. Run: `pip install -r requirements-enhance.txt`
3. Add `ANTHROPIC_API_KEY` to `.env`
4. Copy slash command: `cp .claude/commands/mem-enhance-summary.md ~/.claude/commands/`

## ❓ Questions to Resolve

1. Should `.claude/settings.local.json` be committed?
   - Currently shows modified
   - Contains local MCP server settings
   - Recommendation: ADD to .gitignore

2. Should slash command be in repo?
   - Currently in ~/.claude/commands/
   - Option A: Keep in repo, document manual copy
   - Option B: Create in ~/.claude/commands/ path in repo
   - Recommendation: Keep `.claude/commands/` dir in repo with README

## 🎯 Recommended Actions Before Commit

1. Add `.claude/settings.local.json` to .gitignore
2. Move slash command to repo: `.claude/commands/mem-enhance-summary.md`
3. Create `.claude/commands/README.md` with installation instructions
4. Stage all Phase 6C files
5. Verify Docker image is current
6. Test one more enhancement to confirm everything works

