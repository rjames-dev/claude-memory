Generate a comprehensive, detailed summary for a specific snapshot using Claude Sonnet's full analysis capabilities.

**Command**: `/mem-enhance-summary <snapshot_id>`

**What this does:**
- Fetches the complete raw conversation from database
- Uses Claude Sonnet 4.5 (200k context) instead of Ollama (4k context)
- Generates comprehensive 1500-3000 word summary
- Captures ALL technical details, decisions, and context
- Regenerates embedding from enhanced summary
- Updates database with new summary

**Use cases:**
- **Fix poor-quality summaries** from before Phase 6C
- **Critical work sessions** requiring detailed archival records
- **Complex features** needing comprehensive documentation
- **Production incidents** requiring compliance/audit trails
- **Knowledge transfer** for team onboarding
- **Search not finding details** - enhance summary to improve searchability

**What you get:**
- Complete timeline of work done
- All technical decisions with WHY, not just WHAT
- Every file modified with specific changes
- Code snippets for key solutions
- Dead ends explored (prevents repeating mistakes)
- Dependencies and downstream impacts
- Follow-up items and next steps
- Risks and concerns to watch for

**Cost:**
- ~$0.15-0.25 per enhanced summary (uses your Claude API)
- Only for snapshots you choose - not automatic

**Usage:**
```bash
/mem-enhance-summary 31
```

Or I can help you find which snapshot to enhance:
```bash
/mem-search "topic you need more detail on"
# Find the snapshot ID, then:
/mem-enhance-summary <snapshot_id>
```

**Before/After Example:**

**Before (Ollama standard):**
"Worked on timeout issues. Fixed parser bug. Captured 206 messages."

**After (Claude detailed):**
"## Timeline
1. Diagnosed Ollama timeout after 180s due to 4096 token context limit
2. Analyzed prompt size: 10k tokens attempting to fit in 4k window
3. Implemented two-part solution:
   - Reduced message truncation from 1000 to 500 chars (summarize.js:320)
   - Increased HTTP timeout from 180s to 300s (summarize.js:368)
4. Rebuilt Docker container to test changes
5. Verified: summary generated in 136s (well within 5min limit)

## Technical Decisions
- **Why 500 chars**: Ollama auto-truncates; smaller messages = more messages fit
- **Why 5min timeout**: Ollama takes 2-3min with llama3.2; need headroom
- **Why not larger model**: llama3.2:8k would need different approach

## Files Modified
- processor/src/summarize.js:320 (message char limit)
- processor/src/summarize.js:368 (HTTP timeout)

..." (continues for 2000+ words)

**Arguments:**
- `snapshot_id` (required): The snapshot ID to enhance

Execute:
python3 /Users/jamesmba/Data/00\ GITHUB/Code/claude-memory/enhance-summary.py "$@"

**Note:** This is a POC (Proof of Concept) feature. The enhanced summary will overwrite the existing summary.
